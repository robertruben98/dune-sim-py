"""Live integration tests against the real Dune Sim API.

These are marked ``integration`` and deselected by default (see ``addopts`` in
pyproject.toml). They run only when a real key is provided:

    SIM_API_KEY=your-key pytest -m integration

Without ``SIM_API_KEY`` set, every test here is skipped.
"""

import os

import pytest

from dune_sim import AsyncDuneSimClient, DuneSimClient

pytestmark = pytest.mark.integration

API_KEY = os.environ.get("SIM_API_KEY")
# vitalik.eth - a well-known, always-populated address.
VITALIK = "0xd8da6bf26964af9d7eed9e03e53415d37aa96045"

requires_key = pytest.mark.skipif(not API_KEY, reason="SIM_API_KEY not set")


@requires_key
def test_live_supported_chains():
    with DuneSimClient(api_key=API_KEY) as client:
        chains = client.get_supported_chains()
    assert len(chains.chains) > 0
    assert any(c.chain_id == 1 for c in chains.chains)


@requires_key
def test_live_evm_balances():
    with DuneSimClient(api_key=API_KEY) as client:
        balances = client.get_evm_balances(VITALIK, limit=10)
    assert balances.wallet_address is not None


@requires_key
async def test_live_async_balances():
    async with AsyncDuneSimClient(api_key=API_KEY) as client:
        balances = await client.get_evm_balances(VITALIK, limit=10)
    assert balances.wallet_address is not None
