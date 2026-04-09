from __future__ import annotations

import secrets

import pytest

from encedo_hem._base64 import (
    b64_std_decode,
    b64_std_encode,
    b64url_nopad_decode,
    b64url_nopad_encode,
)


def test_std_encode_known_value() -> None:
    assert b64_std_encode(b"foo") == "Zm9v"
    assert b64_std_decode("Zm9v") == b"foo"


def test_std_encode_includes_padding() -> None:
    assert b64_std_encode(b"a") == "YQ=="
    assert b64_std_encode(b"ab") == "YWI="


def test_url_nopad_uses_urlsafe_alphabet() -> None:
    assert b64url_nopad_encode(b"\xff\xff\xff") == "____"
    assert b64url_nopad_decode("____") == b"\xff\xff\xff"


def test_url_nopad_strips_padding() -> None:
    # base64 of b"a" is "YQ==" -> base64url no-pad form is "YQ"
    assert b64url_nopad_encode(b"a") == "YQ"
    assert b64url_nopad_decode("YQ") == b"a"


@pytest.mark.parametrize("length", [0, 1, 31, 32, 33, 64])
def test_round_trip_random(length: int) -> None:
    blob = secrets.token_bytes(length)
    assert b64_std_decode(b64_std_encode(blob)) == blob
    assert b64url_nopad_decode(b64url_nopad_encode(blob)) == blob
