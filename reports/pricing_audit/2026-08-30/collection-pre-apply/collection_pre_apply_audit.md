# Collection Pricing — Final Approval + Pre-Apply Gate

Fecha de auditoría: `2026-08-30`
Scope: `collection`
Fuente: Cardmarket Product Catalogue + Price Guide local, manifiesto `54189435f777e9746d116ff2e4e83ab5071dc63465a645a923edce2b1307fb2c`.

## Approval

- Manual review rows: **76**.
- Magic aprobadas: **53**.
- One Piece aprobadas: **23**.
- Total aprobadas: **76**.
- Todas las filas tienen `approved=true`, `proposed_status=EXACT`, selección única y hash recalculado por `audit_pricing.collection_review_hash`.
- `collection_manual_review.csv` no fue aprobado mediante el workflow: el workflow lo leyó como entrada y el apply real no se ejecutó.

Magic queda en `97 / 97 EXACT`; One Piece en `23 / 23 EXACT`; Collection en `120 / 120 EXACT`.

Magic Gold-Stamped: `PENDING BEFORE: 44`, `EXACT_RECOVERED: 44`, `MANUAL_WEB_REVIEW: 0`, `PHYSICAL_CONFIRMATION_REQUIRED: 0`.
La clasificación consolidada Magic es `Original manual review: 53`, `EXACT_RECOVERED: 53`, `MANUAL_WEB_REVIEW: 0`, `PHYSICAL_CONFIRMATION_REQUIRED: 0`.

Las provenance gaps de Magic se conservan (`45`); para Art Series Frodo item 108 se registra `A16g` como conflictiva/incorrecta y para Samwise item 128 `A52g` como conflictiva/incorrecta.

## Pricing dry-run

Comando ejecutado:

```text
./update-prices --dry-run --scope collection --source-dir price-history --collection-review reports/pricing_audit/2026-08-29/collection-first/collection_manual_review.csv
```

Resultado: **SUCCESS**, `NOT_APPLIED`, integridad `ok`, foreign keys `ok`.

- Exact con el metric seleccionado: **119 priced + 1 UNPRICED = 120 EXACT**.
- Cardmarket `Low` base disponible: **120 / 120**, pero item 65 es foil y ese valor corresponde a otra variante/finish.
- Item 65: dry-run propone `current_price=NULL`; simulación temporal persiste `current_price=NULL`, `selected_metric=Foil Low`, con `Foil Low=NULL`.
- No existe fallback al `Low` base para item 65.
- Cardmarket Low current: **YES**.
- Cardmarket Trend separado: **YES**.
- CardTrader current price fallback propuesto: **0**.
- Proposed unsafe: **0**.
- No se usaron precios, seller listings ni candidato más barato/caro para identidad.

El detalle por item está en [`collection_pre_apply_audit.csv`](./collection_pre_apply_audit.csv) y el delta propuesto en [`collection_price_changes.csv`](./collection_price_changes.csv). Las fórmulas dealer/trade permanecen derivadas y no se almacenan como source price.

## Critical regressions

| Caso | Estado | idProduct | Low | Trend |
|---|---|---:|---:|---:|
| EB02-061A | SAFE | 808172 | EUR 28.00 | EUR 44.59 |
| Mihawk base | SAFE | 768324 | EUR 0.02 | EUR 1.10 |
| Mihawk alternate art | SAFE | 768325 | EUR 14.00 | EUR 17.23 |
| Cavendish Box Topper | SAFE | 768247 | EUR 0.50 | EUR 0.92 |
| King JP alternate art | SAFE | 768359 | EUR 2.89 | EUR 6.57 |
| Magic Gold-Stamped | SAFE | — | — | — |

`EB02-061A` conserva EB02 y no PRB02. King usa el target local `printing_id=15505`; no se creó mapping.

## API / simulation

- Apply temporal sobre copia: **SUCCESS / COMMITTED**.
- Apply real: **NO**.
- Collection API rows simuladas: **120**; expected: **120**.
- Current Cardmarket resolutions simuladas: **120 / 120**, con **119 priced + 1 UNPRICED**.
- Approved overrides simulados: **76 / 76**.
- Duplicate rows: **0**.
- Duplicate incompatible `idProduct`: **0**.
- Historical price resurrection: **0**.
- Collection items y Wishlist items sin cambios en la copia (`120` y `5`).

La simulación también verificó King `card_id=15505` → `768359`, EB02 `808172`, Mihawk base/alternate separados y materialización transaccional de cualquier Product Catalogue row ausente, sin modificar mappings.

## DB real

- SHA-256 before: `e155b0776922ac72e191a98b30b6bb44427664cf2ef0ead4f9c6d5e7c53ec225`.
- SHA-256 after: `e155b0776922ac72e191a98b30b6bb44427664cf2ef0ead4f9c6d5e7c53ec225`.
- Unchanged: **YES**.
- `PRAGMA integrity_check`: `ok`.
- `PRAGMA foreign_key_check`: sin filas.

## Tests

- Backend: pendiente de ejecución final.
- Frontend build: pendiente de ejecución final.
- `git diff --check`: pendiente de ejecución final.

## Pre-apply verdict

**SAFE**: item 65 recibe correctamente `current_price=NULL`; su `Low` base no se usa porque corresponde a otro finish y no existe fallback. Resultado: **119 priced + 1 UNPRICED = 120 EXACT**.

Si se decide aplicar posteriormente, el comando autorizado sería:

```text
./update-prices --apply --scope collection --source-dir price-history --collection-review reports/pricing_audit/2026-08-29/collection-first/collection_manual_review.csv
```

Este comando **no fue ejecutado**.
