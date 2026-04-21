"""Integration tests for Phase 3 system endpoints."""
from __future__ import annotations

import time

import pytest

from encedo_hem import AttestationResult, HemClient, SelftestResult

_REBOOT_TIMEOUT = 20  # seconds


def test_selftest(hem: HemClient) -> None:
    result = hem.system.selftest()
    assert isinstance(result, SelftestResult)
    assert isinstance(result.fls_state, int)
    assert isinstance(result.kat_busy, bool)


def test_config_attestation(hem: HemClient) -> None:
    result = hem.system.config_attestation()
    assert isinstance(result, AttestationResult)
    assert result.crt  # non-empty PEM or certificate string
    assert isinstance(result.genuine, bool)


def test_reboot(hem: HemClient) -> None:
    """Reboot the device and verify it comes back up within 20 seconds."""
    uptime_before = hem.system.status().uptime
    hem.system.reboot()  # invalidates all tokens

    # Wait for device to come back — probe unauthenticated version endpoint.
    deadline = time.monotonic() + _REBOOT_TIMEOUT
    while time.monotonic() < deadline:
        try:
            hem.system.version()
            break
        except Exception:
            time.sleep(1.0)
    else:
        pytest.fail(f"Device did not come back within {_REBOOT_TIMEOUT}s after reboot")

    # Re-authenticate and verify uptime was reset.
    uptime_after = hem.system.status().uptime
    if uptime_before is not None and uptime_after is not None:
        assert uptime_after < uptime_before, (
            f"Expected uptime to decrease after reboot "
            f"(before={uptime_before}, after={uptime_after})"
        )


def test_shutdown(hem: HemClient) -> None:
    """Shut down the device and verify it stops responding.

    Skipped in normal test runs — set HEM_ALLOW_SHUTDOWN=1 to execute.
    """
    import os
    if not os.environ.get("HEM_ALLOW_SHUTDOWN"):
        pytest.skip("set HEM_ALLOW_SHUTDOWN=1 to run")

    hem.system.shutdown()

    # Device should stop responding within ~10 seconds.
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            hem.system.version()
            time.sleep(1.0)
        except Exception:
            return  # expected — device is down

    pytest.fail("Device still responding 10s after shutdown")
