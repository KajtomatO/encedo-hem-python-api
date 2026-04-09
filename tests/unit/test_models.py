from __future__ import annotations

from encedo_hem.enums import HardwareForm
from encedo_hem.models import DeviceVersion, ParsedKeyType


def test_parsed_keytype_full() -> None:
    parsed = ParsedKeyType.parse("PKEY,ECDH,ExDSA,SECP256R1")
    assert parsed.flags == frozenset({"PKEY", "ECDH", "ExDSA"})
    assert parsed.algorithm == "SECP256R1"


def test_parsed_keytype_single_term() -> None:
    parsed = ParsedKeyType.parse("AES256")
    assert parsed.flags == frozenset()
    assert parsed.algorithm == "AES256"


def test_parsed_keytype_empty() -> None:
    parsed = ParsedKeyType.parse("")
    assert parsed.flags == frozenset()
    assert parsed.algorithm == ""


def test_device_version_epa_diag() -> None:
    v = DeviceVersion(hwv="EPA-2.0", blv="bl", fwv="1.2.2-DIAG", fws="x", uis=None)
    assert v.hardware is HardwareForm.EPA
    assert v.is_diag is True


def test_device_version_ppa_release() -> None:
    v = DeviceVersion(hwv="PPA-1.0", blv="bl", fwv="1.2.2", fws="x", uis="ui")
    assert v.hardware is HardwareForm.PPA
    assert v.is_diag is False


def test_device_version_unknown_hardware() -> None:
    v = DeviceVersion(hwv="?", blv="bl", fwv="1.2.2", fws="x", uis=None)
    assert v.hardware is HardwareForm.UNKNOWN
