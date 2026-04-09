# Open Questions — API Documentation Gaps

Issues found in `HEM-REST-API-DESIGN.md` and `INTEGRATION_GUIDE.md` that block
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
page size and paginate via `offset`. INTEGRATION_GUIDE.md §4.2.1 updated
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

**Affected endpoints:** `POST /api/auth/ext/init` (pairing), `POST /api/auth/ext/request` (login)

The API design states the device response must be forwarded to:
```
POST api.encedo.com/notify/event/new
```
Testing confirmed this URL returns **HTTP 404**. The check-in broker
(`https://api.encedo.com/checkin`) works, so the server is reachable — only
this path is wrong.

**Blocked:** `hem_auth_ext_pair` and `hem_auth_ext_login` are stubbed out until
the correct URL is confirmed.

**Questions:**
- What is the correct broker URL?
- Does the URL include the device `eid` as a path segment (e.g. `.../event/<eid>`)?
- Is there a query parameter or request header required?

---

### OQ-2 — Notification broker request/response format undefined

**Affected endpoints:** same as OQ-1

The API design says "forward the entire response verbatim" but does not document
what the broker returns.

For **pairing** (`ext/init` → broker → `ext/validate`):
- The broker response is assumed to contain `pid` and `reply` fields (based on
  what `ext/validate` expects), but this is not stated anywhere.

For **login** (`ext/request` → broker → `ext/token`):
- The broker response is assumed to contain an `authreply` field (based on what
  `ext/token` expects), but this is not stated anywhere.

**Questions:**
- What JSON fields does the broker return for pairing? (`pid`, `reply`?)
- What JSON fields does the broker return for login? (`authreply`?)
- Does the broker block synchronously until the phone approves, or does it return
  immediately and require polling? If polling, what is the polling endpoint?
- Is there a timeout on the broker side? What HTTP status is returned on timeout?

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

**Affected endpoints:** `POST /api/auth/ext/init`, `POST /api/auth/ext/request`

Both endpoints accept an `epk` described as "backend session public key (base64)".
The word "backend" is ambiguous — it could mean:
- The calling application generates an ephemeral X25519 keypair and passes the
  public key (this is the current assumption in the implementation).
- The Encedo cloud backend generates a session keypair, and `epk` must be
  retrieved from there first.

If the application generates it, the corresponding private key must be used to
decrypt something in the broker response (which would explain why the broker
response format is undefined — it may be encrypted).

**Questions:**
- Does the client (library) generate the `epk` keypair, or does it come from
  the Encedo cloud backend?
- Is the broker response encrypted to `epk`? If so, what encryption scheme?
- Should the library generate and manage the ephemeral keypair internally, or
  should the caller provide both the public and private key?

---

## Significant (causes unclear behaviour)

### OQ-18 — `POST /api/keymgmt/update` requires `label` even when only updating `descr`

**Affected endpoint:** `POST /api/keymgmt/update`
**Confirmed via:** live device testing (firmware v1.2.2-DIAG)

The API design doc says all fields are optional (at least one of `label`/`descr` required).
In practice the device returns **HTTP 400** if `label` is omitted, even when a valid
`descr` is provided. Sending both `label` and `descr` succeeds.

The spec needs to note that `label` is mandatory. Bindings that expose a
"set description only" helper will silently break without this.

---

### OQ-19 — NIST ECC keys created without `mode` are ECDH-only; signing returns 406

**Affected endpoint:** `POST /api/keymgmt/create`
**Confirmed via:** live device testing (firmware v1.2.2-DIAG, SECP256R1 key)

The API design doc describes `mode` as optional with no stated default. In practice,
omitting `mode` for NIST ECC key types (`SECP256R1`, etc.) creates a key that only
supports ECDH. Calling sign (`POST /api/crypto/exdsa/sign`) on such a key returns
**HTTP 406**.

The spec should state the default explicitly: omitting `mode` for NIST ECC keys
is equivalent to `"ECDH"`. Callers that need signing must pass `"ExDSA"` or
`"ECDH,ExDSA"`.

Note: `ED25519` and other non-NIST curve types are sign-only by nature and are
unaffected — `mode` is only relevant for NIST ECC.

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

**Questions:**
- Is the field's presence over HTTPS a firmware bug, or is the spec
  wording incomplete?
- If the latter, what does `false` actually indicate on a TLS-served
  session — and does it ever flip to `true` after attested cert
  provisioning?
- Should bindings rename it (e.g. `https_provisioned`) or keep the wire
  name?

---

### OQ-20 — `POST /api/keymgmt/import` returns 406 on duplicate public key

**Affected endpoint:** `POST /api/keymgmt/import`
**Confirmed via:** live device testing (firmware v1.2.2-DIAG)

Importing the same public key a second time returns **HTTP 406**. This is not listed
in the API design doc's error table for this endpoint (which shows no 406 case), nor
in the global status code table (which lists 406 as "auth/init only").

