# VAL-AVG30-005 — Reestructuración del modelo de valuación

## Estado

Foundation implementada de forma aditiva. La activación de Avg30 como valor económico
principal queda fuera de este contrato.

## Semántica

`Cardmarket Avg30` representa una estimación de valor de mercado, no un precio actual
exacto. `avg7`, `avg1`, `trend` y `low` se conservan como métricas auxiliares.

`current_price` mantiene durante esta fase su semántica legacy actual basada en Low.
No es alias de `valuation_value`.

## Identidad y elegibilidad

La elegibilidad reutiliza, en este orden, `match_status`, `language_scope`,
`cardmarket_product_printing_scopes` y `cardmarket_product_metric_mappings`.
No se duplican estados de identidad cuando pueden derivarse de esas estructuras.

Una resolución puede ser `ESTIMATED` solo con Product ID validado, identidad canónica y
set correctos, sin conflicto material de idioma/finish/variante/arte y con Avg30 usable.
Un producto que agrupa varias printings no se fuerza a una printing física.

`EXACT` queda reservado para evidencia completa de printing, idioma, finish, variante y
métrica.

## Modelo de resolución

`printing_price_resolutions` conserva Low, Trend, Avg1, Avg7 y Avg30 históricos y añade:

```text
valuation_status   EXACT | ESTIMATED
valuation_method   CARDMARKET_AVG30
valuation_value    valor de la resolución, independiente de current_price
reason             motivo de una valuación nula
```

Los motivos de incertidumbre se representan mediante el modelo existente o, cuando sea
necesario para preservar el snapshot de la decisión, mediante `reason`: `FINISH_UNRESOLVED`,
`LANGUAGE_UNRESOLVED`, `IDENTITY_UNRESOLVED` y `MISSING_AVG30`.

## Compatibilidad

La API expone los nuevos campos de forma aditiva. Overview, Collection, Wishlist,
portfolio totals, P/L, ROI, ordenamientos y valores visibles continúan usando el flujo
legacy durante esta fase.

La transición de `current_price` a `valuation_value` como valor económico principal
requiere un contrato posterior con migración, activación y regresión propia.

## Validación

- Migración aditiva e idempotente en bases nuevas y existentes.
- Product ID/identidad elegibles con Avg30 producen `ESTIMATED`.
- Finish o idioma no demostrables producen valuación nula con motivo explícito.
- `current_price`, histórico y cálculos productivos permanecen sin cambios.
- Integridad SQLite, backend tests, `git diff --check` y build frontend si corresponde.

## VAL-AVG30-008 — Closeout de consumo global

Estado: **CLOSED / READY_FOR_VALUATION_UI**.

Collection y Wishlist exponen de forma aditiva el contrato completo:

```text
valuation_status
valuation_method
valuation_value
valuation_currency
valuation_source
valuation_reason
```

El consumo es scope-aware y set-based: una valuación scoped del item tiene precedencia
sobre la global, sin fallback entre idiomas. Collection usa `ci.language_id`; Wishlist
usa `COALESCE(wi.language_id, c.language_id)`. No se crearon filas scoped durante 008.

Baseline validado el `2026-09-09`:

- `367` global valuations.
- `0` scoped valuations.
- Collection: `68/97` compatible.
- Wishlist `wanted`: `0` compatible de `18` filas.
- Pokémon: `NULL`.
- One Piece: `NULL`.

`current_price`, `market_value`, Overview, P/L, ROI y `WishlistSummary` continúan
usando exclusivamente su semántica legacy. `valuation_value` queda disponible para
la futura etapa de activación, pero no es alias ni reemplazo del valor legacy.
