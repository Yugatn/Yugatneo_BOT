"""Ed25519-signed manifest verifier; fail closed, no code execution.

Requires 'cryptography'. Public key must be pinned independently by operator.
"""
import base64
import json
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


class SignatureError(ValueError):
    pass


def canonical_payload(manifest):
    if not isinstance(manifest, dict) or manifest.get("schema") != 1:
        raise SignatureError("Unsupported manifest")
    if not isinstance(manifest.get("agents"), list):
        raise SignatureError("Missing agents")
    return json.dumps(manifest, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def verify_signed_manifest(envelope_path, pinned_public_key_hex):
    """Return manifest only after verifying a detached signature.

    Envelope: {"manifest": {...}, "signature": "<base64>"}.
    The pinned public key is an out-of-band trust anchor, not read from envelope.
    """
    try:
        key = bytes.fromhex(pinned_public_key_hex)
        if len(key) != 32:
            raise ValueError("Ed25519 key must be 32 bytes")
        envelope = json.loads(Path(envelope_path).read_text(encoding="utf-8"))
        if set(envelope) != {"manifest", "signature"}:
            raise SignatureError("Invalid envelope fields")
        signature = base64.b64decode(envelope["signature"], validate=True)
        if len(signature) != 64:
            raise SignatureError("Invalid signature size")
        manifest = envelope["manifest"]
        Ed25519PublicKey.from_public_bytes(key).verify(signature, canonical_payload(manifest))
        return manifest
    except (InvalidSignature, ValueError, TypeError, KeyError, OSError) as exc:
        raise SignatureError("Signature or manifest verification failed") from exc
