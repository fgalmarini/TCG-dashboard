# TCG Dashboard — Sprint Contract Fase 2→3
**Para: Claude Code CLI, ejecutando en el repo `/Users/facundogalmarini/Desktop/TCG DASHBOARD`**
**Estado: Fase 2 cerrada. Este documento es el contrato de implementación para Fase 3 (schema).**

---

## 0. Checklist de Fase 3 (lo que hay que ejecutar)

1. Crear base SQLite local con las tablas de la sección 3.
2. Aplicar exactamente los tipos, PKs, FKs e índices listados — no improvisar campos no mencionados acá.
3. No implementar todavía: importer (Fase 4), UI de colección (Fase 5), dashboard (Fase 6).
4. Cualquier decisión de diseño no cubierta en este documento: parar y preguntar, no asumir (regla general vigente en `AGENTS.md`).

---

## 1. Hallazgos confirmados (los tres juegos)

Basado en inspección directa de archivos reales de Cardmarket: `price_guide_18/1/6.json` + `products_singles_18/1/6.json` (One Piece, Magic, Pokémon).

| Tema | Hallazgo |
|---|---|
| Formato | JSON plano, snapshot único por archivo (`createdAt` + una fila de precio por producto). Sin histórico interno de Cardmarket. |
| Singles | Filtro confiable: `categoryName` conteniendo "Single" (`"One Piece Single"`, `"Magic Single"`, `"Pokémon Single"`) |
| `idProduct` | Clave global de Cardmarket, única entre los 3 juegos |
| Idioma | No existe en ningún archivo, para ningún juego. Se resuelve manualmente en `collection_items` |
| Foil/Holo | Magic y One Piece usan `-foil`; Pokémon usa `-holo`. Se normalizan en un solo par de columnas internas |
| Variantes (parallel/alt-art/gold-stamp) | Se detectan agrupando por `(idExpansion, idMetacard)`, confirmado en los 3 juegos. El precio más alto es una sugerencia, no una certeza. El sufijo `(V.N)` en el nombre (confirmado solo en 30 tokens de Magic) se guarda como dato adicional cuando existe, pero **no está garantizado ni siquiera para pares de variantes reales** — confirmado con captura de pantalla: la web de Cardmarket muestra "(V.2)" en el título de la página, pero el campo `name` del archivo bulk para ese mismo producto no lo trae. La confirmación manual sigue siendo necesaria; el usuario puede verificar "V.1/V.2" abriendo el link de Cardmarket cuando tenga dudas. |
| Card number | Presente en el nombre solo en One Piece (`"Nombre (OP01-001)"`). Ausente en Magic y Pokémon |
| Expansiones | Sin catálogo oficial de nombres disponible (756 en Magic, 773 en Pokémon) |

---

## 2. Scope de la colección (decisión final del usuario)

| Juego | Scope de importación automática | Cómo se suman las demás |
|---|---|---|
| **One Piece** | Todo el catálogo de singles | — |
| **Magic** | **Solo LOTR.** Ver expansiones exactas abajo | Cualquier carta LOTR fuera de esas expansiones → alta manual |
| **Pokémon** | **Ninguno por ahora.** El usuario tiene ~10-15 cartas nada más | Alta 100% manual (ver sección 5) |

### Expansiones de Magic a importar (LOTR) — confirmado con datos reales

Se identificaron cruzando las apariciones de "The One Ring" y "Andúril" (cartas únicas e inconfundibles de LOTR) en todo el catálogo de Magic:

| `idExpansion` | Contenido real (verificado) | # productos | ¿Importar? |
|---|---|---|---|
| 5285 | Set principal -Tales of Middle-earth- (LTR). 281 productos = coincide exacto con el conteo real del set | 281 | **Sí** |
| 5308 | "Extras": bonus sheet + Art Series + Arena Codes de LTR | 386 | **Sí** |
| 5396 | Commander decks de LTR (LTC) | 90 | **Sí** |
| 5489 | ⚠️ **NO es un producto de LOTR** — es un pool de reprints cruzado tipo "The List" (contiene cartas genéricas como "Ancient Tomb", "Abyssal Persecutor" mezcladas con 1-2 reprints de Andúril/One Ring). Importarlo entero traería ~1000 cartas de Magic sin relación con LOTR | 1013 | **No** |
| 6665 | ⚠️ Mismo patrón que 5489 pero de 2026 (mezcla Arcane Signet, Banishing Light, etc. con Andúril/Aragorn) | 158 | **No** |

**Regla para el importer de Fase 4:** `WHERE idExpansion IN (5285, 5308, 5396)`. No incluir 5489 ni 6665 aunque contengan cartas de Andúril — esas copias puntuales se cargan a mano si alguna vez aparecen en la colección (mecanismo de la sección 5). Si en el futuro sale un nuevo pool tipo "The List" con alguna carta de LOTR, mismo criterio: no se agrega la expansión entera, se usa el alta manual para esa carta puntual.

---

## 3. Schema (SQLite)

### `games`
`id` PK · `code` UNIQUE (`pokemon`/`one_piece`/`magic`) · `name`

### `languages`
`id` PK · `code` UNIQUE (`en`,`ja`,...) · `name`

### `cardmarket_categories`
`id` PK · `game_id` FK · `cardmarket_id_category` UNIQUE · `category_name` · `is_single` BOOLEAN

### `expansions`
`id` PK · `game_id` FK · `cardmarket_id_expansion` UNIQUE · `name` NULLABLE · `set_code` NULLABLE · `release_date` NULLABLE

