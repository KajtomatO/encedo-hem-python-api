"""Python client library for the Encedo HEM REST API."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

from .client import HemClient
from .enums import CipherAlg, HardwareForm, KeyMode, KeyType, Role
from .errors import (
    HemAuthError,
    HemBadRequestError,
    HemDeviceFailureError,
    HemError,
    HemNotAcceptableError,
    HemNotFoundError,
    HemNotSupportedError,
    HemPayloadTooLargeError,
    HemTlsRequiredError,
    HemTransportError,
)
from .models import (
    DeviceConfig,
    DeviceStatus,
    DeviceVersion,
    EncryptResult,
    KeyDetails,
    KeyId,
    KeyInfo,
    ParsedKeyType,
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
    "EncryptResult",
    "HardwareForm",
    "HemAuthError",
    "HemBadRequestError",
    "HemClient",
    "HemDeviceFailureError",
    "HemError",
    "HemNotAcceptableError",
    "HemNotFoundError",
    "HemNotSupportedError",
    "HemPayloadTooLargeError",
    "HemTlsRequiredError",
    "HemTransportError",
    "KeyDetails",
    "KeyId",
    "KeyInfo",
    "KeyMode",
    "KeyType",
    "ParsedKeyType",
    "Role",
    "__version__",
]
