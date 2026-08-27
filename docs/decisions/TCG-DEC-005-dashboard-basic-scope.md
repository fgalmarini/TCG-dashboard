# TCG-DEC-005 — Basic Dashboard Scope

## Metadata

- ID: `TCG-DEC-005`
- Date: 2026-08-25
- Type: scope decision
- Status: implemented

## Decision

Phase 6 implements only:

- Overview dashboard totals.
- Read-only Collection browsing, filtering, sorting and details.

For current market value, use Cardmarket Trend Price from the latest
`market_price_history` snapshot.

Do not add collection editing, Market trend charts, Analytics, Trading or CARDMADNESS
in Phase 6.

## Context

The full dashboard roadmap is larger than the useful first local app surface. Facundo
confirmed the smaller Phase 6 scope and Trend Price as the market value metric.

Manual collection editing remains through `load_collection.py`/CSV until a write API
is explicitly scoped.

## Consequences

- `backend/api/` is read-only and additive.
- `frontend/` starts with Overview and Collection only.
- Manual entries without market value are shown as missing price, never as `EUR 0`.
- Market charts and repeated historical snapshots move to Phase 7.
- Trading, Analytics and CARDMADNESS remain later phases.

## References

- `docs/plans/fase6-dashboard-basico-sprint-contract.md`
- `conventions.json`
