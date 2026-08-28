# TCG-DEC-008 — Multi-TCG Foundation and One Piece provider policy

Status: Implemented  
Date: 2026-08-27

## Context

The original schema coupled printing identity, Magic naming and provider IDs. One
Piece also had 11,502 legacy rows whose physical-printing validity could not be assumed.

## Decision

- Keep `cards.id` as the stable internal printing identity.
- Add provider-neutral sets, canonical cards, external IDs, printing relations and
  price-resolution history without rebuilding existing tables.
- Group Magic by Oracle ID when present and One Piece by validated card number with
  explicit name conflicts.
- Use CardTrader Blueprint as One Piece's main external catalog/image/pricing ID,
  never as an internal primary key.
- Keep EN and JP separate for identity, image and price resolution.
- Keep `release_kind` and `art_kind` independent and derive separate printing/reprint
  counts.
- Resolve One Piece prices through exact-language Cardmarket, exact-language CardTrader
  median-5, then null. Mixed prices are retained only for audit.
- Use Bandai EN/JP as release and card-number validation through a checked-in registry,
  without scraping or runtime dependency.
- Preserve all legacy rows. Exact reusable rows are enriched; all others remain legacy
  or ambiguous.

## Consequences

Provider changes cannot alter internal identity. Pokémon can reuse the neutral model
later. Ambiguous commercial identities remain visible to audit but are excluded from
the active catalog until manually resolved. Missing data is preferred over guessed
identity, image or pricing.

## Validated Sources

- CardTrader API Blueprints and Marketplace:
  <https://www.cardtrader.com/en/docs/api/full/reference>
- Cardmarket public Product Catalogue and Price Guide:
  <https://news.cardmarket.com/en/DragonBallSuper/were-making-the-price-guide-and-product-catalogue-available-for-download>
- Bandai EN card list: <https://en.onepiece-cardgame.com/cardlist/>
- Bandai JP card list: <https://www.onepiece-cardgame.com/cardlist/>
