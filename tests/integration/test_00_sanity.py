"""Sanity checks — always the first tests to run.

These verify the most basic pre-conditions before exercising any API:
  1. ICMP ping succeeds (network layer).
  2. GET /api/system/version succeeds (API layer).
  3. Device reports itself as initialised.
"""

from __future__ import annotations

from encedo_hem import HemClient


def test_device_responds_to_ping(hem: HemClient) -> None:
    """ICMP echo round-trip — confirms network-layer reachability."""
    assert hem.is_alive(), (
        "Device did not respond to ICMP ping. "
        "Check network connectivity and that ICMP is not blocked by a firewall."
    )


def test_version_endpoint_responds(hem: HemClient) -> None:
    """API layer sanity — version endpoint returns a non-empty firmware version."""
    version = hem.system.version()
    assert version.fwv, "Empty firmware version string"


def test_device_is_initialised(hem: HemClient) -> None:
    """Device must be initialised before any further test can run."""
    status = hem.system.status()
    assert status.initialized, (
        "Device is not initialised — run auth/init before executing the suite"
    )
