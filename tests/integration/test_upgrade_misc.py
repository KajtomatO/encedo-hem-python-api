"""Integration tests for bootloader upload and USB mode."""

from __future__ import annotations

import os
import pathlib

import pytest

from encedo_hem import HemClient

_BL_PATH = pathlib.Path(os.environ.get("HEM_BL_PATH", ""))


def test_upload_bootldr(hem: HemClient) -> None:
    if not _BL_PATH.is_file():
        pytest.skip("HEM_BL_PATH not set or file not found")
    hem.upgrade.upload_bootldr(_BL_PATH.read_bytes())


@pytest.mark.skip(reason="enables USB serial mode — may disrupt TCP connectivity")
def test_usbmode(hem: HemClient) -> None:
    hem.upgrade.usbmode()
