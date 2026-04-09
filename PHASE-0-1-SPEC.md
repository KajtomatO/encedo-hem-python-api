# Phase 0 + Phase 1 Implementation Spec

This document is the working spec for the first two phases of `encedo-hem`.
It is the level of detail an implementer needs **without re-reading every reference doc**.
For the "why" behind any decision, see [`ARCHITECTURE.md`](./ARCHITECTURE.md).
For device quirks and known undocumented behaviour, see [`.ai/.api-reference/INTEGRATION_GUIDE.md`](./.ai/.api-reference/INTEGRATION_GUIDE.md) and [`.ai/.api-reference/OPEN-QUESTIONS.md`](./.ai/.api-reference/OPEN-QUESTIONS.md).

---

## 1. Goal

Ship `encedo-hem v0.1.0`. A user can:

```bash
pip install encedo-hem
HEM_HOST=my.ence.do HEM_PASSPHRASE=... python examples/mvp.py
```

…and see the MVP script run end-to-end against a real PPA or EPA device:

1. Print device status.
2. Run an explicit check-in.
3. Create an AES-256 key.
4. Encrypt a 64-byte random message with AES-256-GCM.
5. Decrypt the ciphertext and assert the plaintext matches.
6. Delete the key.

This corresponds 1:1 to the MVP checklist in `.ai/app-description.txt`.

## 2. Acceptance criteria

A reviewer can mark Phase 1 done when **all** of the following hold:

- [ ] `uv sync --extra dev && uv run pytest -q` is green locally on Python 3.10, 3.11, 3.12.
- [ ] `uv run ruff check . && uv run ruff format --check .` is green.
- [ ] `uv run mypy --strict src` is green.
- [ ] CI on the `main` branch is green.
- [ ] `python examples/mvp.py` against a configured device produces the six steps above with no Python tracebacks and a clean exit code 0.
- [ ] Every public symbol exported from `encedo_hem` has a docstring.
- [ ] `CHANGELOG.md` lists everything in `0.1.0` under `Added`.
- [ ] A `v0.1.0` git tag exists.

## 3. Non-goals (deferred to Phase 2/3/4)

These are **explicitly out of scope** for Phase 0/1. Do not implement them.

- HMAC, ExDSA, ECDH, AES wrap/unwrap, ML-KEM, ML-DSA — Phase 2.
- `keymgmt/derive`, `keymgmt/import`, `keymgmt/search` — Phase 2.
- `system/shutdown`, `system/config/attestation`, `system/config/provisioning` — Phase 3.
- `logger/*`, `storage/*`, `system/upgrade/*` — Phase 3.
- `auth/init` (device personalisation), `auth/ext/*` (remote auth) — Phase 4 (blocked on OQ-1/2/3).
- Async API surface.
- Multi-threading or multi-process safety beyond "one client per thread".
- Hardware attestation verification, audit log signature verification.
- Anything not in §6 below.

---

## 4. Final source layout (after Phase 1)

```
encedo-hem-python-api/
├── pyproject.toml
├── README.md
├── LICENSE
├── CHANGELOG.md
├── ARCHITECTURE.md
├── PHASE-0-1-SPEC.md            ← this file
├── .gitignore
├── .github/
│   └── workflows/
│       └── ci.yml
├── src/
│   └── encedo_hem/
│       ├── __init__.py
│       ├── client.py
│       ├── transport.py
│       ├── auth.py
│       ├── models.py
│       ├── errors.py
│       ├── enums.py
│       ├── _base64.py
│       └── api/
│           ├── __init__.py
│           ├── system.py
│           ├── keymgmt.py
│           └── crypto.py
├── examples/
│   └── mvp.py
└── tests/
    ├── __init__.py
    ├── unit/
    │   ├── __init__.py
    │   ├── test_smoke.py
    │   ├── test_base64.py
    │   ├── test_errors.py
    │   ├── test_enums.py
    │   ├── test_models.py
    │   ├── test_transport.py
    │   ├── test_auth_vectors.py
    │   ├── test_keymgmt_parse.py
    │   └── test_client.py
    └── integration/
        ├── __init__.py
        ├── conftest.py
        └── test_mvp_flow.py
```

Files **not** in this list must not be created in Phase 0/1.

---

## 5. Phase 0 — Scaffolding

The goal of Phase 0 is a green CI run on an empty package. No functionality.

### 5.1 Files to create

#### `pyproject.toml`

```toml
[project]
name = "encedo-hem"
version = "0.1.0.dev0"
description = "Python client library for the Encedo HEM REST API"
readme = "README.md"
requires-python = ">=3.10"
license = { file = "LICENSE" }
authors = [{ name = "Tomasz Targiel" }]
keywords = ["encedo", "hem", "hsm", "cryptography", "rest"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Security :: Cryptography",
    "Typing :: Typed",
]
dependencies = [
    "httpx>=0.27,<1",
    "cryptography>=42",
]

[project.optional-dependencies]
dev = [
    "pytest>=8",
    "pytest-cov>=5",
    "respx>=0.21",
    "ruff>=0.5",
    "mypy>=1.10",
]

[project.urls]
Homepage = "https://github.com/encedo/encedo-hem-python-api"
Issues = "https://github.com/encedo/encedo-hem-python-api/issues"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/encedo_hem"]

[tool.ruff]
line-length = 100
target-version = "py310"
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "UP", "SIM", "RUF"]
ignore = []

[tool.mypy]
strict = true
python_version = "3.10"
files = ["src", "tests"]
warn_unused_configs = true

[[tool.mypy.overrides]]
module = ["respx.*"]
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests/unit"]
addopts = "-ra --strict-markers"
```

#### `.github/workflows/ci.yml`

```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python: ["3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python }}
      - run: uv sync --extra dev
      - run: uv run ruff check .
      - run: uv run ruff format --check .
      - run: uv run mypy --strict src
      - run: uv run pytest -q
```

#### `.gitignore` (additions)

Append to the existing `.gitignore`:

```
.venv/
.pytest_cache/
.mypy_cache/
.ruff_cache/
dist/
build/
*.egg-info/
htmlcov/
.coverage
```

#### `src/encedo_hem/__init__.py`

```python
"""Python client library for the Encedo HEM REST API."""

from importlib.metadata import PackageNotFoundError, version as _pkg_version

try:
    __version__ = _pkg_version("encedo-hem")
except PackageNotFoundError:  # pragma: no cover -- editable install before metadata exists
    __version__ = "0.0.0+local"

__all__ = ["__version__"]
```

The remaining re-exports (`HemClient`, `Role`, etc.) are added in Phase 1, not Phase 0.

#### `src/encedo_hem/api/__init__.py`

Empty file (package marker).

#### `tests/__init__.py`, `tests/unit/__init__.py`, `tests/integration/__init__.py`

Empty files (package markers).

#### `tests/unit/test_smoke.py`

```python
import encedo_hem


def test_package_imports() -> None:
    assert isinstance(encedo_hem.__version__, str)
    assert encedo_hem.__version__
```

