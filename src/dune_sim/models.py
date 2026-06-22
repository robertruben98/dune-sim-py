"""Pydantic models for Dune Sim API responses.

Field names and shapes follow the documented contract at
https://docs.sim.dune.com. Every model permits unknown fields (``extra="allow"``)
so a forward-compatible API addition never breaks deserialization. The reserved
Python keyword ``from`` is exposed as ``from_address`` via an alias.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "ActivityFunction",
    "ActivityItem",
    "ActivityResponse",
    "ActivityTokenMetadata",
    "Balance",
    "BalancesResponse",
    "ChainCapability",
    "ContractMetadata",
    "DecodedCall",
    "FunctionInput",
    "HistoricalPrice",
    "Pool",
    "SimModel",
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
    "TokenMetadata",
    "Transaction",
    "TransactionLog",
    "TransactionsResponse",
    "Warning",
]


class SimModel(BaseModel):
    """Base model for all Sim responses.

    Configured to populate fields by name or alias and to retain unknown fields,
    so new API attributes are preserved rather than dropped or rejected.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class Warning(SimModel):
    """A non-fatal warning attached to a response (e.g. a chain was skipped)."""

    code: Optional[str] = Field(default=None, description="Machine-readable warning code.")
    message: Optional[str] = Field(default=None, description="Human-readable warning message.")
    chain_ids: Optional[list[int]] = Field(
        default=None, description="Chain IDs the warning applies to."
    )
    docs_url: Optional[str] = Field(
        default=None, description="Link to documentation explaining the warning."
    )


class HistoricalPrice(SimModel):
    """A token's USD price at a given number of hours in the past."""

    offset_hours: Optional[int] = Field(
        default=None, description="Hours in the past this price corresponds to."
    )
    price_usd: Optional[float] = Field(
        default=None, description="USD price at the historical offset."
    )


class TokenMetadata(SimModel):
    """Optional token metadata returned when requested via the ``metadata`` param."""

    logo: Optional[str] = Field(default=None, description="URL of the token logo image.")
    url: Optional[str] = Field(default=None, description="Project or token website URL.")


class Pool(SimModel):
    """Liquidity-pool context for a balance, returned when requested."""

    pool_type: Optional[str] = Field(default=None, description="Type of liquidity pool.")
    address: Optional[str] = Field(default=None, description="Pool contract address.")
    chain_id: Optional[int] = Field(default=None, description="Chain the pool lives on.")
    tokens: Optional[list[str]] = Field(
        default=None, description="Addresses of tokens in the pool."
    )


class Balance(SimModel):
    """A single token balance held by a wallet on one chain."""

    chain: Optional[str] = Field(default=None, description="Chain name, e.g. ``ethereum``.")
    chain_id: Optional[int] = Field(default=None, description="Numeric chain identifier.")
    address: Optional[str] = Field(
        default=None, description="Token contract address, or ``native`` for the gas token."
    )
    amount: Optional[str] = Field(
        default=None, description="Raw balance in the token's smallest unit (as a string)."
    )
    symbol: Optional[str] = Field(default=None, description="Token ticker symbol.")
    name: Optional[str] = Field(default=None, description="Token name.")
    decimals: Optional[int] = Field(default=None, description="Number of token decimals.")
    price_usd: Optional[float] = Field(default=None, description="Unit price in USD.")
    value_usd: Optional[float] = Field(default=None, description="Total holding value in USD.")
    pool_size: Optional[float] = Field(
        default=None, description="USD size of the token's liquidity pool."
    )
    low_liquidity: Optional[bool] = Field(
        default=None, description="True if the token has low on-chain liquidity."
    )
    historical_prices: Optional[list[HistoricalPrice]] = Field(
        default=None, description="Historical USD prices when requested."
    )
    token_metadata: Optional[TokenMetadata] = Field(
        default=None, description="Extra token metadata when requested."
    )
    pool: Optional[Pool] = Field(default=None, description="Liquidity-pool context when requested.")


class BalancesResponse(SimModel):
    """Response body for ``GET /v1/evm/balances/{address}``."""

    wallet_address: Optional[str] = Field(
        default=None, description="The wallet address that was queried."
    )
    balances: list[Balance] = Field(
        default_factory=list, description="Token balances held by the wallet."
    )
    next_offset: Optional[str] = Field(
        default=None, description="Opaque cursor for the next page, or null when exhausted."
    )
    warnings: Optional[list[Warning]] = Field(
        default=None, description="Non-fatal warnings raised while building the response."
    )
    request_time: Optional[str] = Field(
        default=None, description="Server timestamp when the request was received."
    )
    response_time: Optional[str] = Field(
        default=None, description="Server timestamp when the response was produced."
    )


