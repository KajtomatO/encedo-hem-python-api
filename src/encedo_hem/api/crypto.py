"""``client.crypto`` -- crypto operations.

Phase 1 implements only the ``cipher`` subnamespace. Future phases will add
``hmac``, ``exdsa``, ``ecdh``, and ``pqc``; the class shape leaves room for
them without breaking imports.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .._base64 import b64_std_decode, b64_std_encode
from ..enums import CipherAlg
from ..models import EncryptResult, KeyId

if TYPE_CHECKING:
    from ..client import HemClient


class CipherAPI:
    """Wrapper around ``/api/crypto/cipher/*`` endpoints."""

    def __init__(self, client: HemClient) -> None:
        self._client = client

    def encrypt(
        self,
        kid: KeyId,
        plaintext: bytes,
        *,
        alg: CipherAlg = CipherAlg.AES256_GCM,
        aad: bytes | None = None,
    ) -> EncryptResult:
        """Encrypt ``plaintext`` with the key identified by ``kid``."""
        body: dict[str, str] = {
            "kid": kid,
            "alg": alg.value,
            "msg": b64_std_encode(plaintext),
        }
        if aad is not None:
            body["aad"] = b64_std_encode(aad)
        token = self._client._auth.ensure_token(f"keymgmt:use:{kid}")
        raw = self._client._transport.request(
            "POST", "/api/crypto/cipher/encrypt", json_body=body, token=token
        )
        return EncryptResult(
            ciphertext=b64_std_decode(raw["ciphertext"]),
            iv=b64_std_decode(raw["iv"]) if "iv" in raw else None,
            tag=b64_std_decode(raw["tag"]) if "tag" in raw else None,
        )

    def decrypt(
        self,
        kid: KeyId,
        ciphertext: bytes,
        *,
        alg: CipherAlg,
        iv: bytes | None = None,
        tag: bytes | None = None,
        aad: bytes | None = None,
    ) -> bytes:
        """Decrypt ``ciphertext`` with the key identified by ``kid``."""
        body: dict[str, str] = {
            "kid": kid,
            "alg": alg.value,
            "msg": b64_std_encode(ciphertext),
        }
        if iv is not None:
            body["iv"] = b64_std_encode(iv)
        if tag is not None:
            body["tag"] = b64_std_encode(tag)
        if aad is not None:
            body["aad"] = b64_std_encode(aad)
        token = self._client._auth.ensure_token(f"keymgmt:use:{kid}")
        raw = self._client._transport.request(
            "POST", "/api/crypto/cipher/decrypt", json_body=body, token=token
        )
        return b64_std_decode(raw["plaintext"])


class CryptoAPI:
    """Top-level crypto namespace. Sub-namespaces are added in later phases."""

    def __init__(self, client: HemClient) -> None:
        self.cipher = CipherAPI(client)
