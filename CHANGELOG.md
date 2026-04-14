# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-04-14

### Added
- `HemClient.keys.derive()` — derive a new key via ECDH (`POST /api/keymgmt/derive`).
- `HemClient.keys.import_key()` — import an external public key (`POST /api/keymgmt/import`).
- `HemClient.keys.search()` — search keys by description prefix with auto-pagination (`POST /api/keymgmt/search`).
- `HemClient.crypto.hmac.hash()` / `.verify()` — HMAC hash and verify with optional ECDH-derived key support (`POST /api/crypto/hmac/*`).
- `HemClient.crypto.exdsa.sign()` / `.verify()` — ExDSA sign and verify for ECDSA and EdDSA algorithms (`POST /api/crypto/exdsa/*`).
- `HemClient.crypto.ecdh.exchange()` — raw or hashed ECDH key exchange (`POST /api/crypto/ecdh`).
- `HemClient.crypto.cipher.wrap()` / `.unwrap()` — AES Key Wrap / Unwrap per RFC 3394 (`POST /api/crypto/cipher/wrap|unwrap`).
- `HemClient.crypto.pqc.mlkem.encaps()` / `.decaps()` — ML-KEM encapsulation and decapsulation per FIPS 203 (`POST /api/crypto/pqc/mlkem/*`).
- `HemClient.crypto.pqc.mldsa.sign()` / `.verify()` — ML-DSA sign and verify per FIPS 204 (`POST /api/crypto/pqc/mldsa/*`).
- `HashAlg`, `SignAlg`, `WrapAlg` enumerations.
- `HmacResult`, `SignResult`, `EcdhResult`, `WrapResult`, `MlKemEncapsResult`, `MlKemDecapsResult` dataclasses.
- 56 new unit tests (138 total); 9 integration test files covering all new endpoints.
- `examples/crypto_smoke.py` — end-to-end smoke test exercising all Phase 2 crypto endpoints. Verified against `my.ence.do` on 2026-04-14.

### Fixed
- **OQ-23**: `keys.derive()` now requests scope `keymgmt:gen` instead of `keymgmt:ecdh` — the documented scope is rejected with 403 by firmware; the HEM test suite empirically uses `keymgmt:gen`.

### Known issues
- **OQ-22**: `crypto.pqc.mldsa.verify()` raises `HemError` instead of returning `False` when the signature is invalid — the device returns HTTP 795 instead of the documented 406. Integration test skipped pending upstream clarification.

## [0.1.0] - 2026-04-09

### Added
- `HemClient` — top-level client object with `ensure_ready()`, context-manager support, and endpoint namespaces (`system`, `keys`, `crypto`).
- `HemClient.system.status()` — maps `GET /api/system/status` to `DeviceStatus`.
- `HemClient.system.checkin()` — two-phase check-in flow (device → `api.encedo.com` → device); callable manually or triggered automatically via `auto_checkin=True` (default).
- `HemClient.keys.create()`, `.list()`, `.get()`, `.delete()` — full key-management CRUD over `POST/GET/DELETE /api/keys/*`.
- `HemClient.crypto.cipher.encrypt()` / `.decrypt()` — AES-256-GCM symmetric cipher via `/api/crypto/cipher/*`.
- `encedo_hem.auth` — eJWT builder + scoped token cache (`ensure_token(scope)`): PBKDF2-SHA256 → X25519 → HMAC-SHA256.
- `encedo_hem.transport` — `httpx`-based transport with per-request TCP connections (`Connection: close`), TLS verification bypass for the device endpoint, 413 pre-flight guard, and a separate verified client for `api.encedo.com`.
- `encedo_hem.models` — typed dataclasses for all Phase 1 request/response payloads; base64 fields are `bytes` on the Python side.
- `encedo_hem.errors` — exception hierarchy: `HemAuthError`, `HemNotFoundError`, `HemDeviceFailureError`, `HemBadRequestError`, `HemTlsRequiredError`, `HemPayloadTooLargeError`, `HemNotSupportedError`, `HemTransportError`.
- `encedo_hem.enums` — `KeyType`, `CipherAlg`, `Role` enumerations.
- `examples/mvp.py` — end-to-end script: status → check-in → create key → encrypt → decrypt → delete key. Verified against `my.ence.do` on 2026-04-08.
- 79 unit tests, 93% coverage; `auth`, `transport`, `_base64`, `errors` modules at 100%.

### Fixed
- **MVP-OQ-1**: `DeviceStatus.ts` is now `datetime | None` parsed from ISO 8601 (was incorrectly typed as `int | None`; the wire format is e.g. `"2022-03-16T18:17:27Z"`, not a Unix integer). Local API spec corrected.
- **MVP-OQ-2**: `Auth` no longer treats `challenge.exp` (the challenge response deadline, a few seconds) as the bearer-token lifetime. Cached tokens are now held for the full `_TOKEN_LIFETIME_S`, eliminating the per-call re-login that doubled network traffic on every authenticated call.
- **MVP-OQ-3**: `DeviceStatus.hostname` is now `str | None` and the integration test no longer asserts truthiness — per upstream spec, `hostname` is only returned when the request `Host` header differs from the device's configured hostname.
- **MVP-OQ-4**: `DeviceStatus.https` is now `bool | None` and documented as an HTTP-only capability probe (not a TLS-provisioned flag). The firmware-vs-spec divergence where `my.ence.do` returns the field over HTTPS is tracked upstream as OQ-21.