The spec's 406 description needs to be generalized: it also covers duplicate key
import and (from the derive spec) ECDH shared secret too small for the requested type.

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

**Affected endpoint:** `GET /api/auth/token`

Response includes a `lbl` field:
```json
{ "eid": "...", "spk": "...", "jti": "...", "exp": ..., "lbl": "<label>" }
```
The `lbl` field is present in the spec but never explained. The library currently
ignores it.

**Questions:**
- What does `lbl` contain? (Device label? User label?)
- Should the library expose it to callers?
- Is it required to be included in the eJWT payload?

---

### OQ-5 — `ctx` field in `POST /api/auth/token` eJWT payload

**Partially resolved (2026-04-08):** Upstream lists `ctx` in the eJWT payload
field set; elsewhere in `system/config` it is described as **"Instance context
id"**. The exact effect on token issuance/claims is still not documented.
Library may continue to omit it; revisit if a use case appears.

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

**Affected endpoint:** `POST /api/keymgmt/update`

Response is described as "Empty or acknowledgement object" with no JSON example.
The library cannot tell whether the update succeeded other than by checking HTTP 200.

**Questions:**
- Is the response body always empty `{}`?
- Is there an `updated: true/false` field similar to `POST /api/system/config`?

---

### OQ-7 — `POST /api/keymgmt/search` minimum pattern length for unauthenticated use

**Affected endpoint:** `POST /api/keymgmt/search`

The spec says unauthenticated search is allowed "if `allow_keysearch` is enabled
and pattern >= 6 bytes". It is unclear whether "6 bytes" refers to the raw binary
length of the `descr` pattern before base64 encoding, or the length of the
base64 string itself.

**Questions:**
- Is the 6-byte minimum applied before or after base64 encoding?
- What HTTP status is returned if the pattern is too short?

---

### OQ-8 — Audit log entry format only partially described

**Affected endpoint:** `GET /api/logger/{id}`

The spec says the response is "plain text" with entries that are "pipe-delimited
with 7 fields" but does not name the fields.

**Questions:**
- What are the 7 pipe-delimited fields? (timestamp, event type, KID, user, ...?)
- Is the response Content-Type `text/plain` or `application/octet-stream`?
- Is there a maximum file size, or can log files be arbitrarily large?

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

**Questions:**
- What is the expected verification duration?
- Is there a timeout after which the device gives up and returns an error?
- Same question applies to `GET /api/system/upgrade/check_ui`.

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

**Affected endpoints:** both verify endpoints

Both are described as "Response 200: HMAC is valid" / "Response 200: Signature valid"
with no example JSON body. It is unclear whether the body is `{}`, absent, or
contains a confirmation field.

**Questions:**
- What is the exact response body on successful verification?
- Is there a body that distinguishes "valid" from "invalid" (vs. relying solely
  on HTTP status codes)?

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

| ID | Severity | Topic | Blocks |
|---|---|---|---|
| OQ-1 | Critical | Broker URL returns 404 | `hem_auth_ext_pair`, `hem_auth_ext_login` |
| OQ-2 | Critical | Broker request/response format | Same |
| OQ-3 | Critical | `epk` generation and encryption | Same |
| OQ-4 | Significant | `lbl` field undocumented | Minor — library ignores it |
| OQ-5 | Significant | `ctx` in eJWT payload undocumented | Minor — library omits it |
| OQ-6 | Significant | `update` response format | `hem_key_update` |
| OQ-7 | Significant | Search pattern minimum length | `hem_key_search` |
| OQ-8 | Significant | Log entry field names | `hem_logger_download` |
| OQ-9 | Significant | Firmware binary upload format | `hem_upgrade_upload_fw/ui` |
| OQ-10 | Significant | `check_fw` polling interval | `hem_upgrade_check_fw` |
| OQ-11 | Significant | Storage scope format for disk N | `hem_storage_unlock/lock` |
| OQ-12 | Significant | Verify endpoints response body | `hem_hmac_verify`, `hem_verify` |
| OQ-13 | Minor | `genuine` blob max size | Buffer sizing |
| OQ-14 | Minor | Checkin/challenge blob max sizes | Buffer sizing in bindings |
| OQ-15 | Minor | Broker `reply` field max size | Buffer sizing |
| OQ-16 | Critical | `keymgmt:get` rejects `keymgmt:list` scope (spec wrong) | All bindings using `hem_key_get` |
| OQ-17 | Critical | List endpoint silently caps page size at ~15 (undocumented) | Any paginated list operation |
| OQ-18 | Significant | `keymgmt:update` requires `label` even for descr-only update | `hem_key_update` |
| OQ-19 | Significant | NIST ECC default mode is ECDH-only; signing fails with 406 | `hem_key_create` + `hem_sign` |
| OQ-20 | Significant | `keymgmt:import` returns 406 on duplicate public key (undocumented) | `hem_key_import` |
| OQ-21 | Significant | `status.https` returned over HTTPS, contradicting upstream "HTTP-only" spec | Field semantics in all bindings |
