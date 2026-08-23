# AGENTS.md

# TCG Collection & Trading Dashboard

## 1. Project Overview

This project is a personal collection management, valuation, market analysis and trading dashboard for collectible trading cards.

The supported TCGs are:

- Pokémon TCG
- One Piece Card Game
- Magic: The Gathering
  - Initially focused on The Lord of the Rings (LOTR) related cards

The primary goal is NOT to create an Excel spreadsheet or spreadsheet-like application.

The final product must be an interactive web dashboard that allows the user to manage their collection, monitor European market prices, analyze portfolio performance and prepare trades.

The application will initially run locally.

---

# 2. Main Objectives

The system should eventually allow the user to:

1. Manage their card collection.
2. Track acquisition costs.
3. Track current European market values.
4. Track historical market prices.
5. Calculate portfolio value.
6. Calculate profit/loss.
7. Calculate ROI.
8. Identify cards suitable for trading.
9. Maintain a Want List.
10. Compare cards for potential trades.
11. Calculate fair trade values.
12. Prepare specifically for physical TCG events such as CARDMADNESS Düsseldorf.
13. Preserve historical valuation data rather than overwriting previous values.

---

# 3. Supported Games

The database must distinguish between:

- Pokémon
- One Piece
- Magic: The Gathering

The architecture must allow additional TCGs to be added later without requiring a major rewrite.

Do not hard-code game-specific logic into the core portfolio system when a generic solution is possible.

---

# 4. Market Data

## Primary Market Source

Cardmarket is the primary source for European market prices.

Cardmarket Price Guides are currently available for:

- Magic: The Gathering
- Pokémon
- One Piece
- Other TCGs

Cardmarket's public data/price-guide system should be investigated before implementing any scraper or API integration.

Official Cardmarket API access must NOT be assumed to be available.

Currently, Cardmarket states that it is not accepting new applications for API access.

Therefore:

- Do not build the application around requiring private Cardmarket API credentials.
- Do not ask the user to provide Cardmarket API credentials.
- Do not implement unauthorized access methods.
- Prefer official downloadable/public Cardmarket data where available.
- Investigate the current Cardmarket Price Guide and Product Catalogue before writing the market-data importer.

Official sources:

https://www.cardmarket.com/en/Magic/Data/Price-Guide

https://help.cardmarket.com/en/cardmarket-api

---

# 5. Cardmarket Data Strategy

The intended architecture is:

Cardmarket
    ↓
Price Guide / Product Catalogue
    ↓
Market Data Importer
    ↓
Validation / Normalization
    ↓
Database
    ↓
Dashboard

The application should NOT simply replace a current price with a new price.

Historical prices must be preserved.

Example:

2026-08-22 → €450
2026-08-29 → €462
2026-09-05 → €438
2026-09-12 → €475

This allows the dashboard to display price evolution.

The initial update frequency should be approximately weekly.

However, the architecture should allow manual updates as well.

Eventually the dashboard should have a button similar to:

"Update Market Prices"

The update process should:

1. Retrieve the latest available Cardmarket data.
2. Validate the downloaded data.
3. Identify the relevant products.
4. Map Cardmarket products to cards in the local database.
5. Update current prices.
6. Store a historical price snapshot.
7. Report how many products/cards were successfully updated.
8. Report errors or unmapped products.

Never silently discard failed mappings.

---

# 6. Important Market Price Fields

When available, store separate Cardmarket metrics rather than reducing everything to one price.

Potential fields include:

- Low Price
- Trend Price
- Average Price
- 1-day average
- 7-day average
- 30-day average
- Date of price observation

The exact fields must be verified against the current Cardmarket data format before implementation.

Do NOT invent fields that are not actually provided by Cardmarket.

---

# 7. Market Value vs Trade Value

The application must distinguish between:

## Market Value

The estimated European market value based primarily on Cardmarket.

## Trade Value

The value assigned for physical trading.

These values should NOT automatically be assumed to be identical.

Eventually the system should allow the user to define or adjust trade-value logic.

Example:

Market Trend: €500
30-day average: €480
Lowest relevant NM listing: €450

Possible Trade Value:

€450–€480

The exact calculation should be configurable and should not be hard-coded without discussion.

---

# 8. Collection Data

Each collection item should eventually support information such as:

- TCG
- Card name
- Set
- Set code
- Card number
- Cardmarket Product ID
- Language
- Condition
- Grading company
- Grade
- Quantity
- Purchase price
- Purchase currency
- Purchase date
- Current market value
- Trade value
- Notes
- Collection status

Possible collection statuses:

- KEEP
- HOLD
- TRADE
- SELL
- WANT

