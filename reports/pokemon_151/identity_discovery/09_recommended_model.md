# Pokémon 151 — Recommended Discovery Model

This is a discovery recommendation only. No schema, DB or catalog change was made.

## Identity hierarchy

```text
game / set / collector_number
  -> numbered printing identity
  -> finish (normal / holo / reverse_holo)
  -> treatment (stamped / cosmos / other, nullable and source-backed)
  -> Cardmarket idProduct
```

## Rules

- `collector_number` is mandatory for numbered printing identity.
- `rarity` is separate from finish.
- `idProduct` is provider identity; `idMetacard` is grouping evidence only.
- Same-name cards with different numbers never share uniqueness.
- A single provider Product ID may carry multiple finish evidences; the model must not invent products.
- Ambiguous mappings remain unresolved and cannot feed automatic pricing/import.

## Provenance

Keep source, method, confidence and notes per important derived datum. Retain external candidate IDs without promoting them to local Cardmarket identity until validated.

Suggested next-step input: `POKEMON-151-001` may be designed only from the explicit statuses and blockers in this audit; this sprint does not execute it.
