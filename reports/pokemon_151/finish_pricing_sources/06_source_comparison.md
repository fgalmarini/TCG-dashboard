# Source comparison

| Dimension | Cardmarket public listings | Pokémon TCG API | TCGdex |
|---|---|---|---|
| Finish precision | Unknown while blocked | Cardmarket reverse fields + TCGplayer keys | TCGplayer variant keys; Cardmarket variant records |
| Identity precision | Product ID/page, finish listing attribute | `Counter({'EXACT': 193, 'MISMATCH': 14})` set + number + name | `Counter({'EXACT': 195, 'MISMATCH': 12})` set + localId + name |
| Currency | EUR when directly obtained | Cardmarket-derived EUR; TCGplayer USD | Cardmarket EUR; TCGplayer USD |
| Freshness | Not observable from blocked sample | Cardmarket/TCGplayer timestamps in response | Per-response update timestamps |
| Coverage | Direct finish-specific: `0/362` | Reverse Cardmarket-derived positive: `149/207`; TCGplayer normal/holo/reverse: `{'normal': 121, 'holo': 72, 'reverse_holo': 146}` | TCGplayer normal/holo/reverse: `{'normal': 123, 'holo': 72, 'reverse_holo': 148}` |
| Availability agreement on common exact identities | N/A | `{'normal': 193, 'holo': 193, 'reverse_holo': 193}` agreements; `{'normal': 0, 'holo': 0, 'reverse_holo': 0}` disagreements | Compared against Pokémon TCG API |
| Reproducibility | `BLOCKED` | Cached JSON response | Cached JSON set + card responses |
| Maintenance risk | High while anti-automation blocks access | Medium; provider response and reverse semantics must be revalidated | Medium/high; TCGdex documents known ID-mapping caveats |
| Source transparency | Direct marketplace, but not obtained here | Explicit `cardmarket` and `tcgplayer` objects | Explicit provider objects, but per-variant mapping is still evolving |

The table is an audit comparison, not a pricing policy change. TCGplayer values remain USD secondary references; no currency conversion is performed.
