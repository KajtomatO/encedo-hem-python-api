# Open Questions — API Documentation Gaps

Issues found in API documentation and `INTEGRATION_GUIDE.md` that block
implementation or were discovered during testing. Each item notes which endpoint is
affected and what specifically is missing or wrong.

---

## Critical (blocks implementation)

### OQ-16 — `GET /api/keymgmt/get/{kid}` only accepts `keymgmt:use:<kid>` scope

**Status (2026-04-08):** Spec checked against upstream docs
(`api-reference/key-management/get-a-public-key.md`). Upstream states the
required scope is **`keymgmt:get`** (or `keymgmt:gen` + `keymgmt:use:<KID>`),
**not** `keymgmt:list` as previously written in INTEGRATION_GUIDE.md. The
empirical 403 with `keymgmt:list` is therefore consistent with the spec — the
guide was wrong, not the device. The remaining open question is whether
`keymgmt:get` itself works on firmware v1.2.2-DIAG, or whether only
`keymgmt:use:<KID>` does as observed. Re-test with a token scoped to
`keymgmt:get` to confirm.

---

### OQ-16 (original report)

**Affected endpoint:** `GET /api/keymgmt/get/{kid}`
**Confirmed via:** live device testing (firmware v1.2.2-DIAG)

The API design doc states the required scope is `keymgmt:list` **or** `keymgmt:use:<kid>`.
The device returns **HTTP 403** when a token scoped to `keymgmt:list` is used; only
`keymgmt:use:<kid>` is accepted.

The spec and INTEGRATION_GUIDE.md (scope table) both need correcting: remove
`keymgmt:list` from this endpoint's scope requirement.

**Impact:** Any binding that uses a cached list token for get calls will get a 403.
The C library was already fixed to always use `keymgmt:use:<kid>` for `hem_key_get`.

---

### OQ-17 — `GET /api/keymgmt/list/{offset}/{limit}` silently caps page size

**Resolved (2026-04-08):** Upstream
(`api-reference/key-management/list-the-keys.md`) documents `limit` as having a
**default of 15**. The empirical "cap at 15" is the device ignoring the
requested value and falling back to the default. Treat 15 as the effective max
page size and paginate via `offset`. INTEGRATION_GUIDE.md §5.2.1 updated
accordingly. The original "what is the cap" question is answered (15);
"is this per-firmware vs per-config" is no longer blocking.

---

### OQ-17 (original report)

**Affected endpoint:** `GET /api/keymgmt/list/{offset}/{limit}`
**Confirmed via:** live device testing (firmware v1.2.2-DIAG, 90 keys on device)

The device returns at most ~15 entries per page regardless of the requested `limit`.
Observed: `limit=10` → `listed=10` (correct); `limit=64` → `listed=15` (capped).
The response `listed` field reflects the actual count returned, not the requested limit.

Neither the API design doc nor INTEGRATION_GUIDE.md mention any page size cap.

**Impact:** Any client that uses `listed < requested_limit` as the end-of-list signal
will exit after the first page when `limit > cap`, silently missing all subsequent keys.
Safe workaround: use a page size ≤ 10 until the exact cap is confirmed.

**Questions:**
- What is the exact maximum `limit` the device honours?
- Is the cap per-firmware or per-device configuration?

---

### OQ-1 — Notification broker URL is wrong

**Resolved (2026-04-14):** The `encedo-hem-api-doc` repo (`auth/ext-init.md`,
`auth/ext-request.md`) documents the full broker flows extracted from Encedo
Manager source code. The broker is **not** a single URL — it is a multi-step
sequence:

**Pairing flow:**
1. `POST https://api.encedo.com/notify/session` with `{ eid }` → returns `{ epk }`
2. `POST /api/auth/ext/init` with `{ epk }` → returns `{ request, eid }`
3. `POST https://api.encedo.com/notify/register/init` with `{ request, eid, epk }`

