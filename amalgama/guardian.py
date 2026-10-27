"""AMALGAMA Guardian: read-only verification of an explicitly trusted manifest.

No networking, subprocesses, imports of AI frameworks, or automatic repairs.
The expected digest must be supplied from a separately trusted source.
"""
import argparse
import hashlib
import hmac
import json
import sys
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_manifest(manifest: Path, trusted_sha256: str, base_dir: Path):
    if len(trusted_sha256) != 64 or any(c not in "0123456789abcdef" for c in trusted_sha256):
        raise ValueError("Expected manifest digest must be lowercase SHA-256 hex")
    if not hmac.compare_digest(sha256_file(manifest), trusted_sha256):
        return {"status": "untrusted_manifest", "verified": [], "mismatches": []}
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if data.get("schema") != 1 or not isinstance(data.get("agents"), list):
        raise ValueError("Unsupported manifest schema")
    base = base_dir.resolve(strict=True)
    verified, mismatches = [], []
    for agent in data["agents"]:
        if not isinstance(agent, dict) or not isinstance(agent.get("path"), str):
            raise ValueError("Invalid agent entry")
        relative = Path(agent["path"])
        expected = agent.get("sha256")
        if relative.is_absolute() or ".." in relative.parts or not relative.parts:
            raise ValueError("Agent path must stay inside base directory")
        if not isinstance(expected, str) or len(expected) != 64:
            raise ValueError("Invalid agent digest")
        target = (base / relative).resolve()
        if not target.is_relative_to(base):
            raise ValueError("Agent path escapes base directory")
        name = relative.as_posix()
        if not target.is_file() or not hmac.compare_digest(sha256_file(target), expected):
            mismatches.append(name)
        else:
            verified.append(name)
    return {"status": "mismatch" if mismatches else "verified",
            "verified": verified, "mismatches": mismatches}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline read-only AMALGAMA Guardian")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--trusted-sha256", required=True)
    parser.add_argument("--base-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = verify_manifest(args.manifest, args.trusted_sha256, args.base_dir)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] == "verified" else 1
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"Guardian error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
