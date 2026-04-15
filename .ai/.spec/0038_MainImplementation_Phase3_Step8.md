# Phase 3 Step 8: Integration tests

**Files:** `tests/integration/` — one file per API group

**Dependencies:** Steps 1–7 complete. Follows the same patterns as existing
integration tests: `hem` fixture from `conftest.py`, `finally` blocks for
cleanup.

**Important:** Upgrade tests require actual firmware/bootloader binaries.
Skip with a fixture-level mark when test assets are not present on disk.
Logger tests depend on log entries existing on the device — create a key
operation first to generate a log event, then fetch/delete.

---

## File map

| File | Endpoint(s) |
|---|---|
| `test_system_additions.py` | `system/selftest`, `system/config/attestation`, `system/reboot`, `system/shutdown` |
| `test_storage.py` | `storage/unlock`, `storage/lock` |
| `test_logger.py` | `logger/key`, `logger/list`, `logger/get`, `logger/delete` |
| `test_upgrade_fw.py` | `upgrade/upload_fw`, `upgrade/check_fw`, `upgrade/install_fw` |
| `test_upgrade_ui.py` | `upgrade/upload_ui`, `upgrade/check_ui`, `upgrade/install_ui` |
| `test_upgrade_misc.py` | `upgrade/upload_bootldr`, `upgrade/usbmode` |

**`config/provisioning`** is not tested — one-time operation with no safe teardown.

---

## Per-file test plan

### `test_system_additions.py`

```python
def test_selftest(hem: HemClient) -> None:
    result = hem.system.selftest()
    assert isinstance(result.fls_state, int)
    assert isinstance(result.kat_busy, bool)

def test_config_attestation(hem: HemClient) -> None:
    result = hem.system.config_attestation()
    assert result.crt  # non-empty PEM string
    assert isinstance(result.genuine, bool)
```

**`test_reboot`** — runs in normal suite. Records uptime before reboot, calls
`hem.system.reboot()`, then polls `hem.system.version()` (unauthenticated) every
1s until it responds or 20s timeout. After recovery, re-authenticates and verifies
uptime decreased.

```python
_REBOOT_TIMEOUT = 20  # seconds

def test_reboot(hem: HemClient) -> None:
    uptime_before = hem.system.status().uptime
    hem.system.reboot()  # invalidates all tokens
    # Wait for device to come back up (unauthenticated probe).
    deadline = time.monotonic() + _REBOOT_TIMEOUT
    while time.monotonic() < deadline:
        try:
            hem.system.version()
            break
        except Exception:
            time.sleep(1.0)
    else:
        pytest.fail(f"device did not come back within {_REBOOT_TIMEOUT}s")
    # Re-authenticate and verify uptime reset.
    uptime_after = hem.system.status().uptime
    if uptime_before is not None and uptime_after is not None:
        assert uptime_after < uptime_before
```

**`test_shutdown`** — skipped in normal suite via `HEM_ALLOW_SHUTDOWN` env var.
Run manually with `HEM_ALLOW_SHUTDOWN=1 pytest tests/integration/test_system_additions.py::test_shutdown`.

```python
def test_shutdown(hem: HemClient) -> None:
    if not os.environ.get("HEM_ALLOW_SHUTDOWN"):
        pytest.skip("set HEM_ALLOW_SHUTDOWN=1 to run")
    hem.system.shutdown()
    # Device should stop responding within a few seconds.
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            hem.system.version()
            time.sleep(1.0)
        except Exception:
            return  # expected — device is down
    pytest.fail("device still responding after shutdown")
```

### `test_storage.py`

**PPA-only.** The `hem` fixture connects to whatever device is configured.
Skip the whole module if device is EPA (check `hem.system.version().hardware`).

```python
def test_storage_unlock_lock(hem: HemClient) -> None:
    version = hem.system.version()
    if version.hardware != HardwareForm.PPA:
        pytest.skip("storage is PPA-only")
    hem.storage.unlock(StorageDisk.DISK0)
    hem.storage.lock()
```

Test both `DISK0` and `DISK0_RW` if available; at minimum test one unlock + lock round-trip.

### `test_logger.py`

```python
def test_logger_key(hem: HemClient) -> None:
    info = hem.logger.key()
    assert info.key  # non-empty

def test_logger_list_and_get(hem: HemClient) -> None:
    # Perform an operation to ensure at least one log entry exists.
    hem.system.selftest()
    ids = list(hem.logger.list())
    assert len(ids) > 0
    entry_text = hem.logger.get(ids[0])
    assert isinstance(entry_text, str)

def test_logger_delete(hem: HemClient) -> None:
    hem.system.selftest()
    ids = list(hem.logger.list())
    assert ids, "need at least one log entry to delete"
    hem.logger.delete(ids[-1])  # delete the last entry
    # Verify deletion: re-list and confirm id is gone
    ids_after = list(hem.logger.list())
    assert ids[-1] not in ids_after
```

### `test_upgrade_fw.py`

```python
FW_PATH = pathlib.Path(os.environ.get("HEM_FW_PATH", ""))

def test_upload_and_check_fw(hem: HemClient) -> None:
    if not FW_PATH.is_file():
        pytest.skip("HEM_FW_PATH not set or file not found")
    fw_bytes = FW_PATH.read_bytes()
    hem.upgrade.upload_fw(fw_bytes)
    result = hem.upgrade.check_fw()
    assert result.raw  # non-empty body

@pytest.mark.skip(reason="destructive — installs firmware and reboots device")
def test_install_fw(hem: HemClient) -> None: ...
```

### `test_upgrade_ui.py`

```python
UI_PATH = pathlib.Path(os.environ.get("HEM_UI_PATH", ""))

def test_upload_and_check_ui(hem: HemClient) -> None:
    if not UI_PATH.is_file():
        pytest.skip("HEM_UI_PATH not set or file not found")
    ui_bytes = UI_PATH.read_bytes()
    hem.upgrade.upload_ui(ui_bytes)
    result = hem.upgrade.check_ui()
    assert result.raw

@pytest.mark.skip(reason="destructive — installs UI and reboots device")
def test_install_ui(hem: HemClient) -> None: ...
```

### `test_upgrade_misc.py`

```python
BL_PATH = pathlib.Path(os.environ.get("HEM_BL_PATH", ""))

def test_upload_bootldr(hem: HemClient) -> None:
    if not BL_PATH.is_file():
        pytest.skip("HEM_BL_PATH not set or file not found")
    hem.upgrade.upload_bootldr(BL_PATH.read_bytes())

@pytest.mark.skip(reason="enables USB mode — may disrupt TCP connectivity")
def test_usbmode(hem: HemClient) -> None: ...
```

---

## Common imports

```python
import os
import pathlib
import time

import pytest

from encedo_hem import (
    FirmwareCheckResult,
    HardwareForm,
    HemClient,
    LoggerKeyInfo,
    SelftestResult,
    StorageDisk,
)
```
