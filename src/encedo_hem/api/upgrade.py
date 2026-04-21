"""``client.upgrade`` -- firmware and UI upgrade endpoints."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from ..errors import HemNotAcceptableError, HemTransportError, from_status
from ..models import FirmwareCheckResult

if TYPE_CHECKING:
    from ..client import HemClient


class UpgradeAPI:
    """Wrapper around ``/api/system/upgrade/*`` endpoints.

    All endpoints require ``system:upgrade`` scope.

    Firmware upgrade workflow::

        hem.upgrade.upload_fw(fw_bytes)   # upload binary
        result = hem.upgrade.check_fw()   # poll until verified (4 s interval)
        hem.upgrade.install_fw()          # trigger install + reboot

    The same pattern applies for the UI (``upload_ui`` / ``check_ui`` /
    ``install_ui``), with a 60-second initial wait before polling.
    """

    def __init__(self, client: HemClient) -> None:
        self._client = client

    # --- firmware ---

    def upload_fw(self, firmware: bytes) -> None:
        """Upload a firmware binary.

        Uses binary transport (``application/octet-stream`` +
        ``Content-Disposition`` + ``Expect: 100-continue``).
        """
        token = self._client._auth.ensure_token("system:upgrade")
        self._client._transport.post_binary(
            "/api/system/upgrade/upload_fw", firmware, "fw.bin", token=token
        )

    def check_fw(self) -> FirmwareCheckResult:
        """Poll until firmware verification completes.

        Polls every 4 seconds for up to ~60 seconds (15 attempts).

        Returns :class:`~encedo_hem.models.FirmwareCheckResult` on success.
        Raises :class:`~encedo_hem.errors.HemNotAcceptableError` on verification
        failure (HTTP 406). Raises :class:`~encedo_hem.errors.HemTransportError`
        on timeout.

        OQ-10 (resolved): check_fw polls every 4 s.
        """
        return self._poll(
            "/api/system/upgrade/check_fw",
            initial_wait=0.0,
            interval=4.0,
            max_attempts=15,
        )

    def install_fw(self) -> None:
        """Install the verified firmware and reboot the device.

        The device will reboot; all cached tokens are invalidated.
        """
        token = self._client._auth.ensure_token("system:upgrade")
        self._client._transport.request("GET", "/api/system/upgrade/install_fw", token=token)
        self._client._auth.invalidate()

    # --- UI ---

    def upload_ui(self, firmware: bytes) -> None:
        """Upload a UI firmware binary."""
        token = self._client._auth.ensure_token("system:upgrade")
        self._client._transport.post_binary(
            "/api/system/upgrade/upload_ui", firmware, "ui.bin", token=token
        )

    def check_ui(self) -> FirmwareCheckResult:
        """Poll until UI verification completes.

        Waits 60 seconds before the first poll, then every 5 seconds for up
        to 24 additional polls (~2 minutes of polling total).

        OQ-10 (resolved): check_ui initial wait 60 s, then 5 s interval.
        """
        return self._poll(
            "/api/system/upgrade/check_ui",
            initial_wait=60.0,
            interval=5.0,
            max_attempts=24,
        )

    def install_ui(self) -> None:
        """Install the verified UI and reboot the device."""
        token = self._client._auth.ensure_token("system:upgrade")
        self._client._transport.request("GET", "/api/system/upgrade/install_ui", token=token)
        self._client._auth.invalidate()

    # --- bootloader ---

    def upload_bootldr(self, bootldr: bytes) -> None:
        """Upload a bootloader binary.

        No check or install step — the bootloader is written immediately.
        """
        token = self._client._auth.ensure_token("system:upgrade")
        self._client._transport.post_binary(
            "/api/system/upgrade/upload_bootldr", bootldr, "bootldr.bin", token=token
        )

    # --- USB mode ---

    def usbmode(self) -> None:
        """Enable USB serial (CDC ACM) mode for direct-USB firmware flashing.

        Discovered in the HEM test suite only — not exposed in the Manager UI.
        """
        token = self._client._auth.ensure_token("system:upgrade")
        self._client._transport.request("GET", "/api/system/upgrade/usbmode", token=token)

    # --- internal ---

    def _poll(
        self,
        path: str,
        *,
        initial_wait: float,
        interval: float,
        max_attempts: int,
    ) -> FirmwareCheckResult:
        """Poll ``path`` until 200 (done), 406 (failed), or timeout.

        HTTP 201/202 = still processing → sleep ``interval`` → retry.
        """
        token = self._client._auth.ensure_token("system:upgrade")
        if initial_wait > 0:
            time.sleep(initial_wait)
        for _ in range(max_attempts):
            status, body = self._client._transport.request_no_raise("GET", path, token=token)
            if status == 200:
                return FirmwareCheckResult(raw=body)
            if status == 406:
                raise HemNotAcceptableError(
                    f"{path}: firmware verification failed",
                    endpoint=path,
                )
            if status not in (201, 202):
                raise from_status(status, endpoint=path, body=body)
            time.sleep(interval)
        raise HemTransportError(
            f"{path}: timed out after {max_attempts} attempts",
            endpoint=path,
        )
