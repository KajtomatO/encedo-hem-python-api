"""Python client library for the Encedo HEM REST API."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

from .client import HemClient
from .enums import CipherAlg, HardwareForm, HashAlg, KeyMode, KeyType, Role, SignAlg, WrapAlg
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
    DeviceConfig,
    DeviceStatus,
    DeviceVersion,
    EcdhResult,
    EncryptResult,
    HmacResult,
    KeyDetails,
    KeyId,
    KeyInfo,
    MlKemDecapsResult,
    MlKemEncapsResult,
    ParsedKeyType,
    SignResult,
    WrapResult,
)

try:
    __version__ = _pkg_version("encedo-hem")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0+local"

__all__ = [
    "CipherAlg",
    "DeviceConfig",
    "DeviceStatus",
    "DeviceVersion",
    "EcdhResult",
    "EncryptResult",
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
    "MlKemDecapsResult",
    "MlKemEncapsResult",
    "ParsedKeyType",
    "Role",
    "SignAlg",
    "SignResult",
    "WrapAlg",
    "WrapResult",
    "__version__",
]
