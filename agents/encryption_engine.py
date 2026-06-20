"""
APX v1 — Optional E2EE encryption engine (Phase 2).

X25519 key exchange + XSalsa20-Poly1305 via PyNaCl (libsodium-compatible).
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import nacl.bindings as sodium
from nacl.exceptions import CryptoError

E2EE_ALGORITHM = "X25519-XSalsa20-Poly1305"
DEFAULT_KEYPAIR_NAME = "e2ee-keypair.json"

_INSTANCE: Optional["APXE2EE"] = None


@dataclass(frozen=True)
class EncryptedPayload:
    ciphertext: str
    nonce: str
    ephemeral_public_key: str

    def as_dict(self) -> Dict[str, str]:
        return {
            "ciphertext": self.ciphertext,
            "nonce": self.nonce,
            "ephemeralPublicKey": self.ephemeral_public_key,
        }


class APXE2EE:
    """X25519 + XSalsa20-Poly1305 encryption for optional payload protection."""

    def __init__(
        self,
        *,
        base_path: Optional[Path] = None,
        ephemeral: bool = False,
        keypair_path: Optional[Path] = None,
    ) -> None:
        self._base_path = Path(base_path) if base_path else Path(__file__).parent.parent
        self._keypair_path = keypair_path or self._resolve_keypair_path()
        self._public_key: Optional[bytes] = None
        self._private_key: Optional[bytes] = None
        if ephemeral:
            self._load_ephemeral_keypair()
        else:
            self._load_or_create_persistent_keypair()

    def _resolve_keypair_path(self) -> Path:
        keys_dir = os.environ.get("APX_KEYS_DIR")
        if keys_dir:
            return Path(keys_dir) / DEFAULT_KEYPAIR_NAME
        return self._base_path / "managed" / "config" / DEFAULT_KEYPAIR_NAME

    def _load_ephemeral_keypair(self) -> None:
        public_key, private_key = sodium.crypto_box_keypair()
        self._public_key = bytes(public_key)
        self._private_key = bytes(private_key)

    def _load_or_create_persistent_keypair(self) -> None:
        path = self._keypair_path
        try:
            raw_text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            self._generate_and_save_keypair(path)
            return
        except OSError as exc:
            raise RuntimeError(
                f"[E2EE] Keypair file unreadable ({exc}) — refusing to overwrite: {path}"
            ) from exc

        try:
            raw = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"[E2EE] Keypair file contains invalid JSON — refusing to overwrite: {path}"
            ) from exc

        public_b64 = raw.get("publicKey")
        private_b64 = raw.get("privateKey")
        if not isinstance(public_b64, str) or not isinstance(private_b64, str):
            raise RuntimeError(
                f"[E2EE] Keypair file is missing required fields — refusing to overwrite: {path}"
            )

        self._public_key = base64.b64decode(public_b64.encode("ascii"))
        self._private_key = base64.b64decode(private_b64.encode("ascii"))

    def _generate_and_save_keypair(self, path: Path) -> None:
        public_key, private_key = sodium.crypto_box_keypair()
        self._public_key = bytes(public_key)
        self._private_key = bytes(private_key)
        self._save_keypair(path)

    def _save_keypair(self, path: Path) -> None:
        if self._public_key is None or self._private_key is None:
            raise RuntimeError("[E2EE] Cannot persist uninitialized keypair")
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "publicKey": self._b64(self._public_key),
            "privateKey": self._b64(self._private_key),
            "algorithm": E2EE_ALGORITHM,
            "created": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _require_keys(self) -> Tuple[bytes, bytes]:
        if self._public_key is None or self._private_key is None:
            raise RuntimeError("E2EE not initialized")
        return self._public_key, self._private_key

    @staticmethod
    def _b64(data: bytes) -> str:
        return base64.b64encode(data).decode("ascii")

    @staticmethod
    def _from_b64(value: str) -> bytes:
        return base64.b64decode(value.encode("ascii"))

    @staticmethod
    def _generichash(data: bytes, digest_size: int) -> bytes:
        digest = sodium.crypto_generichash_blake2b_salt_personal(
            data,
            digest_size=digest_size,
        )
        return bytes(digest)

    def generate_keypair(self) -> Tuple[bytes, bytes]:
        public_key, private_key = sodium.crypto_box_keypair()
        return bytes(public_key), bytes(private_key)

    def get_public_key(self) -> str:
        public_key, _ = self._require_keys()
        return self._b64(public_key)

    def encrypt(self, plaintext: str, recipient_public_key: str) -> EncryptedPayload:
        _, _ = self._require_keys()
        recipient_pk = self._from_b64(recipient_public_key)
        ephemeral_pk, ephemeral_sk = sodium.crypto_box_keypair()
        nonce = sodium.randombytes(sodium.crypto_box_NONCEBYTES)
        ciphertext = sodium.crypto_box(
            plaintext.encode("utf-8"),
            nonce,
            recipient_pk,
            ephemeral_sk,
        )
        return EncryptedPayload(
            ciphertext=self._b64(bytes(ciphertext)),
            nonce=self._b64(bytes(nonce)),
            ephemeral_public_key=self._b64(bytes(ephemeral_pk)),
        )

    def decrypt(self, payload: EncryptedPayload | Dict[str, str]) -> str:
        _, private_key = self._require_keys()
        if isinstance(payload, dict):
            payload = EncryptedPayload(
                ciphertext=payload["ciphertext"],
                nonce=payload["nonce"],
                ephemeral_public_key=payload["ephemeralPublicKey"],
            )
        try:
            plaintext = sodium.crypto_box_open(
                self._from_b64(payload.ciphertext),
                self._from_b64(payload.nonce),
                self._from_b64(payload.ephemeral_public_key),
                private_key,
            )
        except CryptoError as exc:
            raise ValueError("E2EE decryption failed — ciphertext tampered or wrong key") from exc
        return plaintext.decode("utf-8")

    def encrypt_local(self, plaintext: str) -> Dict[str, str]:
        _, private_key = self._require_keys()
        key = self._generichash(private_key, sodium.crypto_secretbox_KEYBYTES)
        nonce = sodium.randombytes(sodium.crypto_secretbox_NONCEBYTES)
        ciphertext = sodium.crypto_secretbox(plaintext.encode("utf-8"), nonce, key)
        return {
            "ciphertext": self._b64(bytes(ciphertext)),
            "nonce": self._b64(bytes(nonce)),
        }

    def decrypt_local(self, ciphertext: str, nonce: str) -> str:
        _, private_key = self._require_keys()
        key = self._generichash(private_key, sodium.crypto_secretbox_KEYBYTES)
        try:
            plaintext = sodium.crypto_secretbox_open(
                self._from_b64(ciphertext),
                self._from_b64(nonce),
                key,
            )
        except CryptoError as exc:
            raise ValueError("E2EE local decryption failed — wrong nonce or tampered data") from exc
        return plaintext.decode("utf-8")

    def generate_session_token(self) -> str:
        return bytes(sodium.randombytes(32)).hex()

    def hash_data(self, data: str) -> str:
        return self._generichash(data.encode("utf-8"), 32).hex()

    def export_public_key_info(self) -> Dict[str, str]:
        return {
            "publicKey": self.get_public_key(),
            "algorithm": E2EE_ALGORITHM,
            "keyExchange": "X25519 (Curve25519 ECDH)",
            "encryption": "XSalsa20-Poly1305 (256-bit)",
        }

    def encrypt_artifact_payload(
        self,
        artifact: Dict[str, Any],
        field: str = "proposed_artifact",
    ) -> Dict[str, Any]:
        if field not in artifact:
            raise ValueError(f"Artifact missing field: {field}")
        plaintext = json.dumps(artifact[field], sort_keys=True, separators=(",", ":"))
        envelope = self.encrypt_local(plaintext)
        artifact["e2ee"] = {
            "algorithm": E2EE_ALGORITHM,
            "mode": "local",
            "publicKey": self.get_public_key(),
            "encryptedField": field,
            **envelope,
        }
        artifact[field] = {"status": "E2EE_ENCRYPTED"}
        return artifact

    def decrypt_artifact_payload(self, artifact: Dict[str, Any]) -> Dict[str, Any]:
        e2ee = artifact.get("e2ee")
        if not isinstance(e2ee, dict):
            raise ValueError("Artifact has no e2ee envelope")
        field = e2ee.get("encryptedField", "proposed_artifact")
        plaintext = self.decrypt_local(e2ee["ciphertext"], e2ee["nonce"])
        artifact[field] = json.loads(plaintext)
        return artifact


def get_e2ee_instance(
    *,
    base_path: Optional[Path] = None,
    ephemeral: bool = False,
    keypair_path: Optional[Path] = None,
) -> APXE2EE:
    global _INSTANCE
    if ephemeral or keypair_path is not None or base_path is not None:
        return APXE2EE(base_path=base_path, ephemeral=ephemeral, keypair_path=keypair_path)
    if _INSTANCE is None:
        _INSTANCE = APXE2EE()
    return _INSTANCE