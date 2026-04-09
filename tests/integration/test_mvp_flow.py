"""Integration tests against a real HEM device.

These tests are skipped automatically by ``conftest.py`` when ``HEM_HOST`` and
``HEM_PASSPHRASE`` are not set in the environment. Run them locally with::

    HEM_HOST=my.ence.do HEM_PASSPHRASE='...' uv run pytest tests/integration -v
"""

from __future__ import annotations

import contextlib
import secrets

import pytest

from encedo_hem import CipherAlg, HardwareForm, HemClient, HemError, KeyId, KeyType


def test_status(hem: HemClient) -> None:
    status = hem.system.status()
    # Per upstream spec, ``hostname`` is only present when the request Host
    # header differs from the device hostname -- so ``None`` is a legal
    # response, not a failure (MVP-OQ-3).
    assert status.hostname is None or isinstance(status.hostname, str)


def test_version(hem: HemClient) -> None:
    version = hem.system.version()
    assert version.fwv
    assert hem.hardware in (HardwareForm.PPA, HardwareForm.EPA)


def test_checkin_idempotent(hem: HemClient) -> None:
    hem.system.checkin()
    hem.system.checkin()


def test_create_encrypt_decrypt_delete(hem: HemClient) -> None:
    kid = hem.keys.create(label="it-mvp", type=KeyType.AES256)
    try:
        plaintext = secrets.token_bytes(64)
        enc = hem.crypto.cipher.encrypt(kid, plaintext, alg=CipherAlg.AES256_GCM)
        assert enc.iv is not None and enc.tag is not None
        recovered = hem.crypto.cipher.decrypt(
            kid,
            enc.ciphertext,
            alg=CipherAlg.AES256_GCM,
            iv=enc.iv,
            tag=enc.tag,
        )
        assert recovered == plaintext
    finally:
        hem.keys.delete(kid)


def test_repeated_calls_no_keepalive_failure(hem: HemClient) -> None:
    """Regression for the Connection: close quirk -- 20 fast status calls."""
    for _ in range(20):
        hem.system.status()


def test_pagination(hem: HemClient) -> None:
    existing = list(hem.keys.list())
    if len(existing) > 50:
        pytest.skip("device has > 50 keys; skipping to avoid surprises")
    created: list[KeyId] = []
    try:
        for i in range(12):
            created.append(hem.keys.create(label=f"it-page-{i}", type=KeyType.AES256))
        listed = list(hem.keys.list())
        assert len(listed) >= len(existing) + 12
    finally:
        for kid in created:
            with contextlib.suppress(HemError):
                hem.keys.delete(kid)


def test_keymgmt_get_uses_use_scope(hem: HemClient) -> None:
    """Confirms the OQ-16 workaround (keymgmt:use:<kid> instead of keymgmt:get)."""
    kid = hem.keys.create(label="it-get", type=KeyType.AES256)
    try:
        details = hem.keys.get(kid)
        assert details is not None
    finally:
        hem.keys.delete(kid)
