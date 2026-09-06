# AGENTS.md

## Project Context

Personal TCG collection, valuation and trading dashboard for Pokemon, One Piece
and Magic: The Gathering.

Read these docs before large changes:

- `docs/PRODUCT.md` — product vision, roadmap and UX principles.
- `docs/ARCHITECTURE.md` — stack, data model and source-of-truth rules.
- `docs/CURRENT_STATE.md` — real current phase, closed phases and known metrics.
- `docs/DATA_SOURCES.md` — authoritative current external-provider map and fallback rules.
- `docs/decisions/` — human-readable ADRs migrated from `conventions.json`.
- `docs/plans/` — sprint contracts and execution plans.

For any work involving external APIs, prices, card metadata, images or market history,
also read the relevant `backend/integrations/<provider>/README.md`.

## Current Scope

Current phase: Phase 7.

Phase 6 is closed. Do not reopen closed phases unless new evidence requires it.

Next work includes the external-provider POC/migration for current pricing and
historical market snapshots/trend charts.

Do not build Trading, CARDMADNESS Mode, Supabase migration or unrelated scrapers
unless explicitly requested.

## Commands

Backend tests:

```bash
python3 -m pytest backend/api/ backend/db backend/importer backend/scripts backend/integrations -q
```

Backend API:

```bash
cd backend
uvicorn api.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
npm run build
```

Documentation-only verification:

```bash
git diff --check
```

## Data Safety

- Do not write directly to the mounted SQLite DB if the bridge/FUSE issue applies.
- For SQLite writes against the mounted DB, work on a local temporary copy, then copy
  the DB back only after `PRAGMA integrity_check` and `PRAGMA foreign_key_check`.
- Never silently discard failed mappings or ambiguous product/card matches.
- Never show missing market prices as `EUR 0` or `€0`; use null/empty states.

## External Sources

`docs/DATA_SOURCES.md` is the authoritative current provider map.

Current policy:

- `cardmarketapi.com` = PRIMARY current EUR price.
- TCG Cardmarket API = FALLBACK current EUR price.
- TCGdex = Pokémon identity/metadata/variants/images only, not current price.
- Scryfall = Magic identity/printings/finishes/metadata/images only, not current price.
- TCG API = secondary market analytics; Free tier only for now.
- CardTrader = outside the new current-price architecture.

Important: `cardmarketapi.com` is a third-party Cardmarket-data service, not
Cardmarket's official API.

Fallback is allowed only for PRIMARY timeout/unavailability/error, missing usable
price, or failure to resolve a Cardmarket product ID already validated by our DB.
Never activate fallback to repair ambiguous identity or choose a more attractive price.
If PRIMARY and FALLBACK both fail, current price is NULL.

Before changing any provider:

1. read `docs/DATA_SOURCES.md`;
2. read `backend/integrations/<provider>/README.md`;
3. verify provider availability, documented endpoint, authentication, limits,
   freshness and usage restrictions;
4. update code-local documentation in the same commit as behavior changes.

Provider authentication belongs beside provider code in
`backend/integrations/<provider>/auth.py`. Real credentials belong only in `.env` or
the runtime environment. `.env.example` contains empty names only. Never hard-code,
commit, log or fixture real keys.

Do not implement undocumented endpoints, unauthorized access methods, access-control
workarounds or new scrapers.

## Implementation Rules

- Prefer simple, incremental changes that match the current stack.
- Keep core portfolio logic game-generic when practical.
- External provider IDs never replace internal card/printing identity.
- External network calls belong in maintenance/synchronization workflows, not normal
  FastAPI read requests.
- Preserve historical price data; do not overwrite snapshots as "current only".
- Use relational tables for cards, products, collection entries and price history.
- Do not touch unrelated importer/scripts/frontend/DB/data during scoped provider
  documentation/foundation work.
- If a mapping is ambiguous, report it and require a decision. Incorrect pricing is
  worse than missing pricing.
- Do not remove legacy CardTrader/provider code until callers and migration safety are
  explicitly audited.

## Definition Of Done

A change is done only when:

- relevant tests/checks pass;
- `git diff --check` is clean;
- frontend builds if frontend changed;
- DB integrity checks pass if the DB changed;
- ambiguous mappings are reported;
- provider-local README changes with provider behavior/auth changes;
- `docs/DATA_SOURCES.md` changes when the global source contract changes;
- docs/current state are updated when phase behavior changes.
