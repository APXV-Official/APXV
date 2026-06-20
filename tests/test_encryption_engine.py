"""Tests for APX E2EE encryption engine (Phase 2)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.encryption_engine import APXE2EE, EncryptedPayload

pytest.importorskip("nacl")


@pytest.fixture
def temp_keys_dir(tmp_path: Path) -> Path:
    return tmp_path / "keys"


@pytest.fixture
def alice(temp_keys_dir: Path) -> APXE2EE:
    return APXE2EE(ephemeral=True, keypair_path=temp_keys_dir / "alice.json")


@pytest.fixture
def bob(temp_keys_dir: Path) -> APXE2EE:
    return APXE2EE(ephemeral=True, keypair_path=temp_keys_dir / "bob.json")


def test_encrypt_decrypt_round_trip_same_instance(alice: APXE2EE):
    pub = alice.get_public_key()
    payload = alice.encrypt("Hello, APX!", pub)
    assert alice.decrypt(payload) == "Hello, APX!"


def test_encrypt_decrypt_json_round_trip(alice: APXE2EE):
    pub = alice.get_public_key()
    plaintext = json.dumps({"ssn": "123-45-6789", "email": "test@example.com"})
    payload = alice.encrypt(plaintext, pub)
    assert alice.decrypt(payload) == plaintext


def test_encrypt_produces_unique_nonces(alice: APXE2EE):
    pub = alice.get_public_key()
    first = alice.encrypt("same plaintext", pub)
    second = alice.encrypt("same plaintext", pub)
    assert first.nonce != second.nonce
    assert first.ciphertext != second.ciphertext


def test_cross_keypair_encrypt_decrypt(alice: APXE2EE, bob: APXE2EE):
    bob_pub = bob.get_public_key()
    payload = alice.encrypt("secret from alice", bob_pub)
    assert bob.decrypt(payload) == "secret from alice"


def test_wrong_recipient_cannot_decrypt(alice: APXE2EE, bob: APXE2EE):
    bob_pub = bob.get_public_key()
    payload = alice.encrypt("for bob only", bob_pub)
    with pytest.raises(ValueError, match="decryption failed"):
        alice.decrypt(payload)


def test_tampered_ciphertext_rejected(alice: APXE2EE):
    pub = alice.get_public_key()
    payload = alice.encrypt("tamper me", pub)
    raw = bytearray(APXE2EE._from_b64(payload.ciphertext))
    raw[0] ^= 0xFF
    tampered = EncryptedPayload(
        ciphertext=APXE2EE._b64(bytes(raw)),
        nonce=payload.nonce,
        ephemeral_public_key=payload.ephemeral_public_key,
    )
    with pytest.raises(ValueError, match="decryption failed"):
        alice.decrypt(tampered)


def test_tampered_nonce_rejected(alice: APXE2EE):
    pub = alice.get_public_key()
    payload = alice.encrypt("tamper nonce", pub)
    raw = bytearray(APXE2EE._from_b64(payload.nonce))
    raw[0] ^= 0xFF
    tampered = EncryptedPayload(
        ciphertext=payload.ciphertext,
        nonce=APXE2EE._b64(bytes(raw)),
        ephemeral_public_key=payload.ephemeral_public_key,
    )
    with pytest.raises(ValueError, match="decryption failed"):
        alice.decrypt(tampered)


def test_encrypt_local_round_trip(alice: APXE2EE):
    envelope = alice.encrypt_local("local secret")
    assert alice.decrypt_local(envelope["ciphertext"], envelope["nonce"]) == "local secret"


def test_encrypt_local_empty_string(alice: APXE2EE):
    envelope = alice.encrypt_local("")
    assert alice.decrypt_local(envelope["ciphertext"], envelope["nonce"]) == ""


def test_encrypt_local_wrong_nonce_rejected(alice: APXE2EE):
    envelope = alice.encrypt_local("data")
    other = alice.encrypt_local("other")
    with pytest.raises(ValueError, match="local decryption failed"):
        alice.decrypt_local(envelope["ciphertext"], other["nonce"])


def test_hash_data_is_deterministic_hex(alice: APXE2EE):
    digest = alice.hash_data("hello")
    assert len(digest) == 64
    assert digest == alice.hash_data("hello")
    assert digest != alice.hash_data("world")


def test_generate_session_token_unique(alice: APXE2EE):
    first = alice.generate_session_token()
    second = alice.generate_session_token()
    assert len(first) == 64
    assert first != second


def test_export_public_key_info(alice: APXE2EE):
    info = alice.export_public_key_info()
    assert info["publicKey"] == alice.get_public_key()
    assert info["algorithm"] == "X25519-XSalsa20-Poly1305"
    assert "keyExchange" in info
    assert "encryption" in info


def test_persistent_keypair_created_and_reloaded(temp_keys_dir: Path):
    key_path = temp_keys_dir / "e2ee-keypair.json"
    first = APXE2EE(keypair_path=key_path)
    pub = first.get_public_key()

    second = APXE2EE(keypair_path=key_path)
    assert second.get_public_key() == pub
    assert key_path.exists()

    saved = json.loads(key_path.read_text(encoding="utf-8"))
    assert saved["algorithm"] == "X25519-XSalsa20-Poly1305"
    assert "publicKey" in saved
    assert "privateKey" in saved


def test_invalid_keypair_json_fail_closed(temp_keys_dir: Path):
    key_path = temp_keys_dir / "e2ee-keypair.json"
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_text("{ this is: not valid JSON }", encoding="utf-8")
    with pytest.raises(RuntimeError, match="invalid JSON"):
        APXE2EE(keypair_path=key_path)


def test_missing_keypair_fields_fail_closed(temp_keys_dir: Path):
    key_path = temp_keys_dir / "e2ee-keypair.json"
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_text(json.dumps({"algorithm": "X25519"}), encoding="utf-8")
    with pytest.raises(RuntimeError, match="missing required fields"):
        APXE2EE(keypair_path=key_path)


def test_encrypt_decrypt_artifact_payload_round_trip(alice: APXE2EE):
    artifact = {
        "attestation_id": "att-001",
        "proposed_artifact": {
            "output": {"redacted_text": "[EMAIL]", "total_redactions": 2},
        },
    }
    encrypted = alice.encrypt_artifact_payload(dict(artifact))
    assert encrypted["proposed_artifact"] == {"status": "E2EE_ENCRYPTED"}
    assert "e2ee" in encrypted
    assert encrypted["e2ee"]["encryptedField"] == "proposed_artifact"

    restored = alice.decrypt_artifact_payload(dict(encrypted))
    assert restored["proposed_artifact"] == artifact["proposed_artifact"]
    assert restored["attestation_id"] == "att-001"


def test_decrypt_artifact_payload_without_envelope_raises(alice: APXE2EE):
    with pytest.raises(ValueError, match="no e2ee envelope"):
        alice.decrypt_artifact_payload({"proposed_artifact": {}})