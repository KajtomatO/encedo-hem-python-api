# Phase 3 Step 9: `is_alive()` — ICMP ping check

**Files:**
- `src/encedo_hem/client.py` — add `is_alive()` method
- `ARCHITECTURE.md` — document `is_alive()` on HemClient
- `.ai/.api-reference/INTEGRATION_GUIDE.md` — add ping fact to Section 2
- `tests/integration/test_00_sanity.py` — new file, runs first
- `tests/unit/test_client_is_alive.py` — new file

---

## Context and design rationale

The `conftest.py` pre-flight already does an HTTP-based liveness check
(`GET /api/system/version`) and its comment explicitly says:

> *"ICMP ping is the wrong primitive here — many devices block ICMP, and
> what the integration suite actually depends on is HTTPS reachability."*

`is_alive()` serves a **different purpose**: a network-layer reachability
check (L3) before any API call is attempted. HEM devices respond to ICMP echo
requests. This is useful for:
- Pre-flight "is the device plugged in / on the network?" check
- Distinguishing a network failure (ping fails, HTTP also fails) from an
  API failure (ping succeeds, HTTP fails — device is up but API broken)

`is_alive()` is therefore an ICMP-based check, complementary to (not replacing)
the existing HTTP check in `conftest.py` and in `ensure_ready()`.

**It is NOT called automatically from `ensure_ready()`** — ICMP may be blocked
by firewalls or container networking. It is an opt-in diagnostic tool.

---

## `HemClient.is_alive(*, timeout: float = 2.0) -> bool`

Placed directly on `HemClient` (not under a namespace). Rationale: this is a
pre-API connectivity check; it does not go through `transport` or `auth` and
does not fit cleanly under `system.*` (which is HTTP-only).

**Signature:**
```python
def is_alive(self, *, timeout: float = 2.0) -> bool:
    """Return ``True`` if the device responds to an ICMP echo request.

    Uses the OS ``ping`` command via :mod:`subprocess`. ICMP may be blocked
    by firewalls — a ``False`` return does not necessarily mean the API is
    unreachable; use :meth:`ensure_ready` for an HTTP-level liveness check.

    :param timeout: Seconds to wait for a reply (minimum 1).
    """
```

**Implementation — subprocess ICMP ping:**

```python
import platform
import subprocess

def is_alive(self, *, timeout: float = 2.0) -> bool:
    is_windows = platform.system().lower() == "windows"
    count_flag = "-n" if is_windows else "-c"
    # Windows -w is in milliseconds; Linux/macOS -W is in whole seconds.
    if is_windows:
        timeout_flag, timeout_val = "-w", str(int(timeout * 1000))
    else:
        timeout_flag, timeout_val = "-W", str(max(1, int(timeout)))
    cmd = [
        "ping", count_flag, "1", timeout_flag, timeout_val, self._host
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=timeout + 2)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False
```

`self._host` is already stored on `HemClient` (set in `__init__` as `self._host = host`).

---

## ARCHITECTURE.md update

In the `HemClient` component section, add `is_alive()` to the interfaces list:

> `is_alive(*, timeout: float = 2.0) -> bool` — sends one ICMP echo request to
> `host`. Pure network-layer check (not HTTP). Returns `False` on timeout,
> ICMP-blocked networks, or if the OS `ping` command is unavailable. Does NOT
> imply API availability — use `ensure_ready()` for that.

In the Key architectural decisions, note:

> **`is_alive()` is opt-in, not integrated into `ensure_ready()`.** ICMP may be
> blocked in containerised or cloud environments. The library never silently
> depends on ICMP; `ensure_ready()` uses the HTTP version probe which is the
> correct liveness check for the API.

---

## INTEGRATION_GUIDE.md update

Add to **Section 2 (Transport)**, as a new subsection **2.6**:

> **2.6 ICMP ping**
>
> HEM devices respond to ICMP echo requests (standard `ping`). This is useful
> as a fast network-layer reachability probe before any HTTPS connection attempt.
> Note that ICMP may be blocked by firewalls or container networking; absence of
> a ping reply does not guarantee the HTTPS API is unreachable. For API-level
> liveness, use `GET /api/system/version` (unauthenticated, always available).

---

## Unit tests

`tests/unit/test_client_is_alive.py`

Mock `subprocess.run` — do not shell out in unit tests.

```python
from unittest.mock import MagicMock, patch

def test_is_alive_true_on_returncode_0(make_client):
    with patch("encedo_hem.client.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        assert make_client().is_alive() is True

def test_is_alive_false_on_nonzero_returncode(make_client):
    with patch("encedo_hem.client.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1)
        assert make_client().is_alive() is False

def test_is_alive_false_on_timeout(make_client):
    with patch("encedo_hem.client.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=[], timeout=2)
        assert make_client().is_alive() is False

def test_is_alive_false_when_ping_not_found(make_client):
    with patch("encedo_hem.client.subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError
        assert make_client().is_alive() is False

def test_is_alive_uses_host(make_client):
    with patch("encedo_hem.client.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        make_client("device.local").is_alive()
        cmd = mock_run.call_args[0][0]
        assert "device.local" in cmd
```

`make_client` is a local fixture (or a helper function) that creates a
`HemClient("device.local", "x")` without hitting the network.

---

## Integration test

`tests/integration/test_00_sanity.py` — filename starts with `00` so it sorts
before all other test files and runs first.

```python
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
        "Check network connectivity and that ICMP is not blocked."
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
```

**Note:** The conftest `_device_reachability_check` session fixture already
hard-fails the suite if the HTTP probe cannot reach the device. These three
tests make that check explicit and visible in the test report, and add the
ICMP-layer check that the conftest does not perform.

---

## No changes to conftest.py

The existing `_device_reachability_check` fixture stays untouched. It serves
a different role (hard-fail the session before any test) and uses HTTP correctly
for that purpose.
