import numpy as np
import pytest
from fluidgym_physics.audit import validate_snapshot, verify_recorded_hashes
from fluidgym_physics.characterization import digest


def test_recorded_hash_detects_missing_and_changed_bytes(tmp_path):
    p=tmp_path/'data';p.write_bytes(b'original')
    status={'sha256':{'data':digest(p),'missing':'0'*64}}
    p.write_bytes(b'changed')
    count,errors=verify_recorded_hashes(tmp_path,status)
    assert count==1
    assert len(errors)==2
    assert any('hash mismatch' in e for e in errors)
    assert any('missing:' in e for e in errors)


@pytest.mark.parametrize('bad', ['nan','shape','dtype','extra'])
def test_snapshot_rejects_invalid_field(tmp_path,bad):
    a=np.ones((2,3),dtype='float32'); values={'pressure':a}
    if bad=='nan':a[0,0]=np.nan
    if bad=='shape':values['pressure']=a[:1]
    if bad=='dtype':values['pressure']=a.astype('float64')
    if bad=='extra':values['extra']=a
    p=tmp_path/'fields.npz';np.savez(p,**values)
    with pytest.raises(ValueError):validate_snapshot(p,{'pressure':{'shape':[2,3],'dtype':'float32'}})


def test_snapshot_reports_values_without_mutation(tmp_path):
    p=tmp_path/'fields.npz';np.savez(p,pressure=np.array([[1.,2.]],dtype='float32'))
    before=digest(p)
    assert validate_snapshot(p,{'pressure':{'shape':[1,2],'dtype':'float32'}})=={'pressure':[1.,2.]}
    assert digest(p)==before
