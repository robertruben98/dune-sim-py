# dune-sim-py

[![CI](https://github.com/robertruben98/dune-sim-py/actions/workflows/ci.yml/badge.svg)](https://github.com/robertruben98/dune-sim-py/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/dune-sim-py.svg)](https://pypi.org/project/dune-sim-py/)
[![Python versions](https://img.shields.io/pypi/pyversions/dune-sim-py.svg)](https://pypi.org/project/dune-sim-py/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Checked with mypy](https://img.shields.io/badge/mypy-checked-blue.svg)](https://mypy-lang.org/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

A typed, batteries-included Python client for the [Dune Sim API](https://docs.sim.dune.com)
— real-time, multi-chain on-chain data across 60+ EVM chains and Solana.

> **Note:** Dune Sim is distinct from Dune Analytics. This library targets the Sim
> real-time data API at `https://api.sim.dune.com`, not the Dune Analytics query API.

## Features

- Sync (`DuneSimClient`) and async (`AsyncDuneSimClient`) clients sharing one interface.
- Full [pydantic v2](https://docs.pydantic.dev/) models for every documented response.
- EVM endpoints: balances, activity, transactions, token info, token holders, supported chains.
- SVM (Solana / Eclipse) endpoints: balances, transactions.
- Automatic retry with exponential backoff on `429` and `5xx`, honoring `Retry-After`.
- Typed errors mapped from HTTP status codes; handles both JSON and plain-text error bodies.
- Cursor-based pagination helpers that transparently follow `next_offset`.
- Ships with `py.typed`; fully type-checked under `mypy --strict`.

## Installation

```bash
pip install dune-sim-py
```

Requires Python 3.9+.

## Authentication

Every request requires a Sim API key sent in the `X-Sim-Api-Key` header. Get a free
key from the [Sim dashboard](https://sim.dune.com). The API returns `401` without it.

## Quickstart

```python
from dune_sim import DuneSimClient

client = DuneSimClient(api_key="YOUR_SIM_API_KEY")

# Token balances for a wallet across default chains
balances = client.get_evm_balances("0xd8da6bf26964af9d7eed9e03e53415d37aa96045")
for token in balances.balances:
    print(token.symbol, token.amount, token.value_usd)

# Supported chains
chains = client.get_supported_chains()
print([c.name for c in chains.chains])

client.close()
```

Use it as a context manager to close the underlying HTTP connection automatically:

```python
with DuneSimClient(api_key="YOUR_SIM_API_KEY") as client:
    activity = client.get_evm_activity("0xd8da...", limit=20)
```

### Async

```python
import asyncio
from dune_sim import AsyncDuneSimClient

async def main():
    async with AsyncDuneSimClient(api_key="YOUR_SIM_API_KEY") as client:
        txns = await client.get_evm_transactions("0x7532cd0651030d3dc80b28199a125fc9f5ac80fa")
        print(txns.next_offset)

asyncio.run(main())
```

### Pagination

Every list endpoint returns an opaque `next_offset` cursor. Pass it back as `offset`
to fetch the next page, or use the built-in iterator helpers:

```python
for token in client.iter_evm_balances("0xd8da6bf26964af9d7eed9e03e53415d37aa96045"):
    print(token.symbol)
```

### Configuration

```python
client = DuneSimClient(
    api_key="YOUR_SIM_API_KEY",
    base_url="https://api.sim.dune.com",   # configurable
    api_key_header="X-Sim-Api-Key",        # configurable
    timeout=30.0,
    max_retries=3,
)
```

## Endpoints

| Method | Sim endpoint |
| --- | --- |
| `get_evm_balances` / `iter_evm_balances` | `GET /v1/evm/balances/{address}` |
| `get_evm_activity` / `iter_evm_activity` | `GET /v1/evm/activity/{address}` |
| `get_evm_transactions` / `iter_evm_transactions` | `GET /v1/evm/transactions/{address}` |
| `get_evm_token_info` | `GET /v1/evm/token-info/{address}` |
| `get_evm_token_holders` / `iter_evm_token_holders` | `GET /v1/evm/token-holders/{chain_id}/{address}` |
| `get_supported_chains` | `GET /v1/evm/supported-chains` |
| `get_svm_balances` | `GET /beta/svm/balances/{address}` |
| `get_svm_transactions` | `GET /beta/svm/transactions/{address}` |

## Development

```bash
pip install -e ".[dev]"
ruff check .
mypy src
pytest                      # unit tests (respx mocks, no network)
SIM_API_KEY=... pytest -m integration   # live smoke test against the real API
```

## License

MIT — see [LICENSE](LICENSE).
