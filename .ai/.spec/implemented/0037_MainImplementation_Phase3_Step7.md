# Phase 3 Step 7: Client wiring and exports

**Files:** `src/encedo_hem/client.py`, `src/encedo_hem/__init__.py`

Wire up the three new API objects and export new public types.

---

## `client.py` changes

Three new sub-namespaces on `HemClient`:

```python
from .api.storage import StorageAPI
from .api.logger import LoggerAPI
from .api.upgrade import UpgradeAPI

class HemClient:
    # existing: self.system, self.keys, self.crypto
    self.storage: StorageAPI   # new
    self.logger: LoggerAPI     # new
    self.upgrade: UpgradeAPI   # new
```

All three are instantiated in `__init__` the same way as the existing sub-APIs.

---

## `__init__.py` additions

Add to imports and `__all__`:

```python
from .enums import StorageDisk
from .models import (
    SelftestResult,
    AttestationResult,
    LoggerKeyInfo,
    FirmwareCheckResult,
)
```

No new error types — all errors already exist in `errors.py`.

---

## No unit tests for this step

The wiring is verified by the integration tests in Step 8.
