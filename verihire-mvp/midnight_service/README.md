# VeriHire Midnight Service

This is the piece that turns the mocked proof step into a **real** Midnight
ZK proof. It's a small Node/TypeScript HTTP service (Midnight's own
tooling is JS/TypeScript, not Python) that the backend calls instead of
`backend/app/midnight_mock.py`, once it's actually running.

**Status: written against the current public Midnight docs, not yet
compiled or run.** This environment had no Compact compiler, no Midnight
node/indexer, no proof server, and no funded testnet wallet available, so
none of this has been exercised end-to-end. Treat everything here as a
grounded starting point — real package names (checked against the npm
registry), real documented code patterns — not a verified-working
integration. Budget real time to stand up the toolchain and debug it.

## What you need to actually run this

1. **The Compact compiler**, to turn `../contract/verihire.compact` into
   the TypeScript bindings this service imports:
   ```bash
   curl --proto '=https' --tlsv1.2 -LsSf https://github.com/midnightntwrk/compact/releases/latest/download/compact-installer.sh | sh
   compact compile ../contract/verihire.compact managed/verihire
   ```

2. **A local proof server** (generates the actual ZK proofs):
   ```bash
   docker run -p 6300:6300 midnightntwrk/proof-server:8.1.0 midnight-proof-server -v
   ```

3. **Midnight node + indexer RPC endpoints.** Get current testnet URLs
   from [docs.midnight.network](https://docs.midnight.network) — these
   change as the network progresses, so don't hardcode last month's values.

4. **A funded testnet wallet.** `providers.ts` leaves the wallet/signing
   provider as an explicit `TODO` — it needs to sign transactions with a
   real wallet, which is specific to whether your team wants a
   programmatic wallet (`@midnight-ntwrk/wallet`) or a browser Lace
   wallet connection. Check the current docs for the recommended approach
   before wiring this up; it's genuinely the piece most likely to have
   moved since these docs were written.

## Setup

```bash
npm install
cp .env.example .env   # fill in the URLs above once you have them
npm run deploy-contract  # after compiling the contract - prints CONTRACT_ADDRESS
# paste that address into .env, then:
npm run dev
```

Once this is running and reachable, set `MIDNIGHT_SERVICE_URL=http://localhost:7000`
in `backend/.env` and restart the backend — `backend/app/midnight_client.py`
will start calling this service for every application instead of the
offline mock, and will automatically fall back to the mock again if this
service becomes unreachable.

## What the circuit actually proves

See `../contract/verihire.compact` for the full contract and its own
design notes. Short version: it takes the candidate's real Python years /
PostgreSQL / AWS cert / education level as **private** circuit inputs,
compares them against the job's **public** requirement thresholds, and
writes only a `Boolean` ("eligible or not") to public ledger state, keyed
by a hash of `(candidate_ref, job_id)` — never the candidate's name, CV,
or raw values. That's the actual privacy-preserving proof this hackathon
track is asking for; everything else in this repo is scaffolding around
getting real values into and out of that one circuit call.

**Known MVP limitation:** the circuit's shape is fixed at compile time, so
it only faithfully represents jobs built from those four criteria (the
flagship seed job). See `backend/app/midnight_client.py`'s
`_map_to_circuit_inputs` for exactly how the mapping works and where it
falls short for other jobs — worth a real conversation before this goes
past a demo.
