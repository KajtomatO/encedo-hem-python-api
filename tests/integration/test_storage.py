"""Integration tests for storage lock/unlock (PPA only)."""

from __future__ import annotations

import time

import pytest

from encedo_hem import HardwareForm, HemClient, StorageDisk

_STORAGE_SETTLE_S = 5
"""Seconds to wait after unlock before locking — the device OS needs time
to register the disk state change.  Mirrors ``hem-api-tester/test_12.php``
which uses ``sleep(5)`` between every unlock/lock pair."""


def _require_ppa(hem: HemClient) -> None:
    version = hem.system.version()
    if version.hardware != HardwareForm.PPA:
        pytest.skip(f"storage is PPA-only (device is {version.hardware.value})")


def test_storage_unlock_disk0_and_lock(hem: HemClient) -> None:
    _require_ppa(hem)
    hem.storage.unlock(StorageDisk.DISK0)
    time.sleep(_STORAGE_SETTLE_S)
    hem.storage.lock(StorageDisk.DISK0)


def test_storage_unlock_disk0_rw_and_lock(hem: HemClient) -> None:
    _require_ppa(hem)
    hem.storage.unlock(StorageDisk.DISK0_RW)
    time.sleep(_STORAGE_SETTLE_S)
    hem.storage.lock(StorageDisk.DISK0_RW)
