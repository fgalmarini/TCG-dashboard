# Schema audit — TCGplayer secondary pricing

`market_price_history` remains Cardmarket-specific and `printing_price_resolutions` remains the primary valuation path.
The generic `market_price_observations` table stores one positive metric per physical printing and source snapshot.

Uniqueness:
`card_id + provider + market + metric + currency + snapshot_key`.

Temporal semantics:
`source_updated_at` is supplied by Pokémon TCG API; `observed_at` is the audited snapshot acquisition time.

Database SHA before: `5975a033c76bf7939bc23d4f8eae7339116c6973b7305f4563d93fabec7a57a8`
Database SHA after: `not applied`
