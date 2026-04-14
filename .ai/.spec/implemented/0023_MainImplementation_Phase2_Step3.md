# Phase 2 Step 3: HmacAPI

**File:** `src/encedo_hem/api/crypto.py` (new `HmacAPI` class)

---

## `hash(kid, msg, *, alg, ext_kid, pubkey) -> HmacResult`

**Endpoint:** `POST /api/crypto/hmac/hash`
**Scope:** `keymgmt:use:{kid}`

**Wire format:**
```
{kid, msg, alg?, ext_kid?, pubkey?}  →  {mac}
```

**Parameters:**
- `kid: KeyId` — key ID (32-char hex).
- `msg: bytes` — message to hash (max 2048 bytes plaintext, base64-encoded on wire).
- `alg: HashAlg | None` — hash algorithm. Optional (device has a default, likely SHA2-256).
- `ext_kid: KeyId | None` — external key ID for ECDH-derived HMAC key. Mutually exclusive with `pubkey`.
- `pubkey: bytes | None` — raw external public key for ECDH-derived HMAC key. Mutually exclusive with `ext_kid`.

**Returns:** `HmacResult(mac: bytes)`.

**ECDH-derived key mechanism:** when `ext_kid` or `pubkey` is provided, the HMAC key is derived as `Hash(X25519(kid_priv, peer_pub))` where `Hash` uses the `alg` field. The same algorithm is used for both derivation and the HMAC itself.

**Error codes:** 400, 401, 403, 406, 409, 418.

---

## `verify(kid, msg, mac, *, alg, ext_kid, pubkey) -> bool`

**Endpoint:** `POST /api/crypto/hmac/verify`
**Scope:** `keymgmt:use:{kid}`

**Wire format:**
```
{kid, msg, mac, alg?, ext_kid?, pubkey?}  →  200 (valid) / 406 (invalid)
```

**Parameters:**
- `kid: KeyId` — key ID.
- `msg: bytes` — original message (max 2048 bytes, base64-encoded on wire).
- `mac: bytes` — MAC value to verify (base64-encoded on wire).
- `alg: HashAlg | None` — hash algorithm.
- `ext_kid: KeyId | None` — for ECDH-derived HMAC key.
- `pubkey: bytes | None` — for ECDH-derived HMAC key.

**Returns:** `True` on HTTP 200, `False` on HTTP 406.

**Implementation:** catch `HemNotAcceptableError` (406) internally and return `False` instead of raising. OQ-12: no response body either way — distinction is by HTTP status code only.

**Error codes:** 400, 401, 403, 406 (verification failed), 409, 418.

---

## Unit test

`tests/unit/test_crypto_hmac.py`:
- Mock hash response, verify base64 decoding into `HmacResult`.
- Test verify returns `True` on 200, `False` on 406.
- Test ECDH-derived key body fields (`ext_kid` or `pubkey` present in request).
