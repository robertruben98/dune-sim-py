"""Typed Python client for the Dune Sim API.

Dune Sim provides real-time, multi-chain on-chain data across 60+ EVM chains and
Solana. This package exposes a synchronous :class:`DuneSimClient` and an
asynchronous :class:`AsyncDuneSimClient`, plus pydantic models for every
documented response and a typed exception hierarchy.

Example:
    >>> from dune_sim import DuneSimClient
    >>> with DuneSimClient(api_key="...") as client:
    ...     balances = client.get_evm_balances("0xd8da...")
"""

from .client import AsyncDuneSimClient, DuneSimClient
from .errors import (
    APIError,
    AuthenticationError,
    BadRequestError,
    DuneSimError,
    ForbiddenError,
    NotFoundError,
    QuotaExceededError,
    RateLimitError,
    ServerError,
)
from .models import (
    ActivityItem,
    ActivityResponse,
    Balance,
    BalancesResponse,
    SupportedChain,
    SupportedChainsResponse,
    SvmBalance,
    SvmBalancesResponse,
    SvmTransaction,
    SvmTransactionsResponse,
    TokenHolder,
    TokenHoldersResponse,
    TokenInfo,
    TokenInfoResponse,
    Transaction,
    TransactionsResponse,
)

__version__ = "0.1.0"

__all__ = [
    "APIError",
    "ActivityItem",
    "ActivityResponse",
    "AsyncDuneSimClient",
    "AuthenticationError",
    "BadRequestError",
    "Balance",
    # Models
    "BalancesResponse",
    # Clients
    "DuneSimClient",
    # Errors
    "DuneSimError",
    "ForbiddenError",
    "NotFoundError",
    "QuotaExceededError",
    "RateLimitError",
    "ServerError",
    "SupportedChain",
    "SupportedChainsResponse",
    "SvmBalance",
    "SvmBalancesResponse",
    "SvmTransaction",
    "SvmTransactionsResponse",
    "TokenHolder",
    "TokenHoldersResponse",
    "TokenInfo",
    "TokenInfoResponse",
    "Transaction",
    "TransactionsResponse",
    "__version__",
]
