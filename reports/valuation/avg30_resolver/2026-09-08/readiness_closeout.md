# VAL-AVG30-006B — Backfill Readiness Closeout

- Resolver correctness: `RESOLVER_VALID`
- Backfill readiness: `NOT_READY_FOR_BACKFILL`
- Eligible valuations: `367`
- NULL rows: `3150`

## Causa exacta de NOT_READY

La condición que disparó el `NOT_READY` del resolver fue `technical_resolver_correct=True` combinado con `proposed_scopes` igual a todos los grupos evaluados y al menos un grupo con cero filas elegibles. No fue un fallo de clasificación. La auditoría adicional detecta 67 de las 367 elegibles sin provenance/hash/manifest; esas 67 requieren evidencia antes de aplicarse, pero no invalidan las otras 300.

| Causa | Scope | Juegos | Filas | Bloquea las 367 |
|---|---|---|---:|---|
| DATA_COVERAGE_BLOCK | catalog | pokemon | 362 | No |
| SCOPE_SPECIFIC_BLOCK | collection/wishlist | magic, pokemon, one_piece | 164 | No |
| SYSTEMIC_IDENTITY_BLOCK | catalog/collection/wishlist | magic, one_piece, pokemon | 1050 | No |
| MISSING_PROVENANCE | catalog:magic | magic | 67 | No (67 afectadas) |

## Elegibles

- Por scope: `{'catalog': 367}`
- Por juego: `{'magic': 367}`
- Por status: `{'ESTIMATED': 367}`
- Por metric family: `{'base': 367}`
- Resultado: 367 `ESTIMATED`, 0 `EXACT`; 367 base, 0 foil/alt.

## NULL

- Distribución: `{'FINISH_UNRESOLVED': 14, 'IDENTITY_UNRESOLVED': 1050, 'LANGUAGE_UNRESOLVED': 97, 'MISSING_AVG30': 303, 'PRODUCT_UNRESOLVED': 1686}`
- Aceptables por limitación conocida: FINISH_UNRESOLVED=14, LANGUAGE_UNRESOLVED=97, MISSING_AVG30=303.
- Bloqueos de cobertura/identidad: PRODUCT_UNRESOLVED=1686, IDENTITY_UNRESOLVED=1050.
- No hay resultados sin clasificación ni promoción insegura.

## Readiness por scope

| Scope | Decisión |
|---|---|
| Collection | NOT_READY |
| Wishlist | NOT_READY |
| Pokémon 151 | NOT_READY |
| Magic LOTR / catalog:magic | READY_FOR_PARTIAL_BACKFILL condicionado a provenance completa |

## Portfolio impact

La simulación productiva permanece sin cambios. Todas las filas Collection/Wishlist resultaron NULL, por lo que las 367 elegibles de catalog:magic no impactan portfolio.

| Scope | Legacy | Proposed Avg30 | Difference | Difference % | Valued units | Unvalued units | Coverage |
|---|---:|---:|---:|---:|---:|---:|---:|
| Collection | EUR 223.78 | EUR 0.00 | EUR -223.78 | -100.0% | 0 | 128 | 0.0% |
| Wishlist | EUR 155.25 | EUR 0.00 | EUR -155.25 | -100.0% | 0 | 39 | 0.0% |

Por juego en Collection: Magic legacy EUR 165.23 / propuesta EUR 0.00 / 0 de 100 unidades; Pokémon EUR 0.00 / EUR 0.00 / 0 de 5; One Piece EUR 58.55 / EUR 0.00 / 0 de 23. Wishlist: Magic EUR 155.25 / EUR 0.00 / 0 de 19; Pokémon EUR 0.00 / EUR 0.00 / 0 de 20.

## Auditoría de muestra

Se auditaron 20 elegibles representativas del único estrato disponible: Magic nonfoil/base, con precios bajos, medios y altos. Todas tienen Product ID, canonical, idioma/finish compatibles, `CARDMARKET_AVG30`, Avg30 positivo y sin fallback. No existen elegibles Pokémon, One Piece, Collection, Wishlist ni Magic foil en este run; por tanto no se puede fabricar una muestra de esas categorías.

La muestra completa, con evidencia y provenance por fila, está en `readiness_closeout.json`.

## Decisión final

`RESOLVER_VALID` para clasificación y cálculo; `NOT_READY_FOR_BACKFILL` global por scopes propuestos sin cobertura y 67 elegibles sin provenance auditable. Un backfill parcial delimitado a las filas Magic con provenance completa sería seguro dejando los NULL intactos.
