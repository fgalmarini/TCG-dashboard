# AGENTS.md

## Project Context

Personal TCG collection, valuation and trading dashboard for Pokemon, One Piece
and Magic: The Gathering, currently focused on Magic/LOTR.

Read these docs before large changes:

- `docs/PRODUCT.md` — product vision, roadmap and UX principles.
- `docs/ARCHITECTURE.md` — stack, data model and source-of-truth rules.
- `docs/CURRENT_STATE.md` — real current phase, closed phases and known metrics.
- `docs/decisions/` — human-readable ADRs migrated from `conventions.json`.
- `docs/plans/` — sprint contracts and execution plans.

## Current Scope

Current phase: Phase 7.

Phase 6 is closed. Do not reopen closed phases unless new evidence requires it.

Next work: historical market data, repeated price snapshots and price-trend charts.

Do not build Trading, Analytics, CARDMADNESS Mode, collection web editing,
Supabase migration or scrapers unless explicitly requested.

## Commands

Backend tests:

```bash
python3 -m pytest backend/api/ backend/db backend/importer backend/scripts -q
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

- Cardmarket remains the source for European market prices.
- Use public/downloadable Cardmarket data. Do not assume private Cardmarket API
  credentials are available.
- Scryfall may be used only for Magic metadata/catalog enrichment when there is a
  direct Cardmarket product lookup.
- Do not implement scrapers, undocumented endpoints or access-control workarounds.
- Before adding any external source, verify availability, format, usage restrictions
  and update cadence, then document the result.

## Implementation Rules

- Prefer simple, incremental changes that match the current stack.
- Keep core portfolio logic game-generic when practical.
- Preserve historical price data; do not overwrite snapshots as "current only".
- Use relational tables for cards, products, collection entries and price history.
- Do not touch `backend/importer/`, `backend/scripts/`, `frontend/`, the DB or data
  files during documentation-only work.
- If a mapping is ambiguous, report it and require a decision. Incorrect pricing is
  worse than missing pricing.

## Definition Of Done

A change is done only when:

- relevant tests/checks pass;
- `git diff --check` is clean;
- frontend builds if frontend changed;
- DB integrity checks pass if the DB changed;
- ambiguous mappings are reported;
- docs/current state are updated when phase behavior changes.
