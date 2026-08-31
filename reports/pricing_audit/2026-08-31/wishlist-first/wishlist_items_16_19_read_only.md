# Wishlist items 16–19 — reporte read-only

Fecha de auditoría: 2026-08-31  
Scope: `wishlist`  
Status seleccionado: `wanted`  
Modo: solo lectura; no se ejecutó `apply`, migración ni escritura contra la DB.

## Seguridad y fuente

- DB auditada: `/Users/facundogalmarini/Desktop/TCG DASHBOARD/backend/db/tcg_dashboard.db`
- SQLite: `mode=ro`, `PRAGMA query_only=1`
- SHA-256 leído: `8988a31eb5e4e5f57f8080b18f413728ffcda1fb6f9307fde1b710155811e345`
- SHA antes/después de la lectura: idéntico
- `PRAGMA integrity_check`: `ok`
- `PRAGMA foreign_key_check`: `[]`
- Fuente Cardmarket: `price-history/magic/products_singles_1.json` y
  `price-history/magic/price_guide_1.json`
- No se creó ni modificó una resolución Wishlist. La DB actual todavía no contiene
  `wishlist_item_id` en `printing_price_resolutions`; por eso el current DB state de
  estos items es `NULL` y no se trata como un write candidato aplicado.

## Resumen del universo activo

| Métrica | Resultado |
| --- | ---: |
| Items wanted | 4 |
| Unidades wanted | 4 |
| Identidad EXACT | 1 / 4 (25.00%) |
| Cobertura EXACT por unidades | 1 / 4 (25.00%) |
| Legacy value actual | EUR 0.00 |
| Resolved Low diagnostic | EUR 0.30 |
| Estimated value coverage | 100.00%* |
| Value without exact resolution | EUR 0.00 |
| Revisión manual requerida | 3 / 4 |

\* La cobertura de valor usa como denominador el valor con Low exacto más valor
current no-EXACT disponible. Los tres items bloqueados no aportan valor estimado;
la cobertura de items/unidades es la métrica que muestra que solo 1 de 4 está
resuelto.

## Detalle por Wishlist item

### Item 16 — Ancient Tomb

- `wishlist_item_id`: `16`
- `card_id / printing_id`: `14205 / 14205`
- Nombre: `Ancient Tomb`
- Set: `ltc`
- Collector number: `357`
- Finish: `foil`
- Treatment: `Realms & Relics`
- Status de identidad Cardmarket: `AMBIGUOUS`
- Categoría de conflicto: `TREATMENT` (`ambiguous_identity`)
- Motivo del bloqueo: el nombre de producto bulk `Ancient Tomb` no prueba el
  tratamiento físico local `Realms & Relics`; no se acepta el candidato como
  identidad exacta.
- Candidatos considerados: `717914 — Ancient Tomb — Tales of Middle-earth
  Commander (idExpansion 5387)`
- Candidato seleccionado: ninguno; el ID almacenado/Scryfall `717914` queda como
  candidato diagnóstico, no como resolución.
- Cardmarket Low / Trend / AVG7 disponibles para el finish seleccionado:
  `EUR 154.95 / EUR 187.49 / EUR 188.29` (Foil Low / Foil Trend / Foil AVG7)
- Current DB price: `NULL`; current resolution: ninguna
- Revisión manual: **sí**

### Item 17 — Access Tunnel

- `wishlist_item_id`: `17`
- `card_id / printing_id`: `14132 / 14132`
- Nombre: `Access Tunnel`
- Set: `ltc`
- Collector number: `294`
- Finish: `nonfoil`
- Treatment: no informado
- Status de identidad Cardmarket: `EXACT`
- Categoría de conflicto: ninguna
- Motivo del bloqueo: ninguno; la identidad está validada por el ID Cardmarket
  `717343`.
- Candidatos considerados: `717343 — Access Tunnel — idExpansion 5296`
- Candidato seleccionado: `717343` (selección diagnóstica; no persistida)
- Cardmarket Low / Trend / AVG7 disponibles:
  `EUR 0.30 / EUR 0.73 / EUR 0.70`
- Current DB price: `NULL`; current resolution: ninguna
- Revisión manual: **no**

### Item 18 — Abyssal Persecutor

- `wishlist_item_id`: `18`
- `card_id / printing_id`: `14540 / 14540`
- Nombre: `Abyssal Persecutor`
- Set: `ltc`
- Collector number: `525`
- Finish: `nonfoil`
- Treatment: `Borderless`
- Status de identidad Cardmarket: `MISMATCH`
- Categoría de conflicto: `SET/EXPANSION` (`wrong_expansion`); también queda
  evidencia de tratamiento no probado.
- Motivo del bloqueo: el candidato almacenado `735313` pertenece a la expansión
  `The Lord of the Rings: Tales of Middle-earth` (`idExpansion 5489`), mientras el
  printing Wishlist es `ltc`; no se permite usarlo como fallback.
- Candidatos considerados: `735313 — Abyssal Persecutor — The Lord of the Rings:
  Tales of Middle-earth (idExpansion 5489)`
- Candidato seleccionado: ninguno; candidato rechazado por conflicto de expansión.
- Cardmarket Low / Trend / AVG7 disponibles en el candidato rechazado:
  `EUR 167.67 / EUR 123.18 / EUR 97.65`
- Current DB price: `NULL`; current resolution: ninguna
- Revisión manual: **sí**

### Item 19 — Andúril, Flame of the West

- `wishlist_item_id`: `19`
- `card_id / printing_id`: `13726 / 13726`
- Nombre: `Andúril, Flame of the West`
- Set: `ltr`
- Collector number: `746`
- Finish: `foil`
- Treatment: `Borderless`
- Status de identidad Cardmarket: `AMBIGUOUS`
- Categoría de conflicto: `TREATMENT` (`ambiguous_identity`)
- Motivo del bloqueo: el nombre de producto bulk no prueba el tratamiento físico
  local `Borderless`; no se acepta el candidato como identidad exacta.
- Candidatos considerados: `735375 — Andúril, Flame of the West — The Lord of the
  Rings: Tales of Middle-earth (idExpansion 5489)`
- Candidato seleccionado: ninguno; el ID almacenado/Scryfall `735375` queda como
  candidato diagnóstico, no como resolución.
- Cardmarket Low / Trend / AVG7 disponibles para el finish seleccionado:
  `EUR 205.00 / EUR 190.71 / EUR 199.07` (Foil Low / Foil Trend / Foil AVG7)
- Current DB price: `NULL`; current resolution: ninguna
- Revisión manual: **sí**

## Decisión de pricing

- No se ejecutaron writes. Los 4 items fueron auditados como work items del dry-run;
  solo el item `17` tiene identidad EXACT y precio Low diagnostic disponible.
- El único item que podría pasar identidad automática es el `17`; su Low
  `EUR 0.30` es diagnóstico y no current persistido.
- Los items `16`, `18` y `19` permanecen bloqueados por tratamiento o expansión.
- No se usaron Trend, AVG7, históricos, CardTrader ni candidatos ambiguos como
  fallback.
