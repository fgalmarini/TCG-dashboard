# Wishlist Scope Safety Audit

Date: 2026-08-31

## Scope tested

- Pricing scope: `wishlist`
- Wishlist status: `wanted` (default); explicit status values are covered by CLI validation
- Games: Magic and One Piece regression fixtures
- Validation DB: temporary test databases and temporary copies created by the workflow

## Results

- Active Wishlist items in the production read-only audit: `0` (`wanted`)
- Write candidates in the production read-only audit: `0`
- Current pricing changes in the production read-only audit: `0`
- Out-of-scope candidates before/after target validation: `0 / 0`
- Wishlist current NULL resolutions block global and historical fallback: PASS
- Scope invariants for global/Collection/Wishlist: PASS
- Temporary apply creates Wishlist-scoped resolution only: PASS
- Collection, Wishlist rows, mappings and global resolutions remain unchanged in the
  Wishlist temporary apply fixture: PASS
- Source-table writes are restricted to product IDs selected by the active target: PASS

## Production DB safety

- SHA-256 before: `38959ecb8224c9c4e06c00dbc7ccda37d17660c828b72be0418f1419c1437aff`
- SHA-256 after: `38959ecb8224c9c4e06c00dbc7ccda37d17660c828b72be0418f1419c1437aff`
- `PRAGMA integrity_check`: `ok`
- `PRAGMA foreign_key_check`: `[]`
- Production DB apply: **not executed**
- Production DB migration: **not executed**
- Migration validation: **temporary copies/fixtures only**

The four historical ambiguous Wishlist records remain unresolved; no ambiguous
mapping was converted into pricing.
