"""``client.keys`` -- key lifecycle (create, list, get, update, delete)."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

from .._base64 import b64_std_decode, b64_std_encode
from ..enums import KeyMode, KeyType
from ..models import KeyDetails, KeyId, KeyInfo, ParsedKeyType

if TYPE_CHECKING:
    from ..client import HemClient

_LIST_PAGE_SIZE = 10  # device caps at 15; stay safely below


class KeyMgmtAPI:
    """Wrapper around ``/api/keymgmt/*`` endpoints."""

    def __init__(self, client: HemClient) -> None:
        self._client = client

    def create(
        self,
        label: str,
        type: KeyType,
        *,
        descr: bytes | None = None,
        mode: KeyMode | None = None,
    ) -> KeyId:
        """Create a key on the device and return its ``kid``.

        Notes:
        - ``label`` must be at most 31 characters.
        - ``descr`` must be at most 128 raw bytes (before base64).
        - For NIST ECC types, the library defaults ``mode`` to ``ECDH,ExDSA``
          (see OQ-19); the device's own default is ECDH-only.
        """
        if len(label) > 31:
            raise ValueError("label must be at most 31 characters")
        body: dict[str, str] = {"label": label, "type": type.value}
        if descr is not None:
            if len(descr) > 128:
                raise ValueError("descr must be at most 128 raw bytes before base64")
            body["descr"] = b64_std_encode(descr)
        # OQ-19: device default for NIST ECC is ECDH-only; library default is permissive.
        if type.is_nist_ecc and mode is None:
            mode = KeyMode.ECDH_EXDSA
        if mode is not None:
            body["mode"] = mode.value
        token = self._client._auth.ensure_token("keymgmt:gen")
        raw = self._client._transport.request(
            "POST", "/api/keymgmt/create", json_body=body, token=token
        )
        return KeyId(raw["kid"])

    def list(self) -> Iterator[KeyInfo]:
        """Iterate over every key on the device, paginating as needed.

        OQ-17: end-of-list signal must be ``offset >= total``; ``listed < limit``
        is unreliable on observed firmware.
        """
        offset = 0
        token = self._client._auth.ensure_token("keymgmt:list")
        while True:
            path = f"/api/keymgmt/list/{offset}/{_LIST_PAGE_SIZE}"
            raw = self._client._transport.request("GET", path, token=token)
            total = int(raw.get("total", 0))
            listed = int(raw.get("listed", 0))
            for entry in raw.get("list", []):
                yield _key_info(entry)
            offset += listed
            if offset >= total or listed == 0:
                return

    def get(self, kid: KeyId) -> KeyDetails:
        """Return the public details of a single key.

        OQ-16: only ``keymgmt:use:<kid>`` is honoured on observed firmware,
        not the documented ``keymgmt:get`` scope.
        """
        token = self._client._auth.ensure_token(f"keymgmt:use:{kid}")
        raw = self._client._transport.request("GET", f"/api/keymgmt/get/{kid}", token=token)
        # IT-OQ-1: ``pubkey`` is absent for symmetric key types.
        raw_pubkey = raw.get("pubkey")
        return KeyDetails(
            pubkey=b64_std_decode(raw_pubkey) if raw_pubkey is not None else None,
            type=ParsedKeyType.parse(raw.get("type", "")),
            updated=int(raw.get("updated", 0)),
        )

    def update(self, kid: KeyId, *, label: str, descr: bytes | None = None) -> None:
        """Update a key's label and/or description.

        OQ-18: ``label`` is mandatory on the wire even for descr-only updates.
        """
        body: dict[str, str] = {"kid": kid, "label": label}
        if descr is not None:
            body["descr"] = b64_std_encode(descr)
        token = self._client._auth.ensure_token("keymgmt:upd")
        self._client._transport.request("POST", "/api/keymgmt/update", json_body=body, token=token)

    def delete(self, kid: KeyId) -> None:
        """Delete a key from the device."""
        token = self._client._auth.ensure_token("keymgmt:del")
        self._client._transport.request("DELETE", f"/api/keymgmt/delete/{kid}", token=token)


def _key_info(entry: dict[str, Any]) -> KeyInfo:
    return KeyInfo(
        kid=KeyId(entry["kid"]),
        label=entry.get("label", ""),
        type=ParsedKeyType.parse(entry.get("type", "")),
        created=int(entry.get("created", 0)),
        updated=int(entry.get("updated", 0)),
        descr=b64_std_decode(entry["descr"]) if entry.get("descr") else None,
    )
