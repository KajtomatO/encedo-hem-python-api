# Phase 3 Step 5: Logger API

**File:** `src/encedo_hem/api/logger.py` (new file)

New `LoggerAPI` class. All endpoints require `logger:get` scope, except
`delete()` which requires `logger:del`.

---

## `LoggerAPI`

```python
class LoggerAPI:
    def __init__(self, client: HemClient) -> None: ...
```

---

## `key() -> LoggerKeyInfo`

**Endpoint:** `GET /api/logger/key`
**Scope:** `logger:get`

Returns the audit log public key and the current nonce with its device signature.

**Wire response:**
```json
{"key": "<base64>", "nonce": "<base64>", "nonce_signed": "<base64>"}
```

Returns `LoggerKeyInfo` (defined in Step 1).

---

## `list(offset=0) -> Iterator[str]`

**Endpoint:** `GET /api/logger/list/{offset}`
**Scope:** `logger:get`

Returns an auto-paginated iterator over log entry IDs (strings).

**Wire response:**
```json
{"total": 42, "listed": 10, "list": ["<id1>", "<id2>", ...]}
```

- `offset` is embedded in the path: `/api/logger/list/0`, `/api/logger/list/10`, etc.
- Pagination: if `listed < total`, advance offset by `listed` and fetch again.
- Yields each ID string from `list[]`.

**Note:** Unlike `keymgmt/list`, there is no configurable page size — the device
controls page size via `listed`. Always start at offset 0.

---

## `get(entry_id: str) -> str`

**Endpoint:** `GET /api/logger/{entry_id}`
**Scope:** `logger:get`

Returns the raw log entry as a plain-text string.

**Wire response:** plain text body (not JSON). The transport's `_safe_parse_body`
will return `None`; raw bytes must be decoded separately.

**Implementation note:** This endpoint does NOT return JSON. Add a
`Transport.request_text(method, path, *, token) -> str` helper, OR call
`_device.request(...)` directly in `logger.py` and decode `response.text`.
The preferred approach is a dedicated `request_text()` method on `Transport`
so error handling stays consistent.

**Wire:** `GET /api/logger/{entry_id}` → `Content-Type: text/plain` (or similar).
Decode as UTF-8.

---

## `delete(entry_id: str) -> None`

**Endpoint:** `DELETE /api/logger/{entry_id}`
**Scope:** `logger:del`

Deletes the log entry. No response body.

---

## Transport addition required

Add `Transport.request_text(method, path, *, token=None) -> str`:
- Same structure as `request()` but returns `response.text` instead of parsed JSON.
- Raises `HemTransportError` on network errors, `from_status()` on non-200.

---

## Unit tests

`tests/unit/test_logger.py`:

- `test_key_returns_logger_key_info` — mock GET, assert `LoggerKeyInfo` fields.
- `test_list_paginates` — two-page mock (total=15, listed=10 then listed=5), assert 15 IDs yielded.
- `test_get_returns_text` — mock GET returning `text/plain`, assert string returned.
- `test_delete_uses_del_scope` — mock DELETE, assert `logger:del` scope in auth request.
- `test_delete_path` — assert request goes to `/api/logger/{id}` with DELETE method.
