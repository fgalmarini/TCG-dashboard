# Fase 4 — Importer de Cardmarket (Sprint Contract)
**Para: Claude Code CLI. Depende de `docs/plans/fase2-cardmarket-hallazgos-y-schema.md` (cerrado) y del schema ya implementado en Fase 3 (commiteado).**

---

## 0. URLs de descarga — confirmadas y funcionando

Bucket S3 público de Cardmarket, sin autenticación, sin bot-detection (verificado con fetch directo):

| Juego | Price Guide | Product Catalogue |
|---|---|---|
| Magic (idGame 1) | `https://downloads.s3.cardmarket.com/productCatalog/priceGuide/price_guide_1.json` | `https://downloads.s3.cardmarket.com/productCatalog/productList/products_singles_1.json` |
| Pokémon (idGame 6) | `https://downloads.s3.cardmarket.com/productCatalog/priceGuide/price_guide_6.json` | `https://downloads.s3.cardmarket.com/productCatalog/productList/products_singles_6.json` |
| One Piece (idGame 18) | `https://downloads.s3.cardmarket.com/productCatalog/priceGuide/price_guide_18.json` | `https://downloads.s3.cardmarket.com/productCatalog/productList/products_singles_18.json` |

Patrón: `https://downloads.s3.cardmarket.com/productCatalog/{priceGuide|productList}/{price_guide|products_singles}_{idGame}.json`

## 1. Carpeta de descarga

```
TCG DASHBOARD/
└── price-history/
    ├── magic/
    │   ├── price_guide_1.json
    │   └── products_singles_1.json
    ├── pokemon/
    │   ├── price_guide_6.json
    │   └── products_singles_6.json
    └── one-piece/
        ├── price_guide_18.json
        └── products_singles_18.json
```

**Regla confirmada:** cada archivo se **pisa** en cada corrida. No se versionan por fecha — el histórico real vive en `market_price_history`, no en el filesystem (ver razón en la sección "Preguntas abiertas" de Fase 2: guardar cada descarga cruda por fecha reintroduciría el problema de crecimiento que ya evitamos scopeando la tabla de histórico).

## 2. Responsabilidades del script (`backend/importer/`)

Corre bajo demanda (botón manual o CLI), no como servicio.

1. **Descargar** las 6 URLs de la sección 0, sobrescribiendo `price-history/{juego}/`.
2. **Cargar `cardmarket_products`**: upsert por `cardmarket_id_product`, filtrando `categoryName` que contenga "Single" (ya viene así en `products_singles_*`, pero validar igual).
3. **Aplicar scope por juego**:
   - One Piece: todo el catálogo de singles.
   - Magic: solo `idExpansion IN (5285, 5308, 5396)`.
   - Pokémon: **no correr el import de catálogo/precios para este juego en esta fase** — ver sección 5 del contrato de Fase 2 (alta 100% manual).
4. **Self-healing de `expansions`**: por cada `idExpansion` no visto antes (dentro del scope de arriba), insertar fila con `name = NULL`, y agregarlo al reporte final como "expansión nueva sin nombre".
5. **Detección de variantes**: agrupar por `(idExpansion, idMetacard)`. Si hay 2+ productos:
   - Extraer `(V.N)` del `name` crudo con regex si está presente → guardar en `cards.variant_label`.
   - Marcar el de mayor `trend` como `printing_variant = 'suggested_parallel'`, el resto `'normal'`.
   - Si no hay ambigüedad de precio (grupo con precios iguales/similares, ej. el caso "Erg Raiders" de Fase 2), dejar `'other'` y reportarlo para revisión manual en vez de forzar una sugerencia sin sustento.
6. **`market_price_history`**: insertar únicamente para `cardmarket_product_id` ya referenciados en `collection_items` o `want_list_items`. **Nota de orden de fases:** como Fase 5 (colección manual) todavía no existe, esta corrida probablemente no inserte ninguna fila de histórico todavía — es esperado, no es un bug.
7. **Imágenes**: no resolver todo el catálogo de una — resolver **on-demand**, solo cuando una carta se agrega a `collection_items` o `want_list_items` (evita llamadas innecesarias a Scryfall para miles de cartas que el usuario nunca va a tener):
   - One Piece: `image_url = f"https://en.onepiece-cardgame.com/images/cardlist/card/{card_number}.png"`.
   - Magic: `GET https://api.scryfall.com/cards/cardmarket/{idProduct}` → tomar el campo de imagen de la respuesta.
8. **Reporte final** (a consola, no silencioso): cantidad de productos importados por juego, expansiones nuevas sin nombre, grupos de variantes detectados y su clasificación, productos que no calzaron en ningún mapeo.

## 3. Fuera de alcance de esta fase

- UI del botón "Actualizar precios" (Fase 6).
- Resolución de imágenes de Pokémon vía pokemontcg.io (pospuesto, ver Fase 2 sección 5).
- Automatización por `launchd` (mejora opcional futura, no bloqueante).

## 4. Verificación

1. Correr el script → confirma 6 archivos en `price-history/`, tamaños > 0.
2. `cardmarket_products` tiene filas de One Piece (~12k) y Magic (~750, solo las 3 expansiones LOTR) — nada de Pokémon.
3. Reporte final lista al menos las expansiones nuevas de Magic/One Piece sin nombre (esperado, ninguna tiene nombre todavía).
4. Correr el script una segunda vez → sin duplicados (upsert funcionando), archivos de `price-history/` actualizados con el nuevo `createdAt`.

## 5. Resultado real de la corrida (Fase 4 cerrada)

- Scope real: 757 Magic/LOTR + 12.110 One Piece = 12.867 productos.
- 12.167 cards mapeadas limpiamente, 700 marcadas `ambiguous` por colisión genuina del índice UNIQUE — **las 700 son necesariamente de One Piece** (en Magic `card_number` es siempre `NULL`, no puede colisionar).
- 143 expansiones nuevas self-healed (coincide con lo esperado: ~139 de One Piece + 3 de Magic/LOTR).
- Segunda corrida: mismos conteos, sin duplicados — idempotencia confirmada.

**Investigado el origen de los 700 ambiguous:** de 2.293 grupos de variantes (mismo `idExpansion`+`idMetacard`) en One Piece, solo 156 tienen algún `trend` faltante. El resto de la ambigüedad (~544 grupos) viene de precios genuinamente parecidos entre variantes — no de datos faltantes. Es decir, no es un defecto del importer ni del umbral del 10%: una porción real del catálogo de One Piece son pares de variantes donde ninguna es claramente "la rara" (mismo patrón que "Erg Raiders" en Magic, documentado en Fase 2). No se ajustó el umbral en base a esto.

**Nota para Fase 5 (colección manual):** van a existir ~700 cartas de One Piece esperando confirmación de variante antes de poder cargarse a la colección. La UI de "confirmar variante" tiene que soportar revisión por lote — no una por una — porque es un volumen real y esperado, no un puñado de casos sueltos.
