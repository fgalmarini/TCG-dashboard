# CARDMADNESS-003 — Create and associate event Wishlist

Status: complete (`2026-09-23`). The existing Wishlist is the sole source of truth;
no parallel event list was introduced.

## Selection policy

The curated `CARDMADNESS_HOB_HOC.csv` contains 116 logical identities. Exactly one
Wishlist item represents each identity:

- If the identity has a Surge Foil printing, Surge is the Wishlist target and the
  matching Traditional Foil is shown only as an event comparison.
- If Surge is unavailable, Traditional Foil is the Wishlist target.
- Non-Foil and other finishes are excluded.

The target printing is resolved structurally by set, collector number, English
language, active catalog status, foil finish and exact treatment. No name-based or
fuzzy matching is used. Each Surge target must have exactly one Traditional Foil
alternative under the same canonical identity, set and language.

## Preflight

Before apply, the existing Wishlist had 39 rows (18 wanted, 2 acquired and 19 removed),
0 HOB/HOC rows and 0 event links. The event existed exactly once. Exact catalog
resolution returned 75 Surge targets and 41 Traditional-only targets (116 distinct
canonical identities), with 75 unique Traditional alternatives, 0 conflicts and
0 missing targets.

## Apply and verification

The safe apply ran on a local temporary DB copy and used the existing Wishlist create
API defaults and event-link API. It inserted 116 rows and 116 links; no existing rows
were reused or changed. Defaults are quantity 1, priority `medium`, currency `EUR`,
and NULL target/max prices. The resulting Wishlist has 155 rows: the original 39 plus
116 Cardmadness targets.

- HOB/HOC Wishlist rows: 116 (75 `surge_foil`, 41 `traditional_foil`); Non-Foil: 0.
- `cardmadness-2026` links: 116; duplicate links: 0.
- Second apply: 0 rows inserted, 0 links inserted; all 116 targets and links reused.
- The 39 original rows retain their exact values and states.
- `/api/events/cardmadness-2026/wishlist` returns all 116 items. Surge items include
  their Surge Low/Avg30 data and a Traditional alternative selected by exact
  `canonical_card_id + set_id + language_id + treatment`; Traditional-only items show
  their own Traditional Low/Avg30 without a fabricated Surge comparison.
- NULL prices display as `—`. The five HOC printings with no exact image keep the
  established missing-image behavior.
- Regression printings: HOB Belladonna Took #250, Bilbo, Thief in the Night #255,
  Smaug the Magnificent #265, Gleaming Splendor #275 and The Lonely Mountain #284;
  HOC Flowering of the White Tree #054, Orcish Bowmasters #059, Sauron, the Dark Lord
  #076, The One Ring #084 and Minas Tirith #089. Two Traditional-only targets
  (HOB #199 and HOC #093) were also checked.
- DB SHA256: `1569c5af44a71b1b1053ac85f08874671130427b8913f2818307fef54715c253` →
  `e75e042ae476441fa8cef98d55ee5bf80ca1161a9052618793b5f251c2cfae74`.
  `integrity_check=ok`; `foreign_key_check` returned 0 rows. Changed tables are
  `wishlist_items`, `event_wishlist_items` and the Wishlist AUTOINCREMENT sequence.
- Backend: 274 tests + 6 subtests; frontend: 13 tests; build, error registry and
  `git diff --check` passed.
- UI: 116 cards render (50 HOB, 66 HOC), with 75 Surge comparisons, 41 Traditional
  targets and 111 images; the five missing images show the existing placeholder. Both
  desktop and 390×844 mobile views have no horizontal overflow. Belladonna Took and
  Dwarven Warriors were inspected directly at mobile width.

## Next start

Wait for the next explicit task. No further CARDMADNESS sprint is selected.