Do not assume every card has a purchase price.

Do not assume every card is raw.

---

# 9. Condition and Grading

The system should support raw and graded cards.

Raw conditions should eventually include common conditions such as:

- NM
- EX
- GD
- LP
- PL
- PO

The exact condition taxonomy should be reviewed before implementation.

Graded cards should support at minimum:

- PSA
- BGS
- CGC
- Other

And numerical grades where applicable.

Graded cards must be distinguishable from raw cards.

---

# 10. Portfolio Calculations

The dashboard should eventually calculate:

- Total acquisition cost
- Current market value
- Unrealized profit/loss
- ROI
- Total trade value
- Number of cards
- Number of unique cards
- Value by TCG
- Value by set
- Value by language
- Value by condition
- Value by grading status

Example:

Portfolio Cost:
€4,200

Current Market Value:
€6,850

Unrealized P/L:
€2,650

ROI:
63.1%

These calculations should be derived dynamically from database data.

Do not manually store calculated totals unless there is a strong technical reason.

---

# 11. Historical Data

Historical market data is important.

The system should preserve snapshots so that the user can eventually answer questions such as:

- How much was my collection worth one month ago?
- Which cards appreciated the most?
- Which cards lost value?
- Which TCG performed best?
- Which sets are trending upward?
- How has my portfolio evolved?

Historical data must not be destroyed when new market data is imported.

---

# 12. CARDMADNESS Mode

The application will eventually have a dedicated mode for preparing for physical TCG events.

The first target event is:

CARDMADNESS Düsseldorf
September 2026

The CARDMADNESS mode should eventually help the user:

- Identify cards available for trade.
- Calculate total trade value.
- Identify cards they want to acquire.
- Calculate target prices.
- Compare potential trades.
- Prepare a physical trade binder.
- Create a list of cards worth bringing.
- Identify cards that should probably stay in the collection.
- Create a pre-event market snapshot.

The user should eventually be able to create a snapshot such as:

CARDMADNESS VALUATION
25/09/2026

This snapshot should preserve the market values used for event preparation.

---

# 13. Trade Calculator

Eventually the application should support comparing two or more cards.

Example:

User gives:

Card A
Market Value: €620
Trade Value: €600

Other person's cards:

Card B
Market Value: €510
Trade Value: €500

Cash:
€100

Result:

Total received:
€600

Difference:
€0

Status:
FAIR TRADE

The calculation rules must be transparent.

Do not simply label trades "good" or "bad" without showing the underlying values.

---

# 14. Want List

The user should eventually be able to maintain a Want List.

Each wanted card may include:

- TCG
- Card
- Set
- Language
- Condition
- Grade
- Target price
- Maximum acquisition price
- Priority
- Notes

Example:

Priority: HIGH
Target price: €450
Maximum price: €500

This will eventually be used by CARDMADNESS Mode.

---

# 15. Dashboard

The final application must be an interactive web application.

It must NOT be designed as an Excel replacement.

Potential dashboard sections:

## Overview

- Total collection value
- Total cost
- P/L
- ROI
- Total cards
- Total trade value
- Value by TCG

## Collection

- Search
- Filters
- Sorting
- Card details
- Edit collection items

## Market

- Current prices
- Price trends
- Historical charts

## Trading

- Trade Binder
- Want List
- Trade Calculator

## Analytics

- Portfolio evolution
- Best performers
- Worst performers
- Set performance
- TCG performance

## CARDMADNESS

- Cards to bring
- Cards to look for
- Trade budget
- Market snapshot
- Trade calculator

---

# 16. Initial Technical Stack

The preferred initial architecture is:

Frontend:

- React
- TypeScript
- Tailwind CSS
- shadcn/ui
- Recharts

Backend:

- Python
- FastAPI

Database:

- SQLite initially

The architecture should allow migration to PostgreSQL later if necessary.

Do not introduce unnecessary infrastructure.

The initial project should be simple enough to run locally on the user's Mac.

---

# 17. Local Development

The dashboard should initially run locally.

Expected frontend:

http://localhost:3000

Expected backend:

http://localhost:8000

These ports may be changed if necessary.

The project should eventually have simple commands such as:

npm run dev

and/or an equivalent single command that starts the entire application.

The exact development workflow should be documented in README.md.

---

# 18. Database Principles

Use a relational database.

Avoid storing the entire collection as one large JSON object.

Cards, sets, prices, historical prices, collection entries and trades should be represented using appropriate relational structures.

The database schema should be normalized where practical.

The schema should support multiple copies of the same card.

Example:

Card:
Luffy OP05-119

Collection:
Quantity = 2

This should not require creating two completely independent card definitions.

