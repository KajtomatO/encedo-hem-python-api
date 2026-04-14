# Phase 2 Step 1: Enums + dataclasses

**Files:** `src/encedo_hem/enums.py`, `src/encedo_hem/models.py`

No network calls. Pure additions to existing files.

## New enums in `enums.py`

```python
class HashAlg(Enum):
    """Hash algorithm for HMAC and ECDH operations."""
    SHA2_256 = "SHA2-256"
    SHA2_384 = "SHA2-384"
    SHA2_512 = "SHA2-512"
    SHA3_256 = "SHA3-256"
    SHA3_384 = "SHA3-384"
    SHA3_512 = "SHA3-512"

class SignAlg(Enum):
    """Signing algorithm for exdsa operations."""
    SHA256_ECDSA = "SHA256WithECDSA"
    SHA384_ECDSA = "SHA384WithECDSA"
    SHA512_ECDSA = "SHA512WithECDSA"
    ED25519 = "Ed25519"
    ED25519PH = "Ed25519ph"
    ED25519CTX = "Ed25519ctx"
    ED448 = "Ed448"
    ED448PH = "Ed448ph"

    @property
    def requires_ctx(self) -> bool:
        """True when the ``ctx`` parameter is mandatory on the wire."""
        return self in {SignAlg.ED25519PH, SignAlg.ED25519CTX, SignAlg.ED448, SignAlg.ED448PH}

class WrapAlg(Enum):
    """AES key-wrap algorithm (RFC 3394). No mode suffix — distinct from CipherAlg."""
    AES128 = "AES128"
    AES192 = "AES192"
    AES256 = "AES256"
```

## New dataclasses in `models.py`

```python
@dataclass(frozen=True, slots=True)
class HmacResult:
    """Result of ``POST /api/crypto/hmac/hash``."""
    mac: bytes  # decoded from base64

@dataclass(frozen=True, slots=True)
class SignResult:
    """Result of ``POST /api/crypto/exdsa/sign`` or ``POST /api/crypto/pqc/mldsa/sign``."""
    signature: bytes  # decoded from base64

@dataclass(frozen=True, slots=True)
class EcdhResult:
    """Result of ``POST /api/crypto/ecdh``."""
    shared_secret: bytes  # decoded from base64, raw or hashed depending on alg

@dataclass(frozen=True, slots=True)
class WrapResult:
    """Result of ``POST /api/crypto/cipher/wrap``."""
    wrapped: bytes  # decoded from base64

@dataclass(frozen=True, slots=True)
class MlKemEncapsResult:
    """Result of ``POST /api/crypto/pqc/mlkem/encaps``."""
    ciphertext: bytes  # decoded from base64, send to peer
    shared_secret: bytes  # decoded from base64, use for symmetric crypto
    alg: str  # MLKEM512, MLKEM768, or MLKEM1024

@dataclass(frozen=True, slots=True)
class MlKemDecapsResult:
    """Result of ``POST /api/crypto/pqc/mlkem/decaps``."""
    shared_secret: bytes  # decoded from base64, matches encapsulator's ss
```
