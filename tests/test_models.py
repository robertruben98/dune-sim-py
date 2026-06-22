"""Tests that the pydantic models parse the documented example payloads.

Each fixture is taken from the official Sim API docs (docs.sim.dune.com) so these
double as a contract check against the documented response shapes.
"""

from dune_sim.models import (
    ActivityResponse,
    BalancesResponse,
    SupportedChainsResponse,
    SvmBalancesResponse,
    SvmTransactionsResponse,
    TokenHoldersResponse,
    TokenInfoResponse,
    TransactionsResponse,
)


def test_balances_response_parses_documented_example():
    payload = {
        "wallet_address": "0xd8da6bf26964af9d7eed9e03e53415d37aa96045",
        "balances": [
            {
                "chain": "ethereum",
                "chain_id": 1,
                "address": "native",
                "amount": "783060447601684229",
                "symbol": "ETH",
                "decimals": 18,
                "price_usd": 3779.154092,
                "value_usd": 2959.30609483726,
            }
        ],
        "next_offset": "opaque-pagination-token",
        "request_time": "2025-08-13T10:31:08Z",
        "response_time": "2025-08-13T10:31:08Z",
    }

    parsed = BalancesResponse.model_validate(payload)

    assert parsed.wallet_address == "0xd8da6bf26964af9d7eed9e03e53415d37aa96045"
    assert parsed.next_offset == "opaque-pagination-token"
    token = parsed.balances[0]
    assert token.symbol == "ETH"
    assert token.chain_id == 1
    assert token.decimals == 18
    assert token.value_usd == 2959.30609483726


def test_balances_response_allows_unknown_fields():
    # extra="allow": the API may add fields without breaking the client.
    parsed = BalancesResponse.model_validate(
        {"wallet_address": "0xabc", "balances": [], "brand_new_field": 123}
    )
    assert parsed.balances == []


def test_activity_response_parses_documented_example():
    payload = {
        "activity": [
            {
                "chain_id": 8453,
                "block_number": 26635101,
                "block_time": "2025-02-20T13:52:29+00:00",
                "tx_hash": "0x184544c8d67a0cbed0a3f04abe5f958b96635e8c743c070f70e24b1c06cd1aa6",
                "type": "receive",
                "asset_type": "erc20",
                "token_address": "0xf92e740ad181b13a484a886ed16aa6d32d71b19a",
                "from": "0xd152f549545093347a162dce210e7293f1452150",
                "value": "123069652500000000000",
                "value_usd": 0.14017463965013963,
                "token_metadata": {
                    "symbol": "ENT",
                    "decimals": 18,
                    "price_usd": 0.001138986230989314,
                    "pool_size": 5.2274054439382835,
                },
            }
        ],
        "next_offset": "KgAAAAAAAAAweDQ4ZDAwNGE2YzE3NWRiMzMxZTk5YmVhZjY0NDIzYjMwOTgzNTdhZTc",
    }

    parsed = ActivityResponse.model_validate(payload)

    item = parsed.activity[0]
    assert item.type == "receive"
    assert item.chain_id == 8453
    # `from` is a Python keyword; ensure it is aliased.
    assert item.from_address == "0xd152f549545093347a162dce210e7293f1452150"
    assert item.token_metadata is not None
    assert item.token_metadata.symbol == "ENT"


def test_transactions_response_parses_documented_example():
    payload = {
        "wallet_address": "0x7532cd0651030d3dc80b28199a125fc9f5ac80fa",
        "transactions": [
            {
                "address": "0x7532cd0651030d3dc80b28199a125fc9f5ac80fa",
                "block_hash": "0x745bdf699cee1fef27b9304be43a2435c744500ef455cc6b7dfb4c34417601a2",
                "block_number": "30819446",
                "block_time": "2025-05-28T10:30:39Z",
                "chain": "base",
                "from": "0x7532cd0651030d3dc80b28199a125fc9f5ac80fa",
                "to": "0x6ff5693b99212da76ad316178a184ab56d299b43",
                "value": "0x0",
            }
        ],
        "next_offset": "QBHrUqbdBQDkBwAAAAAAACHjyAAAAAAAAAAAAAAAAAACAAAAAAAAAA",
    }

    parsed = TransactionsResponse.model_validate(payload)

    txn = parsed.transactions[0]
    assert txn.chain == "base"
    assert txn.from_address == "0x7532cd0651030d3dc80b28199a125fc9f5ac80fa"
    assert txn.to == "0x6ff5693b99212da76ad316178a184ab56d299b43"
    assert txn.value == "0x0"


