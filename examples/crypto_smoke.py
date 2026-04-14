"""Phase 2 integration smoke test.

Exercises one key per algorithm family against a real device. Each test
creates a key, exercises the relevant crypto operations, verifies the
round-trip, then deletes the key.

Usage:
    HEM_HOST=my.ence.do HEM_PASSPHRASE='...' python examples/crypto_smoke.py

PQC tests (MLKEM768, MLDSA65) are skipped gracefully on older firmware that
does not support those key types.
"""

from __future__ import annotations

import logging
import os
import secrets
import sys

from encedo_hem import (
    CipherAlg,
    HashAlg,
    HemBadRequestError,
    HemClient,
    HemError,
    KeyType,
    SignAlg,
    WrapAlg,
)
from encedo_hem.models import KeyId

log = logging.getLogger(__name__)

PASS = "OK"
SKIP = "SKIP"
FAIL = "FAIL"


def _section(name: str) -> None:
    print(f"\n=== {name} ===")


def _ok(msg: str) -> None:
    print(f"  [{PASS}] {msg}")


def _skip(msg: str) -> None:
    print(f"  [{SKIP}] {msg}")


def _fail(msg: str) -> None:
    print(f"  [{FAIL}] {msg}", file=sys.stderr)


def smoke_aes256(hem: HemClient) -> bool:
    _section("AES256 — cipher encrypt/decrypt + wrap/unwrap")
    kid: KeyId | None = None
    try:
        kid = hem.keys.create("smoke-aes256", KeyType.AES256)
        _ok(f"created kid={kid}")

        # encrypt / decrypt round-trip
        plaintext = secrets.token_bytes(64)
        enc = hem.crypto.cipher.encrypt(kid, plaintext, alg=CipherAlg.AES256_GCM)
        recovered = hem.crypto.cipher.decrypt(
            kid, enc.ciphertext, alg=CipherAlg.AES256_GCM, iv=enc.iv, tag=enc.tag
        )
        assert recovered == plaintext, "decrypt mismatch"
        _ok("encrypt/decrypt round-trip")

        # wrap / unwrap round-trip
        key_material = secrets.token_bytes(16)  # 16 bytes — RFC 3394 minimum
        wrap_result = hem.crypto.cipher.wrap(kid, WrapAlg.AES256, msg=key_material)
        unwrapped = hem.crypto.cipher.unwrap(kid, wrap_result.wrapped, alg=WrapAlg.AES256)
        assert unwrapped == key_material, "unwrap mismatch"
        _ok("wrap/unwrap round-trip")

        return True
    except Exception as exc:
        _fail(f"AES256: {exc}")
        return False
    finally:
        _delete(hem, kid)


def smoke_secp256r1(hem: HemClient) -> bool:
    _section("SECP256R1 — exdsa sign/verify + ecdh exchange")
    kid: KeyId | None = None
    kid2: KeyId | None = None
    try:
        kid = hem.keys.create("smoke-secp256r1", KeyType.SECP256R1)
        _ok(f"created kid={kid}")

        # sign / verify round-trip
        msg = b"hello secp256r1"
        sig_result = hem.crypto.exdsa.sign(kid, msg, SignAlg.SHA256_ECDSA)
        assert hem.crypto.exdsa.verify(kid, msg, sig_result.signature, SignAlg.SHA256_ECDSA)
        _ok("sign/verify round-trip")

        # negative: wrong message → False
        assert not hem.crypto.exdsa.verify(
            kid, b"wrong message", sig_result.signature, SignAlg.SHA256_ECDSA
        )
        _ok("verify with wrong message returns False")

        # ecdh: create a second key as the peer, exchange with its pubkey
        kid2 = hem.keys.create("smoke-secp256r1-peer", KeyType.SECP256R1)
        details2 = hem.keys.get(kid2)
        assert details2.pubkey is not None
        ecdh_result = hem.crypto.ecdh.exchange(kid, pubkey=details2.pubkey, alg=HashAlg.SHA2_256)
        assert len(ecdh_result.shared_secret) == 32  # SHA2-256 output
        _ok(f"ecdh exchange shared_secret={len(ecdh_result.shared_secret)}B")

        return True
    except Exception as exc:
        _fail(f"SECP256R1: {exc}")
        return False
    finally:
        _delete(hem, kid)
        _delete(hem, kid2)