#### `CHANGELOG.md`

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - YYYY-MM-DD
### Added
- (filled in at end of Phase 1)
```

### 5.2 Phase 0 acceptance

- [ ] `uv sync --extra dev` succeeds.
- [ ] `uv run pytest -q` runs `test_smoke.py` and reports 1 passed.
- [ ] `uv run ruff check .` reports no issues.
- [ ] `uv run mypy --strict src` reports `Success: no issues found`.
- [ ] CI workflow on a PR to `main` is green for all three Python versions.

Phase 0 is **strictly scaffolding**. No `auth.py`, no `transport.py`, no `client.py`. Resist the urge to start implementing.

---

## 6. Phase 1 — MVP

This section walks the modules in dependency order: leaves first, `client.py` last. Implement them in this order so that each module's tests can pass before the next one starts.

### 6.1 `errors.py`

The exception hierarchy. Every device-side failure is mapped to one of these by `transport.py`.

```python
from __future__ import annotations
from typing import Any


class HemError(Exception):
    """Base class for every error raised by encedo_hem."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        endpoint: str | None = None,
        body: dict[str, Any] | str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.endpoint = endpoint
        self.body = body


class HemTransportError(HemError):
    """Network failure: connection refused, TLS handshake, timeout, DNS, etc."""


class HemBadRequestError(HemError):
    """HTTP 400 -- malformed JSON or invalid argument."""


class HemAuthError(HemError):
    """HTTP 401/403 -- missing/invalid token or wrong scope."""


class HemNotFoundError(HemError):
    """HTTP 404 -- endpoint or resource not found."""


class HemNotSupportedError(HemError):
    """Endpoint not available on the current hardware (PPA vs EPA)."""


class HemNotAcceptableError(HemError):
    """HTTP 406 -- device-side rejection (already initialised, ECDH too small, duplicate, ...)."""


class HemDeviceFailureError(HemError):
    """HTTP 409 -- device in a failure state (FLS != 0)."""


class HemPayloadTooLargeError(HemError):
    """HTTP 413 or local pre-flight: POST body would exceed 7300 bytes."""

    def __init__(
        self,
        message: str,
        *,
        size_actual: int,
        size_limit: int = 7300,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.size_actual = size_actual
        self.size_limit = size_limit


class HemTlsRequiredError(HemError):
    """HTTP 418 -- crypto endpoint hit before TLS is operational on the device."""


def from_status(
    status_code: int,
    *,
    endpoint: str,
    body: dict[str, Any] | str | None,
) -> HemError:
    """Map an HTTP status to the appropriate HemError subclass."""
    msg = f"{endpoint} returned HTTP {status_code}"
    cls: type[HemError]
    match status_code:
        case 400:
            cls = HemBadRequestError
        case 401 | 403:
            cls = HemAuthError
        case 404:
            cls = HemNotFoundError
        case 406:
            cls = HemNotAcceptableError
        case 409:
            cls = HemDeviceFailureError
        case 413:
            return HemPayloadTooLargeError(
                msg, size_actual=-1, status_code=413, endpoint=endpoint, body=body
            )
        case 418:
            cls = HemTlsRequiredError
        case _:
            cls = HemError
    return cls(msg, status_code=status_code, endpoint=endpoint, body=body)
```

**Rules:**
- `__repr__` is **not** overridden — Python's default reveals only the message, which is what we want.
- Never put the passphrase into a `HemError` constructor. The unit test in §7.1 enforces this.
- Translation lives here, not in `transport.py` — but `transport.py` calls `from_status(...)`.

### 6.2 `enums.py`

```python
from __future__ import annotations
from enum import Enum


class Role(Enum):
    USER = "U"      # local user, sub claim "U"
    MASTER = "M"    # local admin, sub claim "M"


class HardwareForm(Enum):
    PPA = "PPA"        # USB Personal Privacy Assistant
    EPA = "EPA"        # 19" rack Enterprise Privacy Appliance
    UNKNOWN = "UNKNOWN"


class KeyType(Enum):
    AES128 = "AES128"
    AES192 = "AES192"
    AES256 = "AES256"
    SECP256R1 = "SECP256R1"
    SECP384R1 = "SECP384R1"
    SECP521R1 = "SECP521R1"
    SECP256K1 = "SECP256K1"
    CURVE25519 = "CURVE25519"
    CURVE448 = "CURVE448"
    ED25519 = "ED25519"
    ED448 = "ED448"
    SHA2_256 = "SHA2-256"
    SHA2_384 = "SHA2-384"
    SHA2_512 = "SHA2-512"
    SHA3_256 = "SHA3-256"
    SHA3_384 = "SHA3-384"
    SHA3_512 = "SHA3-512"
    MLKEM512 = "MLKEM512"
    MLKEM768 = "MLKEM768"
    MLKEM1024 = "MLKEM1024"
    MLDSA44 = "MLDSA44"
    MLDSA65 = "MLDSA65"
    MLDSA87 = "MLDSA87"

    @property
    def is_nist_ecc(self) -> bool:
        return self in {
            KeyType.SECP256R1, KeyType.SECP384R1,
            KeyType.SECP521R1, KeyType.SECP256K1,
        }


class KeyMode(Enum):
    """Mode flag for NIST ECC keys (ignored for other key types)."""
    ECDH = "ECDH"
    EXDSA = "ExDSA"
    ECDH_EXDSA = "ECDH,ExDSA"


class CipherAlg(Enum):
    AES128_ECB = "AES128-ECB"
    AES192_ECB = "AES192-ECB"
    AES256_ECB = "AES256-ECB"
    AES128_CBC = "AES128-CBC"
    AES192_CBC = "AES192-CBC"
    AES256_CBC = "AES256-CBC"
    AES128_GCM = "AES128-GCM"
    AES192_GCM = "AES192-GCM"
    AES256_GCM = "AES256-GCM"

    @property
    def has_iv(self) -> bool:
        return "ECB" not in self.value

    @property
    def has_tag(self) -> bool:
        return "GCM" in self.value
```

**Rules:**
- The `.value` of each enum member is **exactly** the string the device wire protocol expects. Do not rename them.
- `KeyType.SHA2_256.value == "SHA2-256"` (note the dash; Python identifier uses underscore).

### 6.3 `_base64.py`

Two distinct base64 conventions are in use. Mixing them is the #1 source of bugs.

```python
from __future__ import annotations
import base64


def b64_std_encode(data: bytes) -> str:
    """Standard base64 with padding (RFC 4648 §4). Used for API payload fields
    like `msg`, `aad`, `ciphertext`, and for `iss` in the eJWT payload."""
    return base64.b64encode(data).decode("ascii")


def b64_std_decode(text: str) -> bytes:
    """Inverse of b64_std_encode. Padding is required."""
    return base64.b64decode(text, validate=False)


def b64url_nopad_encode(data: bytes) -> str:
    """base64url without padding (RFC 4648 §5). Used only for JWT segments
    (header, payload, signature)."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_nopad_decode(text: str) -> bytes:
    """Inverse of b64url_nopad_encode. Re-adds padding before decoding."""
    pad = (-len(text)) % 4
    return base64.urlsafe_b64decode(text + ("=" * pad))