def test_token_info_response_parses_documented_example():
    payload = {
        "contract_address": "native",
        "tokens": [
            {
                "chain_id": 1,
                "chain": "ethereum",
                "price_usd": 3900.777068,
                "symbol": "ETH",
                "name": "Ethereum",
                "decimals": 18,
                "logo": "https://api.sim.dune.com/beta/token/logo/1",
            }
        ],
    }

    parsed = TokenInfoResponse.model_validate(payload)

    assert parsed.contract_address == "native"
    assert parsed.tokens[0].symbol == "ETH"
    assert parsed.tokens[0].name == "Ethereum"


def test_token_holders_response_parses_documented_example():
    payload = {
        "token_address": "0x63706e401c06ac8513145b7687a14804d17f814b",
        "chain_id": 8453,
        "holders": [
            {
                "wallet_address": "0x4a79b0168296c0ef7b8f314973b82ad406a29f1b",
                "balance": "13794442047246482254818",
                "first_acquired": "2025-02-06T15:11:07+00:00",
                "has_initiated_transfer": False,
            }
        ],
        "next_offset": "eyJwYWdlIjoyLCJsaW1pdCI6Mn0=",
    }

    parsed = TokenHoldersResponse.model_validate(payload)

    assert parsed.chain_id == 8453
    holder = parsed.holders[0]
    assert holder.wallet_address == "0x4a79b0168296c0ef7b8f314973b82ad406a29f1b"
    assert holder.has_initiated_transfer is False


def test_supported_chains_response_parses_documented_example():
    payload = {
        "chains": [
            {
                "name": "ethereum",
                "chain_id": 1,
                "tags": ["default", "mainnet"],
                "balances": {"supported": True},
                "transactions": {"supported": True},
                "activity": {"supported": True},
                "token_info": {"supported": True},
                "token_holders": {"supported": True},
                "collectibles": {"supported": True},
            }
        ]
    }

    parsed = SupportedChainsResponse.model_validate(payload)

    chain = parsed.chains[0]
    assert chain.name == "ethereum"
    assert chain.chain_id == 1
    assert "default" in chain.tags
    assert chain.balances is not None
    assert chain.balances.supported is True


def test_svm_balances_response_parses_documented_example():
    payload = {
        "processing_time_ms": 12,
        "wallet_address": "DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG5CNSKK",
        "next_offset": "abc",
        "balances_count": 1,
        "balances": [
            {
                "chain": "solana",
                "address": "native",
                "amount": "1000000000",
                "balance": "1.0",
                "decimals": 9,
                "name": "Solana",
                "symbol": "SOL",
                "price_usd": 150.0,
                "value_usd": 150.0,
                "program_id": None,
            }
        ],
    }

    parsed = SvmBalancesResponse.model_validate(payload)

    assert parsed.wallet_address == "DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG5CNSKK"
    assert parsed.balances[0].symbol == "SOL"
    assert parsed.balances[0].program_id is None


def test_svm_transactions_response_parses_documented_example():
    payload = {
        "next_offset": "eyJibG9ja190aW1lIjoxNjgwMDAwMDAwLCJpbmRleCI6MH0=",
        "transactions": [
            {
                "address": "DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG5CNSKK",
                "block_slot": 123456789,
                "block_time": 1680000000000000,
                "chain": "solana",
                "raw_transaction": {"foo": "bar"},
            }
        ],
    }

    parsed = SvmTransactionsResponse.model_validate(payload)

    txn = parsed.transactions[0]
    assert txn.block_slot == 123456789
    assert txn.chain == "solana"
    assert txn.raw_transaction == {"foo": "bar"}
