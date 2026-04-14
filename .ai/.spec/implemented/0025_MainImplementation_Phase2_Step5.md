# Phase 2 Step 5: EcdhAPI

**File:** `src/encedo_hem/api/crypto.py` (new `EcdhAPI` class)

**Confidence:** Lower — documented in official docs and registered in Manager scopes, but **not called from Manager UI**. Integration test is the primary validation path.

---

## `exchange(kid, *, pubkey, ext_kid, alg) -> EcdhResult`

**Endpoint:** `POST /api/crypto/ecdh`
**Scope:** `keymgmt:use:{kid}`

**Wire format:**
```
{kid, pubkey?, ext_kid?, alg?}  →  {ecdh}
```

**Parameters:**
- `kid: KeyId` — key ID (32-char hex). Must be an ECDH-capable key (CURVE25519, CURVE448, or NIST ECC with ECDH mode).
- `pubkey: bytes | None` — raw external public key (base64-encoded on wire). Mutually exclusive with `ext_kid`.
- `ext_kid: KeyId | None` — on-device external key ID. Mutually exclusive with `pubkey`.
- `alg: HashAlg | None` — if `None`, returns raw ECDH output. If set, returns `Hash(raw_ecdh_output)`.

**Returns:** `EcdhResult(shared_secret: bytes)`.

**Local validation:**
- Exactly one of `pubkey` or `ext_kid` must be provided. Raise `ValueError` if neither or both.

**Supported hash algorithms (for hashed output):**
`SHA2-256`, `SHA2-384`, `SHA2-512`, `SHA3-256`, `SHA3-384`, `SHA3-512`

**Note:** The key type of `ext_kid` or `pubkey` must match the `kid` key type (e.g., both CURVE25519 or both SECP256R1). Mismatches produce 400 or 406 from the device.

**Error codes:** 400, 401, 403, 406, 409, 418.

---

## Unit test

`tests/unit/test_crypto_ecdh.py`:
- Mock response, verify `EcdhResult` with base64-decoded shared secret.
- Test `ValueError` when neither `pubkey` nor `ext_kid` given.
- Test `ValueError` when both `pubkey` and `ext_kid` given.
- Test `alg` omitted → no `alg` in request body.
- Test `alg` set → `alg` present in request body with correct wire value.
