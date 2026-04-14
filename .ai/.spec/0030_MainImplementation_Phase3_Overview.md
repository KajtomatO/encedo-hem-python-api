# Phase 3: Admin, storage, upgrade, logger

**Status:** Not yet planned in detail

**Goal:** Everything except remote authentication.

**Tasks:**
- [ ] `api/logger.py`: `key` (audit log public key), `list` (PPA), `get` (PPA), plus a helper that verifies the Ed25519-signed nonce to prove the key came from this device.
- [ ] `api/storage.py`: `unlock`, `lock` for disk0/disk1 (PPA only, `HemNotSupportedError` on EPA).
- [ ] `api/upgrade.py`: `upload_fw` / `check_fw` / `install_fw` and the `_ui` equivalents, using the newly-documented `application/octet-stream` + `Content-Disposition` transport (OQ-9 resolved).
- [ ] `api/system.py`: `shutdown` (PPA), `config_attestation`, `config_provisioning`.
- [ ] Binary-body path in `transport.py` (`Transport.post_binary(path, body, filename, token)`).
- [ ] Tests for each.

**Key references:**
- OQ-8 (resolved): log entry structure + chain verification fully specified.
- OQ-9 (resolved): firmware binary upload is `application/octet-stream` with `Content-Disposition` and `Expect: 100-continue`.
- OQ-10 (resolved): `check_fw` polls every 4s, `check_ui` 60s initial + 5s poll.
- OQ-11 (resolved): storage scope format is `storage:diskN[:mode]`.

**Deliverable:** `v0.3.0`. Near-complete device coverage.

**Dependencies:** Phase 1. Independent of Phase 2.
