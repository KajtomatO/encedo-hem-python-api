"""Tests for HemClient.is_alive()."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

from encedo_hem.client import HemClient


def _make_client(host: str = "device.local") -> HemClient:
    return HemClient(host, "passw0rd")


def test_is_alive_true_on_returncode_0() -> None:
    with patch("encedo_hem.client.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        assert _make_client().is_alive() is True


def test_is_alive_false_on_nonzero_returncode() -> None:
    with patch("encedo_hem.client.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1)
        assert _make_client().is_alive() is False


def test_is_alive_false_on_timeout() -> None:
    with patch("encedo_hem.client.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=[], timeout=2)
        assert _make_client().is_alive() is False


def test_is_alive_false_when_ping_not_found() -> None:
    with patch("encedo_hem.client.subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError
        assert _make_client().is_alive() is False


def test_is_alive_false_on_os_error() -> None:
    with patch("encedo_hem.client.subprocess.run") as mock_run:
        mock_run.side_effect = OSError("permission denied")
        assert _make_client().is_alive() is False


def test_is_alive_passes_host_to_ping() -> None:
    with patch("encedo_hem.client.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        _make_client("192.168.1.50").is_alive()
        cmd = mock_run.call_args[0][0]
    assert "192.168.1.50" in cmd


def test_is_alive_capture_output() -> None:
    """ping output must be suppressed so it does not appear on stdout."""
    with patch("encedo_hem.client.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        _make_client().is_alive()
        kwargs = mock_run.call_args[1]
    assert kwargs.get("capture_output") is True
