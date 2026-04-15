# Phase 3 Step 3: System additions

**File:** `src/encedo_hem/api/system.py`

New methods on the existing `SystemAPI` class, plus a scope fix for `reboot()`.

---

## Fix `reboot()` scope

**Current (wrong):** `system:config`
**Correct (per API doc):** `system:upgrade|config|shutdown`

The device accepts any of the three scopes — use `system:config` to match
what's already in use in Phase 1, OR update to `system:upgrade` as the
most specific. **Decision:** update to `system:upgrade` (least privileged that
still covers the operation). Document that any of the three scopes work.

**Also:** `reboot()` invalidates all tokens — the auth cache must be cleared
after a reboot call. Add `self._client._auth.invalidate()` (or equivalent)
after the transport call if `Auth` exposes such a method; otherwise add a note
in the docstring that callers must re-authenticate after calling `reboot()`.

---

## `shutdown() -> None`

**Endpoint:** `GET /api/system/shutdown`
**Scope:** `system:shutdown|config` (either accepted)

Shuts down the device. No response body. Scope: `system:shutdown`.

---

## `selftest() -> SelftestResult`

**Endpoint:** `GET /api/system/selftest`
**Scope:** any valid token (no specific scope required)

Returns the device self-test status.

**Wire response:**
```json
{
  "last_selftest_ts": 1234567890,
  "fls_state": 0,
  "kat_busy": false,
  "se_state": 0
}
```

Map to `SelftestResult`. Additional fields in the response are silently
ignored (forward compatibility).

---

## `config_attestation(*, token=None) -> AttestationResult`

**Endpoint:** `GET /api/system/config/attestation`
**Scope:** Optional — works unauthenticated (PPA only)

Returns the device attestation certificate and genuineness flag.

**Wire response:**
```json
{"crt": "<PEM>", "genuine": true}
```

**PPA-only:** On EPA devices the endpoint likely returns an HTTP error.
Let it propagate naturally (don't add a hardware-form check).

---

## `config_provisioning(user, email, passphrase, *, hostname=None) -> None`

**Endpoint:** `POST /api/system/config/provisioning`
**Scope:** No auth (initial setup, device not yet configured)
**PPA-only.** One-time: returns 403 (`HemForbiddenError`) if already provisioned.

**Wire request body:** _Exact fields TBD — consult `encedo-hem-api-doc` for the
full provisioning request schema before implementing._ Likely:
```json
{"user": "...", "email": "...", "passphrase": "...", "hostname": "..."}
```

**Note:** Raise a comment `# OQ-PROVISIONING: confirm request body schema` in the
implementation until tested against a real device.

---

## Unit tests

- `tests/unit/test_system_additions.py`:
  - `test_shutdown_uses_system_shutdown_scope` — mock GET, assert scope in token request.
  - `test_selftest_returns_result` — mock GET returning the 4-field JSON, assert `SelftestResult`.
  - `test_config_attestation_returns_result` — mock GET, assert `AttestationResult`.
  - `test_config_provisioning_posts_json` — mock POST, assert body contains `user` + `email`.
  - `test_config_provisioning_403_raises` — mock 403, assert `HemForbiddenError`.
