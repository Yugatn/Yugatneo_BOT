import hashlib
import json
from amalgama.guardian import verify_manifest


def digest(data):
    return hashlib.sha256(data).hexdigest()


def test_guardian_detects_agent_change(tmp_path):
    agent = tmp_path / "agent.py"
    agent.write_bytes(b"safe")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"schema": 1, "agents": [
        {"path": "agent.py", "sha256": digest(b"safe")}
    ]}), encoding="utf-8")
    trusted = digest(manifest.read_bytes())
    assert verify_manifest(manifest, trusted, tmp_path)["status"] == "verified"
    agent.write_bytes(b"modified")
    assert verify_manifest(manifest, trusted, tmp_path)["mismatches"] == ["agent.py"]


def test_guardian_rejects_modified_manifest(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"schema":1,"agents":[]}')
    trusted = digest(manifest.read_bytes())
    manifest.write_text('{"schema":1,"agents":[{}]}')
    assert verify_manifest(manifest, trusted, tmp_path)["status"] == "untrusted_manifest"


def test_guardian_rejects_path_escape(tmp_path):
    import pytest
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"schema": 1, "agents": [
        {"path": "../outside", "sha256": digest(b"test")}
    ]}))
    with pytest.raises(ValueError):
        verify_manifest(manifest, digest(manifest.read_bytes()), tmp_path)
