"""Read-only agent registry and independent attestation.

Trust anchor is the SHA-256 digest provided separately by the operator.
No self-registration, network access or automatic privilege changes.
"""
import hashlib
import hmac
import json
from pathlib import Path


class RegistryError(ValueError):
    pass


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_registry(path, trusted_digest):
    if not isinstance(trusted_digest, str) or len(trusted_digest) != 64 or any(
        c not in "0123456789abcdef" for c in trusted_digest
    ):
        raise RegistryError("Trusted digest must be lowercase SHA-256")
    if not hmac.compare_digest(file_hash(path), trusted_digest):
        raise RegistryError("Registry failed independent trust check")
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema") != 1 or not isinstance(data.get("agents"), list):
        raise RegistryError("Unsupported registry schema")
    names = set()
    for entry in data["agents"]:
        if not isinstance(entry, dict):
            raise RegistryError("Malformed registry entry")
        name, relative, expected = (entry.get(k) for k in ("id", "path", "sha256"))
        if not isinstance(name, str) or not name or name in names:
            raise RegistryError("Missing or duplicate agent ID")
        names.add(name)
        if not isinstance(relative, str) or not relative or Path(relative).is_absolute() or ".." in Path(relative).parts:
            raise RegistryError("Unsafe agent path")
        if not isinstance(expected, str) or len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
            raise RegistryError("Invalid agent hash")
        if entry.get("permissions") not in ([], None):
            raise RegistryError("Prototype supports unprivileged agents only")
    return data


def attest_agents(registry, root):
    base = Path(root).resolve(strict=True)
    findings = []
    for entry in registry["agents"]:
        path = (base / entry["path"]).resolve()
        if not path.is_relative_to(base):
            findings.append({"id": entry["id"], "status": "unsafe_path"})
        elif not path.is_file():
            findings.append({"id": entry["id"], "status": "missing"})
        elif not hmac.compare_digest(file_hash(path), entry["sha256"]):
            findings.append({"id": entry["id"], "status": "modified"})
        else:
            findings.append({"id": entry["id"], "status": "verified"})
    return findings
