"""Signal-aware runner support and CPU-only campaign process supervision."""
import argparse
import contextlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from .characterization import write_json


class ExecutionSignal(BaseException):
    def __init__(self, signum):
        self.signum = signum
        super().__init__(signal.Signals(signum).name)


def termination_reason(exc):
    if isinstance(exc, ExecutionSignal):
        return signal.Signals(exc.signum).name
    if isinstance(exc, KeyboardInterrupt):
        return 'SIGINT'
    return 'PYTHON_EXCEPTION'


@contextlib.contextmanager
def capture_signals():
    old = {}
    def handler(signum, frame):
        # Allow status writing to finish; the external supervisor escalates if stuck.
        for sig in old:
            signal.signal(sig, signal.SIG_IGN)
        raise ExecutionSignal(signum)
    try:
        for sig in (signal.SIGTERM, signal.SIGINT):
            old[sig] = signal.signal(sig, handler)
        yield
    finally:
        for sig, value in old.items():
            signal.signal(sig, value)


def emit_progress(directory, run, steps, started, phase, last_output=None):
    event = {'run_id':run.get('run_id', directory.name), 'env_id':run['env_id'],
             'protocol':run['protocol'], 'seed':run['seed'], 'randomize':run['randomize'],
             'completed_steps':steps, 'wall_seconds':time.monotonic()-started,
             'phase':phase, 'last_successful_output':last_output}
    with (directory/'progress.jsonl').open('a', buffering=1) as stream:
        stream.write(json.dumps(event)+'\n')
    print(json.dumps(event), flush=True)


def recover_statuses(campaign, output, reason):
    """Sidecar only: never edit existing artifacts, even interrupted ones."""
    rows = []
    if campaign.exists():
        for d in sorted(p for p in campaign.iterdir() if p.is_dir()):
            if not (d/'request.json').exists():
                continue
            terminal = d/'status.json'
            if terminal.exists():
                rows.append({'run_id':d.name, 'terminal':json.loads(terminal.read_text()), 'source':'runner'})
                continue
            last = None
            if (d/'trajectory.jsonl').exists():
                with (d/'trajectory.jsonl').open() as stream:
                    for line in stream:
                        try: last = json.loads(line)
                        except json.JSONDecodeError: break
            progress = None
            if (d/'progress.jsonl').exists():
                try: progress = json.loads((d/'progress.jsonl').read_text().splitlines()[-1])
                except (ValueError,IndexError): pass
            rows.append({'run_id':d.name,'status':'interrupted','reason':reason,
                         'last_progress':progress,
                         'request':json.loads((d/'request.json').read_text()),
                         'completed_steps':0 if last is None else last['step'],
                         'last_successful_output':None if last is None else str(d/'trajectory.jsonl'),
                         'source':'supervisor recovery; not a complete trajectory'})
    write_json(output, {'runs':rows})


