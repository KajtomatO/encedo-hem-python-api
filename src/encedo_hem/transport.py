"""Thin httpx wrapper with two clients.

The device client (``self._device``) talks to the HEM hardware over its
self-signed TLS endpoint with TLS verification disabled and keep-alive forced
off (the device closes TCP after every response).

The backend client (``self._backend``) talks to ``api.encedo.com`` for the
check-in handshake. That endpoint uses a publicly trusted certificate, so
``verify=True`` is **mandatory** -- a regression here would expose the
check-in flow to MITM.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from .errors import HemError, HemPayloadTooLargeError, HemTransportError, from_status

MAX_BODY_BYTES = 7300

_log = logging.getLogger(__name__)


class Transport:
    """Owns the two httpx clients and translates HTTP errors to :mod:`encedo_hem.errors`."""

    def __init__(
        self,
        host: str,
        *,
        timeout: float = 30.0,
        scheme: str = "https",
    ) -> None:
        self._base_url = f"{scheme}://{host}"
        self._device = httpx.Client(
            base_url=self._base_url,
            verify=False,
            timeout=timeout,
            limits=httpx.Limits(max_keepalive_connections=0),
            headers={"Connection": "close"},
        )
        self._backend = httpx.Client(
            base_url="https://api.encedo.com",
            verify=True,
            timeout=timeout,
            limits=httpx.Limits(max_keepalive_connections=0),
            headers={"Connection": "close"},
        )

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        token: str | None = None,
    ) -> dict[str, Any]:
        """Send a request to the device, returning the parsed JSON body or ``{}``."""
        headers: dict[str, str] = {}
        body: bytes | None = None
        if json_body is not None:
            body = json.dumps(json_body, separators=(",", ":")).encode("utf-8")
            if len(body) > MAX_BODY_BYTES:
                raise HemPayloadTooLargeError(
                    f"{path}: request body is {len(body)} bytes, max {MAX_BODY_BYTES}",
                    size_actual=len(body),
                    endpoint=path,
                )
            headers["Content-Type"] = "application/json"
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        try:
            response = self._device.request(method, path, content=body, headers=headers)
        except httpx.HTTPError as exc:
            raise HemTransportError(f"{path}: {exc}", endpoint=path) from exc
        if response.status_code != 200:
            parsed = _safe_parse_body(response)
            raise from_status(response.status_code, endpoint=path, body=parsed)
        return _safe_parse_body(response) or {}

    def backend_post(self, path: str, json_body: dict[str, Any]) -> dict[str, Any]:
        """POST to ``api.encedo.com`` and return the parsed JSON body."""
        try:
            response = self._backend.post(path, json=json_body)
        except httpx.HTTPError as exc:
            raise HemTransportError(f"backend {path}: {exc}", endpoint=path) from exc
        if response.status_code != 200:
            raise from_status(
                response.status_code,
                endpoint=f"backend:{path}",
                body=_safe_parse_body(response),
            )
        parsed = _safe_parse_body(response)
        if parsed is None:
            raise HemError(f"backend {path}: empty body", endpoint=path)
        return parsed

    def close(self) -> None:
        """Close both underlying httpx clients."""
        self._device.close()
        self._backend.close()


def _safe_parse_body(response: httpx.Response) -> dict[str, Any] | None:
    if not response.content:
        return None
    try:
        parsed = response.json()
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, dict):
        return parsed
    return None
