# Fase 5 — Alta manual de colección (Sprint Contract)

**Para: agente `developer` (Claude Code CLI), ejecutando en el repo
`/Users/facundogalmarini/Desktop/TCG DASHBOARD`. Depende de Fase 3 (schema,
commiteado), Fase 4 (`fase4-importer-sprint-contract.md`, cerrada) y Fase 5 parcial
(`fase5-scryfall-magic-backfill-sprint-contract.md`, cerrada — backfill de catálogo
Magic vía Scryfall). Especifica el "próximo paso (Fase 5, trabajo principal)" descrito
en `AGENTS.md` §23: alta manual de colección + UI de confirmación por lote para
One Piece `ambiguous`. Decisiones de mecánica confirmadas con Facundo el 2026-08-24
(sesión Cowork), registradas en `conventions.json` → `TCG-DEC-004`.**

---

## 0. Precondición bloqueante

`coleccion-a-cargar.csv` (raíz del repo) tiene 153 filas con la distribución esperada
(115 `magic`, 30 `one_piece`, 8 `pokemon` — coincide con lo estimado en
`conventions.json` TCG-DEC-001 para Pokémon), pero **todas las columnas de datos están
vacías** salvo `game`, `status=KEEP` y `quantity=1`. Es una plantilla, no la colección
real todavía.

**Nada de este sprint puede correrse hasta que Facundo complete el CSV** con al mínimo
`card_name` por fila (idealmente también `set_hint`/`card_number`/`variant` cuando los
tenga a mano, y `purchase_price`/`purchase_date`/`condition`/`cardmarket_link` si quiere
esos datos desde el arranque en vez de completarlos después). Si Facundo no lo completa
antes de que el developer arranque este sprint, el developer debe frenar y avisar — no
inventar datos de ejemplo para "probar" el loader contra la colección real.

---

## 1. Layout

Dos scripts nuevos en `backend/scripts/` (mismo directorio que
`scryfall_backfill.py`, mismo patrón de `connect()` propio de ~13 líneas —
**no tocar `backend/importer/` ni `scryfall_backfill.py`**):

- `backend/scripts/load_collection.py` — carga inicial desde el CSV.
- Reutiliza el mismo módulo para el modo `--apply-review` (sección 3) en vez de un
  tercer archivo — es la misma lógica de inserción, distinta fuente de filas.

Scripts de corrida bajo demanda (CLI manual), no servicios permanentes — mismo patrón
que el importer y el backfill de Scryfall.

## 2. Responsabilidades de `load_collection.py` (corrida inicial)

Por cada fila no vacía (`card_name` presente) de `coleccion-a-cargar.csv`:

**a. Magic:**
- Buscar en `cards` (`game=magic`) por `name` + expansión (via `set_hint`/`card_number`
  si vienen) + `variant`.
- Si matchea una sola `card` dentro del scope LOTR ya importado (`5285`/`5308`/`5396`):
  resolver `cardmarket_product_id` vía `cardmarket_product_mappings`, insertar
  `collection_item` con `card_id` + `cardmarket_product_id`, `manual_entry=false`.
- Si no matchea (carta de Magic fuera del scope LOTR, ej. reprint en el pool `5489`/
  `6665` mencionado en `fase2-cardmarket-hallazgos-y-schema.md` §2): alta manual —
  `card_id=NULL`, `cardmarket_product_id=NULL`, `manual_entry=true`,
  `manual_entry_note` armado desde `notes`+`cardmarket_link` de la fila (mismo patrón
  que fase2 §5).

**b. One Piece:**
- Buscar en `cards` + `cardmarket_product_mappings`.
- `status='mapped'` → insertar directo, igual que Magic.
- `status='ambiguous'` → **no insertar todavía**, va a la cola de revisión (sección 3).
- Sin match en absoluto → alta manual y reportarlo (no debería pasar, todo el catálogo
  de One Piece está importado — pero reportar, no asumir, AGENTS.md §20).

**c. Pokémon:**
- Sin catálogo importado (decisión Fase 2 §5, sigue sin cambios) → siempre alta manual:
  `card_id=NULL`, `cardmarket_product_id=NULL`, `manual_entry=true`.

**d. Filas con `card_name` vacío:** skip, reportar como fila incompleta. No generar
cartas fantasma.

## 3. Cola de revisión — One Piece `ambiguous` (mecánica confirmada: CSV de revisión)

En vez de un prompt interactivo o de asignar automáticamente la variante sugerida:

1. `load_collection.py` genera `backend/scripts/collection-ambiguous-review.csv` con:
   la fila original del CSV + las `cards` candidatas del mismo grupo
   (`expansion_id`+`cardmarket_id_metacard`) con `variant_label`, `printing_variant` y
   el precio (`trend`) más reciente de cada una desde `market_price_history`/
   `cardmarket_products` si existe + una columna vacía `chosen_card_id`.
2. Facundo completa `chosen_card_id` a mano por fila (puede abrir el link de Cardmarket
   si tiene dudas, como ya preveía `fase2-cardmarket-hallazgos-y-schema.md` §1).
