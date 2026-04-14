# Phase 2: Full crypto surface

**Status:** Planned (2026-04-14)

**Goal:** Cover every `/api/crypto/*` endpoint and every `/api/keymgmt/*` endpoint not yet in Phase 1.

**Deliverable:** `v0.2.0`. A caller can use any crypto endpoint the device exposes (except external auth).

**Dependencies:** Phase 1.

## Step files

| File | Topic |
|---|---|
| [0021](0021_MainImplementation_Phase2_Step1.md) | Enums + dataclasses |
| [0022](0022_MainImplementation_Phase2_Step2.md) | KeyMgmt additions: derive, import_key, search |
| [0023](0023_MainImplementation_Phase2_Step3.md) | HmacAPI |
| [0024](0024_MainImplementation_Phase2_Step4.md) | ExdsaAPI |
| [0025](0025_MainImplementation_Phase2_Step5.md) | EcdhAPI |
| [0026](0026_MainImplementation_Phase2_Step6.md) | Cipher wrap/unwrap |
| [0027](0027_MainImplementation_Phase2_Step7.md) | PQC: MlKemAPI + MlDsaAPI |
| [0028](0028_MainImplementation_Phase2_Step8.md) | Exports, tests, integration smoke |

## Implementation order

1. Enums + dataclasses (no network, pure additions).
2. `keymgmt` additions (`derive`, `import_key`, `search`) + unit tests — straightforward REST wrappers following the Phase 1 pattern.
3. `HmacAPI` + `ExdsaAPI` + unit tests — highest-value crypto additions, well-documented.
4. `CipherAPI` additions (`wrap`/`unwrap`) + unit tests — thin wrappers, lower confidence on wire format.
5. `EcdhAPI` + unit tests — lowest Manager coverage, saved for later.
6. `PqcAPI` (`MlKemAPI` + `MlDsaAPI`) + unit tests — newest firmware features, may not work on all devices.
7. `__init__.py` exports, `examples/crypto_smoke.py`.

## Scope reference table

| Method | Endpoint | Scope |
|---|---|---|
| `keys.derive()` | `POST /api/keymgmt/derive` | `keymgmt:ecdh` |
| `keys.import_key()` | `POST /api/keymgmt/import` | `keymgmt:imp` |
| `keys.search()` | `POST /api/keymgmt/search` | `keymgmt:search` |
| `crypto.hmac.hash()` | `POST /api/crypto/hmac/hash` | `keymgmt:use:{kid}` |
| `crypto.hmac.verify()` | `POST /api/crypto/hmac/verify` | `keymgmt:use:{kid}` |
| `crypto.exdsa.sign()` | `POST /api/crypto/exdsa/sign` | `keymgmt:use:{kid}` |
| `crypto.exdsa.verify()` | `POST /api/crypto/exdsa/verify` | `keymgmt:use:{kid}` |
| `crypto.ecdh.exchange()` | `POST /api/crypto/ecdh` | `keymgmt:use:{kid}` |
| `crypto.cipher.wrap()` | `POST /api/crypto/cipher/wrap` | `keymgmt:use:{kid}` |
| `crypto.cipher.unwrap()` | `POST /api/crypto/cipher/unwrap` | `keymgmt:use:{kid}` |
| `crypto.pqc.mlkem.encaps()` | `POST /api/crypto/pqc/mlkem/encaps` | `keymgmt:use:{kid}` |
| `crypto.pqc.mlkem.decaps()` | `POST /api/crypto/pqc/mlkem/decaps` | `keymgmt:use:{kid}` |
| `crypto.pqc.mldsa.sign()` | `POST /api/crypto/pqc/mldsa/sign` | `keymgmt:use:{kid}` |
| `crypto.pqc.mldsa.verify()` | `POST /api/crypto/pqc/mldsa/verify` | `keymgmt:use:{kid}` |

## Known risks and lower-confidence items

- **`crypto/ecdh`**: documented but absent from Encedo Manager; no Manager-side usage to cross-reference. Integration test is the only validation path.
- **`cipher/wrap` and `cipher/unwrap`**: official docs return 404; schema from test suite only. Registered in Manager endpoints/scopes but never called from UI. Integration test required.
- **PQC endpoints** (`mlkem`, `mldsa`): not in Manager (newer firmware). Official docs are the sole source. Key creation exists in Manager, but crypto operations don't. Device firmware may not support PQC on older versions — handle gracefully.
- **`mldsa/verify` ctx max size discrepancy**: docs say max 64 bytes for verify vs 255 for sign. Validate locally on both.

## Crypto namespace wiring

Extend `CryptoAPI.__init__` to wire up new sub-namespaces:

```python
class CryptoAPI:
    def __init__(self, client: HemClient) -> None:
        self.cipher = CipherAPI(client)
        self.hmac = HmacAPI(client)
        self.exdsa = ExdsaAPI(client)
        self.ecdh = EcdhAPI(client)
        self.pqc = PqcAPI(client)
```

All crypto endpoints use scope `keymgmt:use:{kid}`. All `msg` fields have a 2048-byte plaintext limit (before base64). All use standard base64 with padding on the wire.
