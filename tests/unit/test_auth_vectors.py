"""Locks in the eJWT algorithm and the Auth scope cache.

PBKDF2 at 600 000 iterations is the slow path here, so structural assertions
re-use a single ``built_ejwt`` fixture computed once per module.
"""

from __future__ import annotations

import base64
import json
from typing import Any

import httpx
import pytest
import respx

from encedo_hem._base64 import b64url_nopad_decode
from encedo_hem.auth import Auth, build_ejwt
from encedo_hem.errors import HemAuthError
from encedo_hem.models import AuthChallenge
from encedo_hem.transport import Transport


def _spk(seed: bytes = b"\x01" * 32) -> str:
    return base64.b64encode(seed).decode("ascii")


@pytest.fixture(scope="module")
def challenge() -> AuthChallenge:
    return AuthChallenge(
        eid="d4ad81b06b1d493ab2b6f9b1a3e2c7f0",
        spk=_spk(),
        jti="0123456789abcdef",
        exp=2_000_000_000,
        lbl="alice",
    )


@pytest.fixture(scope="module")
def built_ejwt(challenge: AuthChallenge) -> str:
    return build_ejwt(
        challenge=challenge,
        scope="keymgmt:gen",
        passphrase=b"correct horse battery staple",
        now=1_700_000_000,
        requested_exp=1_700_003_600,
    )


def test_three_segments(built_ejwt: str) -> None:
    parts = built_ejwt.split(".")
    assert len(parts) == 3


def test_header_segment_is_hardcoded(built_ejwt: str) -> None:
    header_seg = built_ejwt.split(".")[0]
    decoded = b64url_nopad_decode(header_seg)
    assert decoded == b'{"ecdh":"x25519","alg":"HS256","typ":"JWT"}'


def test_payload_keys_exact(built_ejwt: str) -> None:
    payload_seg = built_ejwt.split(".")[1]
    payload = json.loads(b64url_nopad_decode(payload_seg))
    assert set(payload.keys()) == {"jti", "aud", "exp", "iat", "iss", "scope"}


def test_payload_aud_is_passthrough(built_ejwt: str, challenge: AuthChallenge) -> None:
    payload_seg = built_ejwt.split(".")[1]
    payload = json.loads(b64url_nopad_decode(payload_seg))
    # aud is the original base64 string, byte-for-byte.
    assert payload["aud"] == challenge.spk


def test_payload_scope(built_ejwt: str) -> None:
    payload_seg = built_ejwt.split(".")[1]
    payload = json.loads(b64url_nopad_decode(payload_seg))
    assert payload["scope"] == "keymgmt:gen"


def test_signature_is_256_bit_b64url(built_ejwt: str) -> None:
    sig_seg = built_ejwt.split(".")[2]
    # 32 bytes -> 43 char base64url no-pad.
    assert len(sig_seg) == 43
    assert all(c.isalnum() or c in "-_" for c in sig_seg)


def test_deterministic(challenge: AuthChallenge, built_ejwt: str) -> None:
    again = build_ejwt(
        challenge=challenge,
        scope="keymgmt:gen",
        passphrase=b"correct horse battery staple",
        now=1_700_000_000,
        requested_exp=1_700_003_600,
    )
    assert again == built_ejwt


def test_requested_exp_capped_at_challenge_exp(challenge: AuthChallenge) -> None:
    # requested_exp deliberately overshoots challenge.exp
    over = challenge.exp + 999
    ejwt = build_ejwt(
        challenge=challenge,
        scope="keymgmt:gen",
        passphrase=b"correct horse battery staple",
        now=1_700_000_000,
        requested_exp=over,
    )
    payload = json.loads(b64url_nopad_decode(ejwt.split(".")[1]))
    assert payload["exp"] == challenge.exp


def test_empty_passphrase_does_not_crash(challenge: AuthChallenge) -> None:
    # Device will reject this with 401, but the build itself must not throw.
    ejwt = build_ejwt(
        challenge=challenge,
        scope="keymgmt:gen",
        passphrase=b"",
        now=1_700_000_000,
        requested_exp=1_700_003_600,
    )
    assert ejwt.count(".") == 2


# --- Auth (token cache) tests ---


def _mock_auth_responses(router: respx.MockRouter, *, exp: int) -> dict[str, Any]:
    counters = {"get": 0, "post": 0}
    challenge_body = {
        "eid": "d4ad81b06b1d493ab2b6f9b1a3e2c7f0",
        "spk": _spk(),
        "jti": "0123456789abcdef",
        "exp": exp,
        "lbl": "alice",
    }

    def get_handler(request: httpx.Request) -> httpx.Response:
        counters["get"] += 1
        return httpx.Response(200, json=challenge_body)

    def post_handler(request: httpx.Request) -> httpx.Response:
        counters["post"] += 1
        return httpx.Response(200, json={"token": f"bearer-{counters['post']}"})

    router.get("https://device.local/api/auth/token").mock(side_effect=get_handler)
    router.post("https://device.local/api/auth/token").mock(side_effect=post_handler)
    return counters


