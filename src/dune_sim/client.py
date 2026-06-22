"""Synchronous and asynchronous clients for the Dune Sim API.

Both clients share request construction, query-parameter serialization, error
mapping, and retry/backoff logic through :class:`_BaseClient`. The sync client
wraps :class:`httpx.Client`; the async client wraps :class:`httpx.AsyncClient`.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator, Iterator, Sequence
from types import TracebackType
from typing import (
    Any,
    Optional,
    TypeVar,
    Union,
)

import httpx
from pydantic import BaseModel

from .errors import raise_for_status
from .models import (
    ActivityResponse,
    BalancesResponse,
    SupportedChainsResponse,
    SvmBalancesResponse,
    SvmTransactionsResponse,
    TokenHoldersResponse,
    TokenInfoResponse,
    TransactionsResponse,
)

__all__ = ["AsyncDuneSimClient", "DuneSimClient"]

DEFAULT_BASE_URL = "https://api.sim.dune.com"
DEFAULT_API_KEY_HEADER = "X-Sim-Api-Key"
DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_FACTOR = 0.5
DEFAULT_USER_AGENT = "dune-sim-py"

# Statuses worth retrying: rate limiting and transient server failures.
_RETRYABLE_STATUSES = frozenset({429, 500, 502, 503})

ModelT = TypeVar("ModelT", bound=BaseModel)
ParamValue = Union[str, int, float, bool, Sequence[Union[str, int]], None]


def _serialize_params(params: dict[str, ParamValue]) -> dict[str, str]:
    """Render query parameters into the string forms the Sim API expects.

    Drops ``None`` values, renders booleans as ``"true"``/``"false"``, joins
    sequences with commas, and stringifies numbers explicitly (so IntEnum-like
    values never leak their member name into the URL).

    Args:
        params: Raw parameter values keyed by query-string name.

    Returns:
        A mapping of only the present parameters, all as strings.
    """
    out: dict[str, str] = {}
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, bool):
            out[key] = "true" if value else "false"
        elif isinstance(value, (list, tuple)):
            if not value:
                continue
            # str(int(v)) for any int subclass (incl. IntEnum), so an enum
            # renders as its number, not its member name, on Python < 3.11.
            out[key] = ",".join(str(int(v)) if isinstance(v, int) else str(v) for v in value)
        elif isinstance(value, int):
            out[key] = str(int(value))
        else:
            out[key] = str(value)
    return out


class _BaseClient:
    """Shared configuration, param serialization, and retry math."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        api_key_header: str = DEFAULT_API_KEY_HEADER,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    ) -> None:
        if not api_key:
            raise ValueError("api_key is required to authenticate with the Dune Sim API")
        self.api_key = api_key
        self.api_key_header = api_key_header
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    def _headers(self) -> dict[str, str]:
        return {
            self.api_key_header: self.api_key,
            "Accept": "application/json",
            "User-Agent": DEFAULT_USER_AGENT,
        }

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def _should_retry(self, response: httpx.Response, attempt: int) -> bool:
        return attempt < self.max_retries and response.status_code in _RETRYABLE_STATUSES

    def _retry_delay(self, response: httpx.Response, attempt: int) -> float:
        """Compute the delay before the next attempt.

        Honors a ``Retry-After`` header when present; otherwise applies
        exponential backoff (``backoff_factor * 2**attempt``).
        """
        retry_after = response.headers.get("Retry-After")
        if retry_after is not None:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                pass
        return float(self.backoff_factor * (2**attempt))


