"""Frozen dataclasses representing HEM wire-protocol responses.

These are immutable, slot-based, and cheap to construct. None of them perform
network I/O; they are pure data containers populated by ``api/*`` modules.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import NewType

from .enums import HardwareForm

KeyId = NewType("KeyId", str)
"""32 lowercase hex characters identifying a key on the device."""


@dataclass(frozen=True, slots=True)
class DeviceVersion:
    """Result of ``GET /api/system/version``."""

    hwv: str
    blv: str
    fwv: str
    fws: str
    uis: str | None  # PPA only

    @property
    def hardware(self) -> HardwareForm:
        """Map ``hwv`` to a :class:`HardwareForm`."""
        if "EPA" in self.hwv:
            return HardwareForm.EPA
        if "PPA" in self.hwv:
            return HardwareForm.PPA
        return HardwareForm.UNKNOWN

    @property
    def is_diag(self) -> bool:
        """``True`` if the firmware version ends with ``-DIAG``."""
        return self.fwv.endswith("-DIAG")


@dataclass(frozen=True, slots=True)
class DeviceStatus:
    """Result of ``GET /api/system/status``.

    The ``initialized`` field is the inverted ``inited`` quirk: a missing key
    in the response means the device **is** initialized.
    """

    fls_state: int
    ts: datetime | None
    """Device RTC time, parsed from ISO 8601. ``None`` when RTC is not set."""
    hostname: str | None
    """Device hostname. Per upstream spec, only returned when the request
    ``Host`` header differs from the device's configured hostname; ``None``
    when absent on the wire."""
    https: bool | None
    """HTTP-only capability probe. Per upstream spec, only returned when
    called over plain HTTP; ``None`` when absent (the documented behaviour
    over HTTPS). See MVP-OQ-4 for an upstream firmware quirk where some
    devices return this over HTTPS as well."""
    initialized: bool  # True when 'inited' key is ABSENT in the response
    format: str | None
    uptime: int | None
    temp: int | None
    storage: list[str] | None  # PPA only


@dataclass(frozen=True, slots=True)
class DeviceConfig:
    """Result of ``GET /api/system/config``."""

    eid: str
    user: str
    email: str
    hostname: str
    uts: int


@dataclass(frozen=True, slots=True)
class AuthChallenge:
    """Result of ``GET /api/auth/token``."""

    eid: str  # PBKDF2 salt
    spk: str  # device X25519 pubkey, standard base64 with padding
    jti: str  # nonce
    exp: int  # challenge deadline (unix timestamp)
    lbl: str | None  # username/label, may be missing


@dataclass(frozen=True, slots=True)
class CachedToken:
    """A bearer token cached by :class:`encedo_hem.auth.Auth`.

    ``exp`` is already adjusted to ``real_exp - skew_seconds`` so that the
    cache treats tokens as expired slightly before the device does.
    """

    jwt: str
    scope: str
    exp: int


@dataclass(frozen=True, slots=True)
class ParsedKeyType:
    """Parsed form of the comma-separated ``type`` string returned by ``list``/``get``."""

    flags: frozenset[str]  # subset of {"PKEY", "ECDH", "ExDSA"}
    algorithm: str  # last comma-separated element, e.g. "SECP256R1"

    @classmethod
    def parse(cls, raw: str) -> ParsedKeyType:
        """Parse a comma-separated wire string into flags + algorithm."""
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        if not parts:
            return cls(flags=frozenset(), algorithm="")
        return cls(flags=frozenset(parts[:-1]), algorithm=parts[-1])


@dataclass(frozen=True, slots=True)
class KeyInfo:
    """One entry from ``GET /api/keymgmt/list``."""

    kid: KeyId
    label: str
    type: ParsedKeyType
    created: int
    updated: int
    descr: bytes | None


@dataclass(frozen=True, slots=True)
class KeyDetails:
    """Result of ``GET /api/keymgmt/get/<kid>``.

    ``pubkey`` is ``None`` for symmetric key types (AES, HMAC, ...): the
    device omits the field on the wire because there is no public key to
    return. It is only populated for asymmetric types (IT-OQ-1).
    """

    pubkey: bytes | None
    type: ParsedKeyType
    updated: int


@dataclass(frozen=True, slots=True)
class EncryptResult:
    """Result of ``POST /api/crypto/cipher/encrypt``.

    ``iv`` is absent for ECB modes; ``tag`` is present only for AEAD (GCM).
    """

    ciphertext: bytes
    iv: bytes | None
    tag: bytes | None


@dataclass(frozen=True, slots=True)
class HmacResult:
    """Result of ``POST /api/crypto/hmac/hash``."""

    mac: bytes


@dataclass(frozen=True, slots=True)
class SignResult:
    """Result of ``POST /api/crypto/exdsa/sign`` or ``POST /api/crypto/pqc/mldsa/sign``."""

    signature: bytes


@dataclass(frozen=True, slots=True)
class EcdhResult:
    """Result of ``POST /api/crypto/ecdh``."""

    shared_secret: bytes


@dataclass(frozen=True, slots=True)
class WrapResult:
    """Result of ``POST /api/crypto/cipher/wrap``."""

    wrapped: bytes


@dataclass(frozen=True, slots=True)
class MlKemEncapsResult:
    """Result of ``POST /api/crypto/pqc/mlkem/encaps``."""

    ciphertext: bytes
    shared_secret: bytes
    alg: str  # MLKEM512, MLKEM768, or MLKEM1024


@dataclass(frozen=True, slots=True)
class MlKemDecapsResult:
    """Result of ``POST /api/crypto/pqc/mlkem/decaps``."""

    shared_secret: bytes


@dataclass(frozen=True, slots=True)
class SelftestResult:
    """Result of ``GET /api/system/selftest``."""

    last_selftest_ts: int
    fls_state: int
    kat_busy: bool
    se_state: int


@dataclass(frozen=True, slots=True)
class AttestationResult:
    """Result of ``GET /api/system/config/attestation``."""

    crt: str  # PEM certificate
    genuine: bool


@dataclass(frozen=True, slots=True)
class LoggerKeyInfo:
    """Result of ``GET /api/logger/key``."""

    key: str  # audit log public key (base64)
    nonce: str  # current nonce (base64)
    nonce_signed: str  # nonce signed by the device (base64)


@dataclass(frozen=True, slots=True)
class FirmwareCheckResult:
    """Result of a completed ``GET /api/system/upgrade/check_fw`` or ``check_ui`` poll.

    ``raw`` contains the full parsed response body for forward compatibility;
    the exact fields vary by firmware version.
    """

    raw: dict  # type: ignore[type-arg]
