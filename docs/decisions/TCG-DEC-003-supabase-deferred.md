# TCG-DEC-003 — Supabase Deferred

## Metadata

- ID: `TCG-DEC-003`
- Date: 2026-08-24
- Type: scope decision
- Status: deferred

## Decision

Supabase/PostgreSQL migration is deferred and must be treated as its own future phase.

It is independent from Magic/Scryfall catalog enrichment and does not block the local
SQLite dashboard.

## Context

SQLite is enough for the current local personal dashboard. Supabase may become useful
for hosted/mobile access, especially around CARDMADNESS, but it introduces external
infrastructure, backups, auth/storage decisions and free-tier operational limits.

## Consequences

- Continue implementing current phases on SQLite.
- Keep SQLite as the fallback functional storage engine.
- When Supabase starts, define whether FastAPI stays as a backend layer or Supabase
  APIs become the primary access path.
- Plan backups explicitly because the free tier does not provide automatic backups.

## References

- `docs/plans/Revisión-fases 2-4 — Catálogo externo .md`
- `conventions.json`
