"""``client.crypto`` -- crypto operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .._base64 import b64_std_decode, b64_std_encode
from ..enums import CipherAlg, HashAlg, SignAlg, WrapAlg
from ..errors import HemNotAcceptableError
from ..models import (
    EcdhResult,
    EncryptResult,
    HmacResult,
    KeyId,
    MlKemDecapsResult,
    MlKemEncapsResult,
    SignResult,
    WrapResult,
)

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

    def wrap(
        self,
        kid: KeyId,
        alg: WrapAlg,
        *,
        msg: bytes | None = None,
    ) -> WrapResult:
        """Wrap key material under ``kid`` using AES Key Wrap (RFC 3394).

        If ``msg`` is omitted the device generates and wraps random data.
        When ``msg`` is provided its length must be a multiple of 8 bytes
        and at least 16 bytes (RFC 3394 minimum).
        """
        if msg is not None:
            if len(msg) < 16:
                raise ValueError("msg must be at least 16 bytes for AES key wrap (RFC 3394)")
            if len(msg) % 8 != 0:
                raise ValueError(
                    "msg length must be a multiple of 8 bytes for AES key wrap (RFC 3394)"
                )
        body: dict[str, str] = {"kid": kid, "alg": alg.value}
        if msg is not None:
            body["msg"] = b64_std_encode(msg)
        token = self._client._auth.ensure_token(f"keymgmt:use:{kid}")
        raw = self._client._transport.request(
            "POST", "/api/crypto/cipher/wrap", json_body=body, token=token
        )
        return WrapResult(wrapped=b64_std_decode(raw["wrapped"]))

    def unwrap(
        self,
        kid: KeyId,
        wrapped: bytes,
        *,
        alg: WrapAlg,
    ) -> bytes:
        """Unwrap key material that was wrapped under ``kid``."""
        body: dict[str, str] = {
            "kid": kid,
            "alg": alg.value,
            "msg": b64_std_encode(wrapped),
        }
        token = self._client._auth.ensure_token(f"keymgmt:use:{kid}")
        raw = self._client._transport.request(
            "POST", "/api/crypto/cipher/unwrap", json_body=body, token=token
        )
        return b64_std_decode(raw["unwrapped"])


class HmacAPI:
    """Wrapper around ``/api/crypto/hmac/*`` endpoints."""

    def __init__(self, client: HemClient) -> None:
        self._client = client

    def hash(
        self,
        kid: KeyId,
        msg: bytes,
        *,
        alg: HashAlg | None = None,
        ext_kid: KeyId | None = None,
        pubkey: bytes | None = None,
    ) -> HmacResult:
        """Compute an HMAC of ``msg`` using the key identified by ``kid``.

        When ``ext_kid`` or ``pubkey`` is provided, the HMAC key is derived
        as ``Hash(X25519(kid_priv, peer_pub))`` where ``Hash`` uses ``alg``.
        ``ext_kid`` and ``pubkey`` are mutually exclusive.
        """
        body: dict[str, str] = {
            "kid": kid,
            "msg": b64_std_encode(msg),
        }
        if alg is not None:
            body["alg"] = alg.value
        if ext_kid is not None:
            body["ext_kid"] = ext_kid
        if pubkey is not None:
            body["pubkey"] = b64_std_encode(pubkey)
        token = self._client._auth.ensure_token(f"keymgmt:use:{kid}")
        raw = self._client._transport.request(
            "POST", "/api/crypto/hmac/hash", json_body=body, token=token
        )
        return HmacResult(mac=b64_std_decode(raw["mac"]))

    def verify(
        self,
        kid: KeyId,
        msg: bytes,
        mac: bytes,
        *,
        alg: HashAlg | None = None,
        ext_kid: KeyId | None = None,
        pubkey: bytes | None = None,
    ) -> bool:
        """Verify an HMAC. Returns ``True`` on match, ``False`` on mismatch.

        HTTP 406 from the device means the MAC did not match — returns ``False``
        rather than raising. OQ-12: no response body either way.
        """
        body: dict[str, str] = {
            "kid": kid,
            "msg": b64_std_encode(msg),
            "mac": b64_std_encode(mac),
        }
        if alg is not None:
            body["alg"] = alg.value
        if ext_kid is not None:
            body["ext_kid"] = ext_kid
        if pubkey is not None:
            body["pubkey"] = b64_std_encode(pubkey)
        token = self._client._auth.ensure_token(f"keymgmt:use:{kid}")
        try:
            self._client._transport.request(
                "POST", "/api/crypto/hmac/verify", json_body=body, token=token
            )
        except HemNotAcceptableError:
            return False
        return True


class ExdsaAPI:
    """Wrapper around ``/api/crypto/exdsa/*`` endpoints."""

    def __init__(self, client: HemClient) -> None:
        self._client = client

    def sign(
        self,
        kid: KeyId,
        msg: bytes,
        alg: SignAlg,
        *,
        ctx: bytes | None = None,
    ) -> SignResult:
        """Sign ``msg`` with the key identified by ``kid``.

        ``ctx`` is required when ``alg.requires_ctx`` is ``True``
        (Ed25519ph, Ed25519ctx, Ed448, Ed448ph). Max 255 bytes.

        Note: the key must have been created with ExDSA mode enabled (OQ-19).
        NIST ECC keys created via ``keys.create()`` default to ``ECDH,ExDSA``,
        but imported keys or keys with explicit ``mode=ECDH`` will return 406.
        """
        if alg.requires_ctx and ctx is None:
            raise ValueError(f"ctx is required for {alg.value}")
        if ctx is not None and len(ctx) > 255:
            raise ValueError("ctx must be at most 255 bytes")
        if len(msg) > 2048:
            raise ValueError("msg must be at most 2048 bytes")
        body: dict[str, str] = {
            "kid": kid,
            "msg": b64_std_encode(msg),
            "alg": alg.value,
        }
        if ctx is not None:
            body["ctx"] = b64_std_encode(ctx)
        token = self._client._auth.ensure_token(f"keymgmt:use:{kid}")
        raw = self._client._transport.request(
            "POST", "/api/crypto/exdsa/sign", json_body=body, token=token
        )
        return SignResult(signature=b64_std_decode(raw["sign"]))

    def verify(
        self,
        kid: KeyId,
        msg: bytes,
        signature: bytes,
        alg: SignAlg,
        *,
        ctx: bytes | None = None,
    ) -> bool:
        """Verify a signature. Returns ``True`` on match, ``False`` on mismatch.

        HTTP 406 from the device means the signature did not match — returns
        ``False`` rather than raising. OQ-12: no response body either way.
        Wire field name for ``signature`` is ``sign``.
        """
        if alg.requires_ctx and ctx is None:
            raise ValueError(f"ctx is required for {alg.value}")
        if ctx is not None and len(ctx) > 255:
            raise ValueError("ctx must be at most 255 bytes")
        body: dict[str, str] = {
            "kid": kid,
            "msg": b64_std_encode(msg),
            "sign": b64_std_encode(signature),
            "alg": alg.value,
        }
        if ctx is not None:
            body["ctx"] = b64_std_encode(ctx)
        token = self._client._auth.ensure_token(f"keymgmt:use:{kid}")
        try:
            self._client._transport.request(
                "POST", "/api/crypto/exdsa/verify", json_body=body, token=token
            )
        except HemNotAcceptableError:
            return False
        return True


class EcdhAPI:
    """Wrapper around ``POST /api/crypto/ecdh``."""

    def __init__(self, client: HemClient) -> None:
        self._client = client

    def exchange(
        self,
        kid: KeyId,
        *,
        pubkey: bytes | None = None,
        ext_kid: KeyId | None = None,
        alg: HashAlg | None = None,
    ) -> EcdhResult:
        """Perform ECDH key exchange. Exactly one of ``pubkey`` or ``ext_kid`` must be provided.

        ``alg``: if ``None``, returns raw ECDH output. If set, returns ``Hash(raw_ecdh_output)``.
        ``pubkey`` and ``ext_kid`` are mutually exclusive.
        """
        if pubkey is None and ext_kid is None:
            raise ValueError("exactly one of pubkey or ext_kid must be provided")
        if pubkey is not None and ext_kid is not None:
            raise ValueError("pubkey and ext_kid are mutually exclusive")
        body: dict[str, str] = {"kid": kid}
        if pubkey is not None:
            body["pubkey"] = b64_std_encode(pubkey)
        if ext_kid is not None:
            body["ext_kid"] = ext_kid
        if alg is not None:
            body["alg"] = alg.value
        token = self._client._auth.ensure_token(f"keymgmt:use:{kid}")
        raw = self._client._transport.request(
            "POST", "/api/crypto/ecdh", json_body=body, token=token
        )
        return EcdhResult(shared_secret=b64_std_decode(raw["ecdh"]))


class MlKemAPI:
    """Wrapper around ``/api/crypto/pqc/mlkem/*`` endpoints."""

    def __init__(self, client: HemClient) -> None:
        self._client = client

    def encaps(self, kid: KeyId) -> MlKemEncapsResult:
        """Encapsulate: generate a shared secret and ciphertext for ``kid``.

        The ``ciphertext`` should be sent to the peer for decapsulation.
        Both sides derive the same ``shared_secret``.
        """
        body: dict[str, str] = {"kid": kid}
        token = self._client._auth.ensure_token(f"keymgmt:use:{kid}")
        raw = self._client._transport.request(
            "POST", "/api/crypto/pqc/mlkem/encaps", json_body=body, token=token
        )
        return MlKemEncapsResult(
            ciphertext=b64_std_decode(raw["ct"]),
            shared_secret=b64_std_decode(raw["ss"]),
            alg=raw["alg"],
        )

    def decaps(self, kid: KeyId, ciphertext: bytes) -> MlKemDecapsResult:
        """Decapsulate: recover the shared secret from ``ciphertext``.

        Wire field name for ``ciphertext`` is ``ct``.
        """
        body: dict[str, str] = {
            "kid": kid,
            "ct": b64_std_encode(ciphertext),
        }
        token = self._client._auth.ensure_token(f"keymgmt:use:{kid}")
        raw = self._client._transport.request(
            "POST", "/api/crypto/pqc/mlkem/decaps", json_body=body, token=token
        )
        return MlKemDecapsResult(shared_secret=b64_std_decode(raw["ss"]))


class MlDsaAPI:
    """Wrapper around ``/api/crypto/pqc/mldsa/*`` endpoints."""

    def __init__(self, client: HemClient) -> None:
        self._client = client

    def sign(
        self,
        kid: KeyId,
        msg: bytes,
        *,
        ctx: bytes | None = None,
    ) -> SignResult:
        """Sign ``msg`` with the ML-DSA key identified by ``kid``.

        ``ctx`` is optional; max 255 bytes.
        """
        if ctx is not None and len(ctx) > 255:
            raise ValueError("ctx must be at most 255 bytes")
        if len(msg) > 2048:
            raise ValueError("msg must be at most 2048 bytes")
        body: dict[str, str] = {
            "kid": kid,
            "msg": b64_std_encode(msg),
        }
        if ctx is not None:
            body["ctx"] = b64_std_encode(ctx)
        token = self._client._auth.ensure_token(f"keymgmt:use:{kid}")
        raw = self._client._transport.request(
            "POST", "/api/crypto/pqc/mldsa/sign", json_body=body, token=token
        )
        return SignResult(signature=b64_std_decode(raw["sign"]))

    def verify(
        self,
        kid: KeyId,
        msg: bytes,
        signature: bytes,
        *,
        ctx: bytes | None = None,
    ) -> bool:
        """Verify an ML-DSA signature. Returns ``True`` on match, ``False`` on mismatch.

        HTTP 406 means the signature did not match — returns ``False``.
        Note: ``ctx`` max is 64 bytes here (smaller than ``sign``'s 255).
        Wire field name for ``signature`` is ``sign``.
        """
        if ctx is not None and len(ctx) > 64:
            raise ValueError("ctx must be at most 64 bytes for mldsa verify")
        body: dict[str, str] = {
            "kid": kid,
            "msg": b64_std_encode(msg),
            "sign": b64_std_encode(signature),
        }
        if ctx is not None:
            body["ctx"] = b64_std_encode(ctx)
        token = self._client._auth.ensure_token(f"keymgmt:use:{kid}")
        try:
            self._client._transport.request(
                "POST", "/api/crypto/pqc/mldsa/verify", json_body=body, token=token
            )
        except HemNotAcceptableError:
            return False
        return True


class PqcAPI:
    """Post-quantum crypto namespace: ``client.crypto.pqc``."""

    def __init__(self, client: HemClient) -> None:
        self.mlkem = MlKemAPI(client)
        self.mldsa = MlDsaAPI(client)


class CryptoAPI:
    """Top-level crypto namespace."""

    def __init__(self, client: HemClient) -> None:
        self.cipher = CipherAPI(client)
        self.hmac = HmacAPI(client)
        self.exdsa = ExdsaAPI(client)
        self.ecdh = EcdhAPI(client)
        self.pqc = PqcAPI(client)
