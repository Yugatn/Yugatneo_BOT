"""Single-shot offline Guardian worker. Caller is responsible for OS sandbox.

This process does not make itself isolated or disable network access.
"""
import argparse
import json
import sys
from amalgama.signed_manifest import SignatureError, verify_signed_manifest
from amalgama.registry import attest_agents


def main(argv=None):
    parser = argparse.ArgumentParser(description="AMALGAMA independent verification worker")
    parser.add_argument("--envelope", required=True)
    parser.add_argument("--public-key-hex", required=True)
    parser.add_argument("--root", required=True)
    args = parser.parse_args(argv)
    try:
        manifest = verify_signed_manifest(args.envelope, args.public_key_hex)
        findings = attest_agents(manifest, args.root)
        print(json.dumps({"status": "verified" if all(
            item["status"] == "verified" for item in findings
        ) else "mismatch", "findings": findings}, ensure_ascii=False))
        return 0 if all(item["status"] == "verified" for item in findings) else 1
    except (SignatureError, OSError, ValueError, KeyError) as exc:
        print(f"Guardian refused verification: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
