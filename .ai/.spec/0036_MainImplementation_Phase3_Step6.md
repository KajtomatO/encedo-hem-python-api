# Phase 3 Step 6: Upgrade API

**File:** `src/encedo_hem/api/upgrade.py` (new file)

New `UpgradeAPI` class. All endpoints under `GET|POST /api/system/upgrade/...`
require `system:upgrade` scope.

---

## `UpgradeAPI`

```python
class UpgradeAPI:
    def __init__(self, client: HemClient) -> None: ...
```

---

## Firmware upgrade flow: `upload_fw`, `check_fw`, `install_fw`

### `upload_fw(firmware: bytes) -> None`

**Endpoint:** `POST /api/system/upgrade/upload_fw`
**Scope:** `system:upgrade`
**Body:** binary (`application/octet-stream`), filename `fw.bin`

Uses `Transport.post_binary()` (added in Step 2).

### `check_fw() -> FirmwareCheckResult`

**Endpoint:** `GET /api/system/upgrade/check_fw` (poll)
**Scope:** `system:upgrade`
**Polling (OQ-10 resolved):** 4-second interval, up to ~60s total (15 attempts).

Status code semantics (use `Transport.request_no_raise()`):
- `200` — verification done → return `FirmwareCheckResult(raw=body)`
- `201` or `202` — still processing → sleep 4s → retry
- `406` → raise `HemNotAcceptableError("firmware verification failed")`
- Any other non-200 → raise `from_status()`

If max attempts reached without `200`: raise `HemTransportError("check_fw timed out")`.

### `install_fw() -> None`

**Endpoint:** `GET /api/system/upgrade/install_fw`
**Scope:** `system:upgrade`

Triggers firmware installation. The device may reboot. Auth cache should be
treated as invalidated after this call (same as `reboot()`). No response body.
Use a generous timeout (e.g. 60s) for this request.

---

## UI upgrade flow: `upload_ui`, `check_ui`, `install_ui`

Identical structure to firmware, with different paths and a longer polling
cadence for `check_ui` (OQ-10 resolved):

- `upload_ui(firmware: bytes)` → `POST /api/system/upgrade/upload_ui`
- `check_ui()` → `GET /api/system/upgrade/check_ui`
  - **Initial wait:** 60 seconds before the first poll (UI verification is slow).
  - **Poll interval:** 5 seconds.
  - **Max polls:** 24 (2 minutes of polling after initial wait).
  - Same 200/201/202/406 semantics as `check_fw`.
- `install_ui()` → `GET /api/system/upgrade/install_ui`

---

## Bootloader upload: `upload_bootldr`

### `upload_bootldr(bootldr: bytes) -> None`

**Endpoint:** `POST /api/system/upgrade/upload_bootldr`
**Scope:** `system:upgrade`
**Body:** binary (`application/octet-stream`), filename `bootldr.bin`

No `check_bootldr` or `install_bootldr` — the bootloader is written immediately
on upload (or verified and installed in one step). No polling needed.

---

## USB mode: `usbmode`

### `usbmode() -> None`

**Endpoint:** `GET /api/system/upgrade/usbmode`
**Scope:** `system:upgrade`

Enables USB serial (CDC ACM) mode for direct-USB firmware flashing.
Discovered in the HEM test suite only — not exposed in the Manager UI.
No response body.

---

## Helper: `_poll(path, token, *, initial_wait, interval, max_attempts) -> FirmwareCheckResult`

Internal method shared by `check_fw` and `check_ui`. Parameters:
- `initial_wait: float` — seconds to sleep before first poll (0 for `check_fw`, 60 for `check_ui`).
- `interval: float` — seconds between polls.
- `max_attempts: int` — total retries before timeout error.

---

## Unit tests

`tests/unit/test_upgrade.py`:

- `test_upload_fw_uses_binary_transport` — mock POST, assert `application/octet-stream` and `Content-Disposition` headers, assert scope `system:upgrade`.
- `test_check_fw_returns_on_200` — mock sequence `[202, 200]`, assert `FirmwareCheckResult` returned after 2 calls.
- `test_check_fw_raises_on_406` — mock `[202, 406]`, assert `HemNotAcceptableError`.
- `test_check_fw_timeout` — mock all `202` responses, assert `HemTransportError` after max attempts.
- `test_upload_bootldr_no_poll` — mock POST to `upload_bootldr`, assert only one request made.
- `test_usbmode_scope` — mock GET, assert scope `system:upgrade`.
- `test_check_ui_initial_wait` — mock immediate `200`, assert initial wait before poll (mock `time.sleep`).
