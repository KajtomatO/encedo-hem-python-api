"""Integration tests for UI upgrade flow."""
from __future__ import annotations

import os
import pathlib

import pytest

from encedo_hem import FirmwareCheckResult, HemClient

_UI_PATH = pathlib.Path(os.environ.get("HEM_UI_PATH", ""))


def test_upload_and_check_ui(hem: HemClient) -> None:
    if not _UI_PATH.is_file():
        pytest.skip("HEM_UI_PATH not set or file not found")
    ui_bytes = _UI_PATH.read_bytes()
    hem.upgrade.upload_ui(ui_bytes)
    result = hem.upgrade.check_ui()
    assert isinstance(result, FirmwareCheckResult)
    assert result.raw is not None


@pytest.mark.skip(reason="destructive — installs UI firmware and reboots device")
def test_install_ui(hem: HemClient) -> None:
    hem.upgrade.install_ui()
