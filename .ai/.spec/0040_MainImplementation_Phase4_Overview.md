# Phase 4: External (remote) authentication

**Status:** Not yet planned in detail. Protocol fully documented (OQ-1/2/3 resolved 2026-04-14).

**Goal:** Implement `auth_flow.pair()` and `auth_flow.remote_login()`.

OQ-1/2/3 were resolved on 2026-04-14 — the broker URLs, flow sequence, and
`epk` origin are now documented in `encedo-hem-api-doc`. The full login
sequence — including cloud polling via `GET notify/event/check/{eventid}`
and cleanup via `DELETE notify/event/{eventid}` — is fully specified.

**Tasks:**
- [ ] `api/auth_flow.py::pair()`: `GET /api/system/config` (for eid) → `POST https://api.encedo.com/notify/session` (get `epk`) → `POST /api/auth/ext/init` (scope `auth:ext:pair`) → `POST https://api.encedo.com/notify/register/init` → wait for mobile → `POST /api/auth/ext/validate` (scope `auth:ext:pair`). Returns `(kid, confirmation_code)`.
- [ ] `api/auth_flow.py::remote_login()`: check-in handshake → `GET https://api.encedo.com/notify/session` (get session+`epk`) → `POST /api/auth/ext/request` (unauthenticated, uses check-in context) → `POST https://api.encedo.com/notify/event/new` → poll `GET https://api.encedo.com/notify/event/check/{eventid}` until `{authreply}` → `POST /api/auth/ext/token`. Returns JWT token.
- [ ] On timeout/cancel: `DELETE https://api.encedo.com/notify/event/{eventid}`.
- [ ] New `transport` method for cloud GET requests (notify/session).
- [ ] Integration test against a real device with a paired mobile app.

**Notes:**
- The `ext/init` scope is `auth:ext:pair` (not `system:config` as previously assumed).
- The `ext/request` response contains `{authreq, epk}` (not `{eid, challenge}`).
- The `ext/validate` response contains `{kid, code}` (not `{confirmation}`).
- Polling cadence from Encedo Manager: ~900ms (setInterval 300ms with divide-by-3 guard). Overall timeout ~60s.

**Deliverable:** `v0.4.0` (or later).

**Dependencies:** Phase 1. OQ-1/2/3 fully resolved — no remaining protocol gaps.
