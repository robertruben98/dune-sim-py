# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-06-22

### Added

- Initial release of `dune-sim-py`, a typed client for the Dune Sim API.
- Sync `DuneSimClient` and async `AsyncDuneSimClient` sharing a common interface.
- EVM endpoints: balances, activity, transactions, token info, token holders,
  and supported chains.
- SVM endpoints: balances and transactions (Solana / Eclipse).
- Pydantic v2 response models for every documented endpoint.
- Cursor-based pagination iterator helpers for list endpoints.
- Automatic exponential-backoff retries on `429` and `5xx`, honoring `Retry-After`.
- Typed exception hierarchy mapped from HTTP status codes, handling both JSON and
  plain-text error bodies.
- `py.typed` marker; the package is fully checked under `mypy --strict`.

[Unreleased]: https://github.com/robertruben98/dune-sim-py/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/robertruben98/dune-sim-py/releases/tag/v0.1.0
