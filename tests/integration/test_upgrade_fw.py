"""Integration tests for firmware upgrade flow."""

from __future__ import annotations

import os
import pathlib

import pytest

from encedo_hem import FirmwareCheckResult, HemClient

_FW_PATH = pathlib.Path(os.environ.get("HEM_FW_PATH", ""))


def test_upload_and_check_fw(hem: HemClient) -> None:
    if not _FW_PATH.is_file():
        pytest.skip("HEM_FW_PATH not set or file not found")
    fw_bytes = _FW_PATH.read_bytes()
    hem.upgrade.upload_fw(fw_bytes)
    result = hem.upgrade.check_fw()
    assert isinstance(result, FirmwareCheckResult)
    assert result.raw is not None


@pytest.mark.skip(reason="destructive — installs firmware and reboots device")
def test_install_fw(hem: HemClient) -> None:
    hem.upgrade.install_fw()
