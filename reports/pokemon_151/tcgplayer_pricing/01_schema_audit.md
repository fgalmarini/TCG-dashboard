# Schema audit — TCGplayer secondary pricing

`market_price_history` remains Cardmarket-specific and `printing_price_resolutions` remains the primary valuation path.
The generic `market_price_observations` table stores one positive metric per physical printing and source snapshot.

Uniqueness:
`card_id + provider + market + metric + currency + snapshot_key`.

Temporal semantics:
`source_updated_at` is supplied by Pokémon TCG API; `observed_at` is the audited snapshot acquisition time.

Database SHA before: `bce907591a43dbbff620fced5ef192fa08c94d303aa14991d486077706f25b73`
Database SHA after: `not applied`
