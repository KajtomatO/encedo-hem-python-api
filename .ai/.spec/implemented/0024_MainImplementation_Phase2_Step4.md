# Phase 2 Step 4: ExdsaAPI

**File:** `src/encedo_hem/api/crypto.py` (new `ExdsaAPI` class)

---

## `sign(kid, msg, alg, *, ctx) -> SignResult`

**Endpoint:** `POST /api/crypto/exdsa/sign`
**Scope:** `keymgmt:use:{kid}`

**Wire format:**
```
{kid, msg, alg, ctx?}  →  {sign}
```

**Parameters:**
- `kid: KeyId` — key ID (32-char hex).
- `msg: bytes` — message to sign (max 2048 bytes plaintext, base64-encoded on wire).
- `alg: SignAlg` — **required**. One of: `SHA256WithECDSA`, `SHA384WithECDSA`, `SHA512WithECDSA`, `Ed25519`, `Ed25519ph`, `Ed25519ctx`, `Ed448`, `Ed448ph`.
- `ctx: bytes | None` — context data (max 255 bytes, base64-encoded on wire). **Required** when `alg.requires_ctx` is True.

**Returns:** `SignResult(signature: bytes)`.

**Local validation:**
- If `alg.requires_ctx` and `ctx is None`, raise `ValueError("ctx is required for {alg}")`.
- `ctx` max 255 bytes.
- `msg` max 2048 bytes.

**`ctx` requirement by algorithm:**
| Algorithm | `ctx` required? |
|---|---|
| `SHA256WithECDSA` | No |
| `SHA384WithECDSA` | No |
| `SHA512WithECDSA` | No |
| `Ed25519` | No |
| `Ed25519ph` | **Yes** |
| `Ed25519ctx` | **Yes** |
| `Ed448` | **Yes** |
| `Ed448ph` | **Yes** |

**Quirks:**
- OQ-19: if the key was created without `mode: "ExDSA"` or `"ECDH,ExDSA"`, the device returns 406. The library's `keys.create()` defaults NIST ECC to `ECDH,ExDSA`, but imported keys or keys created with explicit `mode=ECDH` will fail. Docstring notes this.

**Error codes:** 400, 401, 403, 406, 409, 418.

---

## `verify(kid, msg, signature, alg, *, ctx) -> bool`

**Endpoint:** `POST /api/crypto/exdsa/verify`
**Scope:** `keymgmt:use:{kid}`

**Wire format:**
```
{kid, msg, sign, alg, ctx?}  →  200 (valid) / 406 (invalid)
```

**Parameters:**
- `kid: KeyId` — key ID.
- `msg: bytes` — original message (max 2048 bytes, base64-encoded on wire).
- `signature: bytes` — signature to verify (base64-encoded on wire, wire field name is `sign`).
- `alg: SignAlg` — **required**.
- `ctx: bytes | None` — context data (max 255 bytes). Same requirements as `sign`.

**Returns:** `True` on HTTP 200, `False` on HTTP 406.

**Implementation:** catch `HemNotAcceptableError` (406) internally and return `False`. OQ-12: no response body either way.

**Error codes:** 400, 401, 403, 406 (verification failed), 409, 418.

---

## Unit test

`tests/unit/test_crypto_exdsa.py`:
- Mock sign response, verify `SignResult` with base64-decoded signature.
- Test verify returns `True` on 200, `False` on 406.
- Test `ctx` required for `Ed25519ph` — raises `ValueError` if missing.
- Test `ctx` not required for `Ed25519` — no error when omitted.
- Test `alg` wire value matches `SignAlg.value`.
