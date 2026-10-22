# VeriHire Midnight service

This Node/TypeScript service is the real Midnight.js boundary used by the
FastAPI backend. It exposes:

- `GET /health` — service, contract, wallet, and network configuration status
- `POST /prove` — validates the fixed-shape request, calls
  `proveEligibility`, and reads the public result back from the ledger

The service is intentionally not a proof simulator. Without a configured
contract, proof server, and funded wallet, `/prove` fails explicitly and the
Python backend reports `not_configured` or `unavailable` rather than claiming
verification.

## Current compatibility set

The contract was compiled and the TypeScript service was built with the
current tested preprod matrix:

- Compact toolchain: `0.31.1`
- Compact runtime: `0.16.0`
- Midnight.js: `4.1.1`
- Proof server: `8.1.0`
- Wallet SDK: `1.2.0`

## Local setup

```bash
npm ci
export PATH="$HOME/.local/bin:$PATH"
compact compile ../contract/verihire.compact managed/verihire
npm run build
npm run dev
```

The compiler can be installed from the official Compact devtools release:

```bash
curl --proto '=https' --tlsv1.2 -LsSf \
  https://github.com/midnightntwrk/compact/releases/latest/download/compact-installer.sh | sh
compact update 0.31.1
```

## Real preprod configuration

Copy `.env.example` to `.env` and provide:

- the current preprod indexer and WebSocket URLs
- a compatible proof-server URL
- a deployed contract address
- `WALLET_SEED`, a 32-byte or 64-byte hexadecimal seed
- `MIDNIGHT_STORAGE_PASSWORD`, at least 16 characters

The service uses the official programmatic `@midnight-ntwrk/wallet-sdk`
pattern: `HDWallet`, `WalletFacade`, `ShieldedWallet`, `UnshieldedWallet`,
and `DustWallet`. This repository does not include a funded seed and has not
submitted a live transaction.

The generated contract is a fixed-shape MVP circuit for `job-001`. It proves
Python years, PostgreSQL presence, AWS certification, and
Bachelor's-or-equivalent education without writing those private values to
public ledger state.