def test_auth_caches_per_scope() -> None:
    transport = Transport("device.local")
    try:
        with respx.mock() as router:
            counters = _mock_auth_responses(router, exp=2_000_000_000)
            auth = Auth(transport, lambda: b"correct horse battery staple")

            t1 = auth.ensure_token("keymgmt:gen")
            t2 = auth.ensure_token("keymgmt:gen")
            assert t1 == t2
            assert counters["get"] == 1
            assert counters["post"] == 1
    finally:
        transport.close()


def test_auth_different_scopes_relogin() -> None:
    transport = Transport("device.local")
    try:
        with respx.mock() as router:
            counters = _mock_auth_responses(router, exp=2_000_000_000)
            auth = Auth(transport, lambda: b"correct horse battery staple")

            auth.ensure_token("keymgmt:gen")
            auth.ensure_token("keymgmt:list")
            assert counters["get"] == 2
            assert counters["post"] == 2
    finally:
        transport.close()


def test_auth_cache_independent_of_short_challenge_exp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression for MVP-OQ-2.

    ``challenge.exp`` is the *response deadline* for the challenge, not the
    bearer-token lifetime. A short ``challenge.exp`` (a few seconds) must
    NOT cause the cached bearer to be treated as expired -- the issued
    token is valid for ~``_TOKEN_LIFETIME_S`` per upstream docs. The
    previous test locked in the buggy behaviour where any
    ``challenge.exp`` inside the skew window forced a re-login on every
    call.
    """
    transport = Transport("device.local")
    try:
        with respx.mock() as router:
            now = 1_700_000_000
            counters = _mock_auth_responses(router, exp=now + 5)

            time_ref = {"now": now}
            monkeypatch.setattr("encedo_hem.auth.time.time", lambda: time_ref["now"])

            auth = Auth(transport, lambda: b"correct horse battery staple")

            t1 = auth.ensure_token("keymgmt:gen")
            time_ref["now"] = now + 1
            t2 = auth.ensure_token("keymgmt:gen")
            assert t1 == t2
            assert counters["get"] == 1
            assert counters["post"] == 1
    finally:
        transport.close()


def test_auth_username_set_from_challenge_lbl() -> None:
    transport = Transport("device.local")
    try:
        with respx.mock() as router:
            _mock_auth_responses(router, exp=2_000_000_000)
            auth = Auth(transport, lambda: b"correct horse battery staple")
            assert auth.username is None
            auth.ensure_token("keymgmt:gen")
            assert auth.username == "alice"
    finally:
        transport.close()


def test_auth_invalidate_single_scope() -> None:
    transport = Transport("device.local")
    try:
        with respx.mock() as router:
            counters = _mock_auth_responses(router, exp=2_000_000_000)
            auth = Auth(transport, lambda: b"correct horse battery staple")
            auth.ensure_token("keymgmt:gen")
            auth.ensure_token("keymgmt:list")
            auth.invalidate("keymgmt:gen")
            # Re-fetch keymgmt:gen, keymgmt:list still cached.
            auth.ensure_token("keymgmt:gen")
            auth.ensure_token("keymgmt:list")
            assert counters["post"] == 3
    finally:
        transport.close()


def test_auth_invalidate_all() -> None:
    transport = Transport("device.local")
    try:
        with respx.mock() as router:
            counters = _mock_auth_responses(router, exp=2_000_000_000)
            auth = Auth(transport, lambda: b"correct horse battery staple")
            auth.ensure_token("keymgmt:gen")
            auth.ensure_token("keymgmt:list")
            auth.invalidate()  # drop everything
            auth.ensure_token("keymgmt:gen")
            auth.ensure_token("keymgmt:list")
            assert counters["post"] == 4
    finally:
        transport.close()


def test_auth_raises_when_token_missing_from_response() -> None:
    transport = Transport("device.local")
    try:
        with respx.mock() as router:
            router.get("https://device.local/api/auth/token").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "eid": "d4ad81b06b1d493ab2b6f9b1a3e2c7f0",
                        "spk": _spk(),
                        "jti": "0123456789abcdef",
                        "exp": 2_000_000_000,
                    },
                )
            )
            router.post("https://device.local/api/auth/token").mock(
                return_value=httpx.Response(200, json={})
            )
            auth = Auth(transport, lambda: b"correct horse battery staple")
            with pytest.raises(HemAuthError):
                auth.ensure_token("keymgmt:gen")
    finally:
        transport.close()
