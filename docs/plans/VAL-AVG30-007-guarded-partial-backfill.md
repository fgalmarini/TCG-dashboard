# VAL-AVG30-007 — Guarded Partial Backfill Apply

## Contrato

Aplicar únicamente el manifest aprobado de VAL-AVG30-006C, limitado a
`resolution_scope=global`, `game=magic`, `metric_family=base` y
`CARDMARKET_AVG30`. El comando [apply_avg30_backfill.py](../../backend/scripts/apply_avg30_backfill.py)
es read-only por defecto; escribir requiere `--apply`.

El preflight valida el hash del manifest, el SHA de la DB, las 367 filas autorizadas,
la evidencia local y el Avg30 exacto. Cualquier cambio aborta antes de la transacción.
El apply se ejecuta sobre una copia temporal, con rollback transaccional, postflight de
integridad y reemplazo de la DB únicamente después de validar la copia.

Se insertan resoluciones valuation-only con `is_current=0` para no alterar el currentness
legacy. `current_price`, métricas legacy, Collection, Wishlist, Overview, P/L y ROI no se
modifican. La valuación vigente se obtiene por las filas con `valuation_status` no nulo,
no por `is_current`.

La simulación y el apply son idempotentes mediante card, idioma, Product ID, método y
snapshot. Los reportes se generan en `reports/valuation/avg30_backfill/2026-09-09/`.

## Resultado

La DB original carecía de las columnas aditivas `valuation_*`. Se ejecutó esa migración
únicamente sobre una copia temporal, se reemitió el manifest con su nuevo SHA y se aplicó
la copia validada. El resultado fue `PARTIAL_BACKFILL_APPLIED`: 367 inserts, 0 rechazos,
integridad SQLite/FK correcta y segunda ejecución con 367 unchanged.
