import base64
import hashlib
import json
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from amalgama.signed_manifest import (
    SignatureError, canonical_payload, verify_signed_manifest
)
from amalgama.platform import discover


def test_signed_manifest_and_tampering(tmp_path):
    private = Ed25519PrivateKey.generate()
    public_hex = private.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    ).hex()
    manifest = {"schema": 1, "agents": []}
    envelope = {"manifest": manifest, "signature": base64.b64encode(
        private.sign(canonical_payload(manifest))).decode()}
    path = tmp_path / "signed.json"
    path.write_text(json.dumps(envelope))
    assert verify_signed_manifest(path, public_hex) == manifest
    envelope["manifest"]["agents"].append({"id": "intruder"})
    path.write_text(json.dumps(envelope))
    with pytest.raises(SignatureError):
        verify_signed_manifest(path, public_hex)


def test_wrong_key_rejected(tmp_path):
    private = Ed25519PrivateKey.generate()
    envelope = {"manifest": {"schema": 1, "agents": []},
                "signature": base64.b64encode(private.sign(
                    canonical_payload({"schema": 1, "agents": []}))).decode()}
    path = tmp_path / "signed.json"
    path.write_text(json.dumps(envelope))
    other_key = Ed25519PrivateKey.generate().public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
    with pytest.raises(SignatureError):
        verify_signed_manifest(path, other_key)


def test_platforms_are_noninvasive():
    for system in ("Darwin", "Linux", "Windows"):
        assert discover(system).supported_readonly_prototype
        assert not discover(system).automatic_install