### `cards` (Card Definition)
`id` PK · `game_id` FK · `expansion_id` FK · `card_number` NULLABLE · `name` · `printing_variant` (`normal`/`suggested_parallel`/`confirmed_parallel`/`other`) · `variant_label` NULLABLE (el `(V.N)` literal si Cardmarket lo trae) · `cardmarket_id_metacard` NULLABLE · `image_url` NULLABLE · `image_source` NULLABLE (`scryfall`/`onepiece_official`/`manual`)
Índice único: (`expansion_id`, `card_number`, `printing_variant`)

### `cardmarket_products`
`id` PK · `cardmarket_id_product` UNIQUE NOT NULL · `raw_name` · `cardmarket_id_category` · `cardmarket_id_expansion` · `cardmarket_id_metacard` NULLABLE · `date_added` · `last_seen_at`

### `cardmarket_product_mappings`
`id` PK · `cardmarket_product_id` FK UNIQUE · `card_id` FK NULLABLE (null = sin mapear) · `status` (`mapped`/`ambiguous`/`unmapped`) · `notes` NULLABLE

### `market_price_history`
Sin tabla de "precio actual" separada — es la fila más reciente de acá.
`id` PK · `cardmarket_product_id` FK · `observed_at` TIMESTAMP · `low`,`avg`,`trend`,`avg1`,`avg7`,`avg30` NUMERIC NULLABLE · `low_alt`,`avg_alt`,`trend_alt`,`avg1_alt`,`avg7_alt`,`avg30_alt` NUMERIC NULLABLE (normalización de `-foil`/`-holo`) · `imported_at`
Índice único: (`cardmarket_product_id`, `observed_at`) · Índice: (`cardmarket_product_id`, `observed_at` DESC)
**Regla de scope:** solo se insertan filas para `cardmarket_product_id` referenciados desde `collection_items` o `want_list_items` — nunca el catálogo completo.

### `collection_items`
`id` PK · `card_id` FK NULLABLE (null permitido para altas 100% manuales sin card definition todavía — ver sección 5) · `cardmarket_product_id` FK NULLABLE · `language_id` FK (default `'en'`) · `condition` NULLABLE (NM/EX/GD/LP/PL/PO) · `grading_company` NULLABLE (PSA/BGS/CGC/Other) · `grade` NULLABLE · `quantity` (default 1) · `purchase_price` NULLABLE · `purchase_currency` NULLABLE · `purchase_date` NULLABLE · `trade_value` NULLABLE · `status` (KEEP/HOLD/TRADE/SELL/WANT) · `manual_entry` BOOLEAN (default false) · `manual_entry_note` NULLABLE (texto libre: link de Cardmarket pegado, o descripción de la carta si no se pudo mapear) · `notes` NULLABLE

### `want_list_items`
`id` PK · `card_id` FK NULLABLE · `language_id` FK NULLABLE · `condition` NULLABLE · `grade_min` NULLABLE · `target_price` NULLABLE · `max_price` NULLABLE · `priority` (LOW/MEDIUM/HIGH) · `notes` NULLABLE

---

## 4. Estrategia de imágenes

| Juego | Fuente | Cómo |
|---|---|---|
| One Piece | `en.onepiece-cardgame.com` (oficial) | `image_url = f"https://en.onepiece-cardgame.com/images/cardlist/card/{card_number}.png"` |
| Magic | Scryfall | `GET https://api.scryfall.com/cards/cardmarket/{idProduct}` |
| Pokémon | — | No aplica todavía (ver sección 5) |

Se guarda solo la URL, no el binario. Prioridad de implementación: One Piece → Magic → Pokémon (cuando se retome).

---

## 5. Alta manual de cartas (Pokémon + casos borde)

Dado que Pokémon no se importa automáticamente (colección chica, ~10-15 cartas) y que pueden aparecer cartas de Magic fuera del scope de LOTR (sección 2), se necesita un mecanismo de alta manual, reusable para cualquier juego:

- Botón/toggle "Add Card" en `collection_items`.
- El usuario puede: (a) pegar un link de producto de Cardmarket como referencia (se guarda en `manual_entry_note`, sin parsear — no se scrapea la página), o (b) describir la carta a mano (juego, nombre, set, condición, precio de compra).
- `card_id` y `cardmarket_product_id` quedan `NULL` en este flujo — no hay tracking de precio de mercado automático para estas cartas hasta que se decida integrar una fuente para Pokémon (pokemontcg.io, evaluado y pospuesto) o se mapeen a mano más adelante.
- `manual_entry = true` marca estas filas para poder filtrarlas/revisarlas después en el dashboard.

Esto no requiere ninguna integración externa nueva — es el mismo patrón de "nullable + completar después" que ya usamos para expansiones e imágenes.

---

## 6. Decisiones de arquitectura (resumen)

| Tema | Decisión |
|---|---|
| Expansiones sin nombre | Auto-alta con `name = NULL` al ver `idExpansion` nuevo; el usuario completa el nombre la primera vez que mapea una carta de esa expansión |
| Scope del histórico de precios | Solo productos referenciados desde colección/want list |
| "Precio anterior" | No se persiste — se calcula por query sobre `market_price_history` |
| Cadencia de actualización | Botón manual para arrancar; automatización semanal opcional más adelante (`launchd`, no bloqueante si la Mac está apagada) |
| Detección de variantes | `(idExpansion, idMetacard)` + sugerencia por precio + confirmación manual (el usuario puede verificar en la página real de Cardmarket si tiene dudas) |
| Scope de Magic | Solo `idExpansion IN (5285, 5308, 5396)` — ver sección 2 |
| Scope de Pokémon | Sin importer automático por ahora — alta 100% manual |
| Imágenes | URL únicamente, por juego (sección 4), Pokémon pospuesto |

**Fase 2 cerrada. Listo para Fase 3.**
