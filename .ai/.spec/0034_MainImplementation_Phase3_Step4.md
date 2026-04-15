# Phase 3 Step 4: Storage API

**File:** `src/encedo_hem/api/storage.py` (new file)

New `StorageAPI` class. PPA-only endpoints — EPA devices will receive an HTTP
error from the device; let it propagate naturally (the device returns an error
that maps to `HemNotSupportedError` or similar; no client-side hardware check).

---

## `StorageAPI`

```python
class StorageAPI:
    def __init__(self, client: HemClient) -> None: ...
```

---

## `unlock(disk: StorageDisk) -> None`

**Endpoint:** `GET /api/storage/unlock/{disk.value}`
**Scope:** `storage:{disk.value}` (e.g. `storage:disk0:rw`)

Unlocks the specified storage disk in the mode encoded in `disk`.

**Examples:**
- `unlock(StorageDisk.DISK0)` → `GET /api/storage/unlock/disk0`, scope `storage:disk0`
- `unlock(StorageDisk.DISK1_RW)` → `GET /api/storage/unlock/disk1:rw`, scope `storage:disk1:rw`

No response body expected.

---

## `lock() -> None`

**Endpoint:** `GET /api/storage/lock`
**Scope:** `storage:disk`

Locks all storage. No response body.

---

## Unit tests

`tests/unit/test_storage.py`:

- `test_unlock_disk0_scope` — mock GET, assert `storage:disk0` scope in auth request.
- `test_unlock_disk1_rw_scope` — assert `storage:disk1:rw` scope and correct path.
- `test_lock_scope` — mock GET, assert `storage:disk` scope.
- `test_lock_path` — assert request goes to `/api/storage/lock`.
