from __future__ import annotations

from encedo_hem.enums import CipherAlg, KeyType


def test_keytype_wire_values_use_dashes() -> None:
    assert KeyType.SHA2_256.value == "SHA2-256"
    assert KeyType.SHA3_512.value == "SHA3-512"


def test_keytype_is_nist_ecc() -> None:
    assert KeyType.SECP256R1.is_nist_ecc is True
    assert KeyType.SECP384R1.is_nist_ecc is True
    assert KeyType.SECP521R1.is_nist_ecc is True
    assert KeyType.SECP256K1.is_nist_ecc is True


def test_keytype_non_nist_ecc() -> None:
    assert KeyType.AES256.is_nist_ecc is False
    assert KeyType.CURVE25519.is_nist_ecc is False
    assert KeyType.ED25519.is_nist_ecc is False
    assert KeyType.MLKEM768.is_nist_ecc is False


def test_cipheralg_gcm_has_iv_and_tag() -> None:
    assert CipherAlg.AES256_GCM.has_iv is True
    assert CipherAlg.AES256_GCM.has_tag is True


def test_cipheralg_ecb_no_iv() -> None:
    assert CipherAlg.AES256_ECB.has_iv is False
    assert CipherAlg.AES256_ECB.has_tag is False


def test_cipheralg_cbc_iv_no_tag() -> None:
    assert CipherAlg.AES256_CBC.has_iv is True
    assert CipherAlg.AES256_CBC.has_tag is False