class DuneSimClient(_BaseClient):
    """Synchronous client for the Dune Sim API.

    Args:
        api_key: Sim API key sent in the ``X-Sim-Api-Key`` header. Required.
        base_url: API base URL. Defaults to ``https://api.sim.dune.com``.
        api_key_header: Header name to carry the API key. Defaults to
            ``X-Sim-Api-Key``.
        timeout: Per-request timeout in seconds.
        max_retries: Maximum retry attempts on ``429``/``5xx`` responses.
        backoff_factor: Base seconds for exponential backoff between retries.

    Example:
        >>> with DuneSimClient(api_key="...") as client:
        ...     balances = client.get_evm_balances("0xd8da...")
    """

    def __init__(self, api_key: str, **kwargs: Any) -> None:
        super().__init__(api_key, **kwargs)
        self._http = httpx.Client(timeout=self.timeout, headers=self._headers())

    def __enter__(self) -> DuneSimClient:
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._http.close()

    def _request(
        self,
        path: str,
        model: type[ModelT],
        params: Optional[dict[str, ParamValue]] = None,
    ) -> ModelT:
        query = _serialize_params(params or {})
        url = self._url(path)
        attempt = 0
        while True:
            response = self._http.get(url, params=query)
            if self._should_retry(response, attempt):
                time.sleep(self._retry_delay(response, attempt))
                attempt += 1
                continue
            raise_for_status(response)
            return model.model_validate(response.json())

    # -- EVM endpoints ----------------------------------------------------

    def get_evm_balances(
        self,
        address: str,
        *,
        chain_ids: Optional[Union[str, Sequence[Union[str, int]]]] = None,
        filters: Optional[str] = None,
        asset_class: Optional[str] = None,
        metadata: Optional[Union[str, Sequence[str]]] = None,
        exclude_spam_tokens: Optional[bool] = None,
        exclude_unpriced: Optional[bool] = None,
        historical_prices: Optional[Union[str, Sequence[int]]] = None,
        offset: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> BalancesResponse:
        """Fetch token balances for a wallet (``GET /v1/evm/balances/{address}``).

        Args:
            address: EVM wallet address.
            chain_ids: Numeric chain IDs or tags (e.g. ``"1"``, ``["1", 137]``,
                or a tag like ``"default"``).
            filters: Restrict to ``"erc20"`` or ``"native"``.
            asset_class: Restrict by asset class, e.g. ``"stablecoin"``.
            metadata: Extra metadata to include: any of ``logo``, ``url``, ``pools``.
            exclude_spam_tokens: Exclude tokens with <100 USD liquidity.
            exclude_unpriced: Exclude tokens without pricing data.
            historical_prices: Up to 3 hour offsets, e.g. ``[24, 168, 720]``.
            offset: Pagination cursor from a previous response's ``next_offset``.
            limit: Page size (max 1000).

        Returns:
            The parsed :class:`~dune_sim.models.BalancesResponse`.
        """
        return self._request(
            f"/v1/evm/balances/{address}",
            BalancesResponse,
            {
                "chain_ids": chain_ids,
                "filters": filters,
                "asset_class": asset_class,
                "metadata": metadata,
                "exclude_spam_tokens": exclude_spam_tokens,
                "exclude_unpriced": exclude_unpriced,
                "historical_prices": historical_prices,
                "offset": offset,
                "limit": limit,
            },
        )

    def get_evm_activity(
        self,
        address: str,
        *,
        chain_ids: Optional[Union[str, Sequence[Union[str, int]]]] = None,
        token_address: Optional[Union[str, Sequence[str]]] = None,
        activity_type: Optional[Sequence[str]] = None,
        asset_type: Optional[Sequence[str]] = None,
        offset: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> ActivityResponse:
        """Fetch chronological wallet activity (``GET /v1/evm/activity/{address}``).

        Args:
            address: EVM wallet address.
            chain_ids: Numeric chain IDs or tags to include.
            token_address: Filter by one or more token contract addresses.
            activity_type: Filter by event type (approve, burn, call, mint,
                receive, send, swap, transfer).
            asset_type: Filter by asset standard (native, erc20, erc721, erc1155).
            offset: Pagination cursor from a previous response's ``next_offset``.
            limit: Page size (1-100, default 20).

        Returns:
            The parsed :class:`~dune_sim.models.ActivityResponse`.
        """
        return self._request(
            f"/v1/evm/activity/{address}",
            ActivityResponse,
            {
                "chain_ids": chain_ids,
                "token_address": token_address,
                "activity_type": activity_type,
                "asset_type": asset_type,
                "offset": offset,
                "limit": limit,
            },
        )

    def get_evm_transactions(
        self,
        address: str,
        *,
        chain_ids: Optional[Union[str, Sequence[Union[str, int]]]] = None,
        decode: Optional[bool] = None,
        offset: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> TransactionsResponse:
        """Fetch transactions for a wallet (``GET /v1/evm/transactions/{address}``).

        Args:
            address: EVM wallet address.
            chain_ids: Numeric chain IDs or tags to include.
            decode: Include decoded transaction logs when ``True``.
            offset: Pagination cursor from a previous response's ``next_offset``.
            limit: Page size (1-100, default 100).

        Returns:
            The parsed :class:`~dune_sim.models.TransactionsResponse`.
        """
        return self._request(
            f"/v1/evm/transactions/{address}",
            TransactionsResponse,
            {
                "chain_ids": chain_ids,
                "decode": decode,
                "offset": offset,
                "limit": limit,
            },
        )

    def get_evm_token_info(
        self,
        address: str,
        *,
        chain_ids: str,
        historical_prices: Optional[Union[str, Sequence[int]]] = None,
        offset: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> TokenInfoResponse:
        """Fetch token metadata and pricing (``GET /v1/evm/token-info/{address}``).

        Args:
            address: Token contract address, or ``"native"`` for the gas token.
            chain_ids: Exactly one numeric chain ID (required; chain names are
                not accepted).
            historical_prices: Up to 3 hour offsets, e.g. ``[24, 168, 720]``.
            offset: Pagination cursor from a previous response's ``next_offset``.
            limit: Page size.

        Returns:
            The parsed :class:`~dune_sim.models.TokenInfoResponse`.
        """
        return self._request(
            f"/v1/evm/token-info/{address}",
            TokenInfoResponse,
            {
                "chain_ids": chain_ids,
                "historical_prices": historical_prices,
                "offset": offset,
                "limit": limit,
            },
        )

    def get_evm_token_holders(
        self,
        chain_id: int,
        token_address: str,
        *,
        offset: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> TokenHoldersResponse:
        """Fetch token holders (``GET /v1/evm/token-holders/{chain_id}/{address}``).

        Args:
            chain_id: Numeric chain ID the token lives on.
            token_address: Token contract address.
            offset: Pagination cursor from a previous response's ``next_offset``.
            limit: Page size (max 500, default 500).

        Returns:
            The parsed :class:`~dune_sim.models.TokenHoldersResponse`.
        """
        return self._request(
            f"/v1/evm/token-holders/{chain_id}/{token_address}",
            TokenHoldersResponse,
            {"offset": offset, "limit": limit},
        )

    def get_supported_chains(self) -> SupportedChainsResponse:
        """List supported chains and their capabilities.

        Calls ``GET /v1/evm/supported-chains``.

        Returns:
            The parsed :class:`~dune_sim.models.SupportedChainsResponse`.
        """
        return self._request("/v1/evm/supported-chains", SupportedChainsResponse)

    # -- SVM endpoints ----------------------------------------------------

    def get_svm_balances(
        self,
        address: str,
        *,
        chains: Optional[Union[str, Sequence[str]]] = None,
        offset: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> SvmBalancesResponse:
        """Fetch SVM token balances (``GET /beta/svm/balances/{address}``).

        Args:
            address: Solana / Eclipse wallet address.
            chains: Comma-separated chains, ``"solana"`` and/or ``"eclipse"``.
            offset: Pagination cursor from a previous response's ``next_offset``.
            limit: Page size (1-1000, default 1000).

        Returns:
            The parsed :class:`~dune_sim.models.SvmBalancesResponse`.
        """
        return self._request(
            f"/beta/svm/balances/{address}",
            SvmBalancesResponse,
            {"chains": chains, "offset": offset, "limit": limit},
        )

    def get_svm_transactions(
        self,
        address: str,
        *,
        offset: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> SvmTransactionsResponse:
        """Fetch SVM transactions (``GET /beta/svm/transactions/{address}``).

        Args:
            address: Solana / Eclipse wallet address.
            offset: Pagination cursor from a previous response's ``next_offset``.
            limit: Page size (default 100, capped at 1000).

        Returns:
            The parsed :class:`~dune_sim.models.SvmTransactionsResponse`.
        """
        return self._request(
            f"/beta/svm/transactions/{address}",
            SvmTransactionsResponse,
            {"offset": offset, "limit": limit},
        )

    # -- Pagination helpers ----------------------------------------------

    def iter_evm_balances(self, address: str, **kwargs: Any) -> Iterator[Any]:
        """Iterate over every balance for a wallet, following pagination.

        Accepts the same keyword arguments as :meth:`get_evm_balances` (except
        ``offset``, which is managed internally).

        Yields:
            Each :class:`~dune_sim.models.Balance` across all pages.
        """
        kwargs.pop("offset", None)
        offset: Optional[str] = None
        while True:
            page = self.get_evm_balances(address, offset=offset, **kwargs)
            yield from page.balances
            if not page.next_offset:
                return
            offset = page.next_offset

    def iter_evm_activity(self, address: str, **kwargs: Any) -> Iterator[Any]:
        """Iterate over every activity event for a wallet, following pagination.

        Yields:
            Each :class:`~dune_sim.models.ActivityItem` across all pages.
        """
        kwargs.pop("offset", None)
        offset: Optional[str] = None
        while True:
            page = self.get_evm_activity(address, offset=offset, **kwargs)
            yield from page.activity
            if not page.next_offset:
                return
            offset = page.next_offset

    def iter_evm_transactions(self, address: str, **kwargs: Any) -> Iterator[Any]:
        """Iterate over every transaction for a wallet, following pagination.

        Yields:
            Each :class:`~dune_sim.models.Transaction` across all pages.
        """
        kwargs.pop("offset", None)
        offset: Optional[str] = None
        while True:
            page = self.get_evm_transactions(address, offset=offset, **kwargs)
            yield from page.transactions
            if not page.next_offset:
                return
            offset = page.next_offset

    def iter_evm_token_holders(
        self, chain_id: int, token_address: str, **kwargs: Any
    ) -> Iterator[Any]:
        """Iterate over every holder of a token, following pagination.

        Yields:
            Each :class:`~dune_sim.models.TokenHolder` across all pages.
        """
        kwargs.pop("offset", None)
        offset: Optional[str] = None
        while True:
            page = self.get_evm_token_holders(chain_id, token_address, offset=offset, **kwargs)
            yield from page.holders
            if not page.next_offset:
                return
            offset = page.next_offset


class AsyncDuneSimClient(_BaseClient):
    """Asynchronous client for the Dune Sim API.

    Mirrors :class:`DuneSimClient` exactly, with awaitable methods and async
    iterators. Construction arguments are identical.

    Example:
        >>> async with AsyncDuneSimClient(api_key="...") as client:
        ...     balances = await client.get_evm_balances("0xd8da...")
    """

    def __init__(self, api_key: str, **kwargs: Any) -> None:
        super().__init__(api_key, **kwargs)
        self._http = httpx.AsyncClient(timeout=self.timeout, headers=self._headers())

    async def __aenter__(self) -> AsyncDuneSimClient:
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the underlying async HTTP connection pool."""
        await self._http.aclose()

    async def _request(
        self,
        path: str,
        model: type[ModelT],
        params: Optional[dict[str, ParamValue]] = None,
    ) -> ModelT:
        query = _serialize_params(params or {})
        url = self._url(path)
        attempt = 0
        while True:
            response = await self._http.get(url, params=query)
            if self._should_retry(response, attempt):
                await asyncio.sleep(self._retry_delay(response, attempt))
                attempt += 1
                continue
            raise_for_status(response)
            return model.model_validate(response.json())

    # -- EVM endpoints ----------------------------------------------------

    async def get_evm_balances(
        self,
        address: str,
        *,
        chain_ids: Optional[Union[str, Sequence[Union[str, int]]]] = None,
        filters: Optional[str] = None,
        asset_class: Optional[str] = None,
        metadata: Optional[Union[str, Sequence[str]]] = None,
        exclude_spam_tokens: Optional[bool] = None,
        exclude_unpriced: Optional[bool] = None,
        historical_prices: Optional[Union[str, Sequence[int]]] = None,
        offset: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> BalancesResponse:
        """Async variant of :meth:`DuneSimClient.get_evm_balances`."""
        return await self._request(
            f"/v1/evm/balances/{address}",
            BalancesResponse,
            {
                "chain_ids": chain_ids,
                "filters": filters,
                "asset_class": asset_class,
                "metadata": metadata,
                "exclude_spam_tokens": exclude_spam_tokens,
                "exclude_unpriced": exclude_unpriced,
                "historical_prices": historical_prices,
                "offset": offset,
                "limit": limit,
            },
        )

    async def get_evm_activity(
        self,
        address: str,
        *,
        chain_ids: Optional[Union[str, Sequence[Union[str, int]]]] = None,
        token_address: Optional[Union[str, Sequence[str]]] = None,
        activity_type: Optional[Sequence[str]] = None,
        asset_type: Optional[Sequence[str]] = None,
        offset: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> ActivityResponse:
        """Async variant of :meth:`DuneSimClient.get_evm_activity`."""
        return await self._request(
            f"/v1/evm/activity/{address}",
            ActivityResponse,
            {
                "chain_ids": chain_ids,
                "token_address": token_address,
                "activity_type": activity_type,
                "asset_type": asset_type,
                "offset": offset,
                "limit": limit,
            },
        )

    async def get_evm_transactions(
        self,
        address: str,
        *,
        chain_ids: Optional[Union[str, Sequence[Union[str, int]]]] = None,
        decode: Optional[bool] = None,
        offset: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> TransactionsResponse:
        """Async variant of :meth:`DuneSimClient.get_evm_transactions`."""
        return await self._request(
            f"/v1/evm/transactions/{address}",
            TransactionsResponse,
            {
                "chain_ids": chain_ids,
                "decode": decode,
                "offset": offset,
                "limit": limit,
            },
        )

    async def get_evm_token_info(
        self,
        address: str,
        *,
        chain_ids: str,
        historical_prices: Optional[Union[str, Sequence[int]]] = None,
        offset: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> TokenInfoResponse:
        """Async variant of :meth:`DuneSimClient.get_evm_token_info`."""
        return await self._request(
            f"/v1/evm/token-info/{address}",
            TokenInfoResponse,
            {
                "chain_ids": chain_ids,
                "historical_prices": historical_prices,
                "offset": offset,
                "limit": limit,
            },
        )

    async def get_evm_token_holders(
        self,
        chain_id: int,
        token_address: str,
        *,
        offset: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> TokenHoldersResponse:
        """Async variant of :meth:`DuneSimClient.get_evm_token_holders`."""
        return await self._request(
            f"/v1/evm/token-holders/{chain_id}/{token_address}",
            TokenHoldersResponse,
            {"offset": offset, "limit": limit},
        )

    async def get_supported_chains(self) -> SupportedChainsResponse:
        """Async variant of :meth:`DuneSimClient.get_supported_chains`."""
        return await self._request("/v1/evm/supported-chains", SupportedChainsResponse)

    # -- SVM endpoints ----------------------------------------------------

    async def get_svm_balances(
        self,
        address: str,
        *,
        chains: Optional[Union[str, Sequence[str]]] = None,
        offset: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> SvmBalancesResponse:
        """Async variant of :meth:`DuneSimClient.get_svm_balances`."""
        return await self._request(
            f"/beta/svm/balances/{address}",
            SvmBalancesResponse,
            {"chains": chains, "offset": offset, "limit": limit},
        )

    async def get_svm_transactions(
        self,
        address: str,
        *,
        offset: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> SvmTransactionsResponse:
        """Async variant of :meth:`DuneSimClient.get_svm_transactions`."""
        return await self._request(
            f"/beta/svm/transactions/{address}",
            SvmTransactionsResponse,
            {"offset": offset, "limit": limit},
        )

    # -- Pagination helpers ----------------------------------------------

    async def iter_evm_balances(self, address: str, **kwargs: Any) -> AsyncIterator[Any]:
        """Async variant of :meth:`DuneSimClient.iter_evm_balances`."""
        kwargs.pop("offset", None)
        offset: Optional[str] = None
        while True:
            page = await self.get_evm_balances(address, offset=offset, **kwargs)
            for item in page.balances:
                yield item
            if not page.next_offset:
                return
            offset = page.next_offset

    async def iter_evm_activity(self, address: str, **kwargs: Any) -> AsyncIterator[Any]:
        """Async variant of :meth:`DuneSimClient.iter_evm_activity`."""
        kwargs.pop("offset", None)
        offset: Optional[str] = None
        while True:
            page = await self.get_evm_activity(address, offset=offset, **kwargs)
            for item in page.activity:
                yield item
            if not page.next_offset:
                return
            offset = page.next_offset

    async def iter_evm_transactions(self, address: str, **kwargs: Any) -> AsyncIterator[Any]:
        """Async variant of :meth:`DuneSimClient.iter_evm_transactions`."""
        kwargs.pop("offset", None)
        offset: Optional[str] = None
        while True:
            page = await self.get_evm_transactions(address, offset=offset, **kwargs)
            for item in page.transactions:
                yield item
            if not page.next_offset:
                return
            offset = page.next_offset

    async def iter_evm_token_holders(
        self, chain_id: int, token_address: str, **kwargs: Any
    ) -> AsyncIterator[Any]:
        """Async variant of :meth:`DuneSimClient.iter_evm_token_holders`."""
        kwargs.pop("offset", None)
        offset: Optional[str] = None
        while True:
            page = await self.get_evm_token_holders(
                chain_id, token_address, offset=offset, **kwargs
            )
            for item in page.holders:
                yield item
            if not page.next_offset:
                return
            offset = page.next_offset
