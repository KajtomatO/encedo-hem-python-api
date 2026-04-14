# Phase 2 Step 8: Exports, tests, integration smoke

**Files:** `src/encedo_hem/__init__.py`, `examples/crypto_smoke.py`

---

## `__init__.py` exports

Add to imports and `__all__`:

**Enums:**
- `HashAlg`
- `SignAlg`
- `WrapAlg`

**Models:**
- `HmacResult`
- `SignResult`
- `EcdhResult`
- `WrapResult`
- `MlKemEncapsResult`
- `MlKemDecapsResult`

---

## Integration test: `examples/crypto_smoke.py`

End-to-end smoke test exercising one key per algorithm family against a real device. Requires `HEM_HOST` and `HEM_PASSPHRASE` environment variables.

**Test matrix:**

| Key type | Operations |
|---|---|
| AES256 | cipher encrypt/decrypt (existing) + wrap/unwrap |
| SECP256R1 | exdsa sign/verify + ecdh exchange |
| ED25519 | exdsa sign/verify |
| SHA2-256 | hmac hash/verify |
| MLKEM768 | mlkem encaps/decaps |
| MLDSA65 | mldsa sign/verify |

**Pattern for each test:**
1. Create key
2. Exercise operation(s)
3. Verify round-trip (decrypt matches plaintext, verify returns True, decaps matches encaps shared secret)
4. Delete key

**PQC graceful skip:** catch HTTP 400 on `keymgmt/create` for MLKEM/MLDSA types and skip those tests — older firmware may not support PQC key types.

**Negative test:** verify with wrong message → returns `False` (not an exception).

---

## Unit test summary (all Phase 2)

| Test file | Coverage |
|---|---|
| `tests/unit/test_keymgmt_derive.py` | derive scope, body fields, KeyId return |
| `tests/unit/test_keymgmt_import.py` | import scope, KeyId return, 406 duplicate |
| `tests/unit/test_keymgmt_search.py` | pagination, 404 empty, descr encoding |
| `tests/unit/test_crypto_hmac.py` | hash result, verify True/False |
| `tests/unit/test_crypto_exdsa.py` | sign result, verify bool, ctx validation |
| `tests/unit/test_crypto_ecdh.py` | exchange result, pubkey/ext_kid validation |
| `tests/unit/test_crypto_wrap.py` | wrap/unwrap, constraint validation |
| `tests/unit/test_crypto_pqc.py` | mlkem encaps/decaps, mldsa sign/verify, ctx limits |
