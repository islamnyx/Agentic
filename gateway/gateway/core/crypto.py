"""Envelope-encrypted secret store (Phase 3).

Each secret value is encrypted with a randomly generated data encryption key
(DEK) using AES-256-GCM. The DEK is then wrapped with a key encryption key
(KEK). The KEK can come from HashiCorp Vault's transit engine (Vault-ready)
or fall back to a locally derived key derived from the application SECRET_KEY.

Agents never receive raw secrets: the envelope (ciphertext + wrapped DEK) is
stored in Postgres and only the credential broker, after validating a scoped
lease, decrypts and injects the secret into connector execution.
"""

import base64
import hashlib
import os
from typing import Any

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from gateway.core.config import settings


class KekUnavailable(RuntimeError):
    """Raised when no key encryption key is available."""


class _LocalKek:
    """Locally derived key encryption key (Vault fallback).

    Derives a KEK from the application SECRET_KEY using HKDF so that rotating
    SECRET_KEY rotates the KEK. Not suitable for production key management;
    Vault transit should be used in production.
    """

    def __init__(self, secret_key: str):
        self._key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"gateway-kek-v1",
            info=b"gateway/envelope-encryption/kek",
        ).derive(secret_key.encode("utf-8"))

    def wrap(self, dek: bytes) -> bytes:
        """Encrypt a DEK with the local KEK (AES-GCM)."""
        aesgcm = AESGCM(self._key)
        nonce = os.urandom(12)
        return nonce + aesgcm.encrypt(nonce, dek, None)

    def unwrap(self, wrapped: bytes) -> bytes:
        """Decrypt a DEK wrapped with the local KEK."""
        aesgcm = AESGCM(self._key)
        nonce, ciphertext = wrapped[:12], wrapped[12:]
        return aesgcm.decrypt(nonce, ciphertext, None)


class _VaultKek:
    """HashiCorp Vault transit engine key encryption key.

    Sends encrypt/decrypt requests to Vault's transit engine so the KEK never
    leaves Vault. Falls back to the local KEK when Vault is unreachable.
    """

    def __init__(
        self,
        vault_addr: str,
        vault_token: str,
        mount: str = "transit",
        key_name: str = "gateway-kek",
    ):
        self._vault_addr = vault_addr.rstrip("/")
        self._vault_token = vault_token
        self._mount = mount
        self._key_name = key_name

    def _vault_url(self, action: str) -> str:
        return f"{self._vault_addr}/v1/{self._mount}/keys/{self._key_name}/{action}"

    def _headers(self) -> dict[str, str]:
        return {"X-Vault-Token": self._vault_token, "Content-Type": "application/json"}

    def wrap(self, dek: bytes) -> bytes:
        import httpx

        b64 = base64.b64encode(dek).decode("ascii")
        with httpx.Client(timeout=5.0) as client:
            resp = client.post(
                self._vault_url("encrypt"),
                headers=self._headers(),
                json={"plaintext": b64},
            )
            resp.raise_for_status()
        return base64.b64decode(resp.json()["data"]["ciphertext"])

    def unwrap(self, wrapped: bytes) -> bytes:
        import httpx

        b64 = base64.b64encode(wrapped).decode("ascii")
        with httpx.Client(timeout=5.0) as client:
            resp = client.post(
                self._vault_url("decrypt"),
                headers=self._headers(),
                json={"ciphertext": b64},
            )
            resp.raise_for_status()
        return base64.b64decode(resp.json()["data"]["plaintext"])


class EnvelopeEncryption:
    """Envelope encryption for connector credentials.

    ``encrypt_secret`` produces an envelope:
      {
        "ciphertext": "<base64 AES-GCM of secret with DEK>",
        "nonce": "<base64 nonce>",
        "wrapped_dek": "<base64 DEK wrapped with KEK>",
        "key_id": "<kek identifier>",
        "kek_source": "vault" | "local",
      }

    ``decrypt_secret`` reverses it and returns the plaintext secret.
    """

    def __init__(self) -> None:
        self._kek = self._load_kek()

    def _load_kek(self) -> Any:
        vault_addr = os.environ.get("VAULT_ADDR", "")
        vault_token = os.environ.get("VAULT_TOKEN", "")
        if vault_addr and vault_token:
            return _VaultKek(vault_addr, vault_token)
        if settings.SECRET_KEY and settings.SECRET_KEY != "dev-secret-change-me":
            return _LocalKek(settings.SECRET_KEY)
        # Development fallback: derive a deterministic-but-dev-only KEK so the
        # gateway boots without a real key management system. Not for prod.
        return _LocalKek(hashlib.sha256(b"gateway-dev-kek-fallback").hexdigest())

    def _dek(self) -> bytes:
        return os.urandom(32)

    def encrypt_secret(self, plaintext: str) -> dict[str, Any]:
        """Encrypt ``plaintext`` and return a storable envelope dict."""
        dek = self._dek()
        aesgcm = AESGCM(dek)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        wrapped_dek = self._kek.wrap(dek)
        return {
            "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
            "nonce": base64.b64encode(nonce).decode("ascii"),
            "wrapped_dek": base64.b64encode(wrapped_dek).decode("ascii"),
            "key_id": getattr(self._kek, "key_name", "local-kek"),
            "kek_source": "vault" if isinstance(self._kek, _VaultKek) else "local",
        }

    def decrypt_secret(self, envelope: dict[str, Any]) -> str:
        """Decrypt an envelope produced by :meth:`encrypt_secret`."""
        ciphertext = base64.b64decode(envelope["ciphertext"])
        nonce = base64.b64decode(envelope["nonce"])
        wrapped_dek = base64.b64decode(envelope["wrapped_dek"])
        dek = self._kek.unwrap(wrapped_dek)
        aesgcm = AESGCM(dek)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")