```

### 6.4 `models.py`

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import NewType

from .enums import HardwareForm

KeyId = NewType("KeyId", str)  # 32 lowercase hex characters


@dataclass(frozen=True, slots=True)
class DeviceVersion:
    hwv: str
    blv: str
    fwv: str
    fws: str
    uis: str | None  # PPA only

    @property
    def hardware(self) -> HardwareForm:
        if "EPA" in self.hwv:
            return HardwareForm.EPA
        if "PPA" in self.hwv:
            return HardwareForm.PPA
        return HardwareForm.UNKNOWN

    @property
    def is_diag(self) -> bool:
        return self.fwv.endswith("-DIAG")


@dataclass(frozen=True, slots=True)
class DeviceStatus:
    fls_state: int
    ts: int | None              # None when RTC is not set
    hostname: str
    https: bool
    initialized: bool           # True when 'inited' key is ABSENT in the response
    format: str | None
    uptime: int | None
    temp: int | None
    storage: list[str] | None   # PPA only


@dataclass(frozen=True, slots=True)
class DeviceConfig:
    eid: str
    user: str
    email: str
    hostname: str
    uts: int


@dataclass(frozen=True, slots=True)
class AuthChallenge:
    eid: str          # PBKDF2 salt
    spk: str          # device X25519 pubkey, standard base64 with padding
    jti: str          # nonce
    exp: int          # challenge deadline (unix timestamp)
    lbl: str | None   # username/label, may be missing


@dataclass(frozen=True, slots=True)
class CachedToken:
    jwt: str
    scope: str
    exp: int          # already adjusted: real_exp - 60s


@dataclass(frozen=True, slots=True)
class ParsedKeyType:
    """Parsed form of the comma-separated `type` string returned by list/get."""
    flags: frozenset[str]    # subset of {"PKEY", "ECDH", "ExDSA"}
    algorithm: str           # last comma-separated element, e.g. "SECP256R1"

    @classmethod
    def parse(cls, raw: str) -> ParsedKeyType:
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        if not parts:
            return cls(flags=frozenset(), algorithm="")
        return cls(flags=frozenset(parts[:-1]), algorithm=parts[-1])


@dataclass(frozen=True, slots=True)
class KeyInfo:
    kid: KeyId
    label: str
    type: ParsedKeyType
    created: int
    updated: int
    descr: bytes | None


@dataclass(frozen=True, slots=True)
class KeyDetails:
    pubkey: bytes
    type: ParsedKeyType
    updated: int


@dataclass(frozen=True, slots=True)
class EncryptResult:
    ciphertext: bytes
    iv: bytes | None      # absent for ECB
    tag: bytes | None     # present only for GCM
```

### 6.5 `transport.py`

The thin httpx wrapper. Two clients: one for the device (TLS verify off, no keep-alive) and one for the Encedo backend (TLS verify on).

```python
from __future__ import annotations
import json
import logging
from typing import Any

import httpx

from .errors import HemError, HemPayloadTooLargeError, HemTransportError, from_status

MAX_BODY_BYTES = 7300

_log = logging.getLogger(__name__)


class Transport:
    def __init__(
        self,
        host: str,
        *,
        timeout: float = 30.0,
        scheme: str = "https",
    ) -> None:
        self._base_url = f"{scheme}://{host}"
        self._device = httpx.Client(
            base_url=self._base_url,
            verify=False,
            timeout=timeout,
            limits=httpx.Limits(max_keepalive_connections=0),
            headers={"Connection": "close"},
        )
        self._backend = httpx.Client(
            base_url="https://api.encedo.com",
            verify=True,
            timeout=timeout,
            limits=httpx.Limits(max_keepalive_connections=0),
            headers={"Connection": "close"},
        )

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        token: str | None = None,
    ) -> dict[str, Any]:
        headers: dict[str, str] = {}
        body: bytes | None = None
        if json_body is not None:
            body = json.dumps(json_body, separators=(",", ":")).encode("utf-8")
            if len(body) > MAX_BODY_BYTES:
                raise HemPayloadTooLargeError(
                    f"{path}: request body is {len(body)} bytes, max {MAX_BODY_BYTES}",
                    size_actual=len(body),
                    endpoint=path,
                )
            headers["Content-Type"] = "application/json"
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        try:
            response = self._device.request(method, path, content=body, headers=headers)
        except httpx.HTTPError as exc:
            raise HemTransportError(f"{path}: {exc}", endpoint=path) from exc
        if response.status_code != 200:
            parsed = _safe_parse_body(response)
            raise from_status(response.status_code, endpoint=path, body=parsed)
        return _safe_parse_body(response) or {}

    def backend_post(self, path: str, json_body: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self._backend.post(path, json=json_body)
        except httpx.HTTPError as exc:
            raise HemTransportError(f"backend {path}: {exc}", endpoint=path) from exc
        if response.status_code != 200:
            raise from_status(
                response.status_code,
                endpoint=f"backend:{path}",
                body=_safe_parse_body(response),
            )
        parsed = _safe_parse_body(response)
        if parsed is None:
            raise HemError(f"backend {path}: empty body", endpoint=path)
        return parsed

    def close(self) -> None:
        self._device.close()
        self._backend.close()


def _safe_parse_body(response: httpx.Response) -> dict[str, Any] | None:
    if not response.content:
        return None
    try:
        return response.json()
    except json.JSONDecodeError:
        return None
```

**Rules:**
- The `_device` client must have **both** `max_keepalive_connections=0` and the `Connection: close` header. Belt and braces.
- `verify=False` triggers an `httpx`/`urllib3` warning at runtime. Suppress it via `warnings.filterwarnings("ignore", category=...)` only inside the test fixture, **never** globally in `transport.py`.
- `request()` parses 200 responses as JSON; 200 with an empty body is allowed (returns `{}`).
- The 401-retry logic lives in `client.py` / API methods, not here. `transport.py` just translates the status to an exception and lets the caller decide.

### 6.6 `auth.py`

The most error-prone module in the whole library. Implement against the test vectors in §7.1 first.

#### 6.6.1 The eJWT algorithm — exact pseudocode

