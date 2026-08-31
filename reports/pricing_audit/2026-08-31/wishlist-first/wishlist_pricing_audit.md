# WISHLIST PRICING AUDIT

## SCOPE

- DB: `/Users/facundogalmarini/Desktop/TCG DASHBOARD/backend/db/tcg_dashboard.db`
- Audit mode: read-only; SQLite `mode=ro`, `PRAGMA query_only=1`.
- Baseline SHA-256 before/after: `38959ecb8224c9c4e06c00dbc7ccda37d17660c828b72be0418f1419c1437aff`.
- `integrity_check`: `ok`.
- `foreign_key_check`: clean.
- Cardmarket snapshots: local `price-history/`, created 2026-08-29; manifest fingerprint `90506db8d5ee005a14eb314e0eb5952f0622598d7bc44368055df71c07a7b27f`.
- All Wishlist rows were audited. Planning metrics use only `status='wanted'`.

## INVENTORY

| Metric | All rows | Wanted | Acquired | Removed |
| --- | ---: | ---: | ---: | ---: |
| Rows | 5 | 0 | 0 | 5 |
| Quantity | 5 | 0 | 0 | 5 |

Game split for active Wishlist: Magic `0 / 0`; One Piece `0 / 0`. All historical rows are Magic.

## IDENTITY COVERAGE — ACTIVE WISHLIST (`wanted`)

No active rows exist, so all ratios are `N/A` (`0/0`).

| Game | Items | Quantity | EXACT | AMBIGUOUS | MISMATCH | MISSING | UNPRICED |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Magic | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| One Piece | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Across all five historical rows: identity EXACT `1`, identity pending `4`; pricing UNPRICED `0` because the four non-EXACT rows are pending identity, not exact-but-unpriced.

- Exact item coverage: `N/A (0/0)`.
- Exact quantity coverage: `N/A (0/0)`.

## ALL WISHLIST ROWS — DIAGNOSTIC RESULT

| Status | Items | Quantity | Interpretation |
| --- | ---: | ---: | --- |
| EXACT | 1 | 1 | Access Tunnel; Scryfall Cardmarket ID `717343`; selected metric `Low`. |
| AMBIGUOUS | 4 | 4 | Three physical treatments are not proven by the Cardmarket bulk product name. |
| MISMATCH | 0 | 0 | None observed. |
| MISSING | 0 | 0 | None observed. |
| UNPRICED | 0 | 0 | No exact identity lacked a usable selected Low in the snapshot. |

## PRICING COVERAGE

Counts below require an exact identity and the physical printing's selected metric. Candidate prices for pending rows are diagnostic only and are not counted as available.

| Metric | Items | Quantity | All rows |
| --- | ---: | ---: | ---: |
| Cardmarket Low available | 1 | 1 | 20.00% |
| Cardmarket Trend available | 1 | 1 | 20.00% |
| CardTrader current fallback | 0 | 0 | 0.00% |

The API's actual current state is `current_price=NULL`, `market_value=NULL`, `source=NULL` for all five rows. No current resolution or mapping exists for these Wishlist cards. Cardmarket snapshot Low is not exposed as current value merely because a candidate has a price.

## VALUE RECONCILIATION

- Legacy/current value: `EUR 0.00` exposed; all five `current_price` values are NULL.
- Cardmarket Low-backed value: `EUR 0.30` on the one exact historical row, diagnostic only; active wanted contribution is `EUR 0.00` because active quantity is zero.
- Value without exact resolution: `EUR 0.00` currently exposed without exact support.
- Non-EXACT item with current value: `0`.
- EXACT with unsupported current value: `0`.
- Historical/stale value resurfacing: `0`.
- CardTrader-backed current value: `0`.
- Other unsupported current value: `0`.

## TARGET PRICE / MAX PRICE

Counts include all rows; active wanted counts are zero.

- Target price present: `1` all rows / `0` active.
- Max price present: `1` all rows / `0` active.
- Both present: `1` all rows / `0` active.
- Neither present: `4` all rows / `0` active.
- No target/max values were changed or recalculated.
- No diagnostic `target_vs_low_pct` or `max_vs_low_pct` was calculated because the only exact row has neither target nor max price.

## REUSABLE COLLECTION RULES

`audit_pricing.resolve_identity()` was reused directly in memory; no duplicate identity logic or production rule was created.

| Rule/evidence | Rule exists | Actually resolved | Items | Quantity |
| --- | --- | --- | ---: | ---: |
| `SCRYFALL_CARDMARKET_ID` | yes | yes | 1 | 1 |
| `SCRYFALL_CARDMARKET_ID + TREATMENT_UNPROVEN` | yes, conservative ambiguity branch | no | 4 | 4 |

No One Piece-specific rule was observed because Wishlist contains no One Piece rows. The resolver's direct Scryfall Cardmarket ID branch resolves Access Tunnel exactly; the other four rows are intentionally held as ambiguous when treatment is not proven.

## NEW CONFLICT PATTERNS

Count: `0`.

The four pending rows are not a new Wishlist-only identity pattern: they fall into the existing Collection resolver's `unproven_treatment` ambiguity behavior. Wishlist introduces no additional language, set/reprint, version, promo, art-variant, finish or provenance conflict in the audited data.

Separate implementation blocker: `./update-prices --scope wishlist` is accepted by `run_workflow()`, but `backend/scripts/update_prices.py:425-445` takes every non-Collection scope through the full-catalog branch; `backend/scripts/update_prices.py:694-716` then writes rows without `collection_item_id`, i.e. global resolutions. This is not executed or corrected by this audit. It must be resolved before any Wishlist apply is considered safe.

## MANUAL REVIEW REQUIRED

- Active wanted: `0`.
- All Wishlist rows: `4`, all blocked by `TREATMENT` evidence.
- No candidate was approved or selected for those rows.

## PENDING BREAKDOWN

### TREATMENT — 4 items / 4 quantity

Items `1`, `2`, `3` and `4` have exact-looking Scryfall Cardmarket IDs and one diagnostic Cardmarket candidate each, but the bulk product name does not prove the local physical treatment: `Surge Foil`, `Realms & Relics`, `Borderless`, and `Realms & Relics`. Candidate products remain unselected. See `wishlist_pending_review.csv`.

No `LANGUAGE`, `SET_REPRINT`, `VERSION`, `PROMO`, `ART_VARIANT`, `FINISH`, `MULTIPLE_FACTORS`, `MISSING_PROVENANCE` or `OTHER` pending categories were observed.

## POSITIVE OBSERVATIONS

- All Wishlist rows reference valid active catalog cards and the Wishlist/API joins do not expose a price for an unresolved identity.
- The exact row uses the correct selected Cardmarket `Low`; no alternate finish, Trend, historical value or CardTrader value was used as fallback.
- `Mark acquired` behavior remains outside this audit and was not changed.

## RECOMMENDED NEXT STEP

Diagnose and design a shared scope-aware resolver contract for `Collection` and `Wishlist`, including a read-only Wishlist dry-run path that filters to `wishlist_items` and persists no global resolution. Only after that contract is reviewed should the four treatment-blocked rows receive manual physical evidence review. Do not run apply yet.

