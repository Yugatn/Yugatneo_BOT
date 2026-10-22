"""YUGATNEO AMALGAMA: local, read-only file-integrity prototype.

Usage:
  python3 -m amalgama.cli init --root ~/Documents/AmalgamaTest --state ~/.amalgama/state.json
  python3 -m amalgama.cli scan --root ~/Documents/AmalgamaTest --state ~/.amalgama/state.json

Never run with elevated privileges. Does not quarantine, delete, upload or alter watched files.
The baseline is NOT a trusted cryptographic attestation: protect its storage separately.
"""
import argparse
import hashlib
import json
import os
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path

MAX_FILE_SIZE = 20 * 1024 * 1024
MAX_FILES = 20000


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def collect(root, state_path):
    root = root.expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Root must be a directory")
    state_path = state_path.expanduser().resolve()
    if state_path == root or root in state_path.parents:
        raise ValueError("State file must be outside the monitored directory")
    records, errors = {}, []
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not (Path(directory) / d).is_symlink())
        for name in sorted(files):
            p = Path(directory) / name
            relative = str(p.relative_to(root))
            if len(records) >= MAX_FILES:
                errors.append("File limit reached; snapshot incomplete")
                return records, errors
            try:
                info = p.lstat()
                if not stat.S_ISREG(info.st_mode):
                    continue
                if info.st_size > MAX_FILE_SIZE:
                    errors.append(f"Skipped oversized file: {relative}")
                    continue
                records[relative] = {"sha256": digest(p), "size": info.st_size}
            except (OSError, PermissionError) as exc:
                errors.append(f"Could not read {relative}: {type(exc).__name__}")
    return records, errors


def main(argv=None):
    parser = argparse.ArgumentParser(description="AMALGAMA read-only integrity prototype")
    parser.add_argument("command", choices=("init", "scan"))
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--state", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        files, errors = collect(args.root, args.state)
        if errors:
            print(json.dumps({"status": "incomplete", "errors": errors}, ensure_ascii=False, indent=2))
            return 2
        state = args.state.expanduser()
        if args.command == "init":
            state.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            payload = {"schema": 1, "root": str(args.root.expanduser().resolve()),
                       "created_at": datetime.now(timezone.utc).isoformat(), "files": files}
            # Exclusive create: do not silently overwrite the baseline.
            with state.open("x", encoding="utf-8") as out:
                os.chmod(state, 0o600)
                json.dump(payload, out, ensure_ascii=False, indent=2)
            print(json.dumps({"status": "baseline_created", "files": len(files)}, ensure_ascii=False))
            return 0
        with state.open(encoding="utf-8") as source:
            baseline = json.load(source)
        if baseline.get("root") != str(args.root.expanduser().resolve()):
            raise ValueError("Monitored root does not match baseline")
        previous = baseline["files"]
        added = sorted(set(files) - set(previous))
        removed = sorted(set(previous) - set(files))
        changed = sorted(k for k in set(files) & set(previous) if files[k] != previous[k])
        print(json.dumps({"status": "changes_detected" if added or removed or changed else "unchanged",
                          "added": added, "removed": removed, "changed": changed}, ensure_ascii=False, indent=2))
        return 1 if added or removed or changed else 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"AMALGAMA error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