```
INPUT:
    challenge: AuthChallenge
    scope:     str
    passphrase: bytes (UTF-8 encoded passphrase, no trailing newline)
    now:       int (unix timestamp)
    requested_exp: int (unix timestamp; capped at challenge.exp below)

CONSTANTS:
    HEADER_BYTES = b'{"ecdh":"x25519","alg":"HS256","typ":"JWT"}'
    HEADER_B64URL = b64url_nopad_encode(HEADER_BYTES)   # cached at module load
    PBKDF2_ITERS = 600_000

STEPS:
  1. Cap the requested expiry: req_exp = min(requested_exp, challenge.exp)

  2. Derive PBKDF2 seed (32 bytes):
       salt = challenge.eid.encode("utf-8")
       seed = PBKDF2HMAC(
           algorithm=hashes.SHA256(),
           length=32,
           salt=salt,
           iterations=PBKDF2_ITERS,
       ).derive(passphrase)
     -- the eid string is used DIRECTLY as the salt bytes (UTF-8). It is NOT
        decoded as hex or base64.

  3. Build user X25519 keypair from seed:
       priv = X25519PrivateKey.from_private_bytes(seed)
       pub  = priv.public_key().public_bytes(
           encoding=serialization.Encoding.Raw,
           format=serialization.PublicFormat.Raw,
       )

  4. Derive ECDH shared secret with the device's static pubkey:
       spk_bytes = b64_std_decode(challenge.spk)        # 32 bytes
       peer = X25519PublicKey.from_public_bytes(spk_bytes)
       shared = priv.exchange(peer)                     # 32 bytes

  5. Build JWT payload:
       payload = {
           "jti":   challenge.jti,                      # passthrough
           "aud":   challenge.spk,                      # ORIGINAL base64 string
           "exp":   req_exp,
           "iat":   now,
           "iss":   b64_std_encode(pub),                # standard b64 WITH padding
           "scope": scope,
       }

  6. Encode segments:
       header_seg  = HEADER_B64URL                              # cached
       payload_seg = b64url_nopad_encode(
           json.dumps(payload, separators=(",", ":")).encode("utf-8")
       )
       signing_input = (header_seg + "." + payload_seg).encode("ascii")

  7. HMAC-SHA256:
       sig = HMAC(key=shared, message=signing_input, hash=SHA256)
       sig_seg = b64url_nopad_encode(sig)

  8. ejwt = header_seg + "." + payload_seg + "." + sig_seg

  9. Zero `seed` and `shared` (both stored as bytearray for this purpose).

 10. Return ejwt
```

**Critical gotchas (each one is a known footgun):**

