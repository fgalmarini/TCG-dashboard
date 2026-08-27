# Fase 5 (parcial) — Backfill de catálogo Magic vía Scryfall (Sprint Contract)

**Para: agente `developer`. Depende de Fase 3 (schema, commiteado) y Fase 4
(`docs/plans/fase4-importer-sprint-contract.md`, cerrada — no se re-abre). Origina en
`docs/plans/Revisión-fases 2-4 — Catálogo externo .md`, que reemplaza para Magic el mecanismo de
self-healing de `docs/plans/fase2-cardmarket-hallazgos-y-schema.md` sección 6. Decisiones
estructurales registradas en `conventions.json` → `TCG-DEC-001`/`TCG-DEC-002`.**

---

## 0. Fuente verificada

`GET https://api.scryfall.com/cards/cardmarket/:id` — acepta directamente el
`idProduct` de Cardmarket (`cardmarket_id` en Scryfall) y devuelve el objeto Card
completo. Gratis, sin API key. Cortesía de rate limit: ~100-150ms entre requests (no es
un límite duro, pero Scryfall lo pide). Cumple `docs/ARCHITECTURE.md` — no es scraper ni
endpoint no documentado, es la API pública oficial-de-facto del ecosistema Magic.

Campos relevantes del objeto Card: `set`, `set_name`, `collector_number`, `name`,
`frame_effects` (`showcase`, `extendedart`, etc.), `border_color` (`borderless`),
`promo_types`, `finishes` (`foil`/`nonfoil`/`etched`), `image_uris`.

`backend/importer/images.py:20-43` (`resolve_magic_image_url`) ya pega contra este
mismo endpoint pero solo extrae `image_url` — no alcanza para este backfill, que
necesita el objeto completo. No modificar `images.py`; este script hace su propio
fetch (evita duplicar la llamada HTTP entre dos módulos para la misma card).

## 1. Layout

Nuevo archivo: `backend/scripts/scryfall_backfill.py`. Directorio nuevo (`backend/scripts/`
no existe todavía), deliberadamente separado de `backend/importer/` — **no tocar nada
dentro de `backend/importer/`**.

Import strategy: este script NO reusa `backend/importer/db.py` vía manipulación de
`sys.path`. Duplica su propio `connect()` mínimo (mismo patrón de 13 líneas:
`sqlite3.connect` + `PRAGMA foreign_keys = ON`, apuntando a
`backend/db/tcg_dashboard.db`) — es más simple que acoplar dos carpetas para 4 líneas
de código. Documentar esta elección en el docstring del módulo (`AGENTS.md`).

Script de backfill de una sola corrida (no un servicio permanente). Si en el futuro se
amplía el scope de expansiones LOTR, se vuelve a correr con el scope ampliado.

## 2. Responsabilidades del script

1. **Migración idempotente al arrancar** (no depender de re-correr `schema.sql`, que es
   `CREATE TABLE IF NOT EXISTS` y por lo tanto no-op sobre la DB existente):
   - `PRAGMA table_info(cards)` → si faltan `data_source` o `scryfall_raw`, ejecutar
     `ALTER TABLE cards ADD COLUMN data_source TEXT` y
     `ALTER TABLE cards ADD COLUMN scryfall_raw TEXT`.
   - Actualizar también `backend/db/schema.sql` (bloque `CREATE TABLE cards`) agregando
     ambas columnas, para que una DB nueva las tenga desde el `init_db.py` inicial.
     `data_source` con `CHECK (data_source IS NULL OR data_source IN ('scryfall',
     'cardmarket_heuristic', 'manual'))`, `scryfall_raw` sin constraint (JSON crudo).
2. Filtrar `cardmarket_products` por `cardmarket_id_expansion IN (5285, 5308, 5396)`
   (mismo scope que Fase 2/4).
