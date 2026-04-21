# Phase 2 Step 9: Integration tests

**Files:** `tests/integration/` — one file per endpoint group (see table below)

**Status:** Not yet implemented

**Dependencies:** Steps 1–8 (all Phase 2 code complete). Follows the same
patterns as `tests/integration/test_mvp_flow.py`: `hem` fixture from
`conftest.py`, `finally` blocks for cleanup.

PQC key types (MLKEM768, MLDSA65) are assumed to be supported — no skip logic.

---

## File map

| File | Endpoint(s) | Key type |
|---|---|---|
| `test_keymgmt_derive.py` | `keymgmt/derive` | CURVE25519 + AES256 |
| `test_keymgmt_import.py` | `keymgmt/import` | ED25519 |
| `test_keymgmt_search.py` | `keymgmt/search` | AES256 |
| `test_crypto_hmac.py` | `crypto/hmac/hash`, `crypto/hmac/verify` | SHA2-256 |
| `test_crypto_exdsa.py` | `crypto/exdsa/sign`, `crypto/exdsa/verify` | SECP256R1 + ED25519 |
| `test_crypto_ecdh.py` | `crypto/ecdh` | SECP256R1 |
| `test_crypto_cipher_wrap.py` | `crypto/cipher/wrap`, `crypto/cipher/unwrap` | AES256 |
| `test_crypto_mlkem.py` | `crypto/pqc/mlkem/encaps`, `crypto/pqc/mlkem/decaps` | MLKEM768 |
| `test_crypto_mldsa.py` | `crypto/pqc/mldsa/sign`, `crypto/pqc/mldsa/verify` | MLDSA65 |

---

## Per-file test plan

### `test_keymgmt_derive.py`
- Create a CURVE25519 source key and an AES256 derived key via `keymgmt/derive`
- Verify the derived key is usable: encrypt + decrypt round-trip with it
- Two-key cleanup pattern in `finally`

### `test_keymgmt_import.py`
- Create an ED25519 key, read its `pubkey` via `keys.get`, delete the original
- Import the pubkey back via `keymgmt/import` — assert a new `kid` is returned
- Import the same pubkey again — assert `HemNotAcceptableError` (OQ-20 duplicate)
- Cleanup imported key in `finally`

### `test_keymgmt_search.py`
- Create a key with a known `descr` (base64-encoded prefix)
- Search with `'^' + base64(prefix)` — assert the created key appears in results
- Search with a pattern that matches nothing — assert empty result (no exception)
- Cleanup in `finally`

### `test_crypto_hmac.py`
- Create SHA2-256 key
- `hash()` a random message; assert `mac` is non-empty
- `verify()` with correct message → `True`
- `verify()` with wrong message → `False`
- Cleanup in `finally`

### `test_crypto_exdsa.py`
- Two test functions, one per key type:
  - `test_exdsa_secp256r1`: SECP256R1 + `SHA256WithECDSA`
  - `test_exdsa_ed25519`: ED25519 + `Ed25519`
- Each: sign random message; verify correct → `True`; verify wrong message → `False`
- Cleanup in `finally`

### `test_crypto_ecdh.py`
- Create two SECP256R1 keys
- Exchange: `kid1` with `pubkey` of `kid2`, `alg=SHA2-256`
- Assert `shared_secret` is 32 bytes
- Two-key cleanup pattern in `finally`

### `test_crypto_cipher_wrap.py`
- Create AES256 key
- `wrap()` 16 random bytes; `unwrap()` the result; assert round-trip
- Cleanup in `finally`

### `test_crypto_mlkem.py`
- Create MLKEM768 key
- `encaps()` → get `ciphertext` + `shared_secret`
- `decaps(ciphertext)` → assert `shared_secret` matches encaps result
- Cleanup in `finally`

### `test_crypto_mldsa.py`
- Create MLDSA65 key
- Sign random message; verify correct → `True`; verify wrong message → `False`
- Cleanup in `finally`

---

## Test patterns

### Standard pattern

```python
def test_hmac_hash_and_verify(hem: HemClient) -> None:
    kid = hem.keys.create("it-hmac", KeyType.SHA2_256)
    try:
        msg = secrets.token_bytes(32)
        result = hem.crypto.hmac.hash(kid, msg, alg=HashAlg.SHA2_256)
        assert hem.crypto.hmac.verify(kid, msg, result.mac, alg=HashAlg.SHA2_256)
        assert not hem.crypto.hmac.verify(kid, b"wrong", result.mac, alg=HashAlg.SHA2_256)
    finally:
        hem.keys.delete(kid)
```

### Two-key pattern (ECDH, derive)

Both keys must be cleaned up in `finally`, even if the second create fails:

```python
def test_ecdh_exchange(hem: HemClient) -> None:
    kid1 = kid2 = None
    try:
        kid1 = hem.keys.create("it-ecdh-1", KeyType.SECP256R1)
        kid2 = hem.keys.create("it-ecdh-2", KeyType.SECP256R1)
        details2 = hem.keys.get(kid2)
        assert details2.pubkey is not None
        result = hem.crypto.ecdh.exchange(kid1, pubkey=details2.pubkey, alg=HashAlg.SHA2_256)
        assert len(result.shared_secret) == 32
    finally:
        for kid in (kid1, kid2):
            if kid:
                with contextlib.suppress(HemError):
                    hem.keys.delete(kid)
```

---

## Common imports

```python
import contextlib
import secrets

from encedo_hem import (
    HashAlg, HemClient, HemError, HemNotAcceptableError,
    KeyType, SignAlg, WrapAlg,
)
```