**Login flow:**
1. Check-in handshake (3 steps)
2. `GET https://api.encedo.com/notify/session` → returns session data (incl. `epk`)
3. `POST /api/auth/ext/request` with session data → returns `{ authreq, epk }`
4. `POST https://api.encedo.com/notify/event/new` with `{ authreq, epk }`
5. Poll cloud for mobile's response
6. `POST /api/auth/ext/token` with `{ authreply }`

The original 404 was likely caused by calling `/notify/event/new` without a
prior `/notify/session` call to establish context.

---

### OQ-2 — Notification broker request/response format undefined

**Largely resolved (2026-04-14):** The `encedo-hem-api-doc` repo documents the
data flow between device, cloud, and client from Encedo Manager source code:

**Pairing:**
- `notify/session` takes `{ eid }`, returns `{ epk }`.
- `ext/init` takes `{ epk }`, returns `{ request, eid }`.
- `notify/register/init` takes `{ request, eid, epk }` — response presumably
  contains `pid` and `reply` for `ext/validate`, but this is inferred from
  `ext/validate`'s documented request fields (`{ pid, reply }`), not directly
  shown.

**Login:**
- `notify/session` (GET) returns session data including `epk`.
- `ext/request` takes session data, returns `{ authreq, epk }`.
- `notify/event/new` takes `{ authreq, epk }` — pushes to mobile.
- Cloud is polled for the mobile's response containing `authreply`.
- `ext/token` takes `{ authreply }`, returns `{ token }`.

**Resolved (2026-04-14):** From Encedo Manager source (`encedo.js:1517`):

- **Poll:** `GET https://api.encedo.com/notify/event/check/{eventid}` —
  `eventid` comes from the `/notify/event/new` response (`dataEvent.eventid`).
  When the mobile has responded the body contains `{ authreply: "..." }`,
  which is then POSTed to `/api/auth/ext/token`.
- **Cancel / cleanup:** `DELETE https://api.encedo.com/notify/event/{eventid}`
  (on timeout or user cancel).
- **Cadence (Manager UI):** `setInterval` at 300ms with a divide-by-3 guard
  — check fires every ~900ms. Overall timeout ~60s (`timerNow` from 198 ticks).

The full login sequence is therefore:

1. Check-in handshake (3 steps)
2. `GET https://api.encedo.com/notify/session` → session data (incl. `epk`)
3. `POST /api/auth/ext/request` with session data → `{ authreq, epk }`
4. `POST https://api.encedo.com/notify/event/new` with `{ authreq, epk }` → `{ eventid }`
5. Poll `GET https://api.encedo.com/notify/event/check/{eventid}` until `{ authreply }`
6. `POST /api/auth/ext/token` with `{ authreply }` → `{ token }`
7. (On timeout/cancel) `DELETE https://api.encedo.com/notify/event/{eventid}`

---

### OQ-3 — `epk` field: who generates it and in what format?

**Partially resolved (2026-04-08):** Upstream
(`api-reference/authorization/external-authenticator/...`) consistently
describes `epk` as **"broker ephemeral public key"**. This implies the
**broker (Encedo cloud)** generates the keypair, and the client must obtain
`epk` from the broker before calling `ext/init` / `ext/request` — not generate
it locally as the current C stub assumes. The broker URL/endpoint that returns
`epk` is still undocumented (see OQ-1). Until OQ-1 is resolved this remains
blocking, but the implementation assumption ("client generates epk") should be
removed.

---

### OQ-3 (original report)

**Resolved (2026-04-14):** The `encedo-hem-api-doc` repo (`auth/ext-init.md`)
shows the definitive flow from Encedo Manager source:

```javascript
// 1. Get device config (for eid)
app.api('api/system/config')
// 2. Create cloud session — BROKER returns epk
.then(data => app.api('https://api.encedo.com/notify/session', 'POST', { eid: data.eid }))
// 3. Pass broker's epk to device
.then(data => {
    epk_temp = data.epk;
    return app.api('api/auth/ext/init', 'POST', { epk: data.epk });
})
```

