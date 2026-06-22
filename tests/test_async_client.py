"""Tests for the asynchronous AsyncDuneSimClient using respx HTTP mocks."""

import httpx
import pytest
import respx

from dune_sim import AsyncDuneSimClient
from dune_sim.errors import AuthenticationError, RateLimitError

BASE = "https://api.sim.dune.com"
ADDR = "0xd8da6bf26964af9d7eed9e03e53415d37aa96045"


@respx.mock
async def test_async_get_evm_balances_sends_api_key():
    route = respx.get(f"{BASE}/v1/evm/balances/{ADDR}").mock(
        return_value=httpx.Response(200, json={"wallet_address": ADDR, "balances": []})
    )

    async with AsyncDuneSimClient(api_key="test-key") as client:
        result = await client.get_evm_balances(ADDR)

    assert route.called
    assert route.calls.last.request.headers["X-Sim-Api-Key"] == "test-key"
    assert result.wallet_address == ADDR


@respx.mock
async def test_async_get_supported_chains():
    respx.get(f"{BASE}/v1/evm/supported-chains").mock(
        return_value=httpx.Response(200, json={"chains": [{"name": "ethereum", "chain_id": 1}]})
    )

    async with AsyncDuneSimClient(api_key="k") as client:
        result = await client.get_supported_chains()

    assert result.chains[0].name == "ethereum"


@respx.mock
async def test_async_get_svm_transactions_uses_beta_path():
    svm_addr = "DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG5CNSKK"
    route = respx.get(f"{BASE}/beta/svm/transactions/{svm_addr}").mock(
        return_value=httpx.Response(200, json={"transactions": []})
    )

    async with AsyncDuneSimClient(api_key="k") as client:
        await client.get_svm_transactions(svm_addr)

    assert route.called


@respx.mock
async def test_async_401_raises_authentication_error():
    respx.get(f"{BASE}/v1/evm/balances/{ADDR}").mock(
        return_value=httpx.Response(401, json={"error": "invalid API Key"})
    )

    async with AsyncDuneSimClient(api_key="bad") as client:
        with pytest.raises(AuthenticationError):
            await client.get_evm_balances(ADDR)


@respx.mock
async def test_async_retries_on_429_then_succeeds():
    route = respx.get(f"{BASE}/v1/evm/balances/{ADDR}")
    route.side_effect = [
        httpx.Response(429, json={"error": "slow down"}),
        httpx.Response(200, json={"wallet_address": ADDR, "balances": []}),
    ]

    async with AsyncDuneSimClient(api_key="k", backoff_factor=0.0) as client:
        result = await client.get_evm_balances(ADDR)

    assert result.wallet_address == ADDR
    assert route.call_count == 2


@respx.mock
async def test_async_429_exhausts_retries_and_raises():
    respx.get(f"{BASE}/v1/evm/balances/{ADDR}").mock(
        return_value=httpx.Response(429, json={"error": "slow down"})
    )

    async with AsyncDuneSimClient(api_key="k", max_retries=1, backoff_factor=0.0) as client:
        with pytest.raises(RateLimitError):
            await client.get_evm_balances(ADDR)


@respx.mock
async def test_async_iter_evm_balances_follows_pagination():
    route = respx.get(f"{BASE}/v1/evm/balances/{ADDR}")
    route.side_effect = [
        httpx.Response(
            200,
            json={"wallet_address": ADDR, "balances": [{"symbol": "ETH"}], "next_offset": "p2"},
        ),
        httpx.Response(
            200,
            json={"wallet_address": ADDR, "balances": [{"symbol": "USDC"}], "next_offset": None},
        ),
    ]

    async with AsyncDuneSimClient(api_key="k") as client:
        symbols = [b.symbol async for b in client.iter_evm_balances(ADDR)]

    assert symbols == ["ETH", "USDC"]
    assert route.calls[1].request.url.params["offset"] == "p2"
