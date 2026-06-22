"""Tests for the synchronous DuneSimClient using respx HTTP mocks (no network)."""

import httpx
import pytest
import respx

from dune_sim import DuneSimClient
from dune_sim.errors import AuthenticationError, RateLimitError

BASE = "https://api.sim.dune.com"
ADDR = "0xd8da6bf26964af9d7eed9e03e53415d37aa96045"


@pytest.fixture
def client():
    c = DuneSimClient(api_key="test-key", max_retries=2, backoff_factor=0.0)
    yield c
    c.close()


@respx.mock
def test_get_evm_balances_hits_correct_path_and_sends_api_key(client):
    route = respx.get(f"{BASE}/v1/evm/balances/{ADDR}").mock(
        return_value=httpx.Response(200, json={"wallet_address": ADDR, "balances": []})
    )

    result = client.get_evm_balances(ADDR)

    assert route.called
    sent = route.calls.last.request
    assert sent.headers["X-Sim-Api-Key"] == "test-key"
    assert result.wallet_address == ADDR


@respx.mock
def test_custom_api_key_header_name_is_used():
    c = DuneSimClient(api_key="k", api_key_header="Authorization")
    respx.get(f"{BASE}/v1/evm/supported-chains").mock(
        return_value=httpx.Response(200, json={"chains": []})
    )

    c.get_supported_chains()

    sent = respx.calls.last.request
    assert sent.headers["Authorization"] == "k"
    assert "X-Sim-Api-Key" not in sent.headers
    c.close()


@respx.mock
def test_custom_base_url_is_used():
    c = DuneSimClient(api_key="k", base_url="https://proxy.example.com/sim")
    route = respx.get("https://proxy.example.com/sim/v1/evm/supported-chains").mock(
        return_value=httpx.Response(200, json={"chains": []})
    )

    c.get_supported_chains()

    assert route.called
    c.close()


@respx.mock
def test_balances_query_params_are_serialized(client):
    route = respx.get(f"{BASE}/v1/evm/balances/{ADDR}").mock(
        return_value=httpx.Response(200, json={"wallet_address": ADDR, "balances": []})
    )

    client.get_evm_balances(
        ADDR,
        chain_ids=["1", "137"],
        exclude_spam_tokens=True,
        limit=50,
        offset="cursor123",
    )

    params = route.calls.last.request.url.params
    assert params["chain_ids"] == "1,137"
    assert params["exclude_spam_tokens"] == "true"
    assert params["limit"] == "50"
    assert params["offset"] == "cursor123"


@respx.mock
def test_none_query_params_are_omitted(client):
    route = respx.get(f"{BASE}/v1/evm/balances/{ADDR}").mock(
        return_value=httpx.Response(200, json={"wallet_address": ADDR, "balances": []})
    )

    client.get_evm_balances(ADDR)

    assert "limit" not in route.calls.last.request.url.params
    assert "chain_ids" not in route.calls.last.request.url.params


@respx.mock
def test_get_evm_activity(client):
    respx.get(f"{BASE}/v1/evm/activity/{ADDR}").mock(
        return_value=httpx.Response(200, json={"activity": [{"type": "send"}]})
    )

    result = client.get_evm_activity(ADDR, limit=20)

    assert result.activity[0].type == "send"


@respx.mock
def test_get_evm_transactions(client):
    respx.get(f"{BASE}/v1/evm/transactions/{ADDR}").mock(
        return_value=httpx.Response(200, json={"transactions": [{"chain": "base"}]})
    )

    result = client.get_evm_transactions(ADDR, decode=True)

    assert result.transactions[0].chain == "base"
    assert respx.calls.last.request.url.params["decode"] == "true"


@respx.mock
def test_get_evm_token_info_requires_chain_ids(client):
    route = respx.get(f"{BASE}/v1/evm/token-info/native").mock(
        return_value=httpx.Response(200, json={"contract_address": "native", "tokens": []})
    )

    client.get_evm_token_info("native", chain_ids="1")

    assert route.calls.last.request.url.params["chain_ids"] == "1"


