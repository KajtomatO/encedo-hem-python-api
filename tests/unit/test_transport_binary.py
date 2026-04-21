"""Tests for Transport.post_binary()."""

from __future__ import annotations

import httpx
import respx

from encedo_hem.errors import HemNotFoundError
from encedo_hem.transport import Transport


def _make_transport() -> Transport:
    return Transport("device.local")


def test_post_binary_content_type() -> None:
    with respx.mock() as router:
        router.post("https://device.local/api/system/upgrade/upload_fw").mock(
            return_value=httpx.Response(200, json={})
        )
        t = _make_transport()
        t.post_binary("/api/system/upgrade/upload_fw", b"\x00\x01\x02", "fw.bin")
        request = router.calls[0].request
        assert request.headers["content-type"] == "application/octet-stream"


def test_post_binary_content_disposition() -> None:
    with respx.mock() as router:
        router.post("https://device.local/api/system/upgrade/upload_fw").mock(
            return_value=httpx.Response(200, json={})
        )
        t = _make_transport()
        t.post_binary("/api/system/upgrade/upload_fw", b"\x00\x01\x02", "fw.bin")
        request = router.calls[0].request
        assert request.headers["content-disposition"] == 'attachment; filename="fw.bin"'


def test_post_binary_expect_header() -> None:
    with respx.mock() as router:
        router.post("https://device.local/api/system/upgrade/upload_fw").mock(
            return_value=httpx.Response(200, json={})
        )
        t = _make_transport()
        t.post_binary("/api/system/upgrade/upload_fw", b"\x00\x01\x02", "fw.bin")
        request = router.calls[0].request
        assert request.headers["expect"] == "100-continue"


def test_post_binary_non_200_raises() -> None:
    with respx.mock() as router:
        router.post("https://device.local/api/system/upgrade/upload_fw").mock(
            return_value=httpx.Response(404, json={})
        )
        t = _make_transport()
        try:
            t.post_binary("/api/system/upgrade/upload_fw", b"\x00", "fw.bin")
            raise AssertionError("should have raised")
        except HemNotFoundError:
            pass


def test_post_binary_sends_body() -> None:
    captured: list[bytes] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request.content)
        return httpx.Response(200, json={})

    with respx.mock() as router:
        router.post("https://device.local/api/system/upgrade/upload_fw").mock(side_effect=handler)
        t = _make_transport()
        payload = b"\xde\xad\xbe\xef"
        t.post_binary("/api/system/upgrade/upload_fw", payload, "fw.bin")
    assert captured[0] == payload
