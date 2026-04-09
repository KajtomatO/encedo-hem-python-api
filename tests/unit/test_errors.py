from __future__ import annotations

from encedo_hem.errors import (
    HemAuthError,
    HemBadRequestError,
    HemDeviceFailureError,
    HemError,
    HemNotAcceptableError,
    HemNotFoundError,
    HemPayloadTooLargeError,
    HemTlsRequiredError,
    from_status,
)


def test_400_maps_to_bad_request() -> None:
    err = from_status(400, endpoint="/api/x", body=None)
    assert isinstance(err, HemBadRequestError)
    assert err.status_code == 400
    assert err.endpoint == "/api/x"


def test_401_and_403_map_to_auth() -> None:
    assert isinstance(from_status(401, endpoint="/api/x", body=None), HemAuthError)
    assert isinstance(from_status(403, endpoint="/api/x", body=None), HemAuthError)


def test_404_maps_to_not_found() -> None:
    assert isinstance(from_status(404, endpoint="/api/x", body=None), HemNotFoundError)


def test_406_maps_to_not_acceptable() -> None:
    assert isinstance(from_status(406, endpoint="/api/x", body=None), HemNotAcceptableError)


def test_409_maps_to_device_failure() -> None:
    assert isinstance(from_status(409, endpoint="/api/x", body=None), HemDeviceFailureError)


def test_413_maps_to_payload_too_large_with_unknown_size() -> None:
    err = from_status(413, endpoint="/api/x", body=None)
    assert isinstance(err, HemPayloadTooLargeError)
    assert err.size_actual == -1
    assert err.size_limit == 7300
    assert err.status_code == 413


def test_418_maps_to_tls_required() -> None:
    assert isinstance(from_status(418, endpoint="/api/x", body=None), HemTlsRequiredError)


def test_unknown_status_maps_to_base_class() -> None:
    err = from_status(599, endpoint="/api/x", body=None)
    assert type(err) is HemError
    assert err.status_code == 599


def test_str_does_not_leak_passphrase() -> None:
    err = HemAuthError("test message", endpoint="/api/x")
    assert "passphrase" not in str(err)
