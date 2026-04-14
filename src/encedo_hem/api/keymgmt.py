"""``client.keys`` -- key lifecycle (create, list, get, update, delete)."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

from .._base64 import b64_std_decode, b64_std_encode
from ..enums import KeyMode, KeyType
from ..errors import HemNotFoundError
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

        OQ-16: the spec scope is ``keymgmt:get`` (confirmed by upstream docs),
        but firmware v1.2.2-DIAG only accepts ``keymgmt:use:<kid>`` empirically.
        We use the narrow per-key scope that works everywhere.
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

    def derive(
        self,
        kid: KeyId,
        label: str,
        type: KeyType,
        *,
        descr: bytes | None = None,
        ext_kid: KeyId | None = None,
        pubkey: bytes | None = None,
        mode: KeyMode | None = None,
    ) -> KeyId:
        """Derive a new key via ECDH and return its ``kid``.

        ``ext_kid`` and ``pubkey`` are mutually exclusive.
        """
        if len(label) > 31:
            raise ValueError("label must be at most 31 characters")
        if descr is not None and len(descr) > 128:
            raise ValueError("descr must be at most 128 raw bytes before base64")
        if ext_kid is not None and pubkey is not None:
            raise ValueError("ext_kid and pubkey are mutually exclusive")
        body: dict[str, str] = {"kid": kid, "label": label, "type": type.value}
        if descr is not None:
            body["descr"] = b64_std_encode(descr)
        if ext_kid is not None:
            body["ext_kid"] = ext_kid
        if pubkey is not None:
            body["pubkey"] = b64_std_encode(pubkey)
        if type.is_nist_ecc and mode is None:
            mode = KeyMode.ECDH_EXDSA
        if mode is not None:
            body["mode"] = mode.value
        token = self._client._auth.ensure_token("keymgmt:ecdh")
        raw = self._client._transport.request(
            "POST", "/api/keymgmt/derive", json_body=body, token=token
        )
        return KeyId(raw["kid"])

    def import_key(
        self,
        label: str,
        pubkey: bytes,
        type: KeyType,
        *,
        descr: bytes | None = None,
        mode: KeyMode | None = None,
    ) -> KeyId:
        """Import an external public key and return its ``kid``.

        Named ``import_key`` to avoid shadowing the ``import`` keyword.

        Note: HTTP 406 from this endpoint means the public key already exists
        on the device (key deduplication). Raises :class:`HemNotAcceptableError`.
        """
        if len(label) > 31:
            raise ValueError("label must be at most 31 characters")
        body: dict[str, str] = {
            "label": label,
            "pubkey": b64_std_encode(pubkey),
            "type": type.value,
        }
        if descr is not None:
            body["descr"] = b64_std_encode(descr)
        if type.is_nist_ecc and mode is None:
            mode = KeyMode.ECDH_EXDSA
        if mode is not None:
            body["mode"] = mode.value
        token = self._client._auth.ensure_token("keymgmt:imp")
        raw = self._client._transport.request(
            "POST", "/api/keymgmt/import", json_body=body, token=token
        )
        return KeyId(raw["kid"])

    def search(
        self,
        descr: str,
        *,
        offset: int = 0,
        limit: int = _LIST_PAGE_SIZE,
    ) -> Iterator[KeyInfo]:
        """Search keys by description pattern, auto-paginating.

        ``descr`` is passed as-is to the device. Convention (OQ-7):
        ``'^' + base64(raw_prefix)`` where ``raw_prefix`` is ≥6 bytes.

        HTTP 404 from the device means no keys matched — yields nothing.
        """
        token = self._client._auth.ensure_token("keymgmt:search")
        while True:
            body: dict[str, Any] = {"descr": descr, "offset": offset, "limit": limit}
            try:
                raw = self._client._transport.request(
                    "POST", "/api/keymgmt/search", json_body=body, token=token
                )
            except HemNotFoundError:
                return
            total = int(raw.get("total", 0))
            listed = int(raw.get("listed", 0))
            for entry in raw.get("list", []):
                yield _key_info(entry)
            offset += listed
            if offset >= total or listed == 0:
                return


def _key_info(entry: dict[str, Any]) -> KeyInfo:
    return KeyInfo(
        kid=KeyId(entry["kid"]),
        label=entry.get("label", ""),
        type=ParsedKeyType.parse(entry.get("type", "")),
        created=int(entry.get("created", 0)),
        updated=int(entry.get("updated", 0)),
        descr=b64_std_decode(entry["descr"]) if entry.get("descr") else None,
    )