class ActivityTokenMetadata(SimModel):
    """Token metadata embedded in an activity item."""

    symbol: Optional[str] = Field(default=None, description="Token ticker symbol.")
    decimals: Optional[int] = Field(default=None, description="Number of token decimals.")
    name: Optional[str] = Field(default=None, description="Token name.")
    logo: Optional[str] = Field(default=None, description="Token logo URL.")
    price_usd: Optional[float] = Field(default=None, description="Unit price in USD.")
    pool_size: Optional[float] = Field(default=None, description="USD liquidity-pool size.")
    standard: Optional[str] = Field(default=None, description="Token standard, e.g. ``erc20``.")


class FunctionInput(SimModel):
    """A single decoded argument of a called contract function."""

    name: Optional[str] = Field(default=None, description="Argument name.")
    type: Optional[str] = Field(default=None, description="Solidity argument type.")
    value: Optional[Any] = Field(default=None, description="Decoded argument value.")


class ActivityFunction(SimModel):
    """Decoded contract function call attached to an activity item."""

    signature: Optional[str] = Field(default=None, description="4-byte function signature.")
    name: Optional[str] = Field(default=None, description="Function name.")
    inputs: Optional[list[FunctionInput]] = Field(
        default=None, description="Decoded function arguments."
    )


class ContractMetadata(SimModel):
    """Metadata about the contract involved in an activity item."""

    name: Optional[str] = Field(default=None, description="Contract name.")


class ActivityItem(SimModel):
    """A single on-chain activity event for a wallet."""

    chain_id: Optional[int] = Field(default=None, description="Numeric chain identifier.")
    block_number: Optional[int] = Field(default=None, description="Block number of the event.")
    block_time: Optional[str] = Field(default=None, description="ISO-8601 block timestamp.")
    tx_hash: Optional[str] = Field(default=None, description="Transaction hash.")
    type: Optional[str] = Field(
        default=None,
        description="Activity type: approve, burn, call, mint, receive, send, swap, transfer.",
    )
    asset_type: Optional[str] = Field(
        default=None, description="Asset standard: native, erc20, erc721, erc1155."
    )
    token_address: Optional[str] = Field(default=None, description="Token contract address.")
    from_address: Optional[str] = Field(
        default=None, alias="from", description="Sender address (aliased from ``from``)."
    )
    to: Optional[str] = Field(default=None, description="Recipient address.")
    value: Optional[str] = Field(default=None, description="Raw transferred amount as a string.")
    value_usd: Optional[float] = Field(default=None, description="USD value of the transfer.")
    id: Optional[str] = Field(default=None, description="Opaque activity identifier.")
    spender: Optional[str] = Field(
        default=None, description="Approved spender address for approve events."
    )
    token_metadata: Optional[ActivityTokenMetadata] = Field(
        default=None, description="Token metadata for the asset involved."
    )
    function: Optional[ActivityFunction] = Field(
        default=None, description="Decoded contract function call, when applicable."
    )
    contract_metadata: Optional[ContractMetadata] = Field(
        default=None, description="Metadata about the contract involved."
    )
    from_token_address: Optional[str] = Field(
        default=None, description="Source token address for swaps."
    )
    from_token_value: Optional[str] = Field(
        default=None, description="Raw source token amount for swaps."
    )
    from_token_metadata: Optional[ActivityTokenMetadata] = Field(
        default=None, description="Source token metadata for swaps."
    )
    to_token_address: Optional[str] = Field(
        default=None, description="Destination token address for swaps."
    )
    to_token_value: Optional[str] = Field(
        default=None, description="Raw destination token amount for swaps."
    )
    to_token_metadata: Optional[ActivityTokenMetadata] = Field(
        default=None, description="Destination token metadata for swaps."
    )


class ActivityResponse(SimModel):
    """Response body for ``GET /v1/evm/activity/{address}``."""

    activity: list[ActivityItem] = Field(
        default_factory=list, description="Chronological list of activity events."
    )
    warnings: Optional[list[Warning]] = Field(
        default=None, description="Non-fatal warnings raised while building the response."
    )
    next_offset: Optional[str] = Field(
        default=None, description="Opaque cursor for the next page, or null when exhausted."
    )


class DecodedCall(SimModel):
    """A decoded transaction call or log."""

    name: Optional[str] = Field(default=None, description="Decoded function or event name.")
    inputs: Optional[list[FunctionInput]] = Field(default=None, description="Decoded arguments.")


class TransactionLog(SimModel):
    """A single log emitted by a transaction (present when ``decode=true``)."""

    address: Optional[str] = Field(default=None, description="Emitting contract address.")
    data: Optional[str] = Field(default=None, description="Raw log data.")
    topics: Optional[list[str]] = Field(default=None, description="Indexed log topics.")
    decoded: Optional[DecodedCall] = Field(
        default=None, description="Decoded event, when available."
    )


