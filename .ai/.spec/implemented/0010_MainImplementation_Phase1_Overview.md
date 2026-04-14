# Phase 1: MVP — system + auth + keymgmt + cipher

**Status:** Implemented (code-complete + real-device-verified 2026-04-08)

**Goal:** `python examples/mvp.py` runs against a real PPA/EPA, printing status, doing check-in, creating a key, round-tripping an AES-256-GCM message, and deleting the key.

**Tasks:**
- [x] `errors.py`: full exception hierarchy + HTTP-status-to-exception mapping function.
- [x] `_base64.py`: helpers for standard-base64 (with padding) and base64url-nopad; unit tests against known vectors.
- [x] `transport.py`:
  - [x] `Transport` class over `httpx.Client(verify=False, limits=Limits(max_keepalive_connections=0))`.
  - [x] `Connection: close` header on every device request.
  - [x] Local 7300-byte pre-flight guard → `HemPayloadTooLargeError`.
  - [x] `backend_post(url, json)` using a separate httpx client with `verify=True`.
  - [x] Status-to-exception translation.
- [x] `models.py`: `DeviceVersion`, `DeviceStatus` (with inverted `initialized` logic), `DeviceConfig`, `AuthChallenge`, `CachedToken`, `KeyId`, `ParsedKeyType`, `KeyInfo`, `KeyDetails`, `EncryptResult`.
- [x] `enums.py`: `Role`, `KeyType`, `KeyMode`, `CipherAlg`.
- [x] `auth.py`:
  - [x] `build_ejwt(challenge, scope, passphrase)` — PBKDF2-SHA256 (600 000 iters) → X25519 → ECDH → HMAC-SHA256 → JWT assembly. Zero the seed and shared secret at function exit.
  - [x] `Auth` class with `ensure_token(scope)` / `invalidate(scope)` and the 60-second expiry buffer.
  - [x] Unit tests against fixed vectors (mock challenge, mock passphrase → deterministic eJWT).
- [x] `api/system.py`: `version`, `status`, `checkin` (full three-step bounce), `config`, `set_config`, `reboot`, `selftest`.
- [x] `api/keymgmt.py`: `create`, `list` (auto-paginated iterator capped at 15/page), `get` (scope `keymgmt:use:<kid>`), `update` (mandatory label), `delete`.
- [x] `api/crypto.py`: `cipher.encrypt`, `cipher.decrypt` for ECB/CBC/GCM.
- [x] `client.py`: `HemClient` facade with `auto_checkin` and `strict_hardware` flags, `ensure_ready()`, namespace attributes, `__enter__`/`__exit__`, `close()` with passphrase zeroing.
- [x] `examples/mvp.py`: the script in the "Canonical example" section.
- [x] `tests/integration/test_mvp_flow.py`: pytest fixture that skips unless `HEM_HOST` and `HEM_PASSPHRASE` are set; runs the full MVP flow.

**Deliverable:** Tagged `v0.1.0`. A user can `pip install encedo-hem`, write the MVP script in the README, point it at their device, and see the round-trip succeed.

**Dependencies:** Phase 0.
