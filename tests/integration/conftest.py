from __future__ import annotations

import os
from collections.abc import Iterator

import httpx
import pytest

from encedo_hem import HemClient

_REACHABILITY_TIMEOUT_S = 5.0
"""How long the pre-flight probe waits for the device. Kept short so an
unreachable device fails the suite in seconds, not after every test times
out individually (~30s each)."""


def _device_reachable(host: str) -> tuple[bool, str]:
    """Probe ``GET /api/system/version`` once with a short timeout.

    ICMP ping is the wrong primitive here — many devices block ICMP, and
    what the integration suite actually depends on is HTTPS reachability of
    the HEM API. A 200 from ``/api/system/version`` is the cheapest, most
    faithful liveness check: it requires no auth and exercises the same
    transport (TLS-bypass) the suite uses.
    """
    url = f"https://{host}/api/system/version"
    try:
        with httpx.Client(verify=False, timeout=_REACHABILITY_TIMEOUT_S) as client:
            response = client.get(url)
    except httpx.HTTPError as exc:
        return False, f"{type(exc).__name__}: {exc}"
    if response.status_code != 200:
        return False, f"HTTP {response.status_code}"
    return True, ""


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if not (os.environ.get("HEM_HOST") and os.environ.get("HEM_PASSPHRASE")):
        skip = pytest.mark.skip(reason="HEM_HOST and HEM_PASSPHRASE not set")
        for item in items:
            item.add_marker(skip)


@pytest.fixture(scope="session", autouse=True)
def _device_reachability_check() -> None:
    """Pre-flight HEM device probe.

    Runs **once per session** before any test. If ``HEM_HOST`` is set but
    the device does not answer ``GET /api/system/version`` within
    ``_REACHABILITY_TIMEOUT_S``, the suite hard-fails — the caller asked
    for a real-device run, so an unreachable device is an integration
    failure, not a "no environment configured" skip.
    """
    host = os.environ.get("HEM_HOST")
    if not host:
        return
    ok, detail = _device_reachable(host)
    if not ok:
        pytest.fail(
            f"HEM device at {host!r} not reachable ({detail}); "
            f"check power, network, and that GET /api/system/version answers within "
            f"{_REACHABILITY_TIMEOUT_S:.0f}s",
            pytrace=False,
        )


@pytest.fixture
def hem() -> Iterator[HemClient]:
    with HemClient(
        host=os.environ["HEM_HOST"],
        passphrase=os.environ["HEM_PASSPHRASE"],
    ) as client:
        client.ensure_ready()
        yield client