class Transaction(SimModel):
    """A single transaction involving the queried wallet."""

    address: Optional[str] = Field(default=None, description="The queried wallet address.")
    block_hash: Optional[str] = Field(default=None, description="Hash of the containing block.")
    block_number: Optional[str] = Field(default=None, description="Block number as a string.")
    block_time: Optional[str] = Field(default=None, description="ISO-8601 block timestamp.")
    block_version: Optional[int] = Field(default=None, description="Block version.")
    chain: Optional[str] = Field(default=None, description="Chain name.")
    from_address: Optional[str] = Field(
        default=None, alias="from", description="Sender address (aliased from ``from``)."
    )
    to: Optional[str] = Field(default=None, description="Recipient address.")
    data: Optional[str] = Field(default=None, description="Raw input data (hex).")
    gas_price: Optional[str] = Field(default=None, description="Gas price as a string.")
    hash: Optional[str] = Field(default=None, description="Transaction hash.")
    index: Optional[str] = Field(default=None, description="Transaction index within the block.")
    max_fee_per_gas: Optional[str] = Field(default=None, description="EIP-1559 max fee per gas.")
    max_priority_fee_per_gas: Optional[str] = Field(
        default=None, description="EIP-1559 max priority fee per gas."
    )
    nonce: Optional[str] = Field(default=None, description="Sender nonce as a string.")
    transaction_type: Optional[str] = Field(default=None, description="Transaction type.")
    value: Optional[str] = Field(default=None, description="Transferred native value (hex/string).")
    decoded: Optional[DecodedCall] = Field(
        default=None, description="Decoded call when ``decode=true``."
    )
    logs: Optional[list[TransactionLog]] = Field(
        default=None, description="Decoded logs when ``decode=true``."
    )


class TransactionsResponse(SimModel):
    """Response body for ``GET /v1/evm/transactions/{address}``."""

    wallet_address: Optional[str] = Field(
        default=None, description="The wallet address that was queried."
    )
    transactions: list[Transaction] = Field(
        default_factory=list, description="Transactions involving the wallet."
    )
    next_offset: Optional[str] = Field(
        default=None, description="Opaque cursor for the next page, or null when exhausted."
    )
    request_time: Optional[str] = Field(default=None, description="Server receive timestamp.")
    response_time: Optional[str] = Field(default=None, description="Server response timestamp.")
    warnings: Optional[list[Warning]] = Field(
        default=None, description="Non-fatal warnings raised while building the response."
    )


class TokenInfo(SimModel):
    """Pricing and supply information for a token on one chain."""

    chain: Optional[str] = Field(default=None, description="Chain name.")
    chain_id: Optional[int] = Field(default=None, description="Numeric chain identifier.")
    symbol: Optional[str] = Field(default=None, description="Token ticker symbol.")
    name: Optional[str] = Field(default=None, description="Token name.")
    decimals: Optional[int] = Field(default=None, description="Number of token decimals.")
    price_usd: Optional[float] = Field(default=None, description="Unit price in USD.")
    historical_prices: Optional[list[HistoricalPrice]] = Field(
        default=None, description="Historical USD prices when requested."
    )
    total_supply: Optional[str] = Field(default=None, description="Total token supply as a string.")
    market_cap: Optional[float] = Field(default=None, description="Market capitalization in USD.")
    logo: Optional[str] = Field(default=None, description="Token logo URL.")


class TokenInfoResponse(SimModel):
    """Response body for ``GET /v1/evm/token-info/{address}``."""

    contract_address: Optional[str] = Field(
        default=None, description="The token contract address queried (or ``native``)."
    )
    tokens: list[TokenInfo] = Field(
        default_factory=list, description="Per-chain token information."
    )
    warnings: Optional[list[Warning]] = Field(
        default=None, description="Non-fatal warnings raised while building the response."
    )
    next_offset: Optional[str] = Field(
        default=None, description="Opaque cursor for the next page, or null when exhausted."
    )


class TokenHolder(SimModel):
    """A single holder of a token."""

    wallet_address: Optional[str] = Field(default=None, description="Holder wallet address.")
    balance: Optional[str] = Field(
        default=None, description="Raw token balance in the smallest unit (as a string)."
    )
    first_acquired: Optional[str] = Field(
        default=None, description="ISO-8601 timestamp the holder first acquired the token."
    )
    has_initiated_transfer: Optional[bool] = Field(
        default=None, description="Whether the holder has ever sent the token."
    )


class TokenHoldersResponse(SimModel):
    """Response body for ``GET /v1/evm/token-holders/{chain_id}/{address}``."""

    token_address: Optional[str] = Field(default=None, description="The token contract queried.")
    chain_id: Optional[int] = Field(default=None, description="The chain queried.")
    holders: list[TokenHolder] = Field(
        default_factory=list, description="Token holders ordered by balance."
    )
    next_offset: Optional[str] = Field(
        default=None, description="Opaque cursor for the next page, or null when exhausted."
    )