3. Segunda corrida: `load_collection.py --apply-review` lee ese CSV con
   `chosen_card_id` completado, inserta esos `collection_items`
   (`manual_entry=false`, ya no es alta manual — la variante quedó confirmada por
   catálogo real, solo que con ayuda humana), y renombra el CSV aplicado a
   `collection-ambiguous-review.done.csv` para no reprocesarlo por accidente.
4. Filas de ese CSV con `chosen_card_id` todavía vacío al momento de `--apply-review`:
   skip + reportar, no bloquear el resto del lote.

Alcance real esperado: acotado a las cartas de One Piece que Facundo realmente tiene
(hasta 30, no las ~700 del catálogo completo — la cola de revisión solo contiene lo que
efectivamente aparece en `coleccion-a-cargar.csv`).

## 4. Idempotencia entre corridas

`collection_items` no tiene una unique key natural (a propósito — permite múltiples
copias de la misma carta, AGENTS.md §18). Para no duplicar filas si Facundo vuelve a
correr el script (por ejemplo tras agregar cartas nuevas al CSV más adelante):

- Mantener estado local `backend/scripts/.collection_import_state.json` con un hash por
  fila ya importada (`game`+`card_name`+`variant`+`set_hint`+`card_number`+`quantity`+
  `purchase_date`) → si el hash ya está en el estado, skip silencioso en el reporte
  ("ya importada"), no duplicar.
- Documentar esta elección en el docstring del módulo (mismo criterio que
  `fase5-scryfall-magic-backfill-sprint-contract.md` §1, AGENTS.md §24).
- El archivo de estado es local al repo (gitignorear si no lo está ya) — no es parte
  del schema, es solo para evitar relecturas duplicadas del CSV.

## 5. Reporte final (nunca silencioso, AGENTS.md §20)

- Insertadas directas (Magic LOTR + One Piece `mapped`).
- En cola de revisión (One Piece `ambiguous`) — cuántas, y confirmar que el CSV de
  revisión se generó (o que no hizo falta si no hay ninguna).
- Altas manuales — desglosado por motivo (Pokémon / Magic fuera de LOTR / One Piece sin
  match).
- Filas incompletas/saltadas (`card_name` vacío).
- Ya importadas (skip por idempotencia), si aplica.
- Total filas procesadas + skips debe sumar exacto a las filas del CSV.

## 6. Fuera de alcance de este sprint

- Dashboard/UI web (Fase 6, `AGENTS.md` §22) — todo este sprint es CLI + CSV, sin
  frontend nuevo.
- Cualquier cambio a `backend/importer/` o `backend/scripts/scryfall_backfill.py`.
- Integración de pokemontcg.io para Pokémon (sigue diferida, revisar si la colección
  crece a >50 cartas — `TCG-DEC-001`).
- Supabase (`TCG-DEC-003`, sigue diferido, no bloquea esto).
- Ampliar el scope de Magic más allá de LOTR (`5285`/`5308`/`5396`) salvo altas
  manuales puntuales fila por fila.
- Want list (`want_list_items`) — no está en el CSV actual, queda para cuando se pida
  explícitamente.

## 7. Verificación

1. Con el CSV real completado por Facundo, correr `load_collection.py` → el reporte
   debe mostrar total procesado = filas no vacías del CSV.
2. `SELECT manual_entry, COUNT(*) FROM collection_items GROUP BY manual_entry` —
   comparar contra lo esperado (Pokémon 100% manual; Magic no-LOTR manual solo si
   aparece alguna; resto `false`).
3. Revisar `collection-ambiguous-review.csv` generado (si hay filas `ambiguous`),
   completar `chosen_card_id`, correr `--apply-review`, confirmar que esas filas ahora
   están en `collection_items` con `card_id` seteado.
4. Correr `load_collection.py` una segunda vez sobre el mismo CSV sin cambios → el
   reporte debe mostrar 0 filas nuevas insertadas (idempotencia vía el hash state).
5. Spot-check manual: 3-5 `collection_items` al azar por juego, confirmar que
   `card_id`/`cardmarket_product_id`/`manual_entry` son coherentes con la fila de
   origen del CSV.
6. Confirmar que `cardmarket_products`, `cards`, `expansions`, `market_price_history`
   no cambiaron de estructura ni ganaron filas fuera de lo esperado (este sprint solo
   escribe en `collection_items`).

## 8. Cierre

- Actualizar `AGENTS.md` §23 "Current Phase" a Fase 6 al cerrar este sprint.
- Documentar el resultado real en este mismo archivo, agregando una sección
  "Resultado real de la corrida" (mismo patrón que los contracts anteriores), incluida
  cualquier corrección de regla que aparezca al correr contra el CSV real (como pasó en
  Fase 5 parcial con `printing_variant`).
- Actualizar `conventions.json` → `TCG-DEC-004` con `status: "implementado"` y el
  resultado real, una vez cerrado.

---

## 9. Resultado real de la corrida