| # | Footgun | Right answer |
|---|---|---|
| 1 | What format is `eid` for PBKDF2? | UTF-8 bytes of the string verbatim. **Not** hex-decoded. **Not** base64-decoded. |
| 2 | PBKDF2 iterations | Exactly **600 000**. Lower → 401. Higher → still works but ~slower. |
| 3 | What is the `aud` claim? | The **original base64 string** of `spk` from the challenge. **Not** the raw 32 bytes; **not** re-encoded. Pass it through unchanged. |
| 4 | What encoding is `iss`? | Standard base64 **with** padding, of the 32-byte raw user pubkey. |
| 5 | What encoding for header/payload/signature segments? | base64**url** **without** padding (`-`/`_` instead of `+`/`/`, no `=`). |
| 6 | Header serialisation | Hardcoded bytes `{"ecdh":"x25519","alg":"HS256","typ":"JWT"}`. Don't `json.dumps` it — different Python versions may reorder keys. |
| 7 | Payload serialisation | `json.dumps(..., separators=(",", ":"))` — compact, no whitespace. Key order in the dict literal is preserved by CPython 3.7+. |
| 8 | What does HMAC sign? | The bytes of `header_seg + "." + payload_seg`. ASCII. No leading/trailing whitespace. |
| 9 | When to zero secrets | After the function returns the ejwt string. Use `bytearray` so you can overwrite in place. The PBKDF2 output and the ECDH output. **Not** the JWT (it's bearer). |

#### 6.6.2 `Auth` class

```python
from __future__ import annotations
import json
import logging
import time
from dataclasses import dataclass

from cryptography.hazmat.primitives import hashes, hmac, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from ._base64 import b64_std_decode, b64_std_encode, b64url_nopad_encode
from .errors import HemAuthError
from .models import AuthChallenge, CachedToken
from .transport import Transport

_log = logging.getLogger(__name__)

_PBKDF2_ITERS = 600_000
_HEADER_BYTES = b'{"ecdh":"x25519","alg":"HS256","typ":"JWT"}'
_HEADER_SEG = b64url_nopad_encode(_HEADER_BYTES)
_TOKEN_LIFETIME_S = 3600       # request a 1-hour token
_TOKEN_SKEW_S = 60             # treat as expired this many seconds early


class Auth:
    def __init__(self, transport: Transport, passphrase_provider) -> None:
        self._transport = transport
        self._passphrase_provider = passphrase_provider  # () -> bytes
        self._cache: dict[str, CachedToken] = {}
        self._username: str | None = None

    @property
    def username(self) -> str | None:
        return self._username

    def ensure_token(self, scope: str) -> str:
        cached = self._cache.get(scope)
        now = int(time.time())
        if cached is not None and cached.exp > now:
            return cached.jwt
        return self._login(scope, now)

    def invalidate(self, scope: str | None = None) -> None:
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

        capped_exp = min(challenge.exp, now + _TOKEN_LIFETIME_S)
        self._cache[scope] = CachedToken(jwt=token, scope=scope, exp=capped_exp - _TOKEN_SKEW_S)
        return token


def build_ejwt(
    *,
    challenge: AuthChallenge,
    scope: str,
    passphrase: bytes,
    now: int,
    requested_exp: int,
) -> str:
    """Pure function. Deterministic given inputs. Tested against fixed vectors."""
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
```

### 6.7 `api/system.py`

```python
from __future__ import annotations
from typing import TYPE_CHECKING

from ..models import DeviceConfig, DeviceStatus, DeviceVersion

if TYPE_CHECKING:
    from ..client import HemClient


class SystemAPI:
    def __init__(self, client: HemClient) -> None:
        self._client = client

    # --- unauthenticated ---

    def version(self) -> DeviceVersion:
        raw = self._client._transport.request("GET", "/api/system/version")
        return DeviceVersion(
            hwv=raw["hwv"],
            blv=raw["blv"],
            fwv=raw["fwv"],
            fws=raw["fws"],
            uis=raw.get("uis"),
        )

    def status(self) -> DeviceStatus:
        raw = self._client._transport.request("GET", "/api/system/status")
        return DeviceStatus(
            fls_state=int(raw.get("fls_state", 0)),
            ts=raw.get("ts"),
            hostname=raw.get("hostname", ""),
            https=bool(raw.get("https", False)),
            initialized="inited" not in raw,    # inverted logic
            format=raw.get("format"),
            uptime=raw.get("uptime"),
            temp=raw.get("temp"),
            storage=raw.get("storage"),
        )

    def checkin(self) -> None:
        """Run the full three-step check-in bounce. No auth required."""
        challenge = self._client._transport.request("GET", "/api/system/checkin")
        backend_response = self._client._transport.backend_post("/checkin", challenge)
        self._client._transport.request(
            "POST", "/api/system/checkin", json_body=backend_response
        )

    # --- authenticated ---

    def config(self) -> DeviceConfig:
        token = self._client._auth.ensure_token("system:config")
        raw = self._client._transport.request("GET", "/api/system/config", token=token)
        return DeviceConfig(
            eid=raw["eid"],
            user=raw.get("user", ""),
            email=raw.get("email", ""),
            hostname=raw.get("hostname", ""),
            uts=int(raw.get("uts", 0)),
        )

    def reboot(self) -> None:
        token = self._client._auth.ensure_token("system:config")
        self._client._transport.request("GET", "/api/system/reboot", token=token)
```

**Notes:**
- `set_config(...)` is **deferred** — not strictly needed for the MVP. Add in Phase 1 only if time permits; otherwise Phase 2.
- `selftest` is also deferred (not in MVP path).
- The `_client._transport` and `_client._auth` accesses are intentional — the API modules are tightly coupled to `HemClient` and treated as friend classes.

### 6.8 `api/keymgmt.py`

```python
from __future__ import annotations
from collections.abc import Iterator
from typing import TYPE_CHECKING

from .._base64 import b64_std_decode, b64_std_encode
from ..enums import KeyMode, KeyType
from ..models import KeyDetails, KeyId, KeyInfo, ParsedKeyType

if TYPE_CHECKING:
    from ..client import HemClient

_LIST_PAGE_SIZE = 10  # device caps at 15; stay safely below


class KeyMgmtAPI:
    def __init__(self, client: HemClient) -> None:
        self._client = client

    def create(
        self,
        label: str,
        type: KeyType,
        *,
        descr: bytes | None = None,
        mode: KeyMode | None = None,
    ) -> KeyId:
        if len(label) > 31:
            raise ValueError("label must be at most 31 characters")
        body: dict[str, str] = {"label": label, "type": type.value}
        if descr is not None:
            if len(descr) > 128:
                raise ValueError("descr must be at most 128 raw bytes before base64")
            body["descr"] = b64_std_encode(descr)
        # OQ-19: device default for NIST ECC is ECDH-only; library default is permissive.
        if type.is_nist_ecc and mode is None:
            mode = KeyMode.ECDH_EXDSA
        if mode is not None:
            body["mode"] = mode.value
        token = self._client._auth.ensure_token("keymgmt:gen")
        raw = self._client._transport.request(
            "POST", "/api/keymgmt/create", json_body=body, token=token
        )
        return KeyId(raw["kid"])

    def list(self) -> Iterator[KeyInfo]:
        offset = 0
        token = self._client._auth.ensure_token("keymgmt:list")
        while True:
            path = f"/api/keymgmt/list/{offset}/{_LIST_PAGE_SIZE}"
            raw = self._client._transport.request("GET", path, token=token)
            total = int(raw.get("total", 0))
            listed = int(raw.get("listed", 0))
            for entry in raw.get("list", []):
                yield _key_info(entry)
            offset += listed
            # OQ-17: end-of-list signal MUST be `offset >= total`, never `listed < limit`.
            if offset >= total or listed == 0:
                return

    def get(self, kid: KeyId) -> KeyDetails:
        # OQ-16: only `keymgmt:use:<kid>` is honoured on observed firmware.
        token = self._client._auth.ensure_token(f"keymgmt:use:{kid}")
        raw = self._client._transport.request(
            "GET", f"/api/keymgmt/get/{kid}", token=token
        )
        return KeyDetails(
            pubkey=b64_std_decode(raw["pubkey"]),
            type=ParsedKeyType.parse(raw.get("type", "")),
            updated=int(raw.get("updated", 0)),
        )

    def update(self, kid: KeyId, *, label: str, descr: bytes | None = None) -> None:
        # OQ-18: label is mandatory on the wire even for descr-only updates.
        body: dict[str, str] = {"kid": kid, "label": label}
        if descr is not None:
            body["descr"] = b64_std_encode(descr)
        token = self._client._auth.ensure_token("keymgmt:upd")
        self._client._transport.request(
            "POST", "/api/keymgmt/update", json_body=body, token=token
        )

    def delete(self, kid: KeyId) -> None:
        token = self._client._auth.ensure_token("keymgmt:del")
        self._client._transport.request(
            "DELETE", f"/api/keymgmt/delete/{kid}", token=token
        )


def _key_info(entry: dict) -> KeyInfo:
    return KeyInfo(
        kid=KeyId(entry["kid"]),
        label=entry.get("label", ""),
        type=ParsedKeyType.parse(entry.get("type", "")),
        created=int(entry.get("created", 0)),
        updated=int(entry.get("updated", 0)),
        descr=b64_std_decode(entry["descr"]) if entry.get("descr") else None,
    )
```

### 6.9 `api/crypto.py`

Phase 1 implements only the cipher subnamespace. The class shape leaves room for `hmac`, `exdsa`, `ecdh`, `pqc` in Phase 2 without breaking imports.

```python
from __future__ import annotations
from typing import TYPE_CHECKING

from .._base64 import b64_std_decode, b64_std_encode
from ..enums import CipherAlg
from ..models import EncryptResult, KeyId

if TYPE_CHECKING:
    from ..client import HemClient


class CipherAPI:
    def __init__(self, client: HemClient) -> None:
        self._client = client

    def encrypt(
        self,
        kid: KeyId,
        plaintext: bytes,
        *,
        alg: CipherAlg = CipherAlg.AES256_GCM,
        aad: bytes | None = None,
    ) -> EncryptResult:
        body: dict[str, str] = {
            "kid": kid,
            "alg": alg.value,
            "msg": b64_std_encode(plaintext),
        }
        if aad is not None:
            body["aad"] = b64_std_encode(aad)
        token = self._client._auth.ensure_token(f"keymgmt:use:{kid}")
        raw = self._client._transport.request(
            "POST", "/api/crypto/cipher/encrypt", json_body=body, token=token
        )
        return EncryptResult(
            ciphertext=b64_std_decode(raw["ciphertext"]),
            iv=b64_std_decode(raw["iv"]) if "iv" in raw else None,
            tag=b64_std_decode(raw["tag"]) if "tag" in raw else None,
        )

    def decrypt(
        self,
        kid: KeyId,
        ciphertext: bytes,
        *,
        alg: CipherAlg,
        iv: bytes | None = None,
        tag: bytes | None = None,
        aad: bytes | None = None,
    ) -> bytes:
        body: dict[str, str] = {
            "kid": kid,
            "alg": alg.value,
            "msg": b64_std_encode(ciphertext),
        }
        if iv is not None:
            body["iv"] = b64_std_encode(iv)
        if tag is not None:
            body["tag"] = b64_std_encode(tag)
        if aad is not None:
            body["aad"] = b64_std_encode(aad)
        token = self._client._auth.ensure_token(f"keymgmt:use:{kid}")
        raw = self._client._transport.request(
            "POST", "/api/crypto/cipher/decrypt", json_body=body, token=token
        )
        return b64_std_decode(raw["plaintext"])


class CryptoAPI:
    """Top-level crypto namespace. Sub-namespaces are added in later phases."""

    def __init__(self, client: HemClient) -> None:
        self.cipher = CipherAPI(client)
```

### 6.10 `client.py`

```python
from __future__ import annotations
import logging
from collections.abc import Callable
from enum import Enum
from typing import Self

from .api.crypto import CryptoAPI
from .api.keymgmt import KeyMgmtAPI
from .api.system import SystemAPI
from .auth import Auth
from .enums import HardwareForm, Role
from .errors import HemNotSupportedError
from .models import DeviceStatus, DeviceVersion
from .transport import Transport

_log = logging.getLogger(__name__)


class _ReadyState(Enum):
    NOT_READY = "not_ready"
    READY = "ready"


class HemClient:
    def __init__(
        self,
        host: str,
        passphrase: str | Callable[[], str],
        *,
        role: Role = Role.USER,
        auto_checkin: bool = True,
        strict_hardware: bool = True,
        timeout: float = 30.0,
    ) -> None:
        self._host = host
        self._role = role
        self._auto_checkin = auto_checkin
        self._strict_hardware = strict_hardware
        self._ready = _ReadyState.NOT_READY
        self._version: DeviceVersion | None = None
        self._last_status: DeviceStatus | None = None

        self._passphrase_buf: bytearray | None
        if callable(passphrase):
            self._passphrase_buf = None
            self._passphrase_provider = lambda: passphrase().encode("utf-8")
        else:
            self._passphrase_buf = bytearray(passphrase.encode("utf-8"))
            self._passphrase_provider = lambda: bytes(self._passphrase_buf or b"")

        self._transport = Transport(host, timeout=timeout)
        self._auth = Auth(self._transport, self._passphrase_provider)

        self.system = SystemAPI(self)
        self.keys = KeyMgmtAPI(self)
        self.crypto = CryptoAPI(self)

    # --- lifecycle ---

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def close(self) -> None:
        if self._passphrase_buf is not None:
            for i in range(len(self._passphrase_buf)):
                self._passphrase_buf[i] = 0
            self._passphrase_buf = None
        self._transport.close()

    # --- introspection ---

    @property
    def hardware(self) -> HardwareForm:
        return self._version.hardware if self._version else HardwareForm.UNKNOWN

    @property
    def firmware_version(self) -> str | None:
        return self._version.fwv if self._version else None

    @property
    def username(self) -> str | None:
        return self._auth.username

    @property
    def last_status(self) -> DeviceStatus | None:
        return self._last_status

    # --- readiness ---

    def ensure_ready(self) -> None:
        if self._ready is _ReadyState.READY:
            return
        self._version = self.system.version()
        self._last_status = self.system.status()
        if self._last_status.fls_state != 0:
            _log.warning(
                "device fls_state=%d -- some operations may be rejected",
                self._last_status.fls_state,
            )
        if self._auto_checkin and self._last_status.ts is None:
            _log.info("RTC unset; running automatic check-in")
            self.system.checkin()
            self._last_status = self.system.status()
        self._ready = _ReadyState.READY

    # --- hardware-aware error helper ---

    def _require_hardware(self, allowed: HardwareForm, endpoint: str) -> None:
        if not self._strict_hardware:
            return
        if self.hardware is HardwareForm.UNKNOWN:
            return
        if self.hardware is not allowed:
            raise HemNotSupportedError(
                f"{endpoint} is only available on {allowed.value}, "
                f"this device is {self.hardware.value}",
                endpoint=endpoint,
            )
```

**Notes:**
- `ensure_ready()` is called by every authenticated `api.*` method as its first line — but to keep this Phase 1 implementation simple, we instead call it once explicitly from `examples/mvp.py` and from the integration test. (Promoting auto-call to every method is a Phase 2 cleanup.)
- The `_require_hardware()` helper is wired into `system.shutdown()` and `storage.*` in Phase 3, not Phase 1. The shape is reserved here so the API doesn't churn.
- The `_passphrase_buf` zeroing on `close()` is best-effort. We document that.

### 6.11 Re-exports — finalised `src/encedo_hem/__init__.py`

After Phase 1 the package `__init__.py` becomes:

```python
"""Python client library for the Encedo HEM REST API."""

from importlib.metadata import PackageNotFoundError, version as _pkg_version

from .client import HemClient
from .enums import CipherAlg, HardwareForm, KeyMode, KeyType, Role
from .errors import (
    HemAuthError,
    HemBadRequestError,
    HemDeviceFailureError,
    HemError,
    HemNotAcceptableError,
    HemNotFoundError,
    HemNotSupportedError,
    HemPayloadTooLargeError,
    HemTlsRequiredError,
    HemTransportError,
)
from .models import (
    DeviceConfig,
    DeviceStatus,
    DeviceVersion,
    EncryptResult,
    KeyDetails,
    KeyId,
    KeyInfo,
    ParsedKeyType,
)

try:
    __version__ = _pkg_version("encedo-hem")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0+local"

__all__ = [
    "__version__",
    "HemClient",
    # enums
    "CipherAlg", "HardwareForm", "KeyMode", "KeyType", "Role",
    # models
    "DeviceConfig", "DeviceStatus", "DeviceVersion",
    "EncryptResult", "KeyDetails", "KeyId", "KeyInfo", "ParsedKeyType",
    # errors
    "HemError", "HemAuthError", "HemBadRequestError", "HemDeviceFailureError",
    "HemNotAcceptableError", "HemNotFoundError", "HemNotSupportedError",
    "HemPayloadTooLargeError", "HemTlsRequiredError", "HemTransportError",
]
```

### 6.12 `examples/mvp.py`

The exact script that fulfils the brief. Implementer: copy this verbatim.

```python
"""MVP test program for encedo-hem.

Runs the six steps from .ai/app-description.txt against a configured device.

Usage:
    HEM_HOST=my.ence.do HEM_PASSPHRASE='...' python examples/mvp.py
"""

from __future__ import annotations
import logging
import os
import secrets
import sys

from encedo_hem import CipherAlg, HemClient, HemError, KeyType


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    host = os.environ.get("HEM_HOST")
    passphrase = os.environ.get("HEM_PASSPHRASE")
    if not host or not passphrase:
        print("set HEM_HOST and HEM_PASSPHRASE", file=sys.stderr)
        return 2

    with HemClient(host=host, passphrase=passphrase) as hem:
        hem.ensure_ready()

        # 1. Print device status.
        status = hem.system.status()
        print(
            f"[1/6] status: hostname={status.hostname} "
            f"fls_state={status.fls_state} initialized={status.initialized} "
            f"https={status.https} ts={status.ts}"
        )

        # 2. Do a check-in (explicit, even if ensure_ready already ran one).
        hem.system.checkin()
        print("[2/6] checkin: OK")

        # 3. Create an example AES-256 key.
        kid = hem.keys.create(label="mvp-example", type=KeyType.AES256)
        print(f"[3/6] created kid={kid}")

        try:
            # 4. Encrypt a random message.
            plaintext = secrets.token_bytes(64)
            enc = hem.crypto.cipher.encrypt(kid, plaintext, alg=CipherAlg.AES256_GCM)
            assert enc.iv is not None and enc.tag is not None
            print(
                f"[4/6] encrypted: ciphertext={len(enc.ciphertext)}B "
                f"iv={len(enc.iv)}B tag={len(enc.tag)}B"
            )

            # 5. Decrypt and verify round-trip.
            recovered = hem.crypto.cipher.decrypt(
                kid, enc.ciphertext,
                alg=CipherAlg.AES256_GCM, iv=enc.iv, tag=enc.tag,
            )
            if recovered != plaintext:
                print("[5/6] decrypt: MISMATCH", file=sys.stderr)
                return 1
            print("[5/6] decrypt: round-trip OK")
        finally:
            # 6. Always remove the key, even on failure.
            try:
                hem.keys.delete(kid)
                print(f"[6/6] deleted kid={kid}")
            except HemError as exc:
                print(f"[6/6] delete failed: {exc}", file=sys.stderr)
                return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

The script's exit codes:
- `0` — full success.
- `1` — round-trip mismatch or delete failure (the device responded but the result was wrong).
- `2` — missing environment variables.
- Any other non-zero — uncaught exception (treat as a bug; do not catch broadly in `main()`).

---

## 7. Test plan

### 7.1 Unit tests (run in CI)

Each test file owns one module. Tests must be **fully offline** — no network calls, no `verify=False` warnings. Use `respx` to mock httpx for `transport` and `auth` tests.

#### `tests/unit/test_smoke.py` (already in Phase 0)

Trivial import + version check.

#### `tests/unit/test_base64.py`

- `b64_std_encode(b"foo") == "Zm9v"` (and round-trip).
- `b64url_nopad_encode(b"\xff\xff\xff") == "____"` (no padding, urlsafe alphabet).
- `b64url_nopad_decode("____") == b"\xff\xff\xff"` (re-padding works).
- Round-trip for random bytes of length 0, 1, 31, 32, 33, 64.
- `b64_std_encode` always produces padding when needed (e.g. `b"a"` → `"YQ=="`).

#### `tests/unit/test_errors.py`

- `from_status(400, ...)` returns `HemBadRequestError`.
- `from_status(401, ...)` and `from_status(403, ...)` both return `HemAuthError`.
- `from_status(409, ...)` returns `HemDeviceFailureError`.
- `from_status(413, ...)` returns `HemPayloadTooLargeError` with `size_actual=-1`.
- `from_status(418, ...)` returns `HemTlsRequiredError`.
- `from_status(599, ...)` returns plain `HemError`.
- `str(HemAuthError("test", endpoint="/api/x"))` does **not** contain the string `"passphrase"` (defensive — confirms we don't accept that kwarg).

#### `tests/unit/test_enums.py`

- `KeyType.SHA2_256.value == "SHA2-256"`.
- `KeyType.SECP256R1.is_nist_ecc is True`.
- `KeyType.AES256.is_nist_ecc is False`.
- `CipherAlg.AES256_GCM.has_iv is True` and `.has_tag is True`.
- `CipherAlg.AES256_ECB.has_iv is False`.
- `CipherAlg.AES256_CBC.has_iv is True` and `.has_tag is False`.

#### `tests/unit/test_models.py`

- `ParsedKeyType.parse("PKEY,ECDH,ExDSA,SECP256R1")` → `flags={"PKEY","ECDH","ExDSA"}`, `algorithm="SECP256R1"`.
- `ParsedKeyType.parse("AES256")` → empty flags, `algorithm="AES256"`.
- `ParsedKeyType.parse("")` → empty flags, empty algorithm.
- `DeviceVersion(hwv="EPA-2.0", blv="...", fwv="1.2.2-DIAG", fws="x", uis=None).hardware == HardwareForm.EPA`.
- `DeviceVersion(hwv="PPA-1.0", ..., fwv="1.2.2", ...).is_diag is False`.
- `DeviceVersion(hwv="?", ..., fwv="...").hardware == HardwareForm.UNKNOWN`.

#### `tests/unit/test_transport.py`

Use `respx` to mount the device base URL.

- `request("GET", "/api/system/status")` parses JSON body correctly.
- A POST whose body would exceed 7300 bytes raises `HemPayloadTooLargeError` **before** any network call (assert `respx_mock.calls.call_count == 0`).
- HTTP 401 from the device → `HemAuthError`.
- HTTP 409 → `HemDeviceFailureError`.
- HTTP 413 → `HemPayloadTooLargeError`.
- httpx `ConnectError` → `HemTransportError` with the original as `__cause__`.
- The device httpx client has `verify=False` and no keepalive (`limits.max_keepalive_connections == 0`).
- The backend httpx client has `verify=True`. **Critical regression test**: failing this means we'd be MITM-able on check-in.
- Every device request includes the header `Connection: close`.

#### `tests/unit/test_auth_vectors.py`

The most important test file in the package. Locks in the eJWT algorithm.

- `build_ejwt(...)` produces a deterministic string given fixed `passphrase`, `eid`, `spk`, `jti`, `now`, `requested_exp`.
- The output splits into three `.` segments.
- The first segment decodes (base64url, no pad) to exactly `b'{"ecdh":"x25519","alg":"HS256","typ":"JWT"}'`.
- The second segment decodes to JSON containing keys `{jti, aud, exp, iat, iss, scope}` and **only** those keys.
- `payload["aud"] == challenge.spk` (passthrough — string identity, not re-encoded).
- `payload["scope"] == requested_scope`.
- The third segment is 43 ASCII chars (256-bit HMAC, base64url no-pad).
- Re-running `build_ejwt` with the same inputs yields the **identical** string.
- Re-running with `requested_exp > challenge.exp` produces an ejwt whose payload `exp == challenge.exp`.
- The function returns even if `passphrase` is `b""` (the device will reject it with 401, but the build itself must not crash).
- Auth.ensure_token caches by scope: two calls with the same scope make one network round-trip; two calls with different scopes make two.
- Auth.ensure_token treats a token whose `exp - 60s <= now` as expired and refetches.

If a **known-answer vector** is later produced from the C `libhem` reference, add a test that compares byte-for-byte against it. Until then, the round-trip and structural assertions above are the contract.

#### `tests/unit/test_keymgmt_parse.py`

- `KeyMgmtAPI.list()` paginates correctly: 30 keys returned across 3 pages of 10, with `total=30`.
- Single-page case: 5 keys, `total=5`, `listed=5`, iterator yields exactly 5.
- Edge case: `total=15`, `listed=15` → iterator yields 15 then stops (does not loop forever).
- `keys.get(kid)` requests `keymgmt:use:<kid>` scope (assert via respx).
- `keys.update(kid, label="x")` sends `{"kid": ..., "label": "x"}` (label always present, OQ-18).
- `keys.create(label="k", type=KeyType.SECP256R1)` sends `mode="ECDH,ExDSA"` (OQ-19).
- `keys.create(label="k", type=KeyType.AES256)` does **not** send a `mode` field.
- `keys.create(label="x" * 32, ...)` raises `ValueError`.

#### `tests/unit/test_client.py`

- `HemClient` is a context manager: `with HemClient(...) as h: h.system` works.
- `HemClient.close()` zeros the passphrase buffer (inspect `_passphrase_buf` after close — should be `None`).
- `ensure_ready()` calls `version()` then `status()`; if `status.ts is None` and `auto_checkin=True`, it also runs check-in.
- `ensure_ready()` is idempotent: second call makes no extra network requests (mock with respx).
- `ensure_ready()` with `auto_checkin=False` does **not** call checkin even when `ts is None`.
- `last_status` is populated after `ensure_ready()`.
- A passphrase provided as `Callable[[], str]` is resolved on every `_login` and never stored.

### 7.2 Integration tests (skipped in CI, run manually with a real device)

#### `tests/integration/conftest.py`

```python
import os
import pytest

from encedo_hem import HemClient


def pytest_collection_modifyitems(config, items):
    if not (os.environ.get("HEM_HOST") and os.environ.get("HEM_PASSPHRASE")):
        skip = pytest.mark.skip(reason="HEM_HOST and HEM_PASSPHRASE not set")
        for item in items:
            item.add_marker(skip)


@pytest.fixture
def hem():
    with HemClient(
        host=os.environ["HEM_HOST"],
        passphrase=os.environ["HEM_PASSPHRASE"],
    ) as client:
        client.ensure_ready()
        yield client
```

#### `tests/integration/test_mvp_flow.py`

- `test_status(hem)` — `system.status()` returns a `DeviceStatus` with non-None `hostname`.
- `test_version(hem)` — `system.version()` returns a `DeviceVersion`; `hem.hardware` is `PPA` or `EPA` (not `UNKNOWN`).
- `test_checkin_idempotent(hem)` — running `system.checkin()` twice in a row both succeed.
- `test_create_encrypt_decrypt_delete(hem)` — full MVP flow on a fresh AES-256 key. Asserts plaintext round-trip equality. Always deletes the key in a `try/finally`.
- `test_repeated_calls_no_keepalive_failure(hem)` — call `system.status()` 20 times in a tight loop. This is the regression test for the `Connection: close` quirk.
- `test_pagination(hem)` — create 12 throwaway keys, call `keys.list()`, assert exactly 12 (or however many already existed plus 12) are returned, then delete them all. (Skipped if device already has > 50 keys to avoid surprises.)
- `test_keymgmt_get_uses_use_scope(hem)` — create a key, call `keys.get(kid)`, assert it succeeds. Confirms OQ-16 workaround is intact.

These tests live in CI as **collected but skipped** when env vars are absent. To run them locally:

```bash
HEM_HOST=my.ence.do HEM_PASSPHRASE='...' uv run pytest tests/integration -v
```

### 7.3 Coverage target

For Phase 1, **>= 85% line coverage on `src/encedo_hem/`** measured by `pytest-cov`. The under-tested 15% is acceptable for `client.py` glue and trivial `models.py` `__init__`s; the **non-negotiable** modules are `auth.py`, `transport.py`, `_base64.py`, and `errors.py` — these must be **100%** covered.

Add to CI:

```bash
uv run pytest --cov=encedo_hem --cov-report=term-missing --cov-fail-under=85
```

---

## 8. Device quirks reference (cheat sheet)

Every item below has cost someone hours in the C reference implementation. The implementation must encode each one. Cross-references are to `INTEGRATION_GUIDE.md` and `OPEN-QUESTIONS.md`.

| # | Quirk | Where it bites | Spec section |
|---|---|---|---|
| Q1 | Device closes TCP after every response. Keep-alive fails. | `transport.py` | §6.5 — `max_keepalive_connections=0` + `Connection: close` |
| Q2 | Device cert is self-signed; verify must be off. | `transport.py` | §6.5 |
| Q3 | The Encedo backend cert is **public** — `verify=True` for that target. | `transport.py` | §6.5 |
| Q4 | POST body cap is 7300 bytes (5×MTU). | `transport.py` | §6.5 — pre-flight `HemPayloadTooLargeError` |
| Q5 | `inited` field is **inverted**: present means **not** initialized. | `api/system.py::status()` | §6.7 |
| Q6 | `ts` absent (not zero) when RTC unset. | `models.DeviceStatus.ts: int \| None` | §6.4 |
| Q7 | Two base64 conventions in flight at the same time. | `_base64.py`, `auth.py` | §6.3, §6.6 |
| Q8 | PBKDF2 iterations are exactly 600 000. | `auth.py` | §6.6 |
| Q9 | `eid` is used as the **raw UTF-8 salt** — not hex, not base64. | `auth.py` | §6.6 |
| Q10 | `aud` claim is the **original spk string**, not the decoded bytes. | `auth.py` | §6.6 |
| Q11 | JWT header is hardcoded bytes. Don't `json.dumps` it. | `auth.py` | §6.6 |
| Q12 | OQ-16: `keys.get` only honours `keymgmt:use:<kid>`. | `api/keymgmt.py::get` | §6.8 |
| Q13 | OQ-17: list endpoint caps page size at 15; end-of-list signal must be `offset >= total`. | `api/keymgmt.py::list` | §6.8 |
| Q14 | OQ-18: `keymgmt/update` requires `label` even for descr-only updates. | `api/keymgmt.py::update` | §6.8 |
| Q15 | OQ-19: NIST ECC default mode is ECDH-only. Library defaults to `"ECDH,ExDSA"`. | `api/keymgmt.py::create` | §6.8 |
| Q16 | HTTP 418 from a crypto endpoint means TLS not yet provisioned. | `errors.HemTlsRequiredError` | §6.1 |
| Q17 | HTTP 409 from `keys.delete` means FLS != 0. Surface as `HemDeviceFailureError`. | `api/keymgmt.py::delete` | §6.8 |
| Q18 | Token cache must treat tokens as expired 60 s before nominal `exp`. | `auth.py` | §6.6 |
| Q19 | Auth response time is rate-limited (500 ms minimum, 1500 ms after 3 fails). Do not retry 401s in a loop. | `client.py` / API methods | §6.10 |

---

## 9. Dev workflow during Phase 1

Recommended day-to-day loop:

```bash
# Setup once
uv sync --extra dev

# After every change
uv run ruff format .
uv run ruff check . --fix
uv run mypy --strict src
uv run pytest -q

# Before pushing
uv run pytest --cov=encedo_hem --cov-report=term-missing
```

Commit cadence: small, focused commits. Each commit should leave the test suite green. Suggested order matches §6: `errors` → `enums` → `_base64` → `models` → `transport` → `auth` → `api/system` → `api/keymgmt` → `api/crypto` → `client` → `examples/mvp.py`. Every new module ships with its tests in the same commit.

---

## 10. Definition of Done

Phase 1 is **done** when, in addition to §2's acceptance criteria:

- [ ] `git tag v0.1.0` exists on `main`.
- [ ] `uv build` produces a wheel under `dist/` with no warnings.
- [ ] `uv run python -c "import encedo_hem; print(encedo_hem.__version__)"` from a fresh venv prints `0.1.0` (after installing the built wheel).
- [ ] `examples/mvp.py` has been run successfully against at least one PPA **or** EPA device, and the output of that run is captured in the PR description that closes Phase 1.
- [ ] `CHANGELOG.md`'s `[0.1.0]` entry is filled in.
- [ ] `README.md` includes:
  - A one-paragraph description.
  - Install instructions (`pip install encedo-hem`).
  - The MVP example, copy-pasted from `examples/mvp.py`.
  - A link to `ARCHITECTURE.md` and to this spec.
- [ ] No `# TODO` markers remain in `src/encedo_hem/`. Anything still TODO has been moved to a Phase 2/3 issue or is documented in `OPEN-QUESTIONS.md`.

When all of the above are checked, Phase 1 is shippable. Open a PR titled `release: v0.1.0` and tag after merge.
