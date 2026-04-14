# Phase 2 Step 7: PQC — MlKemAPI + MlDsaAPI

**File:** `src/encedo_hem/api/crypto.py` (new `PqcAPI`, `MlKemAPI`, `MlDsaAPI` classes)

**Confidence:** Lower — not present in Encedo Manager (newer firmware features not yet integrated). Official docs are the sole source. Key creation exists in Manager (`keymgmt/create`), but crypto operations have no UI. Device firmware may not support PQC on older versions.

## Namespace structure

```python
class PqcAPI:
    def __init__(self, client: HemClient) -> None:
        self.mlkem = MlKemAPI(client)
        self.mldsa = MlDsaAPI(client)
```

Access: `client.crypto.pqc.mlkem.encaps(...)`, `client.crypto.pqc.mldsa.sign(...)`.

---

## MlKemAPI — `client.crypto.pqc.mlkem`

### `encaps(kid) -> MlKemEncapsResult`

**Endpoint:** `POST /api/crypto/pqc/mlkem/encaps`
**Scope:** `keymgmt:use:{kid}`

**Wire format:**
```
{kid}  →  {ct, ss, alg}
```

**Parameters:**
- `kid: KeyId` — must reference an ML-KEM key (type MLKEM512, MLKEM768, or MLKEM1024).

**Returns:** `MlKemEncapsResult(ciphertext: bytes, shared_secret: bytes, alg: str)`.
- `ciphertext`: send to peer for decapsulation.
- `shared_secret`: use for symmetric encryption.
- `alg`: reports which MLKEM variant was used.

**Error codes:** 400, 401, 403, 406, 409, 418.

### `decaps(kid, ciphertext) -> MlKemDecapsResult`

**Endpoint:** `POST /api/crypto/pqc/mlkem/decaps`
**Scope:** `keymgmt:use:{kid}`

**Wire format:**
```
{kid, ct}  →  {ss}
```

**Parameters:**
- `kid: KeyId` — must reference an ML-KEM key.
- `ciphertext: bytes` — ciphertext from encapsulation (base64-encoded on wire as `ct`).

**Returns:** `MlKemDecapsResult(shared_secret: bytes)` — should match the encapsulator's `ss`.

**Error codes:** 400, 401, 403, 406, 409, 418.

---

## MlDsaAPI — `client.crypto.pqc.mldsa`

### `sign(kid, msg, *, ctx) -> SignResult`

**Endpoint:** `POST /api/crypto/pqc/mldsa/sign`
**Scope:** `keymgmt:use:{kid}`

**Wire format:**
```
{kid, msg, ctx?}  →  {sign, alg}
```

**Parameters:**
- `kid: KeyId` — must reference an ML-DSA key (type MLDSA44, MLDSA65, or MLDSA87).
- `msg: bytes` — message to sign (max 2048 bytes, base64-encoded on wire).
- `ctx: bytes | None` — optional context data (max 255 bytes, base64-encoded on wire).

**Returns:** `SignResult(signature: bytes)` — reuses the same dataclass as `exdsa.sign`.

**Note:** Response also contains `alg` field (MLDSA44/65/87) but we don't surface it in `SignResult` since the caller knows which key they used. If needed later, add `alg` to `SignResult`.

**Error codes:** 400, 401, 403, 406, 409, 418.

### `verify(kid, msg, signature, *, ctx) -> bool`

**Endpoint:** `POST /api/crypto/pqc/mldsa/verify`
**Scope:** `keymgmt:use:{kid}`

**Wire format:**
```
{kid, msg, sign, ctx?}  →  200 (valid) / 406 (invalid)
```

**Parameters:**
- `kid: KeyId` — must reference an ML-DSA key.
- `msg: bytes` — original message (max 2048 bytes, base64-encoded on wire).
- `signature: bytes` — signature to verify (base64-encoded on wire, wire field name is `sign`).
- `ctx: bytes | None` — optional context data (**max 64 bytes** — note: smaller limit than `sign`'s 255).

**Returns:** `True` on HTTP 200, `False` on HTTP 406.

**Local validation:**
- `ctx` max 64 bytes for verify (vs 255 for sign). Raise `ValueError` if exceeded.

**Implementation:** catch `HemNotAcceptableError` (406) internally and return `False`. OQ-12: no response body either way.

**Error codes:** 400, 401, 403, 406 (verification failed), 409, 418.

---

## Unit test

`tests/unit/test_crypto_pqc.py`:
- Mock mlkem encaps response → verify `MlKemEncapsResult` fields.
- Mock mlkem decaps response → verify `MlKemDecapsResult` fields.
- Mock mldsa sign response → verify `SignResult`.
- Mock mldsa verify → test `True` on 200, `False` on 406.
- Test mldsa verify `ctx` max 64 bytes → `ValueError` on 65.
- Test mldsa sign `ctx` max 255 bytes → `ValueError` on 256.