The **broker (Encedo cloud)** generates the ephemeral keypair. The client
obtains `epk` from `POST https://api.encedo.com/notify/session` and forwards
it to the device. The client does **not** generate `epk` locally.

Whether the broker response to `notify/register/init` is encrypted to `epk`
is still unknown, but the generation question is fully answered.

---

## Significant (causes unclear behaviour)

### OQ-18 — `POST /api/keymgmt/update` requires `label` even when only updating `descr`

**Status (2026-04-14):** Documented as optional across all three sources
(`encedo-hem-api-doc`, Encedo Manager, HEM test suite), but every working
implementation sends both `label` and `descr` together:

- Manager (`build.js:5901`, `build.js:6604`, `build.js:6706`) always sends
  `{ kid, label, descr }`.
- Test suite (`test_10.php:362`) constructs `keyupdate_arg` with both fields.

The empirical 400 when `label` is omitted is consistent with this pattern.
**Treat `label` as mandatory in practice**, even though the spec says
otherwise. The device bug/spec inconsistency remains unresolved upstream;
no caller in the wild triggers the documented "label optional" behaviour.

**Affected endpoint:** `POST /api/keymgmt/update`
**Confirmed via:** live device testing (firmware v1.2.2-DIAG)

---

### OQ-19 — NIST ECC keys created without `mode` are ECDH-only; signing returns 406

**Resolved (2026-04-14):** Confirmed by HEM test suite
(`hem-api-tester/test_10.php:79-82`), which explicitly maps every NIST ECC
type to `mode: "ECDH,ExDSA"`:

```php
$support_key_types = array(
    "SECP256R1" => ['mode' => "ECDH,ExDSA", "isECDH" => true],
    "SECP384R1" => ['mode' => "ECDH,ExDSA", "isECDH" => true],
    "SECP521R1" => ['mode' => "ECDH,ExDSA", "isECDH" => true],
    "SECP256K1" => ['mode' => "ECDH,ExDSA", "isECDH" => true],
    ...
);
```

The test suite never omits `mode` for NIST ECC — i.e. the canonical usage
is "always specify the mode". The empirical 406-on-sign when `mode` is
omitted is consistent with the default being ECDH-only. Callers that need
signing must pass `"ExDSA"` or `"ECDH,ExDSA"` explicitly.

`ED25519` and other non-NIST curve types are sign-only by nature — `mode`
is only relevant for NIST ECC. The `encedo-hem-api-doc` `keymgmt/create.md`
should document the default explicitly; opened as a doc issue.

**Affected endpoint:** `POST /api/keymgmt/create`
**Confirmed via:** live device testing (firmware v1.2.2-DIAG, SECP256R1 key)

---

### OQ-21 — `https` field returned over HTTPS, contradicting upstream spec

**Affected endpoint:** `GET /api/system/status`
**Confirmed via:** live device testing on `my.ence.do` (2026-04-08, Python MVP run, originally filed as MVP-OQ-4).

Upstream (`api-reference/system/...`) defines `https` as:

> "True or False to indicate if HTTPS mode is available, **returned only if
> called by HTTP endpoint**."

i.e. the field is meant as a capability probe for plain-HTTP callers asking
"can I upgrade to TLS?" and should be **absent** when the request itself
arrives over HTTPS. Observed behaviour on the PPA at `my.ence.do` is the
opposite: the field is present and set to `false` even when the entire
session is conducted over HTTPS with a valid TLS handshake.

Two possibilities:
1. The firmware always emits the field regardless of scheme (spec wording
   is correct, firmware is wrong).
