"""Periodic read-only integrity watcher. Polling is intentional for portability.

This is not a real-time antivirus; events may be missed between scans.
"""
import argparse
import json
import time
from pathlib import Path
from amalgama.cli import collect


def compare(previous, current):
    return {
        "added": sorted(set(current) - set(previous)),
        "removed": sorted(set(previous) - set(current)),
        "changed": sorted(k for k in set(previous) & set(current) if previous[k] != current[k]),
    }


def watch(root: Path, state: Path, interval: float = 10, iterations: int = 0, sleep=time.sleep, emit=print):
    if interval < 1:
        raise ValueError("Minimum interval is 1 second")
    baseline = json.loads(state.expanduser().read_text(encoding="utf-8"))
    resolved_root = root.expanduser().resolve(strict=True)
    if baseline.get("root") != str(resolved_root):
        raise ValueError("Baseline belongs to another directory")
    previous = baseline["files"]
    count = 0
    while not iterations or count < iterations:
        current, errors = collect(resolved_root, state)
        if errors:
            emit(json.dumps({"type": "incomplete_scan", "errors": errors}, ensure_ascii=False))
        else:
            changes = compare(previous, current)
            if any(changes.values()):
                emit(json.dumps({"type": "integrity_change", **changes}, ensure_ascii=False))
            previous = current
        count += 1
        if not iterations or count < iterations:
            sleep(interval)


def main(argv=None):
    parser = argparse.ArgumentParser(description="AMALGAMA read-only periodic watcher")
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--interval", type=float, default=10)
    parser.add_argument("--iterations", type=int, default=0,
                        help="0 = run until interrupted")
    args = parser.parse_args(argv)
    if args.iterations < 0:
        parser.error("iterations must be nonnegative")
    try:
        watch(args.root, args.state, args.interval, args.iterations)
    except KeyboardInterrupt:
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        parser.exit(2, f"AMALGAMA: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
