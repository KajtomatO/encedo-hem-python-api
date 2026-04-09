"""Enumerations for the HEM wire protocol.

Each ``.value`` is the **exact** string the device expects on the wire. Do not
rename them. Python identifiers use underscores; values may use dashes.
"""

from __future__ import annotations

from enum import Enum


class Role(Enum):
    """Authentication role: local user (``U``) or local admin (``M``)."""

    USER = "U"
    MASTER = "M"


class HardwareForm(Enum):
    """Form factor of the connected HEM device."""

    PPA = "PPA"  # USB Personal Privacy Assistant
    EPA = "EPA"  # 19" rack Enterprise Privacy Appliance
    UNKNOWN = "UNKNOWN"


class KeyType(Enum):
    """Cryptographic key type as understood by ``keymgmt/create``."""

    AES128 = "AES128"
    AES192 = "AES192"
    AES256 = "AES256"
    SECP256R1 = "SECP256R1"
    SECP384R1 = "SECP384R1"
    SECP521R1 = "SECP521R1"
    SECP256K1 = "SECP256K1"
    CURVE25519 = "CURVE25519"
    CURVE448 = "CURVE448"
    ED25519 = "ED25519"
    ED448 = "ED448"
    SHA2_256 = "SHA2-256"
    SHA2_384 = "SHA2-384"
    SHA2_512 = "SHA2-512"
    SHA3_256 = "SHA3-256"
    SHA3_384 = "SHA3-384"
    SHA3_512 = "SHA3-512"
    MLKEM512 = "MLKEM512"
    MLKEM768 = "MLKEM768"
    MLKEM1024 = "MLKEM1024"
    MLDSA44 = "MLDSA44"
    MLDSA65 = "MLDSA65"
    MLDSA87 = "MLDSA87"

    @property
    def is_nist_ecc(self) -> bool:
        """Return ``True`` if this key type is one of the NIST ECC curves."""
        return self in {
            KeyType.SECP256R1,
            KeyType.SECP384R1,
            KeyType.SECP521R1,
            KeyType.SECP256K1,
        }


class KeyMode(Enum):
    """Mode flag for NIST ECC keys (ignored for other key types)."""

    ECDH = "ECDH"
    EXDSA = "ExDSA"
    ECDH_EXDSA = "ECDH,ExDSA"


class CipherAlg(Enum):
    """Symmetric cipher algorithm + mode for ``crypto/cipher`` operations."""

    AES128_ECB = "AES128-ECB"
    AES192_ECB = "AES192-ECB"
    AES256_ECB = "AES256-ECB"
    AES128_CBC = "AES128-CBC"
    AES192_CBC = "AES192-CBC"
    AES256_CBC = "AES256-CBC"
    AES128_GCM = "AES128-GCM"
    AES192_GCM = "AES192-GCM"
    AES256_GCM = "AES256-GCM"

    @property
    def has_iv(self) -> bool:
        """Return ``True`` for any non-ECB mode."""
        return "ECB" not in self.value

    @property
    def has_tag(self) -> bool:
        """Return ``True`` for AEAD modes (GCM)."""
        return "GCM" in self.value
