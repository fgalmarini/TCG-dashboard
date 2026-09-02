# Pokémon 151 Metric → Finish group analysis

The Price Guide supplies metric-family column names, not a physical finish label. Group patterns below are observations/inferences only and are never promoted to exact mappings without product-level evidence.

- Source metric columns: base `['low', 'trend', 'avg1', 'avg7', 'avg30']`; foil `['low-holo', 'trend-holo', 'avg1-holo', 'avg7-holo', 'avg30-holo']`
- Base relationships reviewed: `137`
- Foil relationships reviewed: `133`

| finish scope | compatible finishes | metric family | status | count |
|---|---|---|---:|---:|
| `multiple` | `['holo', 'reverse_holo']` | `base` | `AMBIGUOUS` | 23 |
| `multiple` | `['holo', 'reverse_holo']` | `foil` | `AMBIGUOUS` | 23 |
| `multiple` | `['normal', 'reverse_holo']` | `base` | `AMBIGUOUS` | 110 |
| `multiple` | `['normal', 'reverse_holo']` | `foil` | `AMBIGUOUS` | 110 |
| `unknown` | `['holo']` | `base` | `UNRESOLVED` | 2 |
| `unknown` | `[]` | `base` | `UNRESOLVED` | 2 |

Observed source facts:

- 133 exact products expose both base and foil metric families.
- 4 exact products expose base metrics only; foil columns are absent or zero.
- `idMetacard`, metric family names and the existence of a single internal printing are not treated as finish evidence.
- No global `base=normal` or `foil=reverse_holo` inference is applied.
