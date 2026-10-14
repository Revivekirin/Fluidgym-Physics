import pytest
from fluidgym_physics.errors import UpstreamIntegrityError
from fluidgym_physics.upstream import UpstreamLock, inspect_checkout, read_lock, verify_upstream


def test_lock_parses():
    lock = read_lock()
    assert lock.url.endswith("safe-autonomous-systems/fluidgym")
    assert len(lock.commit) == 40
    assert lock.pinned_deps["torch"] == "==2.9.*"


def test_checkout_matches_lock_and_is_clean():
    info = verify_upstream()
    assert info["dirty"] is False


def test_mismatch_is_detected():
    lock = read_lock()
    bad = UpstreamLock(lock.url, "0" * 40, lock.src_tree, lock.describe, lock.pinned_deps)
    with pytest.raises(UpstreamIntegrityError, match="commit"):
        verify_upstream(bad)


def test_missing_checkout(tmp_path):
    with pytest.raises(UpstreamIntegrityError):
        inspect_checkout(tmp_path)
