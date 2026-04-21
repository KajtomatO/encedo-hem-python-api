# Phase 3: Admin, storage, upgrade, logger

**Status:** Planned — step specs in 0031–0038

**Goal:** Everything except remote authentication.

**Step specs:**
- [0031](0031_MainImplementation_Phase3_Step1.md) — Models + enums (`StorageDisk`, `SelftestResult`, `AttestationResult`, `LoggerKeyInfo`, `FirmwareCheckResult`)
- [0032](0032_MainImplementation_Phase3_Step2.md) — Transport additions (`post_binary`, `request_no_raise`, `request_text`)
- [0033](0033_MainImplementation_Phase3_Step3.md) — System additions (`shutdown`, `selftest`, `config_attestation`, `config_provisioning`) + fix `reboot` scope
- [0034](0034_MainImplementation_Phase3_Step4.md) — Storage API (`unlock`, `lock`)
- [0035](0035_MainImplementation_Phase3_Step5.md) — Logger API (`key`, `list`, `get`, `delete`)
- [0036](0036_MainImplementation_Phase3_Step6.md) — Upgrade API (`upload_fw/check_fw/install_fw`, `upload_ui/check_ui/install_ui`, `upload_bootldr`, `usbmode`)
- [0037](0037_MainImplementation_Phase3_Step7.md) — Client wiring + exports
- [0038](0038_MainImplementation_Phase3_Step8.md) — Integration tests
- [0039](0039_MainImplementation_Phase3_Step9.md) — `is_alive()` ICMP ping check + `test_00_sanity.py`

**Tasks (summary):**
- [ ] `api/logger.py`: `key`, `list`, `get`, `delete` (scope `logger:del`).
- [ ] `api/storage.py`: `unlock`, `lock` for disk0/disk1 (PPA only).
- [ ] `api/upgrade.py`: `upload_fw` / `check_fw` / `install_fw` + UI equivalents + `upload_bootldr` + `usbmode`.
- [ ] `api/system.py`: `shutdown`, fix `reboot` scope, `selftest`, `config_attestation`, `config_provisioning`.
- [ ] Transport: `post_binary`, `request_no_raise`, `request_text`.
- [ ] Integration tests for all above (destructive endpoints marked skip).
- [ ] `HemClient.is_alive()` ICMP ping, `test_00_sanity.py` as the first integration test.

**Key references:**
- OQ-8 (resolved): log entry structure + chain verification fully specified.
- OQ-9 (resolved): firmware binary upload is `application/octet-stream` with `Content-Disposition` and `Expect: 100-continue`.
- OQ-10 (resolved): `check_fw` = 4s poll, `check_ui` = 60s initial + 5s poll.
- OQ-11 (resolved): storage scope format is `storage:diskN[:mode]`.

**Deliverable:** `v0.3.0`. Near-complete device coverage.

**Dependencies:** Phase 1. Independent of Phase 2.
