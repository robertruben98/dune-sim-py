"""Exception hierarchy for the Dune Sim client.

The Sim API signals failures with HTTP status codes and a small JSON body. Some
endpoints (EVM transactions, activity, token info) return errors as plain text
with no JSON wrapper, so :func:`raise_for_status` reads whichever of the
``error``/``message`` fields is present and falls back to the raw response text.
"""

from __future__ import annotations

from typing import Optional

import httpx

__all__ = [
    "APIError",
    "AuthenticationError",
    "BadRequestError",
    "DuneSimError",
    "NotFoundError",
    "PermissionError",
    "QuotaExceededError",
    "RateLimitError",
    "ServerError",
    "raise_for_status",
]


class DuneSimError(Exception):
    """Base class for every error raised by this library."""


class APIError(DuneSimError):
    """Raised when the Sim API returns a non-success HTTP status.

    Attributes:
        status_code: The HTTP status code returned by the API.
        response: The originating :class:`httpx.Response`, when available.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        response: Optional[httpx.Response] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class BadRequestError(APIError):
    """Raised on HTTP 400 - malformed address or invalid query parameters."""


class AuthenticationError(APIError):
    """Raised on HTTP 401 - missing or invalid ``X-Sim-Api-Key`` header."""


class QuotaExceededError(APIError):
    """Raised on HTTP 402 - the account quota has been exhausted."""


class PermissionError(APIError):
    """Raised on HTTP 403 - the API key lacks Sim API permissions."""


class NotFoundError(APIError):
    """Raised on HTTP 404 - the resource or endpoint URL was not found."""


class RateLimitError(APIError):
    """Raised on HTTP 429 - too many requests.

    Attributes:
        retry_after: Seconds to wait before retrying, parsed from the
            ``Retry-After`` header when present.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        response: Optional[httpx.Response] = None,
        retry_after: Optional[float] = None,
    ) -> None:
        super().__init__(message, status_code=status_code, response=response)
        self.retry_after = retry_after


class ServerError(APIError):
    """Raised on HTTP 5xx - a transient server-side failure."""


_STATUS_MAP = {
    400: BadRequestError,
    401: AuthenticationError,
    402: QuotaExceededError,
    403: PermissionError,
    404: NotFoundError,
    429: RateLimitError,
}


def _extract_message(response: httpx.Response) -> str:
    """Pull a human-readable message from a JSON or plain-text error body."""
    try:
        body = response.json()
    except (ValueError, UnicodeDecodeError):
        body = None
    if isinstance(body, dict):
        for key in ("error", "message"):
            value = body.get(key)
            if isinstance(value, str) and value:
                return value
    text = response.text.strip()
    if text:
        return text
    return f"HTTP {response.status_code}"


def raise_for_status(response: httpx.Response) -> None:
    """Raise the appropriate :class:`APIError` subclass for a failed response.

    Args:
        response: The HTTP response to inspect.

    Raises:
        APIError: A subclass matching the status code (or :class:`ServerError`
            for any 5xx, or :class:`APIError` for an unmapped 4xx).
    """
    status = response.status_code
    if status < 400:
        return None

    message = _extract_message(response)

    if status == 429:
        raise RateLimitError(
            message,
            status_code=status,
            response=response,
            retry_after=_parse_retry_after(response),
        )

    exc_class = _STATUS_MAP.get(status)
    if exc_class is None:
        exc_class = ServerError if status >= 500 else APIError

    raise exc_class(message, status_code=status, response=response)


def _parse_retry_after(response: httpx.Response) -> Optional[float]:
    """Parse the ``Retry-After`` header as a float number of seconds, if present."""
    raw = response.headers.get("Retry-After")
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None
