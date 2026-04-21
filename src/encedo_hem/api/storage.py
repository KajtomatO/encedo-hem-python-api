"""``client.storage`` -- storage lock/unlock endpoints (PPA only)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..enums import StorageDisk

if TYPE_CHECKING:
    from ..client import HemClient


class StorageAPI:
    """Wrapper around ``/api/storage/*`` endpoints.

    These endpoints are PPA-only. On EPA devices the device itself returns an
    HTTP error which propagates as the appropriate :class:`~encedo_hem.errors.HemError`
    subclass.
    """

    def __init__(self, client: HemClient) -> None:
        self._client = client

    def unlock(self, disk: StorageDisk) -> None:
        """Unlock the specified storage disk.

        The URL ends in ``/ro`` or ``/rw`` to mirror Encedo Manager
        (``build.js:7729``, ``core2.js:5437``); the plain path documented
        in ``encedo-hem-api-doc/storage/unlock.md`` appears to be a no-op
        on current firmware. See OQ-24.
        """
        suffix = "/rw" if disk.value.endswith(":rw") else "/ro"
        scope = f"storage:{disk.value}"
        token = self._client._auth.ensure_token(scope)
        self._client._transport.request(
            "GET", f"/api/storage/unlock{suffix}", token=token
        )

    def lock(self, disk: StorageDisk = StorageDisk.DISK0) -> None:
        """Lock the specified storage disk.

        Scope is ``storage:disk{N}`` (per Encedo Manager ``build.js:1844``
        and HEM test suite ``test_12.php:118``), not the generic
        ``storage:disk`` listed in ``storage/lock.md``. See OQ-25.
        """
        disk_base = disk.value.split(":", 1)[0]
        scope = f"storage:{disk_base}"
        token = self._client._auth.ensure_token(scope)
        self._client._transport.request("GET", "/api/storage/lock", token=token)
