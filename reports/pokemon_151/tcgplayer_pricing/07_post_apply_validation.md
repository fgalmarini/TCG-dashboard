# Post-apply validation — TCGplayer secondary pricing

Pokémon physical printings: `362`
TCGplayer secondary priced: `339` physical printings
normal priced: `121 / 128`
holo priced: `72 / 81`
reverse priced: `146 / 153`
unpriced: `23`

currency: `USD only`
current_price changed: `NO`
market_value changed: `NO`
Cardmarket pricing changed: `NO`
Cardmarket mappings changed: `NO`
Magic changed: `NO`
One Piece changed: `NO`
Collection changed: `NO`
Wishlist changed: `NO`
DB integrity: `ok`
foreign keys: `OK`
second apply: `NO-OP`

status counts: `{'MATCH': 254, 'MINOR_DIFFERENCE': 80, 'IDENTITY_CONFLICT': 23, 'MATERIAL_DIFFERENCE': 5}`

## Difference distribution

The 20% value is recorded as `diagnostic_threshold_candidate`, not as a persistence gate.
- low: n=360, p50=0.0000, p75=0.0000, p90=0.0000, max=0.8750
- market: n=360, p50=0.0000, p75=0.0000, p90=0.0364, max=0.1562
