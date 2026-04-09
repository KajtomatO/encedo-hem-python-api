"""``client.system`` -- system endpoints (version, status, check-in, config, reboot)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from ..models import DeviceConfig, DeviceStatus, DeviceVersion

if TYPE_CHECKING:
    from ..client import HemClient


def _parse_ts(value: object) -> datetime | None:
    """Parse the ISO 8601 ``ts`` field from ``GET /api/system/status``.

    Per the upstream spec the wire format is e.g. ``"2022-03-16T18:17:27Z"``.
    A trailing ``Z`` is normalised to ``+00:00`` for ``fromisoformat``.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"system/status.ts must be ISO 8601 string, got {type(value).__name__}")
    iso = value[:-1] + "+00:00" if value.endswith("Z") else value
    return datetime.fromisoformat(iso)


class SystemAPI:
    """Wrapper around ``/api/system/*`` endpoints."""

    def __init__(self, client: HemClient) -> None:
        self._client = client

    # --- unauthenticated ---

    def version(self) -> DeviceVersion:
        """Return the device firmware/hardware version banner."""
        raw = self._client._transport.request("GET", "/api/system/version")
        return DeviceVersion(
            hwv=raw["hwv"],
            blv=raw["blv"],
            fwv=raw["fwv"],
            fws=raw["fws"],
            uis=raw.get("uis"),
        )

    def status(self) -> DeviceStatus:
        """Return the live device status snapshot.

        ``inited`` field is inverted: a present ``inited`` key in the wire
        response means the device is **not** yet initialised.
        """
        raw = self._client._transport.request("GET", "/api/system/status")
        return DeviceStatus(
            fls_state=int(raw.get("fls_state", 0)),
            ts=_parse_ts(raw.get("ts")),
            hostname=raw.get("hostname"),
            https=raw.get("https"),
            initialized="inited" not in raw,
            format=raw.get("format"),
            uptime=raw.get("uptime"),
            temp=raw.get("temp"),
            storage=raw.get("storage"),
        )

    def checkin(self) -> None:
        """Run the full three-step check-in bounce. No auth required."""
        challenge = self._client._transport.request("GET", "/api/system/checkin")
        backend_response = self._client._transport.backend_post("/checkin", challenge)
        self._client._transport.request("POST", "/api/system/checkin", json_body=backend_response)

    # --- authenticated ---

    def config(self) -> DeviceConfig:
        """Return the device configuration (requires ``system:config`` scope)."""
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
        """Reboot the device (requires ``system:config`` scope)."""
        token = self._client._auth.ensure_token("system:config")
        self._client._transport.request("GET", "/api/system/reboot", token=token)
