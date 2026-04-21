"""Integration tests for audit logger endpoints."""

from __future__ import annotations

import contextlib

import pytest

from encedo_hem import HemClient, HemError, KeyType, LoggerKeyInfo


def _trigger_audit_event(hem: HemClient) -> None:
    """Drive a known-audited operation so the audit log is non-empty.

    selftest is a diagnostic and is not audited by the device. Key create /
    delete are security-relevant and produce log entries (see
    test_keymgmt_import.py for the same create/delete pattern).
    """
    kid = hem.keys.create("it-logger-trigger", KeyType.ED25519)
    with contextlib.suppress(HemError):
        hem.keys.delete(kid)


def test_logger_key(hem: HemClient) -> None:
    info = hem.logger.key()
    assert isinstance(info, LoggerKeyInfo)
    assert info.key  # non-empty


def test_logger_list_and_get(hem: HemClient) -> None:
    _trigger_audit_event(hem)
    ids = list(hem.logger.list())
    assert len(ids) > 0, "Expected at least one log entry after key create/delete"
    entry_text = hem.logger.get(ids[0])
    assert isinstance(entry_text, str)
    assert entry_text  # non-empty


@pytest.mark.xfail(
    reason=(
        "OQ-26: DELETE /api/logger/:id returns 404 on my.ence.do. Endpoint "
        "is unverified in every reference implementation (Manager UI never "
        "calls DELETE; PHP test_9.php is GET-only). Client code matches "
        "encedo-hem-api-doc/logger/delete.md."
    ),
    strict=False,
)
def test_logger_delete(hem: HemClient) -> None:
    _trigger_audit_event(hem)
    ids = list(hem.logger.list())
    assert ids, "Need at least one log entry to delete"
    target = ids[-1]
    hem.logger.delete(target)
    ids_after = list(hem.logger.list())
    assert target not in ids_after
