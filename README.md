# encedo-hem

`encedo-hem` is a Python client library for the [Encedo HEM](https://encedo.com) (Hardware Encryption Module) REST API. It wraps the full device API — key management, symmetric/asymmetric crypto, system control — in a typed, Pythonic interface while handling the custom eJWT authentication, scoped token caching, TLS quirks, and backend check-in flow transparently.

---

## Using the library

### Install

```bash
pip install encedo-hem
```

Requires Python 3.10+. Runtime dependencies: `httpx`, `cryptography`.

### Quick start

```bash
HEM_HOST=my.ence.do HEM_PASSPHRASE='your-passphrase' python examples/mvp.py
```

Expected output (six steps against a real PPA or EPA device):

```
[1/6] status: hostname= fls_state=0 initialized=True https=False ts=2026-04-08T20:45:23Z
[2/6] checkin: OK
[3/6] created kid=8edce416d863052ffd9411ca86af1948
[4/6] encrypted: ciphertext=64B iv=16B tag=16B
[5/6] decrypt: round-trip OK
[6/6] deleted kid=8edce416d863052ffd9411ca86af1948
```

### MVP example

```python
import os, secrets
from encedo_hem import CipherAlg, HemClient, KeyType

with HemClient(host=os.environ["HEM_HOST"], passphrase=os.environ["HEM_PASSPHRASE"]) as hem:
    hem.ensure_ready()                                    # status + auto check-in if needed

    status = hem.system.status()
    print(f"device ts={status.ts} initialized={status.initialized}")

    kid = hem.keys.create(label="example", type=KeyType.AES256)

    plaintext = secrets.token_bytes(64)
    enc = hem.crypto.cipher.encrypt(kid, plaintext, alg=CipherAlg.AES256_GCM)
    recovered = hem.crypto.cipher.decrypt(
        kid, enc.ciphertext, alg=CipherAlg.AES256_GCM, iv=enc.iv, tag=enc.tag
    )
    assert recovered == plaintext

    hem.keys.delete(kid)
```

The full runnable script lives at [`examples/mvp.py`](examples/mvp.py). See [`examples/README.md`](examples/README.md) for details on both example scripts, including the `wipe_keys.py` maintenance helper.

---

## Contributing

### Setup

```bash
./scripts/bootstrap.sh
```

Installs `uv` (if not present), syncs all dependencies including dev extras, and configures the git pre-commit hook that runs linting and type checks before each commit.

### Running tests

```bash
# Unit tests (no device required)
uv run pytest -q

# With coverage
uv run pytest --cov=encedo_hem --cov-report=term-missing

# Static checks
uv run ruff check . && uv run ruff format --check .
uv run mypy --strict src

# Against a real device (integration tests)
HEM_HOST=my.ence.do HEM_PASSPHRASE='...' uv run pytest tests/integration -q
```

### Release checklist

Before tagging a new version:

- [ ] All unit tests pass on Python 3.10, 3.11, and 3.12:
  ```bash
  uv run --python 3.10 pytest -q
  uv run --python 3.11 pytest -q
  uv run --python 3.12 pytest -q
  ```
- [ ] `uv run ruff check . && uv run ruff format --check .` is green.
- [ ] `uv run mypy --strict src` is green.
- [ ] CI on `main` is green.
- [ ] `examples/mvp.py` runs end-to-end against a real device (exit code 0, all six steps green).
- [ ] `CHANGELOG.md` `[X.Y.Z]` section is filled in with all changes.
- [ ] Version bumped in `pyproject.toml` (`version = "X.Y.Z"`).
- [ ] Wheel builds cleanly: `uv build` (no warnings under `dist/`).
- [ ] Wheel installs and reports the correct version:
  ```bash
  python -m venv /tmp/hem-check && source /tmp/hem-check/bin/activate
  pip install dist/encedo_hem-X.Y.Z-py3-none-any.whl
  python -c "import encedo_hem; print(encedo_hem.__version__)"  # must print X.Y.Z
  deactivate && rm -rf /tmp/hem-check
  ```
- [ ] `git tag vX.Y.Z` on `main`.

### Further reading

- [ARCHITECTURE.md](ARCHITECTURE.md) — component breakdown, data flow, and design decisions.
- [PHASE-0-1-SPEC.md](PHASE-0-1-SPEC.md) — Phase 1 implementation spec and acceptance criteria.
