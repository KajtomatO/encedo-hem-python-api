# Phase 3 Step 2: Transport additions

**File:** `src/encedo_hem/transport.py`

Two new methods on the existing `Transport` class.

---

## `post_binary(path, body, filename, *, token) -> dict[str, Any]`

Used for firmware and bootloader upload.

**Wire format (OQ-9 resolved):**
- Method: `POST`
- `Content-Type: application/octet-stream`
- `Content-Disposition: attachment; filename="{filename}"`
- `Expect: 100-continue`
- Body: raw bytes

**Signature:**
```python
def post_binary(
    self,
    path: str,
    body: bytes,
    filename: str,
    *,
    token: str | None = None,
) -> dict[str, Any]:
```

**Implementation notes:**
- No `MAX_BODY_BYTES` guard — firmware binaries are expected to be much larger.
- `Expect: 100-continue` is set via the headers dict; httpx honours it.
- Error handling identical to `request()`: non-200 → `from_status()`.

---

## `request_no_raise(method, path, *, token) -> tuple[int, dict[str, Any]]`

Low-level method for polling endpoints that use status codes to signal progress
(200 = done, 201/202 = in-progress, 406 = failed).

**Signature:**
```python
def request_no_raise(
    self,
    method: str,
    path: str,
    *,
    token: str | None = None,
) -> tuple[int, dict[str, Any]]:
```

**Returns:** `(status_code, body_dict)` where `body_dict` is `{}` when the body is absent
or unparseable. **Never raises** for HTTP-level errors; only raises on network errors
(`HemTransportError`).

**Usage:** Polling loops in `upgrade.py` call this directly to inspect the status code.

---

## Unit tests

- `tests/unit/test_transport_binary.py`:
  - Mock a POST endpoint, assert `Content-Type: application/octet-stream` header present.
  - Assert `Content-Disposition: attachment; filename="fw.bin"` header present.
  - Assert non-200 response raises the correct `HemError` subclass.
- `tests/unit/test_transport_no_raise.py`:
  - Mock a GET endpoint returning 202; assert `(202, {})` is returned without raising.
  - Mock a GET endpoint returning 200 with JSON body; assert body is parsed.