class ChainCapability(SimModel):
    """Whether a chain supports a particular Sim endpoint family."""

    supported: Optional[bool] = Field(
        default=None, description="True if the endpoint is supported on this chain."
    )


class SupportedChain(SimModel):
    """A chain supported by the Sim API and its capabilities."""

    name: Optional[str] = Field(default=None, description="Chain name.")
    chain_id: Optional[int] = Field(default=None, description="Numeric chain identifier.")
    tags: list[str] = Field(default_factory=list, description="Chain tags, e.g. ``default``.")
    balances: Optional[ChainCapability] = Field(
        default=None, description="Balances endpoint support."
    )
    transactions: Optional[ChainCapability] = Field(
        default=None, description="Transactions endpoint support."
    )
    activity: Optional[ChainCapability] = Field(
        default=None, description="Activity endpoint support."
    )
    token_info: Optional[ChainCapability] = Field(
        default=None, description="Token-info endpoint support."
    )
    token_holders: Optional[ChainCapability] = Field(
        default=None, description="Token-holders endpoint support."
    )
    collectibles: Optional[ChainCapability] = Field(
        default=None, description="Collectibles endpoint support."
    )
    defi_positions: Optional[ChainCapability] = Field(
        default=None, description="DeFi-positions endpoint support."
    )


class SupportedChainsResponse(SimModel):
    """Response body for ``GET /v1/evm/supported-chains``."""

    chains: list[SupportedChain] = Field(
        default_factory=list, description="Supported chains and their capabilities."
    )


class SvmBalance(SimModel):
    """A single SVM (Solana / Eclipse) token balance."""

    chain: Optional[str] = Field(default=None, description="Chain name: ``solana`` or ``eclipse``.")
    address: Optional[str] = Field(
        default=None, description="Token mint address, or ``native`` for SOL."
    )
    amount: Optional[str] = Field(default=None, description="Raw balance in the smallest unit.")
    balance: Optional[str] = Field(default=None, description="Human-readable balance.")
    raw_balance: Optional[str] = Field(default=None, description="Raw balance as a string.")
    value_usd: Optional[float] = Field(default=None, description="Total holding value in USD.")
    program_id: Optional[str] = Field(default=None, description="SPL program ID, if applicable.")
    decimals: Optional[int] = Field(default=None, description="Number of token decimals.")
    total_supply: Optional[str] = Field(default=None, description="Total token supply as a string.")
    name: Optional[str] = Field(default=None, description="Token name.")
    symbol: Optional[str] = Field(default=None, description="Token ticker symbol.")
    uri: Optional[str] = Field(default=None, description="Token metadata URI.")
    price_usd: Optional[float] = Field(default=None, description="Unit price in USD.")
    liquidity_usd: Optional[float] = Field(default=None, description="USD liquidity for the token.")
    pool_type: Optional[str] = Field(default=None, description="Liquidity-pool type.")
    pool_address: Optional[str] = Field(default=None, description="Liquidity-pool address.")
    mint_authority: Optional[str] = Field(default=None, description="Mint authority address.")


class SvmBalancesResponse(SimModel):
    """Response body for ``GET /beta/svm/balances/{address}``."""

    processing_time_ms: Optional[float] = Field(
        default=None, description="Server processing time in milliseconds."
    )
    wallet_address: Optional[str] = Field(default=None, description="The wallet address queried.")
    next_offset: Optional[str] = Field(
        default=None, description="Opaque cursor for the next page, or null when exhausted."
    )
    balances_count: Optional[int] = Field(
        default=None, description="Number of balances in this page."
    )
    balances: list[SvmBalance] = Field(
        default_factory=list, description="Token balances held by the wallet."
    )


class SvmTransaction(SimModel):
    """A single SVM transaction involving the queried wallet."""

    address: Optional[str] = Field(default=None, description="The wallet address queried.")
    block_slot: Optional[int] = Field(default=None, description="Solana block slot.")
    block_time: Optional[int] = Field(default=None, description="Block time (microseconds).")
    chain: Optional[str] = Field(default=None, description="Chain name.")
    raw_transaction: Optional[dict[str, Any]] = Field(
        default=None, description="Raw transaction object as returned by the node."
    )


class SvmTransactionsResponse(SimModel):
    """Response body for ``GET /beta/svm/transactions/{address}``."""

    next_offset: Optional[str] = Field(
        default=None, description="Opaque cursor for the next page, or null when exhausted."
    )
    transactions: list[SvmTransaction] = Field(
        default_factory=list, description="Transactions involving the wallet."
    )