3. Por cada `cardmarket_id_product` del filtro: `GET
   https://api.scryfall.com/cards/cardmarket/{id}`, con el intervalo de cortesía de la
   sección 0. Con la respuesta, completar directamente (no self-heal):
   - `expansions.name`, `expansions.set_code` (desde `set`/`set_name`)
   - `cards.name`, `cards.card_number` (desde `collector_number`)
   - `cards.printing_variant` y `cards.variant_label` — ver regla de mapeo abajo
   - `cards.image_url = image_uris.normal`, `cards.image_source = 'scryfall'`
   - `cards.data_source = 'scryfall'`, `cards.scryfall_raw` = JSON crudo de la respuesta
4. **Regla de mapeo `printing_variant` / `variant_label`** (confirmada con Facundo antes
   de implementar — afecta la semántica de una columna ya usada por Fase 3/4):
   - `printing_variant` sigue restringido al enum existente del schema
     (`'normal' | 'suggested_parallel' | 'confirmed_parallel' | 'other'`) — Scryfall no
     tiene ese concepto, no se amplía el enum.
   - Default `'normal'` cuando la carta es nonfoil, `border_color = 'black'`, y
     `frame_effects` vacío (impresión estándar sin variante visual).
   - `'other'` para cualquier combinación con `frame_effects` no vacío,
     `border_color != 'black'`, `finishes` incluye `foil`/`etched`, o `promo_types` no
     vacío — es decir, cualquier variante visual real cae acá, sin intentar distinguir
     "rara" vs "no rara" (eso no es lo que este pivot resuelve).
   - `'suggested_parallel'`/`'confirmed_parallel'` no se asignan desde Scryfall en este
     backfill (son estados del flujo de self-healing de precios, no de catálogo) — si
     una card ya tenía uno de esos dos valores antes del backfill, no pisarlo.
   - `variant_label`: string legible armado a partir de `frame_effects` + `border_color`
     + `finishes` + `promo_types` (ej. "Showcase Foil Ringframe", "Borderless Foil",
     "Art Series Gold Stamp") — mismo vocabulario que apareció al cargar la colección
     real. Definir el armado exacto (orden de términos, capitalización) en el propio
     script; no hace falta un mapeo exhaustivo previo, con que sea determinístico y
     legible alcanza.
5. **Reporte final**, mismo patrón que `backend/importer/report.py` (dataclass +
   `print_summary()`, nunca silencioso — `docs/ARCHITECTURE.md`):
   - Cuántos de los 757 productos resolvieron OK.
   - Cuántos no matchearon (no debería haber ninguno, ya que vienen del mismo
     `idProduct` que Scryfall indexa — pero reportar, no asumir).
   - Detalle por producto de los que fallaron (idProduct, motivo).
   - Distribución de `printing_variant` asignado (cuántos `normal` vs `other`).

## 3. Fuera de alcance de este sprint

- Ampliar a todo Magic (no solo LOTR/scope de expansiones 5285/5308/5396).
- Backfill de imágenes/metadata para Pokémon u One Piece.
- Cualquier cambio a la lógica de precios (`market_price_history`, self-healing de
  precios existente).
- Cualquier cambio dentro de `backend/importer/`.
- Fase 5 completa (alta manual de colección) — este contract cubre solo el
  enriquecimiento de catálogo de Magic.
- Supabase (`TCG-DEC-003`, diferido).

## 4. Verificación

1. `sqlite3 backend/db/tcg_dashboard.db "PRAGMA table_info(cards)"` antes y después —
   confirmar que `data_source`/`scryfall_raw` no existían y ahora existen.
2. Correr el script sobre la DB real, revisar el reporte final: confirmar que se
   procesaron los 757 productos del scope y ver el desglose OK/no-match.
3. Spot-check manual: `SELECT name, printing_variant, variant_label, data_source FROM
   cards WHERE data_source='scryfall' LIMIT 10` — al menos 2-3 cards con variantes
   conocidas (Showcase Foil Ringframe, Borderless Foil, Art Series Gold Stamp) deben
   tener `variant_label` coherente con esos nombres.
4. Correr el script una segunda vez sobre la misma DB — confirmar en el reporte que no
   duplica filas ni pisa datos ya buenos con valores distintos (idempotencia).
