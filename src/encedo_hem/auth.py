"""eJWT authentication for HEM.

The HEM device speaks a custom JWT scheme: a fixed JOSE header, a small
payload that includes an X25519 user pubkey under ``iss``, and an HMAC-SHA256
signature whose key is an ECDH shared secret derived from PBKDF2 over the
user passphrase.

The exact algorithm is documented in ``PHASE-0-1-SPEC.md`` §6.6 and locked in
by ``tests/unit/test_auth_vectors.py``. Do **not** edit this module without
re-running those tests.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable

from cryptography.hazmat.primitives import hashes, hmac, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from ._base64 import b64_std_decode, b64_std_encode, b64url_nopad_encode
from .errors import HemAuthError
from .models import AuthChallenge, CachedToken
from .transport import Transport

_log = logging.getLogger(__name__)

_PBKDF2_ITERS = 600_000
_HEADER_BYTES = b'{"ecdh":"x25519","alg":"HS256","typ":"JWT"}'
_HEADER_SEG = b64url_nopad_encode(_HEADER_BYTES)
_TOKEN_LIFETIME_S = 3600  # request a 1-hour token
_TOKEN_SKEW_S = 60  # treat as expired this many seconds early

# NOTE: ``AuthChallenge.exp`` is the *response deadline* for that specific
# challenge (a few seconds), NOT the bearer-token lifetime. Per upstream
# docs the issued bearer token is valid for ~8h. Conflating the two
# (MVP-OQ-2) caused every authenticated call to re-login. The ejwt build
# still caps its own ``exp`` claim at ``challenge.exp`` (that's the
# challenge contract), but the cache uses ``_TOKEN_LIFETIME_S`` only.


class Auth:
    """Scope-keyed token cache + login chokepoint.

    Every authenticated API call funnels through :meth:`ensure_token`, which
    either returns a cached non-expired token for the requested scope or
    runs a fresh login (challenge → eJWT → bearer).
    """

    def __init__(
        self,
        transport: Transport,
        passphrase_provider: Callable[[], bytes],
    ) -> None:
        self._transport = transport
        self._passphrase_provider = passphrase_provider
        self._cache: dict[str, CachedToken] = {}
        self._username: str | None = None

    @property
    def username(self) -> str | None:
        """Username (``lbl``) advertised by the most recent challenge, if any."""
        return self._username

    def ensure_token(self, scope: str) -> str:
        """Return a bearer token for ``scope``, refreshing if necessary."""
        cached = self._cache.get(scope)
        now = int(time.time())
        if cached is not None and cached.exp > now:
            return cached.jwt
        return self._login(scope, now)

    def invalidate(self, scope: str | None = None) -> None:
        """Drop one cached scope, or all of them when ``scope`` is ``None``."""
        if scope is None:
            self._cache.clear()
        else:
            self._cache.pop(scope, None)

    def _login(self, scope: str, now: int) -> str:
        raw = self._transport.request("GET", "/api/auth/token")
        challenge = AuthChallenge(
            eid=raw["eid"],
            spk=raw["spk"],
            jti=raw["jti"],
            exp=int(raw["exp"]),
            lbl=raw.get("lbl"),
        )
        if challenge.lbl is not None:
            self._username = challenge.lbl

        passphrase = self._passphrase_provider()
        try:
            ejwt = build_ejwt(
                challenge=challenge,
                scope=scope,
                passphrase=passphrase,
                now=now,
                requested_exp=now + _TOKEN_LIFETIME_S,
            )
        finally:
            _zero(passphrase)

        result = self._transport.request("POST", "/api/auth/token", json_body={"auth": ejwt})
        token = result.get("token")
        if not isinstance(token, str):
            raise HemAuthError("auth/token returned no token", endpoint="/api/auth/token")

        cache_exp = now + _TOKEN_LIFETIME_S - _TOKEN_SKEW_S
        self._cache[scope] = CachedToken(jwt=token, scope=scope, exp=cache_exp)
        return token


def build_ejwt(
    *,
    challenge: AuthChallenge,
    scope: str,
    passphrase: bytes,
    now: int,
    requested_exp: int,
) -> str:
    """Pure function. Deterministic given inputs. Tested against fixed vectors.

    See spec §6.6.1 for the exact algorithm and the gotcha table. Highlights:

    - ``challenge.eid`` is used as the **raw UTF-8 salt** for PBKDF2.
    - ``challenge.spk`` is passed through unchanged as the ``aud`` claim.
    - ``iss`` is the user X25519 pubkey in **standard** base64 (with padding).
    - JWT segments use **base64url** without padding.
    - The header is a hardcoded byte string -- never re-serialised.
    """
    req_exp = min(requested_exp, challenge.exp)

    seed = bytearray(_pbkdf2(passphrase, challenge.eid.encode("utf-8")))
    try:
        priv = X25519PrivateKey.from_private_bytes(bytes(seed))
        pub_bytes = priv.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        peer = X25519PublicKey.from_public_bytes(b64_std_decode(challenge.spk))
        shared = bytearray(priv.exchange(peer))
        try:
            payload = {
                "jti": challenge.jti,
                "aud": challenge.spk,
                "exp": req_exp,
                "iat": now,
                "iss": b64_std_encode(pub_bytes),
                "scope": scope,
            }
            payload_seg = b64url_nopad_encode(
                json.dumps(payload, separators=(",", ":")).encode("utf-8")
            )
            signing_input = (_HEADER_SEG + "." + payload_seg).encode("ascii")
            mac = hmac.HMAC(bytes(shared), hashes.SHA256())
            mac.update(signing_input)
            sig = mac.finalize()
            return _HEADER_SEG + "." + payload_seg + "." + b64url_nopad_encode(sig)
        finally:
            _zero(shared)
    finally:
        _zero(seed)


def _pbkdf2(passphrase: bytes, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=_PBKDF2_ITERS,
    )
    return kdf.derive(passphrase)


def _zero(buf: bytes | bytearray) -> None:
    if isinstance(buf, bytearray):
        for i in range(len(buf)):
            buf[i] = 0