---

# 19. Card Identification

Card identification is critical.

Whenever possible, use stable identifiers such as:

- Cardmarket Product ID
- Set ID
- Set code
- Card number

Do not rely exclusively on card names.

Different games and languages can have identical or very similar card names.

The system must distinguish between:

- Game
- Set
- Card number
- Language
- Printing/version

---

# 20. Data Integrity

Market data must never silently overwrite unrelated cards.

If a Cardmarket product cannot be confidently mapped to a collection card:

- Mark it as unmapped.
- Report it.
- Do not guess.

If multiple possible products exist:

- Report the ambiguity.
- Require a mapping decision.

Incorrect pricing is worse than missing pricing.

---

# 21. External Data Rules

Before implementing an external data integration:

1. Investigate the official source.
2. Verify current availability.
3. Verify the data format.
4. Verify update frequency.
5. Verify usage restrictions.
6. Document the source.
7. Only then implement the importer.

Do not assume that a third-party scraper, unofficial API or undocumented endpoint is stable.

Do not implement methods intended to bypass authentication, subscriptions, rate limits or access controls.

---

# 22. Development Method

Build incrementally.

Do NOT attempt to build the entire application at once.

Recommended order:

Phase 1:
Project documentation and architecture.

Phase 2:
Investigate Cardmarket data.

Phase 3:
Create database schema.

Phase 4:
Implement Cardmarket data importer.

Phase 5:
Implement manual collection management.

Phase 6:
Build basic dashboard.

Phase 7:
Add historical market data.

Phase 8:
Add analytics.

Phase 9:
Add trading functionality.

Phase 10:
Add CARDMADNESS Mode.

---

# 23. Current Phase

CURRENT PHASE: 4

Phases 1 (documentation/architecture), 2 (Cardmarket data investigation) and 3 (database schema) are closed — findings/schema proposal in `fase2-cardmarket-hallazgos-y-schema.md`, schema implementation in `backend/db/`.

Phase 4 (Cardmarket data importer, `fase4-importer-sprint-contract.md`) is implemented and verified against real data: `backend/importer/` downloads the 6 Cardmarket JSON files, loads `cardmarket_products`/`cards`/`cardmarket_product_mappings` in scope (One Piece full catalog, Magic LOTR only), self-heals `expansions`, and classifies variant groups. Real run: 12,867 products in scope, 12,167 mapped cleanly, 700 flagged `ambiguous` (genuine `UNIQUE` collisions on `cards`, reported not silenced), 143 new expansions pending a name.

The next task (Phase 5) is manual collection management.

DO NOT start building the complete dashboard yet.

DO NOT create a scraper yet.

DO NOT assume Cardmarket API credentials are available.

---

# 24. Coding Principles

Prefer:

- Simple solutions
- Strong typing
- Small modules
- Clear naming
- Reusable components
- Explicit error handling
- Automated tests for important calculations
- Documentation for non-obvious decisions

Avoid:

- Overengineering
- Premature microservices
- Unnecessary dependencies
- Hard-coded card data
- Hard-coded prices
- Silent failures
- Unofficial APIs when official data is available
- Scraping when an official downloadable dataset is available

---

# 25. Financial Accuracy

This application is for personal collection management and trading analysis.

Market prices are estimates and can change.

Never represent a Cardmarket metric as a guaranteed sale price.

Always show:

- Source
- Price metric
- Date/time of update

When presenting a valuation, make it clear whether it is:

- Market Trend
- Average
- Lowest listing
- Trade Value
- User-defined valuation

---

# 26. User Interface Principles

The UI should feel like a modern TCG portfolio/investment dashboard.

Prioritize:

- Fast navigation
- Clear cards
- Charts
- Search
- Filters
- Useful information density
- Dark mode support
- Responsive design

Avoid making the UI look like a generic accounting application.

The collection should feel visual and card-oriented.

---

# 27. Future Possibilities

The architecture should leave room for future features such as:

- eBay sold-price comparison
- Additional European marketplaces
- Card images
- OCR/card scanning
- Automatic card recognition
- Mobile-friendly interface
- Barcode/QR support
- Collection import/export
- Public/private trade lists
- Price alerts
- Discord/Telegram notifications
- Automated weekly market reports

These features are NOT part of the initial implementation.

Do not implement them unless explicitly requested.

---

# 28. Important Instruction

When requirements are ambiguous, do not silently make major architectural decisions.

Explain the tradeoff and propose the simplest reasonable solution.

When an external data source is involved, verify it before coding against it.

The goal is to build a reliable personal TCG portfolio and trading tool, not a quick prototype that becomes difficult to maintain.