@respx.mock
def test_get_evm_token_holders_builds_chain_scoped_path(client):
    token = "0x63706e401c06ac8513145b7687a14804d17f814b"
    route = respx.get(f"{BASE}/v1/evm/token-holders/8453/{token}").mock(
        return_value=httpx.Response(
            200, json={"token_address": token, "chain_id": 8453, "holders": []}
        )
    )

    result = client.get_evm_token_holders(8453, token, limit=100)

    assert route.called
    assert result.chain_id == 8453


@respx.mock
def test_get_svm_balances_uses_beta_path(client):
    svm_addr = "DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG5CNSKK"
    route = respx.get(f"{BASE}/beta/svm/balances/{svm_addr}").mock(
        return_value=httpx.Response(200, json={"wallet_address": svm_addr, "balances": []})
    )

    client.get_svm_balances(svm_addr, chains="solana")

    assert route.called
    assert route.calls.last.request.url.params["chains"] == "solana"


@respx.mock
def test_get_svm_transactions_uses_beta_path(client):
    svm_addr = "DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG5CNSKK"
    route = respx.get(f"{BASE}/beta/svm/transactions/{svm_addr}").mock(
        return_value=httpx.Response(200, json={"transactions": []})
    )

    client.get_svm_transactions(svm_addr)

    assert route.called


@respx.mock
def test_401_raises_authentication_error(client):
    respx.get(f"{BASE}/v1/evm/balances/{ADDR}").mock(
        return_value=httpx.Response(401, json={"error": "invalid API Key"})
    )

    with pytest.raises(AuthenticationError):
        client.get_evm_balances(ADDR)


@respx.mock
def test_retries_on_429_then_succeeds(client):
    route = respx.get(f"{BASE}/v1/evm/balances/{ADDR}")
    route.side_effect = [
        httpx.Response(429, json={"error": "slow down"}),
        httpx.Response(200, json={"wallet_address": ADDR, "balances": []}),
    ]

    result = client.get_evm_balances(ADDR)

    assert result.wallet_address == ADDR
    assert route.call_count == 2


@respx.mock
def test_429_exhausts_retries_and_raises(client):
    respx.get(f"{BASE}/v1/evm/balances/{ADDR}").mock(
        return_value=httpx.Response(429, json={"error": "slow down"})
    )

    with pytest.raises(RateLimitError):
        client.get_evm_balances(ADDR)


@respx.mock
def test_retries_on_500_then_succeeds(client):
    route = respx.get(f"{BASE}/v1/evm/supported-chains")
    route.side_effect = [
        httpx.Response(500, text="boom"),
        httpx.Response(200, json={"chains": []}),
    ]

    client.get_supported_chains()

    assert route.call_count == 2


@respx.mock
def test_context_manager_closes_client():
    with DuneSimClient(api_key="k") as c:
        respx.get(f"{BASE}/v1/evm/supported-chains").mock(
            return_value=httpx.Response(200, json={"chains": []})
        )
        c.get_supported_chains()
    assert c._http.is_closed


def test_empty_api_key_raises_value_error():
    with pytest.raises(ValueError, match="api_key"):
        DuneSimClient(api_key="")


@respx.mock
def test_iter_evm_balances_follows_pagination(client):
    route = respx.get(f"{BASE}/v1/evm/balances/{ADDR}")
    route.side_effect = [
        httpx.Response(
            200,
            json={
                "wallet_address": ADDR,
                "balances": [{"symbol": "ETH"}],
                "next_offset": "page2",
            },
        ),
        httpx.Response(
            200,
            json={"wallet_address": ADDR, "balances": [{"symbol": "USDC"}], "next_offset": None},
        ),
    ]

    symbols = [b.symbol for b in client.iter_evm_balances(ADDR)]

    assert symbols == ["ETH", "USDC"]
    assert route.call_count == 2
    # Second request must carry the offset cursor from the first response.
    assert route.calls[1].request.url.params["offset"] == "page2"
