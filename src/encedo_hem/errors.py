"""Exception hierarchy for encedo_hem.

Every device-side failure is mapped to one of these by ``transport.py`` via
:func:`from_status`. Network and TLS failures map to :class:`HemTransportError`.
"""

from __future__ import annotations

from typing import Any


class HemError(Exception):
    """Base class for every error raised by encedo_hem."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        endpoint: str | None = None,
        body: dict[str, Any] | str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.endpoint = endpoint
        self.body = body


class HemTransportError(HemError):
    """Network failure: connection refused, TLS handshake, timeout, DNS, etc."""


class HemBadRequestError(HemError):
    """HTTP 400 -- malformed JSON or invalid argument."""


class HemAuthError(HemError):
    """HTTP 401/403 -- missing/invalid token or wrong scope."""


class HemRtcNotSetError(HemAuthError):
    """HTTP 403 on an unauthenticated auth endpoint -- device RTC is not set.

    The device returns 403 from ``GET /api/auth/token`` and
    ``POST /api/auth/token`` when the RTC clock has not been set via
    check-in.  Run ``client.system.checkin()`` (or use
    ``auto_checkin=True``) before authenticating.
    """


class HemNotFoundError(HemError):
    """HTTP 404 -- endpoint or resource not found."""


class HemNotSupportedError(HemError):
    """Endpoint not available on the current hardware (PPA vs EPA)."""


class HemNotAcceptableError(HemError):
    """HTTP 406 -- device-side rejection (already initialised, ECDH too small, duplicate, ...)."""


class HemDeviceFailureError(HemError):
    """HTTP 409 -- device in a failure state (FLS != 0)."""


class HemPayloadTooLargeError(HemError):
    """HTTP 413 or local pre-flight: POST body would exceed 7300 bytes."""

    def __init__(
        self,
        message: str,
        *,
        size_actual: int,
        size_limit: int = 7300,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.size_actual = size_actual
        self.size_limit = size_limit


class HemTlsRequiredError(HemError):
    """HTTP 418 -- crypto endpoint hit before TLS is operational on the device."""


def from_status(
    status_code: int,
    *,
    endpoint: str,
    body: dict[str, Any] | str | None,
) -> HemError:
    """Map an HTTP status to the appropriate :class:`HemError` subclass."""
    msg = f"{endpoint} returned HTTP {status_code}"
    cls: type[HemError]
    match status_code:
        case 400:
            cls = HemBadRequestError
        case 401 | 403:
            cls = HemAuthError
        case 404:
            cls = HemNotFoundError
        case 406:
            cls = HemNotAcceptableError
        case 409:
            cls = HemDeviceFailureError
        case 413:
            return HemPayloadTooLargeError(
                msg, size_actual=-1, status_code=413, endpoint=endpoint, body=body
            )
        case 418:
            cls = HemTlsRequiredError
        case _:
            cls = HemError
    return cls(msg, status_code=status_code, endpoint=endpoint, body=body)