2. The field has a second, undocumented meaning (e.g. "long-lived attested
   public TLS cert has been provisioned via check-in") and the upstream
   description is incomplete.

The Python library now models it as `bool | None` and treats absence as
the documented case, but the divergence needs an upstream answer before
any binding exposes the field with a meaningful name.

**Update (2026-04-14):** The `encedo-hem-api-doc` (`system/status.md`)
describes `https` simply as **"Optional. HTTPS availability"** — without
the "returned only if called by HTTP endpoint" qualifier from the
original upstream docs. This is backed by the Encedo Manager:

```javascript
// build.js:3623
if (app.encedo_status.https && window.location.protocol != 'https:') {
    window.location.replace(`https:${location.href.substring(...)}`);
}
```

The Manager reads `status.https` as a **capability flag** — "HTTPS is
available on this device" — and only redirects HTTP→HTTPS when the UI
itself is being served over plain HTTP. The field is emitted regardless
of the request scheme; the original upstream "HTTP-only" qualifier is
wrong/outdated.

**Semantics:** `true` = HTTPS listener is up; `false` = HTTPS listener is
not available (e.g. TLS cert not yet provisioned via check-in). The
Python library's `bool | None` model remains correct; surface the field
as `https_available: bool`.

---

### OQ-20 — `POST /api/keymgmt/import` returns 406 on duplicate public key

**Resolved (2026-04-14):** Confirmed as expected device behaviour by the
HEM test suite (`hem-api-tester/test_10.php:303`):

```php
if ( count($failed_calls) == count($keys_to_import)) {
  // expected if re-run - key duplication is impossible (406)
}
```

The test suite treats 406 on re-import as a **valid, expected outcome** —
the device enforces key deduplication and returns 406 rather than silently
re-importing. The `keymgmt/import.md` error table should call out
duplicate key as a specific 406 trigger; Python bindings should surface a
distinct `KeyAlreadyExistsError` on 406 from this endpoint.

**Affected endpoint:** `POST /api/keymgmt/import`
**Confirmed via:** live device testing (firmware v1.2.2-DIAG) + test suite

---

### OQ-4 — `lbl` field in `GET /api/auth/token` response

**Resolved (2026-04-08):** Upstream
(`api-reference/authorization/user-authentication.md`) documents `lbl` as
**"Label, username"** — i.e. the username/label associated with the device
account. It is also listed as a payload field for the POST eJWT. The library
may surface it to callers (e.g. as `ctx->username`); inclusion in the eJWT
payload is allowed but not required for token issuance to work.

---

### OQ-4 (original report)

**Resolved (2026-04-14):** Confirmed by `encedo-hem-api-doc` (`auth/token.md`).
The `lbl` field is documented as **"Device label"** in the GET response table.
It is informational metadata, not required in the eJWT payload. The library
may surface it to callers.

---

### OQ-5 — `ctx` field in `POST /api/auth/token` eJWT payload

**Resolved (2026-04-14):** The HEM test suite (`test_3.php:90`) sends a
literal placeholder string:

```php
$auth_val_user = array(
  'jti' => ..., 'aud' => ..., 'exp' => ..., 'iat' => ...,
  'iss' => ..., 'scope' => "system:config",
  'ctx' => "place_here_max_64chars"
);
```

The returned bearer token's decoded payload contains only
`scope, sub, iat, exp, jti` — no `ctx` is echoed back. So `ctx` is an
opaque free-form string (≤64 chars) that the caller may pass for
audit/trace purposes but which has **no effect on token issuance or
claims**. The Python library may safely continue to omit it.

Note: the numeric `ctx` seen in `GET /api/system/status` and
`POST /api/system/config` (`build.js:724` sets `"ctx": 0`) is a different
field — "instance context id" on the device, unrelated to the eJWT `ctx`.

---

### OQ-5 (original report)

**Affected endpoint:** `POST /api/auth/token`

The eJWT payload spec lists an optional `ctx` field: "optional context max 64 chars".
The purpose, format, and effect of this field are not explained. The library
currently never sends it.

**Questions:**
- What is `ctx` used for on the device side?
- Is it a human-readable string, a base64 blob, or something else?
- Does it affect the issued token in any way (e.g. embedded in the JWT claims)?

---

### OQ-6 — `POST /api/keymgmt/update` response format undefined

**Resolved (2026-04-14):** Encedo Manager (`build.js:5901`, `:6604`,
`:6706`) and test suite (`test_10.php:362`) both **ignore the response
body** — they only check HTTP 200 via the `.then()` callback. No caller
in the wild reads an `updated: true` field. Treat the response as opaque:
success = status code 200, no JSON body expected. The `encedo-hem-api-doc`
`keymgmt/update.md` documents this as-is (no response JSON shown).

---

### OQ-7 — `POST /api/keymgmt/search` minimum pattern length for unauthenticated use

**Partially resolved (2026-04-14):** No source independently documents the
exact byte-counting rule, but the pattern format is now clear from two
working callers:

- Manager (`build.js:5806`) uses `'^RVhUQUlE'` — a `^` regex anchor
  followed by base64 of the ASCII string `EXTAID` (6 bytes).
- Test suite (`test_10.php:407`) builds the pattern as
  `"^" . base64_encode("CCTEST:")` — again `^` + base64 of a 7-byte ASCII
  prefix.

Both wrap a **≥6-byte raw ASCII prefix** in `base64_encode` and prepend
`^`. Interpretation: the 6-byte minimum most likely refers to the raw
(pre-base64) prefix the caller is searching for, which is the semantic
unit — not the length of the JSON-level string. Callers that follow the
Manager/test-suite convention (`^` + base64(≥6-byte prefix)) will always
satisfy the rule, so this is no longer blocking. HTTP status on
too-short patterns is still unconfirmed (likely 400).

**Affected endpoint:** `POST /api/keymgmt/search`

---

### OQ-8 — Audit log entry format only partially described

**Affected endpoint:** `GET /api/logger/{id}`

The spec says the response is "plain text" with entries that are "pipe-delimited
with 7 fields" but does not name the fields.

**Update (2026-04-14):** The `encedo-hem-api-doc` (`logger/get.md`) confirms
Content-Type is `text/plain`. DISCREPANCIES.md #22 adds significant detail:
each log entry is **signed with Ed25519** and entries are **chained via
HMAC-SHA256** (each entry's HMAC includes the previous entry's HMAC). The
logger public key from `GET /api/logger/key` is used to verify signatures.

**Resolved (2026-04-14):** The HEM test suite
(`hem-api-tester/libs/lib.php:364 encedo_log_integrity_check`) reveals
the full record structure. Each line is `f0|f1|f2|f3|f4|f5|f6` where the
last field is always the HMAC tail.

There are two entry kinds, distinguished by `f2 == 0 && f3 == 0`:

- **Header / key-rotation entry** (first entry of a log, and at each
  rotation): `f4` is the new base64url-encoded HMAC-SHA256 key, `f5` is
  the base64url Ed25519 signature of that key. Verified with the logger
  public key from `GET /api/logger/key`.
- **Data entry** (all others): `f0..f5` carry event metadata, `f6` is
  the 16-byte-prefix HMAC over everything up to and including the last
  `|` separator, keyed by the current header's HMAC key. Chaining is
  implicit: breaking any line's HMAC or losing an entry invalidates all
  subsequent entries under that key.

The exact meaning of `f0..f3` in a data entry (timestamp, event type, KID,
user, etc.) is still not labelled anywhere, but the **verification
algorithm is fully specified**. The Python binding can verify log
integrity without needing to name the individual fields — surface them
as a 6-tuple of strings plus the verification status.

Max file size is still undocumented.

**Affected endpoint:** `GET /api/logger/{id}`

---

### OQ-9 — Firmware upgrade uses binary upload, not JSON

**Resolved (2026-04-08):** Upstream
(`api-reference/system/upgrade/firmware.md`) specifies **raw
`application/octet-stream`** (not multipart). Required headers:

```
Content-Type: application/octet-stream
Content-Disposition: attachment; filename="firmware.bin"
Expect: 100-continue
```

For `upload_ui` use `filename="webroot.tar"`. Max size still not documented.
A new transport function `hem_http_post_binary` is still needed in bindings,
but the wire format is no longer ambiguous.

---

### OQ-9 (original report)

**Affected endpoints:** `POST /api/system/upgrade/upload_fw`, `POST /api/system/upgrade/upload_ui`

The spec says Content-Type is "Binary upload (filename: firmware.bin / webroot.tar)"
but does not specify:
- Whether this is `multipart/form-data` or raw `application/octet-stream`
- The form field name if multipart
- The maximum accepted file size

The current `hem_http_post` implementation only handles JSON bodies. A new
transport function (`hem_http_post_binary`) will be needed.

**Questions:**
- Is the upload `multipart/form-data` or raw binary with `Content-Type: application/octet-stream`?
- If multipart, what is the form field name?
- What is the maximum firmware image size?

---

### OQ-10 — `GET /api/system/upgrade/check_fw` polling interval not specified

**Affected endpoint:** `GET /api/system/upgrade/check_fw`

Returns HTTP 202 while verification is in progress, 200 when complete. No
recommended polling interval or maximum wait time is given.

**Update (2026-04-14):** The `encedo-hem-api-doc` (`system/upgrade-firmware.md`)
adds a **201** status code ("Validation process started") distinct from 202
("Validation ongoing"). The Encedo Manager polls in a `setTimeout` loop.
No interval or timeout values are documented.

**Resolved (2026-04-14):** From Encedo Manager (`build.js:1108-1131` and
`build.js:1247-1285`):

- **`check_fw`:** poll interval **4000 ms** (`setTimeout(4000)` after
  201/202); per-request XHR timeout **120000 ms** (2 min). No overall
  cap — the Manager polls indefinitely until 200 or a non-201/202 status.
- **`check_ui`:** initial wait **60000 ms** before the first poll, then
  `setInterval(5000)` (5 s cadence) after 201; per-request XHR timeout
  **4000 ms**. 202 is treated as "continue polling silently".

Suggested binding behaviour: poll every 4 s for `check_fw` and every 5 s
for `check_ui`, with an implementation-chosen upper bound (the Manager
relies on the user aborting; bindings should pick a finite budget, e.g.
5 min, and surface a timeout error).

**Affected endpoint:** `GET /api/system/upgrade/check_fw` (and `check_ui`)

---

### OQ-11 — Storage scope format for disk indices > 0

**Resolved (2026-04-08):** Upstream (`api-reference/storage.md`) confirms the
scope format is `storage:diskN[:mode]` where `N` is the zero-based disk index
and `mode` is `rw` (read/write) or omitted/`ro` (read-only). Example shown:
`storage:disk0:rw` and `storage:disk1`. Both disks can be addressed
independently with separate tokens. PPA-only (EPA returns 404).

---

### OQ-11 (original report)

**Affected endpoints:** `GET /api/storage/unlock`, `GET /api/storage/lock`

The spec mentions `storage:disk0:rw` and `storage:disk1:rw` in the scope table,
but the format is only illustrated for disk0. The `status` response shows a
`storage` array with entries like `"disk0:rw"`, `"disk1:-"`.

**Questions:**
- Is the scope always `storage:diskN:rw` where N is the zero-based disk index?
- Is `storage:disk0:ro` (read-only unlock) a valid scope? The spec lists it but
  the lock endpoint only mentions `rw` scopes.
- Can both disks be unlocked simultaneously with separate tokens?

---

### OQ-12 — `GET /api/crypto/hmac/verify` and `POST /api/crypto/exdsa/verify` response body not shown

**Resolved (2026-04-14):** The `encedo-hem-api-doc` repo
(`crypto/hmac-verify.md`, `crypto/exdsa-verify.md`) confirms:
- **Valid:** HTTP 200, no response body.
- **Invalid / failed:** HTTP 406 ("Operation failed (verification failed)").

The distinction is by HTTP status code only — there is no JSON body for
either outcome.

---

## Minor (low impact, easily worked around)

### OQ-13 — `genuine` attestation blob: format and size unknown

**Affected endpoint:** `GET /api/system/config/attestation`

The `genuine` field is described as opaque. No size guidance is given for
allocating a receive buffer.

**Questions:**
- What is the approximate maximum size of the `genuine` blob?

---

### OQ-14 — Check-in and ext/request response field sizes not specified

**Affected endpoints:** `GET /api/system/checkin`, `POST /api/auth/ext/request`

Both return opaque blobs (`check`, `challenge`) that must be stored and forwarded.
No maximum size is documented. The library currently uses `malloc(resp_len + 1)`
which handles any size, but fixed-size buffers in future language bindings need
this information.

**Questions:**
- What is the maximum size of the `check` challenge from check-in?
- What is the maximum size of the `challenge` from `ext/request`?

---

### OQ-15 — `POST /api/auth/ext/validate` `reply` field size unknown

**Affected endpoint:** `POST /api/auth/ext/validate`

The `reply` value (returned by the notification broker, forwarded to validate)
has no documented size limit. The current stub allocates 1024 bytes for it.

**Questions:**
- What is the maximum size of the `reply` field?

---

## Summary table

| ID | Severity | Status | Topic | Blocks |
|---|---|---|---|---|
| OQ-1 | Critical | **Resolved** | Broker URLs and flow documented | — |
| OQ-2 | Critical | **Resolved** | Broker request/response format; polling via `notify/event/check/{eventid}` | — |
| OQ-3 | Critical | **Resolved** | `epk` comes from broker `/notify/session` | — |
| OQ-4 | Significant | **Resolved** | `lbl` = device label | — |
| OQ-5 | Significant | **Resolved** | `ctx` is opaque free-form ≤64 chars, not echoed in token | — |
| OQ-6 | Significant | **Resolved** | `update` response body is ignored by all callers; success = HTTP 200 | — |
| OQ-7 | Significant | Partially resolved | Pattern convention is `^` + base64(≥6B); exact 6-byte rule still inferred | `hem_key_search` |
| OQ-8 | Significant | **Resolved** | Log entry structure + chain verification fully specified | Field name labels still unlabelled |
| OQ-9 | Significant | **Resolved** | Firmware binary upload format | — |
| OQ-10 | Significant | **Resolved** | `check_fw` = 4s poll, `check_ui` = 60s initial + 5s poll | — |
| OQ-11 | Significant | **Resolved** | Storage scope format for disk N | — |
| OQ-12 | Significant | **Resolved** | Verify: 200 = valid (no body), 406 = failed | — |
| OQ-13 | Minor | Open | `genuine` blob max size | Buffer sizing |
| OQ-14 | Minor | Open | Checkin/challenge blob max sizes | Buffer sizing in bindings |
| OQ-15 | Minor | Open | Broker `reply` field max size | Buffer sizing |
| OQ-16 | Critical | **Resolved** | Scope is `keymgmt:get`, not `keymgmt:list` | — |
| OQ-17 | Critical | **Resolved** | List page size default/cap is 15 | — |
| OQ-18 | Significant | **Practice confirmed** | `keymgmt:update`: all callers send `label` + `descr` together; treat `label` as mandatory | Upstream doc still says optional |
| OQ-19 | Significant | **Resolved** | Test suite always sends `mode: "ECDH,ExDSA"` for NIST ECC | — |
| OQ-20 | Significant | **Resolved** | Test suite confirms 406 on duplicate import is expected device behaviour | — |
| OQ-21 | Significant | **Resolved** | `status.https` = HTTPS listener capability flag; Manager uses it to redirect HTTP→HTTPS | — |