def smoke_ed25519(hem: HemClient) -> bool:
    _section("ED25519 — exdsa sign/verify")
    kid: KeyId | None = None
    try:
        kid = hem.keys.create("smoke-ed25519", KeyType.ED25519)
        _ok(f"created kid={kid}")

        msg = b"hello ed25519"
        sig_result = hem.crypto.exdsa.sign(kid, msg, SignAlg.ED25519)
        assert hem.crypto.exdsa.verify(kid, msg, sig_result.signature, SignAlg.ED25519)
        _ok("sign/verify round-trip")

        # negative: wrong message → False
        assert not hem.crypto.exdsa.verify(
            kid, b"wrong message", sig_result.signature, SignAlg.ED25519
        )
        _ok("verify with wrong message returns False")

        return True
    except Exception as exc:
        _fail(f"ED25519: {exc}")
        return False
    finally:
        _delete(hem, kid)


def smoke_sha2_256(hem: HemClient) -> bool:
    _section("SHA2-256 — hmac hash/verify")
    kid: KeyId | None = None
    try:
        kid = hem.keys.create("smoke-sha2-256", KeyType.SHA2_256)
        _ok(f"created kid={kid}")

        msg = b"hello hmac"
        hmac_result = hem.crypto.hmac.hash(kid, msg, alg=HashAlg.SHA2_256)
        assert len(hmac_result.mac) > 0
        _ok(f"hash mac={len(hmac_result.mac)}B")

        assert hem.crypto.hmac.verify(kid, msg, hmac_result.mac, alg=HashAlg.SHA2_256)
        _ok("verify round-trip")

        # negative: wrong message → False
        assert not hem.crypto.hmac.verify(
            kid, b"wrong message", hmac_result.mac, alg=HashAlg.SHA2_256
        )
        _ok("verify with wrong message returns False")

        return True
    except Exception as exc:
        _fail(f"SHA2-256: {exc}")
        return False
    finally:
        _delete(hem, kid)


def smoke_mlkem768(hem: HemClient) -> bool:
    _section("MLKEM768 — mlkem encaps/decaps")
    kid: KeyId | None = None
    try:
        try:
            kid = hem.keys.create("smoke-mlkem768", KeyType.MLKEM768)
        except HemBadRequestError:
            _skip("MLKEM768 not supported on this firmware")
            return True

        _ok(f"created kid={kid}")

        encaps = hem.crypto.pqc.mlkem.encaps(kid)
        _ok(
            f"encaps ciphertext={len(encaps.ciphertext)}B "
            f"ss={len(encaps.shared_secret)}B alg={encaps.alg}"
        )

        decaps = hem.crypto.pqc.mlkem.decaps(kid, encaps.ciphertext)
        assert decaps.shared_secret == encaps.shared_secret, "decaps shared secret mismatch"
        _ok("decaps shared_secret matches encaps")

        return True
    except Exception as exc:
        _fail(f"MLKEM768: {exc}")
        return False
    finally:
        _delete(hem, kid)


def smoke_mldsa65(hem: HemClient) -> bool:
    _section("MLDSA65 — mldsa sign/verify")
    kid: KeyId | None = None
    try:
        try:
            kid = hem.keys.create("smoke-mldsa65", KeyType.MLDSA65)
        except HemBadRequestError:
            _skip("MLDSA65 not supported on this firmware")
            return True

        _ok(f"created kid={kid}")

        msg = b"hello mldsa"
        sig_result = hem.crypto.pqc.mldsa.sign(kid, msg)
        assert hem.crypto.pqc.mldsa.verify(kid, msg, sig_result.signature)
        _ok("sign/verify round-trip")

        # negative: wrong message → False
        assert not hem.crypto.pqc.mldsa.verify(kid, b"wrong message", sig_result.signature)
        _ok("verify with wrong message returns False")

        return True
    except Exception as exc:
        _fail(f"MLDSA65: {exc}")
        return False
    finally:
        _delete(hem, kid)


def _delete(hem: HemClient, kid: KeyId | None) -> None:
    if kid is None:
        return
    try:
        hem.keys.delete(kid)
        log.debug("deleted kid=%s", kid)
    except HemError as exc:
        _fail(f"delete kid={kid} failed: {exc}")


def main() -> int:
    logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")

    host = os.environ.get("HEM_HOST")
    passphrase = os.environ.get("HEM_PASSPHRASE")
    if not host or not passphrase:
        print("set HEM_HOST and HEM_PASSPHRASE", file=sys.stderr)
        return 2

    results: list[bool] = []

    with HemClient(host=host, passphrase=passphrase) as hem:
        hem.ensure_ready()

        results.append(smoke_aes256(hem))
        results.append(smoke_secp256r1(hem))
        results.append(smoke_ed25519(hem))
        results.append(smoke_sha2_256(hem))
        results.append(smoke_mlkem768(hem))
        results.append(smoke_mldsa65(hem))

    passed = sum(results)
    total = len(results)
    print(f"\n{'=' * 40}")
    print(f"Result: {passed}/{total} passed")

    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
