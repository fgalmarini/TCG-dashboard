# Product Vision

TCG Dashboard is a personal web dashboard for managing a collectible trading card
collection, monitoring European market prices, tracking portfolio performance and
preparing trades.

The product must be an interactive dashboard, not an Excel replacement.

## Supported TCGs

- Pokemon TCG (inactive; future catalog)
- One Piece Card Game (active catalog; personal collection deferred)
- Magic: The Gathering, currently focused on The Lord of the Rings related cards

The architecture should allow additional TCGs later without a major rewrite.

## Main Goals

- Manage the collection and acquisition costs.
- Track current European market values from Cardmarket.
- Preserve historical market values instead of overwriting old prices.
- Calculate portfolio value, profit/loss and ROI.
- Identify cards suitable for trading.
- Maintain a Want List.
- Compare cards and cash for fair trade preparation.
- Prepare for physical TCG events such as CARDMADNESS Dusseldorf.

## Market Value And Trade Value

Market Value is the estimated European market value, based primarily on Cardmarket
metrics such as Trend Price.

Trade Value is the value assigned for physical trading. It must not automatically be
treated as identical to Market Value. Future trade-value logic should be transparent
and configurable instead of hard-coded.

## Collection

Collection entries should support:

- TCG, card name, set, set code and card number.
- Cardmarket Product ID when available.
- Language, condition, grading company and grade.
- Quantity, purchase price, purchase currency and purchase date.
- Current market value, trade value, notes and collection status.

Possible statuses: `KEEP`, `HOLD`, `TRADE`, `SELL`, `WANT`.

Do not assume every card has a purchase price, Cardmarket mapping or raw condition.

## Catalog And Wishlist

Magic LOTR and One Piece use a catalog-first model. `cards` is the physical printing
catalog with stable internal IDs; `canonical_cards` groups logical cards. Collection
and Wishlist reference printings instead of duplicating metadata.

Magic scope is physical LTR and LTC printings. Finish is part of the
printing identity. Treatment labels such as Showcase, Borderless, Scene and Surge Foil
are descriptive metadata only and are never used as identity.

One Piece separates EN and JP printings, release kind and art kind. Collection and
Wishlist show `Reprints: N` when applicable; detail shows printing/reprint counts and
all known related printings. One Piece Collection entry is not part of this sprint.

The wishlist supports wanted quantity, priority, maximum price, currency, notes and
status. Marking an item acquired keeps the wishlist row as `acquired` for traceability
and does not modify Collection. Removed rows remain as `removed`.

## Condition And Grading

Raw conditions should eventually include common values such as `NM`, `EX`, `GD`,
`LP`, `PL` and `PO`. The exact taxonomy should be reviewed before expanding the UI.

Graded cards should support at minimum `PSA`, `BGS`, `CGC` and `Other`, plus
numerical grades where applicable. Graded and raw cards must be distinguishable.

## Portfolio Calculations

The dashboard should calculate dynamically from database data:

- Total acquisition cost.
- Current market value.
- Unrealized profit/loss.
- ROI.
- Total trade value.
- Number of cards and unique cards.
- Value by TCG, set, language, condition and grading status.

Do not manually persist calculated totals unless there is a strong technical reason.

## Historical Data

Historical market data is central to the product. The system should preserve repeated
price snapshots so the user can answer:

- How much was the collection worth one month ago?
- Which cards appreciated or lost value?
- Which TCGs and sets are trending?
- How has the portfolio evolved?

The official manual update workflow is `./update-prices --dry-run` followed by
`./update-prices --apply`. It preserves source currency and repeated snapshots,
rejects mixed-language prices from valuation, and keeps missing prices nullable.

## Display Currency

The dashboard should eventually support choosing between USD and EUR as the display
currency. The model must distinguish the source currency of a price, the selected
display currency and the exchange rate used for conversion. Currency conversion is a
presentation concern only and must never overwrite the original price or its source
currency.

## Dashboard Sections

Planned sections:

- Overview: total value, cost, P/L, ROI, card counts and value by TCG.
- Collection: search, filters, sorting, details and eventual editing.
- Market: current prices, price trends and historical charts.
- Trading: Trade Binder, Want List and Trade Calculator.
- Analytics: portfolio evolution and best/worst performers.
- CARDMADNESS: cards to bring, cards to look for, trade budget and event snapshots.

## CARDMADNESS Mode

Future CARDMADNESS Mode should help prepare for physical events, starting with
CARDMADNESS Dusseldorf in September 2026.

It should identify cards available for trade, calculate total trade value, maintain
target cards, prepare a binder list and preserve a pre-event market snapshot.

## Trade Calculator

Future trade comparison must show the underlying values:

- cards given;
- cards received;
- cash included;
- total received;
- difference;
- fair-trade status.

Do not label a trade good or bad without showing the calculation.

## Want List

Wanted cards use the Multi-TCG printing reference, with mandatory language for One
Piece. Game/language filters, Buying Mode, CSV and state transitions share one flow.

## UI Principles

The UI should feel like a modern TCG portfolio/investment dashboard: fast navigation,
clear cards, charts, search, filters, useful density, dark mode and responsive design.

Avoid a generic accounting-app feel. The collection should feel visual and
card-oriented.

## Future Possibilities

Possible later features include eBay sold-price comparison, additional European
marketplaces, card images, OCR/card scanning, mobile-friendly workflows, collection
import/export, public/private trade lists, price alerts and automated weekly reports.

These are not current scope unless explicitly requested.
