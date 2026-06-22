"""Tests for the typed exception hierarchy and HTTP status mapping."""

import httpx
import pytest

from dune_sim.errors import (
    APIError,
    AuthenticationError,
    DuneSimError,
    NotFoundError,
    PermissionError,
    QuotaExceededError,
    RateLimitError,
    ServerError,
    raise_for_status,
)


def _response(status_code: int, *, json=None, text=None) -> httpx.Response:
    request = httpx.Request("GET", "https://api.sim.dune.com/v1/evm/balances/0xabc")
    if json is not None:
        return httpx.Response(status_code, json=json, request=request)
    return httpx.Response(status_code, text=text or "", request=request)


def test_all_errors_inherit_from_dune_sim_error():
    assert issubclass(APIError, DuneSimError)
    assert issubclass(AuthenticationError, APIError)
    assert issubclass(RateLimitError, APIError)


def test_raise_for_status_passes_through_2xx():
    # Should not raise for a successful response.
    assert raise_for_status(_response(200, json={"ok": True})) is None


def test_401_raises_authentication_error_with_json_error_field():
    with pytest.raises(AuthenticationError) as excinfo:
        raise_for_status(_response(401, json={"error": "invalid API Key"}))
    assert excinfo.value.status_code == 401
    assert "invalid API Key" in str(excinfo.value)


def test_402_raises_quota_exceeded_error():
    with pytest.raises(QuotaExceededError):
        raise_for_status(_response(402, json={"error": "quota exceeded"}))


def test_403_raises_permission_error():
    with pytest.raises(PermissionError):
        raise_for_status(_response(403, json={"error": "forbidden"}))


def test_404_raises_not_found_error():
    with pytest.raises(NotFoundError):
        raise_for_status(_response(404, json={"message": "not found"}))


def test_429_raises_rate_limit_error():
    with pytest.raises(RateLimitError):
        raise_for_status(_response(429, json={"error": "too many requests"}))


def test_500_raises_server_error_with_message_field():
    with pytest.raises(ServerError) as excinfo:
        raise_for_status(_response(500, json={"message": "Internal server error"}))
    assert "Internal server error" in str(excinfo.value)


def test_plain_text_error_body_is_used_as_message():
    # Some endpoints (transactions, activity, token-info) return plain text.
    with pytest.raises(ServerError) as excinfo:
        raise_for_status(_response(500, text="boom"))
    assert "boom" in str(excinfo.value)


def test_unmapped_4xx_raises_generic_api_error():
    with pytest.raises(APIError) as excinfo:
        raise_for_status(_response(418, text="teapot"))
    assert excinfo.value.status_code == 418