def supervise(command, output, wall_seconds=259200, grace_seconds=60, heartbeat=30, telemetry=True):
    if wall_seconds <= 0 or grace_seconds <= 0 or grace_seconds >= wall_seconds or heartbeat <= 0:
        raise ValueError('require wall > grace > 0 and heartbeat > 0')
    output = Path(output)
    # Caller supplies a new execution namespace. Refuse repeated supervision.
    write_json(output/'launch.json', {'command':command, 'wall_seconds':wall_seconds,
               'grace_seconds':grace_seconds, 'supervisor_pid':os.getpid(),
               'started_unix':time.time(), 'device_telemetry':'device-wide, includes other processes'})
    pending = []
    old = {}
    for sig in (signal.SIGINT,signal.SIGTERM):
        old[sig] = signal.signal(sig, lambda s,f: pending.append(s))
    def announce(message):
        # No shell tee child: terminal INT must not destroy the logging pipe.
        with (output/'launcher.log').open('a',buffering=1) as stream:
            stream.write(message+'\n')
        try:
            print(message,flush=True)
        except BrokenPipeError:
            pass
    started = time.monotonic()
    process = monitor = None
    reason = None
    kill_at = None
    kill_sent = False
    try:
        with (output/'run.log').open('x',buffering=1) as log, (output/'gpu.csv').open('x') as gpu, (output/'gpu-monitor-errors.log').open('x') as gpu_errors:
            if telemetry:
                try:
                    monitor = subprocess.Popen(['nvidia-smi','--query-gpu=timestamp,uuid,memory.used,memory.total,utilization.gpu',
                                                '--format=csv','-l','5'],stdout=gpu,stderr=gpu_errors,start_new_session=True)
                except OSError as exc:
                    gpu_errors.write(str(exc)+'\n')
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            write_json(output/'child.json', {'pid':process.pid,'pgid':process.pid})
            next_heartbeat = 0
            while process.poll() is None:
                now = time.monotonic()
                if reason is None and (pending or now-started >= max(0,wall_seconds-grace_seconds)):
                    signum = pending[0] if pending else signal.SIGTERM
                    reason = signal.Signals(signum).name if pending else 'TIMEOUT'
                    kill_at = now+grace_seconds
                    write_json(output/'stop-request.json', {'reason':reason,'signal':signum,'elapsed':now-started})
                    try: os.killpg(process.pid,signum)
                    except ProcessLookupError: pass
                if kill_at is not None and now >= kill_at and not kill_sent:
                    try: os.killpg(process.pid,signal.SIGKILL)
                    except ProcessLookupError: pass
                    kill_sent = True
                if now >= next_heartbeat:
                    progress = None
                    candidates = list((output/'campaign').glob('*/progress.jsonl'))
                    if candidates:
                        try:
                            latest = max(candidates,key=lambda p:p.stat().st_mtime)
                            progress = json.loads(latest.read_text().splitlines()[-1])
                        except (OSError,ValueError,IndexError):
                            pass
                    announce(json.dumps({'event':'heartbeat','elapsed_seconds':round(now-started,1),
                                      'pid':process.pid,'last_progress':progress,
                                      'note':'last persisted progress; does not certify solver liveness'}))
                    next_heartbeat = now+heartbeat
                time.sleep(.1)
            rc = process.wait()
            if reason is None:
                reason = ('SUCCESS' if rc == 0 else
                          signal.Signals(-rc).name if rc < 0 else 'NONZERO_EXIT_UNKNOWN')
            campaign_status = output/'campaign/status.json'
            if rc > 0 and reason == 'NONZERO_EXIT_UNKNOWN' and campaign_status.exists():
                reason = json.loads(campaign_status.read_text()).get('termination_reason',reason)
            write_json(output/'execution-status.json', {'status':'complete' if rc == 0 and reason == 'SUCCESS' else 'interrupted' if reason != 'PYTHON_EXCEPTION' else 'failed',
                       'reason':reason,'child_returncode':rc,'kill_sent':kill_sent,
                       'wall_seconds':time.monotonic()-started,'finished_unix':time.time()})
            recover_statuses(output/'campaign',output/'recovered-run-statuses.json',reason)
            announce(f'Campaign stopped: {reason}, returncode={rc}; {output}')
            return 0 if rc == 0 and reason == 'SUCCESS' else 1
    except BaseException as exc:
        if not (output/'execution-status.json').exists():
            write_json(output/'execution-status.json', {'status':'failed', 'reason':'SUPERVISOR_EXCEPTION',
                       'error_type':type(exc).__name__, 'error':str(exc), 'wall_seconds':time.monotonic()-started})
        raise
    finally:
        if process is not None and process.poll() is None:
            try: os.killpg(process.pid,signal.SIGTERM)
            except ProcessLookupError: pass
            try: process.wait(timeout=grace_seconds)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid,signal.SIGKILL)
                process.wait()
        if monitor is not None:
            try: os.killpg(monitor.pid,signal.SIGTERM)
            except ProcessLookupError: pass
            try: monitor.wait(timeout=2)
            except subprocess.TimeoutExpired:
                os.killpg(monitor.pid,signal.SIGKILL)
                monitor.wait()
        if process is not None and process.poll() is not None and not (output/'recovered-run-statuses.json').exists():
            recover_statuses(output/'campaign',output/'recovered-run-statuses.json','SUPERVISOR_EXCEPTION')
        write_json(output/'telemetry-status.json', {'enabled':telemetry,
                   'monitor_returncode':None if monitor is None else monitor.returncode,
                   'note':'GPU samples are device-wide, not PyTorch allocator peaks; gaps/errors must be reviewed.'})
        for sig,value in old.items(): signal.signal(sig,value)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--output', required=True)
    p.add_argument('--wall-seconds',type=float,default=259200)
    p.add_argument('--grace-seconds',type=float,default=60)
    p.add_argument('--no-telemetry',action='store_true')
    p.add_argument('command',nargs=argparse.REMAINDER)
    a=p.parse_args()
    command=a.command[1:] if a.command[:1]==['--'] else a.command
    if not command: p.error('child command required')
    return supervise(command,a.output,a.wall_seconds,a.grace_seconds,telemetry=not a.no_telemetry)


if __name__ == '__main__':
    sys.exit(main())
