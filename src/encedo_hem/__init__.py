"""Python client library for the Encedo HEM REST API."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

from .client import HemClient
from .enums import (
    CipherAlg,
    HardwareForm,
    HashAlg,
    KeyMode,
    KeyType,
    Role,
    SignAlg,
    StorageDisk,
    WrapAlg,
)
from .errors import (
    HemAuthError,
    HemBadRequestError,
    HemDeviceFailureError,
    HemError,
    HemNotAcceptableError,
    HemNotFoundError,
    HemNotSupportedError,
    HemPayloadTooLargeError,
    HemRtcNotSetError,
    HemTlsRequiredError,
    HemTransportError,
)
from .models import (
    AttestationResult,
    DeviceConfig,
    DeviceStatus,
    DeviceVersion,
    EcdhResult,
    EncryptResult,
    FirmwareCheckResult,
    HmacResult,
    KeyDetails,
    KeyId,
    KeyInfo,
    LoggerKeyInfo,
    MlKemDecapsResult,
    MlKemEncapsResult,
    ParsedKeyType,
    SelftestResult,
    SignResult,
    WrapResult,
)

try:
    __version__ = _pkg_version("encedo-hem")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0+local"

__all__ = [
    "AttestationResult",
    "CipherAlg",
    "DeviceConfig",
    "DeviceStatus",
    "DeviceVersion",
    "EcdhResult",
    "EncryptResult",
    "FirmwareCheckResult",
    "HardwareForm",
    "HashAlg",
    "HemAuthError",
    "HemBadRequestError",
    "HemClient",
    "HemDeviceFailureError",
    "HemError",
    "HemNotAcceptableError",
    "HemNotFoundError",
    "HemNotSupportedError",
    "HemPayloadTooLargeError",
    "HemRtcNotSetError",
    "HemTlsRequiredError",
    "HemTransportError",
    "HmacResult",
    "KeyDetails",
    "KeyId",
    "KeyInfo",
    "KeyMode",
    "KeyType",
    "LoggerKeyInfo",
    "MlKemDecapsResult",
    "MlKemEncapsResult",
    "ParsedKeyType",
    "Role",
    "SelftestResult",
    "SignAlg",
    "SignResult",
    "StorageDisk",
    "WrapAlg",
    "WrapResult",
    "__version__",
]
