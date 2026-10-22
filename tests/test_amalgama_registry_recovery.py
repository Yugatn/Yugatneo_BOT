import hashlib
import json
import pytest
from amalgama.registry import RegistryError, load_registry, attest_agents
from amalgama.recovery import plan_recovery


def digest(data):
    return hashlib.sha256(data).hexdigest()


def make_registry(tmp_path, entries):
    path = tmp_path / "registry.json"
    path.write_text(json.dumps({"schema": 1, "agents": entries}), encoding="utf-8")
    return path, digest(path.read_bytes())


def test_attestation_and_recovery_plan(tmp_path):
    agent = tmp_path / "agent.py"
    agent.write_bytes(b"trusted")
    path, anchor = make_registry(tmp_path, [{"id": "watcher", "path": "agent.py", "sha256": digest(b"trusted"), "permissions": []}])
    registry = load_registry(path, anchor)
    assert attest_agents(registry, tmp_path)[0]["status"] == "verified"
    agent.write_bytes(b"altered")
    findings = attest_agents(registry, tmp_path)
    assert findings[0]["status"] == "modified"
    plan = plan_recovery(findings, registry)
    assert plan["proposals"][0]["auto_execute"] is False
    assert agent.read_bytes() == b"altered"


def test_reject_modified_registry(tmp_path):
    path, anchor = make_registry(tmp_path, [])
    path.write_text("{}")
    with pytest.raises(RegistryError):
        load_registry(path, anchor)


def test_reject_privileged_agent(tmp_path):
    path, anchor = make_registry(tmp_path, [{"id": "admin", "path": "admin.py", "sha256": digest(b"x"), "permissions": ["root"]}])
    with pytest.raises(RegistryError):
        load_registry(path, anchor)


def test_reject_duplicate_ids(tmp_path):
    item = {"id": "a", "path": "a.py", "sha256": digest(b"a")}
    path, anchor = make_registry(tmp_path, [item, item])
    with pytest.raises(RegistryError):
        load_registry(path, anchor)
