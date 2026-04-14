# Phase 2 Step 6: Cipher wrap/unwrap

**File:** `src/encedo_hem/api/crypto.py` (additions to existing `CipherAPI` class)

**Confidence:** Lower — official docs return 404 for these endpoints. Schema recovered from HEM API test suite. Registered in Manager `_endpoints` and `scopes.js` but never called from Manager UI. Integration test required.

---

## `wrap(kid, alg, *, msg) -> WrapResult`

**Endpoint:** `POST /api/crypto/cipher/wrap`
**Scope:** `keymgmt:use:{kid}`

**Wire format:**
```
{kid, alg, msg?}  →  {wrapped}
```

**Parameters:**
- `kid: KeyId` — key ID of an AES key (32-char hex).
- `alg: WrapAlg` — `AES128`, `AES192`, or `AES256`. **Not** the `-ECB`/`-GCM` suffixed forms used in cipher/encrypt.
- `msg: bytes | None` — data to wrap (base64-encoded on wire). If omitted, device generates random data and wraps it.

**Returns:** `WrapResult(wrapped: bytes)`.

**Local validation (when `msg` is provided):**
- Length must be a multiple of 8 bytes (RFC 3394 requirement). Raise `ValueError` if not.
- Length must be ≥16 bytes. Raise `ValueError` if not.

**Notes:**
- Uses NIST AES Key Wrap (RFC 3394), not standard AES encryption.
- Auto-generation mode (no `msg`) is useful for generating random symmetric keys wrapped under a device key.

**Error codes:** 400, 401, 403, 406, 409, 418.

---

## `unwrap(kid, wrapped, *, alg) -> bytes`

**Endpoint:** `POST /api/crypto/cipher/unwrap`
**Scope:** `keymgmt:use:{kid}`

**Wire format:**
```
{kid, alg, msg}  →  {unwrapped}
```

**Parameters:**
- `kid: KeyId` — key ID of an AES key.
- `wrapped: bytes` — wrapped key material (base64-encoded on wire, sent as `msg` field).
- `alg: WrapAlg` — must match the algorithm used for wrapping.

**Returns:** raw unwrapped bytes.

**Error codes:** 400, 401, 403, 406, 409, 418.

---

## Unit test

`tests/unit/test_crypto_wrap.py`:
- Mock wrap response, verify `WrapResult` with base64-decoded wrapped data.
- Mock unwrap response, verify raw bytes returned.
- Test wrap constraint: msg not a multiple of 8 → `ValueError`.
- Test wrap constraint: msg < 16 bytes → `ValueError`.
- Test wrap with no msg → no `msg` field in request body.
- Test `WrapAlg` wire values (`AES128`, `AES192`, `AES256` — no suffix).
