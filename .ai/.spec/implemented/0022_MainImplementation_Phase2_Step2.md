# Phase 2 Step 2: KeyMgmt additions — derive, import_key, search

**File:** `src/encedo_hem/api/keymgmt.py`

Three new methods on the existing `KeyMgmtAPI` class.

---

## `derive(kid, label, type, *, descr, ext_kid, mode, pubkey) -> KeyId`

**Endpoint:** `POST /api/keymgmt/derive`
**Scope:** `keymgmt:ecdh`

**Wire format:**
```
{kid, label, type, descr?, ext_kid?, mode?, pubkey?}  →  {kid}
```

**Parameters:**
- `kid: KeyId` — source key for ECDH derivation (32-char hex).
- `label: str` — label for the derived key (max 31 chars).
- `type: KeyType` — type of key to create.
- `descr: bytes | None` — optional description (max 128 raw bytes, base64-encoded on wire).
- `ext_kid: KeyId | None` — on-device external public key for the ECDH peer. Mutually exclusive with `pubkey`.
- `pubkey: bytes | None` — raw bytes of external public key. Mutually exclusive with `ext_kid`.
- `mode: KeyMode | None` — same OQ-19 defaulting as `create()` for NIST ECC.

**Returns:** new `KeyId`.

**Local validation:**
- `label` max 31 chars.
- `descr` max 128 bytes.
- `ext_kid` and `pubkey` are mutually exclusive (raise `ValueError` if both).

**Error codes:** 400, 401, 403, 406, 409, 418.

---

## `import_key(label, pubkey, type, *, descr, mode) -> KeyId`

**Endpoint:** `POST /api/keymgmt/import`
**Scope:** `keymgmt:imp`

**Wire format:**
```
{label, pubkey, type, mode?, descr?}  →  {kid}
```

**Parameters:**
- `label: str` — max 31 chars.
- `pubkey: bytes` — raw bytes of the public key material (base64-encoded on wire).
- `type: KeyType` — supported types: all ECC, curve, EdDSA, ML-KEM, ML-DSA.
- `descr: bytes | None` — optional description.
- `mode: KeyMode | None` — for NIST ECC, same OQ-19 defaulting as `create()`.

**Returns:** `KeyId`.

**Quirks:**
- **OQ-20:** returns HTTP 406 on duplicate public key. This is expected device behaviour (key deduplication). Surface as `HemNotAcceptableError`. Docstring should note the duplicate-key meaning of 406 on this endpoint.
- Named `import_key` to avoid shadowing the `import` keyword.

**Error codes:** 400, 401, 403, 406 (incl. duplicate), 409, 418.

---

## `search(descr, *, offset, limit) -> Iterator[KeyInfo]`

**Endpoint:** `POST /api/keymgmt/search`
**Scope:** `keymgmt:search`

**Wire format:**
```
{descr, offset?, limit?}  →  {offset, total, listed, list}
```

**Parameters:**
- `descr: str` — search pattern string. Convention (OQ-7): `'^' + base64(raw_prefix)` where `raw_prefix` is ≥6 bytes. Passed as-is (caller encodes).
- `offset: int` — skip entries (default 0). Used internally for pagination.
- `limit: int` — max results per page (default 10, capped at 15 by device).

**Returns:** `Iterator[KeyInfo]` — auto-paginated, same pattern as `list()`.

**Response list entry format:** same as `keymgmt/list` — `{kid, created, type, label, descr, updated}`.

**Quirks:**
- **404 on no match:** device returns HTTP 404 when no keys match (not an empty list). Catch `HemNotFoundError` internally, yield nothing.
- Page size capped at 15 (same as `list()`).
- Unauthenticated path: if `allow_keysearch` is enabled on device and pattern ≥6 bytes, `Authorization` header may be omitted. For simplicity, always authenticate in v0.2; document the unauthenticated option for v0.3+.

**Error codes:** 400, 401, 403, 404 (no match), 406, 409, 418.

---

## Unit tests

- `tests/unit/test_keymgmt_derive.py` — mock 200 response, verify `KeyId` returned, verify scope is `keymgmt:ecdh`, verify body fields.
- `tests/unit/test_keymgmt_import.py` — mock 200 response, verify `KeyId` returned, verify scope is `keymgmt:imp`. Test 406 duplicate → `HemNotAcceptableError`.
- `tests/unit/test_keymgmt_search.py` — mock paginated response. Test 404-on-empty yields nothing. Test `descr` encoding.
