"""``client.logger`` -- audit log endpoints."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from ..models import LoggerKeyInfo

if TYPE_CHECKING:
    from ..client import HemClient


class LoggerAPI:
    """Wrapper around ``/api/logger/*`` endpoints."""

    def __init__(self, client: HemClient) -> None:
        self._client = client

    def key(self) -> LoggerKeyInfo:
        """Return the audit log public key and current signed nonce.

        Scope: ``logger:get``.
        """
        token = self._client._auth.ensure_token("logger:get")
        raw = self._client._transport.request("GET", "/api/logger/key", token=token)
        return LoggerKeyInfo(
            key=raw["key"],
            nonce=raw["nonce"],
            nonce_signed=raw["nonce_signed"],
        )

    def list(self, offset: int = 0) -> Iterator[str]:
        """Yield all log entry IDs, auto-paginating from ``offset``.

        Scope: ``logger:get``.

        The device controls page size via the ``listed`` field. Pagination
        advances by the number of entries returned until all are yielded.
        """
        token = self._client._auth.ensure_token("logger:get")
        current_offset = offset
        while True:
            raw = self._client._transport.request(
                "GET", f"/api/logger/list/{current_offset}", token=token
            )
            entries: list[str] = raw.get("id", [])
            yield from entries
            listed = len(entries)
            total = int(raw.get("total", 0))
            current_offset += listed
            if listed == 0 or current_offset >= total:
                break

    def get(self, entry_id: str) -> str:
        """Return the raw text content of a log entry.

        Scope: ``logger:get``.
        """
        token = self._client._auth.ensure_token("logger:get")
        return self._client._transport.request_text(
            "GET", f"/api/logger/{entry_id}", token=token
        )

    def delete(self, entry_id: str) -> None:
        """Delete a log entry.

        Scope: ``logger:del``.
        """
        token = self._client._auth.ensure_token("logger:del")
        self._client._transport.request(
            "DELETE", f"/api/logger/{entry_id}", token=token
        )