**Corrida real 2026-08-25, 98 filas (100% Magic/LTR — el CSV real que completó Facundo
no terminó trayendo filas One Piece/Pokémon pese a lo estimado en §0/`TCG-DEC-001`;
la cola de revisión de §3 igual se ejercitó porque se generalizó a "cualquier fila con
2+ candidatas ambiguas en `cards`", no solo One Piece `ambiguous` — ver nota
2026-08-25 en `TCG-DEC-004`).**

**Corrida inicial (`load_collection.py`):** 26 directas / 55 en cola de revisión / 17
altas manuales (17 sin candidatas en catálogo). Desvío investigado contra el 25/55/18
esperado de una corrida de prueba anterior: 1 fila ("Shortcut to Mushrooms", fila 44)
se movió de alta manual a directa — confirmado con Facundo que es **dato mal cargado
en el CSV** (el link de Cardmarket pegado apuntaba a una promo Holiday-Release que
Facundo no compró; la carta real es la edición normal), no una regresión del matcher.
No se implementó heurística de "duda de edición" para este caso — decisión explícita de
Facundo: es un error de dato puntual, no amerita lógica nueva sin un caso real que la
justifique.

**Cola de revisión (55 filas → `collection-ambiguous-review.csv`):** Facundo completó
`chosen_card_id` en Apple Numbers (no directo en el CSV). El roundtrip `.numbers → CSV`
vía `osascript`/Numbers.app introdujo corrupción real en columnas no consumidas por
`--apply-review` (`candidate_card_number`, `cardmarket_link` — ~50 líneas) y en un caso
corrompió la propia columna `candidate_card_id` de un grupo (fila 81, "Asceticism"),
lo que produjo un `chosen_card_id` numéricamente válido pero semánticamente equivocado
(685 en vez de 684) — detectado por validación cruzada contra el CSV original antes de
escribir nada, corregido con confirmación explícita de Facundo. Export final validado:
53/55 filas con `chosen_card_id` correcto, 2 filas (fila 40 "King of the Oathbreakers",
fila 41 "Radagast the Brown") deliberadamente sin elegir — Facundo tiene esas cartas en
edición prerelease datestamped (`pltr`, ids 502/488), que no calza limpio con ninguna
de las 3 ediciones candidatas del grupo (base/extended-art/prerelease) sin una decisión
manual adicional pendiente.

**Bug real encontrado y corregido en `load_collection.py`:** `run_initial_load()`
marcaba el hash de idempotencia de una fila (`new_hashes.add(h)`) al encolarla en
`review_queue`, **antes** de que se insertara nada en `collection_items` — bloqueaba
por completo `--apply-review` (todas las filas de revisión aparecían "ya importadas"
sin haberse insertado nunca). Fix: sacar ese `add(h)` de las dos ramas de cola
(`magic`/`one_piece`); el hash ahora solo se marca en `run_apply_review()`, cuando el
insert real ocurre. El state ya envenenado por la corrida inicial (55 hashes marcados
sin insert real) se reparó recalculando esos 55 hashes con la misma `row_hash()` del
módulo (no una reimplementación ad-hoc) y sacándolos de
`.collection_import_state.json`, dejando intactos los 43 hashes de inserts reales.

**`--apply-review` (post-fix):** 53 insertadas, 2 en `manual_entries` con motivo
`"chosen_card_id vacio, sin aplicar (--apply-review)"` (no error silencioso).
`collection_items`: 43 → 96. `collection-ambiguous-review.csv` no se renombró a
`.done.csv` — quedan esas 2 filas pendientes para cuando Facundo decida qué edición
prerelease cargar.

**Re-corrida de `fase4-importer-sprint-contract.md` §6 (poblar `market_price_history`,
ahora que `collection_items` tiene datos reales):** `market_price_history` 0 → 78,
`DISTINCT cardmarket_product_id` = 78 (coincide exacto con el techo teórico —
`COUNT(DISTINCT cardmarket_product_id)` de `collection_items`). `cardmarket_products`/
`cardmarket_product_mappings`: 12867 → 12942 (+75 en ambas, upsert sin duplicar) —
100% catálogo vivo de One Piece creciendo desde el cierre de Fase 4 (Magic se mantuvo
en 757 productos, sin cambios). `cards`: 12167 → 12259 (+92) — también 100% One Piece
(757 Magic sin cambios, 11410 → 11502 One Piece), cards nuevas para productos nunca
vistos del catálogo vivo. Ninguno de estos dos crecimientos afecta la colección real de
Facundo (Magic/LTR). Nombre de One Piece sin parsear por el regex de `card_number`:
`'Wang Zhi(OP17-041)'` (falta espacio antes del paréntesis) — no investigado, queda
para cuando aparezca en el CSV real.

**Pendiente de la sesión, no bloqueante para cerrar este sprint:**
`coleccion-a-cargar.csv` fue reemplazado por `coleccion-a-cargar.numbers` en algún
momento de la sesión (abierto/guardado en Numbers) — no resuelto, no urgente; exportar
de vuelta a `.csv` desde Numbers antes de la próxima corrida de `load_collection.py`.