5. Confirmar que ninguna tabla fuera de `cards`/`expansions` cambió de estructura
   (`cardmarket_products`, `cardmarket_product_mappings`, `market_price_history`,
   `collection_items`, `want_list_items` intactas).

---

## 5. Resultado real de la corrida

**Regla de mapeo ajustada respecto al §2.4 original.** Al implementar contra datos
reales se detectó que `finishes` casi siempre incluye `foil` (describe qué acabados
*existen* para la impresión, no cuál tiene el producto puntual de Cardmarket) y que
`promo_types` casi siempre incluye `universesbeyond` (flag de todo el set LTR, no de la
carta) — con la regla original esto disparaba `other` en el 92.6% de los casos,
incluyendo tierras básicas sin variante real. Regla final, confirmada por Facundo:

```python
is_other = (
    bool(frame_effects)
    or border_color != "black"
    or "etched" in finishes
    or full_art
    or bool(real_promo_types)  # promo_types sin 'universesbeyond'
)
```

Se agregó `full_art` al chequeo (no estaba en el §2.4 original) tras confirmar contra
los 551 productos ya resueltos que aparece en 76/551 (14%) — cubre los basic lands
full-art de LTR, que no tienen `frame_effects` ni `border_color` distinto de negro.

**Corrida final contra `backend/db/tcg_dashboard.db` (DB real):**
- 757/757 productos en scope procesados.
- 550 resueltos OK, 206 sin match (404 de Scryfall — Art Series y tokens de la
  expansión 5308 no indexados por `idProduct`, contradice la expectativa original del
  §2.5 de "no debería haber ninguno", pero está reportado, no asumido), 1 colisión
  UNIQUE reportada (dos tokens de sets Scryfall distintos coinciden en
  `collector_number=3` dentro del mismo `cardmarket_id_expansion` local — no resuelta,
  queda igual que estaba).
- Distribución `printing_variant`: `normal`=193, `other`=317, `suggested_parallel`=40
  (protegidas, no pisadas). 193+317+40=550, cuadra exacto.
- Idempotencia confirmada dos veces sobre la DB real — mismos resultados, `cards` se
  mantiene en 12167 filas, sin duplicar.
- Tablas fuera de scope intactas: `cardmarket_products`=12867,
  `cardmarket_product_mappings`=12867, `market_price_history`/`collection_items`/
  `want_list_items` sin cambios.
- Spot-check: `Plains`/`Island`/`Forest` full-art → `other`/"Full Art Foil"; sus
  versiones base → `normal`. `Gandalf the Grey` showcase-borderless →
  `other`/"Showcase Borderless Foil Booster Fun". `The One Ring` serializada →
  `other`/"Borderless Full Art Foil Booster Fun Serialized".

**Hallazgos adicionales encontrados y corregidos en el mismo pase (fuera del §2 original,
aprobados por Facundo antes de aplicarlos):**
1. `backend/importer/images.py:20-43` tenía el mismo bug de headers faltantes
   (`User-Agent`/`Accept`) contra el mismo endpoint de Scryfall — 400 en el 100% de los
   casos. Corregido, con `backend/importer/test_images.py` nuevo (6 tests, incluye
   regresión del bug de headers). Commit separado del backfill.
2. `expansions.name`/`set_code` para `cardmarket_id_expansion=5308` se pisaba con
   metadata de tokens (`layout='token'`) en vez de cartas reales — "último que escribe
   gana". Corregido con precedencia no-token (`_write_expansion_metadata()`): no-token
   siempre escribe, token solo si `name IS NULL`. Resultado real:
   `"Tales of Middle-earth Tokens"/tltr` → `"The Lord of the Rings: Tales of
   Middle-earth"/ltr`.

Suite completa (`test_schema.py` + `backend/importer/`, incl. `test_images.py` nuevo):
50/50 verde.

**Fase 5 (parcial) cerrada.** Ver `conventions.json` → `TCG-DEC-002` (actualizado con
este resultado). Fase 5 completa (alta manual de colección) y Supabase siguen
pendientes, sin cambios por este sprint.
