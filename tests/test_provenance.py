import json
import pytest
from fluidgym_physics.provenance import SCHEMA_VERSION, ProvenanceRecord, build_record


def test_record_roundtrip_and_no_overwrite(tmp_path):
    rec = build_record({"env_id": "x"}, {"dt": None}, "static_source")
    p = rec.write(tmp_path / "p.json")
    d = json.loads(p.read_text())
    assert d["schema_version"] == SCHEMA_VERSION and d["upstream"]["dirty"] is False
    with pytest.raises(FileExistsError):
        rec.write(p)


def test_bad_level():
    rec = build_record({}, {}, "static_source")
    rec.execution_level = "mock"
    with pytest.raises(ValueError):
        rec.validate()
