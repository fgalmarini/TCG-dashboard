# Sprint Contract — Wishlist Planning Mode

## Objetivo

Convertir la wishlist existente en una herramienta práctica de planificación de
compras para Magic/LOTR, sin crear una lista paralela ni introducir otros TCG.

## Contrato funcional

- `wanted`, `acquired` y `removed` permanecen en `wishlist_items`.
- `mark-acquired` solo cambia la wishlist; nunca crea ni modifica Collection.
- `removed` es soft-delete y los históricos pueden restaurarse a `wanted`.
- El resumen es global e independiente de filtros: `wanted`, `acquired`,
  `missing_price` y `unmatched` cuentan filas; `estimated_total` suma únicamente
  `current_price * quantity_wanted` para filas wanted.
- La prioridad admite `high`, `medium`, `low` y `none`, en ese orden.
- `target_price` y `max_price` son opcionales y no alteran el total estimado.
- Buying Mode, CSV y la vista normal reutilizan los mismos filtros.

## Integridad y matching

- `target_price <= max_price` cuando ambos existen.
- Timestamps mutuamente consistentes con el estado; restaurar limpia ambos.
- `wishlist_items.card_id` continúa siendo obligatorio.
- Collection unmatched se resuelve mediante candidatos locales y selección explícita.
- Un mapping Cardmarket solo se actualiza si es el mapping legacy inequívoco del
  producto y no es utilizado por otras Collection rows; si no, solo se relinka la fila.

## Verificación

Tests backend, build TypeScript/Vite, `git diff --check`, migración sobre copia temporal
de SQLite, `PRAGMA integrity_check` y `PRAGMA foreign_key_check`.
