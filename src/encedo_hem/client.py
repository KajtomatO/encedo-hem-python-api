""":class:`HemClient` -- the user-facing facade.

The client owns the transport, the auth state, and three API namespaces:

- ``client.system`` -- :class:`encedo_hem.api.system.SystemAPI`
- ``client.keys`` -- :class:`encedo_hem.api.keymgmt.KeyMgmtAPI`
- ``client.crypto`` -- :class:`encedo_hem.api.crypto.CryptoAPI`

Use it as a context manager so the underlying httpx clients are closed and
the in-memory passphrase buffer is best-effort zeroed.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from enum import Enum

from .api.crypto import CryptoAPI
from .api.keymgmt import KeyMgmtAPI
from .api.system import SystemAPI
from .auth import Auth
from .enums import HardwareForm, Role
from .errors import HemNotSupportedError
from .models import DeviceStatus, DeviceVersion
from .transport import Transport

_log = logging.getLogger(__name__)


class _ReadyState(Enum):
    NOT_READY = "not_ready"
    READY = "ready"


class HemClient:
    """High-level HEM client."""

    def __init__(
        self,
        host: str,
        passphrase: str | Callable[[], str],
        *,
        role: Role = Role.USER,
        auto_checkin: bool = True,
        strict_hardware: bool = True,
        timeout: float = 30.0,
    ) -> None:
        self._host = host
        self._role = role
        self._auto_checkin = auto_checkin
        self._strict_hardware = strict_hardware
        self._ready = _ReadyState.NOT_READY
        self._version: DeviceVersion | None = None
        self._last_status: DeviceStatus | None = None

        self._passphrase_buf: bytearray | None
        self._passphrase_provider: Callable[[], bytes]
        if callable(passphrase):
            self._passphrase_buf = None
            _provider = passphrase

            def _from_callable() -> bytes:
                return _provider().encode("utf-8")

            self._passphrase_provider = _from_callable
        else:
            self._passphrase_buf = bytearray(passphrase.encode("utf-8"))

            def _from_buffer() -> bytes:
                return bytes(self._passphrase_buf or b"")

            self._passphrase_provider = _from_buffer

        self._transport = Transport(host, timeout=timeout)
        self._auth = Auth(self._transport, self._passphrase_provider)

        self.system = SystemAPI(self)
        self.keys = KeyMgmtAPI(self)
        self.crypto = CryptoAPI(self)

    # --- lifecycle ---

    def __enter__(self) -> HemClient:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def close(self) -> None:
        """Best-effort zero the passphrase buffer and close both httpx clients."""
        if self._passphrase_buf is not None:
            for i in range(len(self._passphrase_buf)):
                self._passphrase_buf[i] = 0
            self._passphrase_buf = None
        self._transport.close()

    # --- introspection ---

    @property
    def hardware(self) -> HardwareForm:
        """Hardware form factor (PPA/EPA/UNKNOWN). Set by :meth:`ensure_ready`."""
        return self._version.hardware if self._version else HardwareForm.UNKNOWN

    @property
    def firmware_version(self) -> str | None:
        """Firmware version string, or ``None`` before :meth:`ensure_ready`."""
        return self._version.fwv if self._version else None

    @property
    def username(self) -> str | None:
        """Username advertised by the most recent auth challenge."""
        return self._auth.username

    @property
    def last_status(self) -> DeviceStatus | None:
        """The most recent :class:`DeviceStatus` snapshot, if any."""
        return self._last_status

    # --- readiness ---

    def ensure_ready(self) -> None:
        """Fetch version + status and (optionally) run an automatic check-in."""
        if self._ready is _ReadyState.READY:
            return
        self._version = self.system.version()
        self._last_status = self.system.status()
        if self._last_status.fls_state != 0:
            _log.warning(
                "device fls_state=%d -- some operations may be rejected",
                self._last_status.fls_state,
            )
        if self._auto_checkin and self._last_status.ts is None:
            _log.info("RTC unset; running automatic check-in")
            self.system.checkin()
            self._last_status = self.system.status()
        self._ready = _ReadyState.READY

    # --- hardware-aware error helper ---

    def _require_hardware(self, allowed: HardwareForm, endpoint: str) -> None:
        if not self._strict_hardware:
            return
        if self.hardware is HardwareForm.UNKNOWN:
            return
        if self.hardware is not allowed:
            raise HemNotSupportedError(
                f"{endpoint} is only available on {allowed.value}, "
                f"this device is {self.hardware.value}",
                endpoint=endpoint,
            )
