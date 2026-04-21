"""``client.system`` -- system endpoints (version, status, check-in, config, reboot)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from ..models import (
    AttestationResult,
    DeviceConfig,
    DeviceStatus,
    DeviceVersion,
    SelftestResult,
)

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
        """Run the full three-step check-in bounce. No auth required.

        The device POST response contains ``newcrt``, ``newfws``, ``newuis``,
        and ``status`` fields signalling available updates. These are discarded
        in Phase 1; Phase 3 (upgrade support) will surface them.
        """
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
        """Reboot the device.

        Requires ``system:upgrade`` scope (also accepted: ``system:config``,
        ``system:shutdown``). Invalidates all tokens — re-authenticate after
        calling this.
        """
        token = self._client._auth.ensure_token("system:upgrade")
        self._client._transport.request("GET", "/api/system/reboot", token=token)
        self._client._auth.invalidate()

    def shutdown(self) -> None:
        """Shut down the device (PPA only; requires ``system:shutdown`` scope).

        The device will stop responding after this call. Re-authenticate (or
        power-cycle) before making further requests.
        """
        token = self._client._auth.ensure_token("system:shutdown")
        self._client._transport.request("GET", "/api/system/shutdown", token=token)

    def selftest(self) -> SelftestResult:
        """Run and return the device self-test status (any valid token)."""
        token = self._client._auth.ensure_token("system:config")
        raw = self._client._transport.request("GET", "/api/system/selftest", token=token)
        return SelftestResult(
            last_selftest_ts=int(raw.get("last_selftest_ts", 0)),
            fls_state=int(raw.get("fls_state", 0)),
            kat_busy=bool(raw.get("kat_busy", False)),
            se_state=int(raw.get("se_state", 0)),
        )

    def config_attestation(self) -> AttestationResult:
        """Return the device attestation certificate and genuineness flag.

        PPA only. The device ignores the access scope on this endpoint, but
        a valid JWT is required on a provisioned device (auth is only
        optional on a fresh, unpersonalized device — see
        ``encedo-hem-api-doc/system/config-attestation.md``). We use
        ``system:config`` since any valid token works.
        """
        token = self._client._auth.ensure_token("system:config")
        raw = self._client._transport.request("GET", "/api/system/config/attestation", token=token)
        return AttestationResult(crt=raw["crt"], genuine=bool(raw["genuine"]))

    def config_provisioning(
        self,
        user: str,
        email: str,
        passphrase: str,
        *,
        hostname: str | None = None,
    ) -> None:
        """Provision the device for the first time (PPA only, no auth required).

        One-time operation: raises ``HemAuthError`` (HTTP 403) if the device is
        already provisioned.

        # OQ-PROVISIONING: confirm request body schema against live device.
        """
        body: dict[str, object] = {
            "user": user,
            "email": email,
            "passphrase": passphrase,
        }
        if hostname is not None:
            body["hostname"] = hostname
        self._client._transport.request("POST", "/api/system/config/provisioning", json_body=body)
