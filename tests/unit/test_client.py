"""HemClient lifecycle, ensure_ready, and passphrase handling."""

from __future__ import annotations

from datetime import datetime, timezone

import httpx
import respx

from encedo_hem.client import HemClient

_RTC_ISO = "2023-11-14T22:13:20Z"
_RTC_DT = datetime(2023, 11, 14, 22, 13, 20, tzinfo=timezone.utc)


def _version_response() -> httpx.Response:
    return httpx.Response(
        200,
        json={"hwv": "PPA-1.0", "blv": "bl", "fwv": "1.2.2", "fws": "x"},
    )


def _status_response_rtc_set() -> httpx.Response:
    return httpx.Response(
        200,
        json={"hostname": "h", "fls_state": 0, "https": True, "ts": _RTC_ISO},
    )


def _status_response_rtc_unset() -> httpx.Response:
    return httpx.Response(200, json={"hostname": "h", "fls_state": 0, "https": True})


def test_context_manager() -> None:
    with HemClient("device.local", "passw0rd") as h:
        assert h.system is not None
        assert h.keys is not None
        assert h.crypto is not None


def test_close_zeroes_passphrase_buffer() -> None:
    h = HemClient("device.local", "passw0rd")
    assert h._passphrase_buf == bytearray(b"passw0rd")
    h.close()
    assert h._passphrase_buf is None


def test_callable_passphrase_never_stored_as_buffer() -> None:
    calls = {"n": 0}

    def provider() -> str:
        calls["n"] += 1
        return "passw0rd"

    h = HemClient("device.local", provider)
    assert h._passphrase_buf is None
    # The provider has not been called at construction time.
    assert calls["n"] == 0
    h.close()


def test_ensure_ready_fetches_version_and_status() -> None:
    with HemClient("device.local", "passw0rd") as h, respx.mock() as router:
        router.get("https://device.local/api/system/version").mock(return_value=_version_response())
        router.get("https://device.local/api/system/status").mock(
            return_value=_status_response_rtc_set()
        )

        h.ensure_ready()

        assert h.firmware_version == "1.2.2"
        assert h.last_status is not None
        assert h.last_status.hostname == "h"


def test_ensure_ready_runs_checkin_when_rtc_unset() -> None:
    with HemClient("device.local", "passw0rd") as h, respx.mock() as router:
        router.get("https://device.local/api/system/version").mock(return_value=_version_response())
        # First status: ts missing -> trigger check-in.
        # After check-in: ts set.
        status_route = router.get("https://device.local/api/system/status")
        status_route.side_effect = [
            _status_response_rtc_unset(),
            _status_response_rtc_set(),
        ]
        checkin_get = router.get("https://device.local/api/system/checkin").mock(
            return_value=httpx.Response(200, json={"nonce": "abc"})
        )
        backend_post = router.post("https://api.encedo.com/checkin").mock(
            return_value=httpx.Response(200, json={"reply": "ok"})
        )
        checkin_post = router.post("https://device.local/api/system/checkin").mock(
            return_value=httpx.Response(200, json={})
        )

        h.ensure_ready()

        assert checkin_get.called
        assert backend_post.called
        assert checkin_post.called
        assert h.last_status is not None
        assert h.last_status.ts == _RTC_DT


def test_ensure_ready_skips_checkin_when_disabled() -> None:
    with (
        HemClient("device.local", "passw0rd", auto_checkin=False) as h,
        respx.mock(assert_all_called=False) as router,
    ):
        router.get("https://device.local/api/system/version").mock(return_value=_version_response())
        router.get("https://device.local/api/system/status").mock(
            return_value=_status_response_rtc_unset()
        )
        checkin_get = router.get("https://device.local/api/system/checkin").mock(
            return_value=httpx.Response(200, json={})
        )

        h.ensure_ready()

        assert not checkin_get.called


def test_ensure_ready_is_idempotent() -> None:
    with HemClient("device.local", "passw0rd") as h, respx.mock() as router:
        version_route = router.get("https://device.local/api/system/version").mock(
            return_value=_version_response()
        )
        status_route = router.get("https://device.local/api/system/status").mock(
            return_value=_status_response_rtc_set()
        )

        h.ensure_ready()
        before_calls = version_route.call_count + status_route.call_count
        h.ensure_ready()
        after_calls = version_route.call_count + status_route.call_count

        assert before_calls == after_calls


def test_last_status_populated_after_ensure_ready() -> None:
    with HemClient("device.local", "passw0rd") as h, respx.mock() as router:
        router.get("https://device.local/api/system/version").mock(return_value=_version_response())
        router.get("https://device.local/api/system/status").mock(
            return_value=_status_response_rtc_set()
        )
        assert h.last_status is None
        h.ensure_ready()
        assert h.last_status is not None
