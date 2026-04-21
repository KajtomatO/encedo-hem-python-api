# Phase 3 Step 1: Models and enums

**Files:** `src/encedo_hem/enums.py`, `src/encedo_hem/models.py`

No network calls. Pure additions to existing files.

---

## New enum in `enums.py`

```python
class StorageDisk(Enum):
    """Disk selector + mode for storage unlock/lock (PPA only).

    The enum value is used directly in the URL path and scope.
    """
    DISK0 = "disk0"
    DISK0_RW = "disk0:rw"
    DISK1 = "disk1"
    DISK1_RW = "disk1:rw"
```

---

## New dataclasses in `models.py`

```python
@dataclass(frozen=True, slots=True)
class SelftestResult:
    """Result of ``GET /api/system/selftest``."""
    last_selftest_ts: int
    fls_state: int
    kat_busy: bool
    se_state: int


@dataclass(frozen=True, slots=True)
class AttestationResult:
    """Result of ``GET /api/system/config/attestation``."""
    crt: str    # PEM certificate
    genuine: bool


@dataclass(frozen=True, slots=True)
class LoggerKeyInfo:
    """Result of ``GET /api/logger/key``."""
    key: str            # audit log public key (base64)
    nonce: str          # current nonce (base64)
    nonce_signed: str   # nonce signed by the device (base64)


@dataclass(frozen=True, slots=True)
class FirmwareCheckResult:
    """Result of a completed ``GET /api/system/upgrade/check_fw`` or ``check_ui`` poll.

    ``ver`` and other fields may be absent depending on firmware version.
    """
    raw: dict[str, object]  # full parsed response body, for forward compatibility
```

**Note on `SelftestResult`:** The wire response may contain additional fields not
listed above (`se_state` structure varies by device). Only the stable fields are
mapped; the rest are discarded. If more fields are needed, add them later.

**Note on `FirmwareCheckResult`:** The exact body of the 200 response from
`check_fw` / `check_ui` is not fully specified in the current API doc. Use `raw`
for now; refine in a later pass once a real response is captured.
