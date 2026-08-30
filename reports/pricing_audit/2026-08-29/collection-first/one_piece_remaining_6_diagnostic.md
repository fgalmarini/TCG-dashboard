# One Piece — Diagnóstico final de los 6 casos no-LANGUAGE

Fecha del diagnóstico: **2026-08-29**
Scope: únicamente los seis rows de `one_piece_web_diagnostic.csv` con `conflict_type` `VERSION`, `PROMO` o `MULTIPLE_FACTORS`.

## Resultado consolidado

```text
ONE PIECE — REMAINING 6 DIAGNOSTIC

ITEMS ANALYZED: 6

VERSION:
1

PROMO:
1

MULTIPLE_FACTORS:
4
```

Clasificación diagnóstica, sin aprobación ni resolución:

```text
RULE_CANDIDATE: 1
INDIVIDUAL_WEB_RESOLUTION: 2
PHYSICAL_CONFIRMATION_REQUIRED: 3
UNRESOLVED: 0
```

## Fuentes, método y seguridad

- Fuente primaria de selección: [one_piece_web_diagnostic.csv](./one_piece_web_diagnostic.csv). El filtro devuelve exactamente 6 items: `134`, `135`, `138`, `141`, `152` y `154`.
- Contexto local: [collection_one_piece_full.csv](./collection_one_piece_full.csv), [collection_one_piece_manual_review.md](./collection_one_piece_manual_review.md), DB read-only y los catálogos locales `price-history/one-piece/products_singles_18.json` y `price-history/one-piece/price_guide_18.json`.
- Cardmarket web se consultó solo para identidad estructural: título, familia/expansión, código, versión y estado de promo/reimpresión. No se usaron precios, sellers, disponibilidad ni candidato más barato/caro.
- Cardmarket catalog local conserva el `name`, `idExpansion`, `idMetacard` y fecha, pero no siempre conserva versión o idioma exacto. Las etiquetas `V.1/V.2/V.3`, `OP01-JP`, `EB02-JP`, `PRB02` y `STP` se contrastaron con las páginas públicas de versiones/productos.
- [Cardmarket OP01-070 versions](https://www.cardmarket.com/en/OnePiece/Cards/Dracule-Mihawk-OP01-070/Versions), [OP01-096 versions](https://www.cardmarket.com/en/OnePiece/Cards/King-OP01-096/Versions), [OP01-008 versions](https://www.cardmarket.com/en/OnePiece/Cards/Cavendish-OP01-008/Versions), [EB02-061 versions](https://www.cardmarket.com/en/OnePiece/Cards/MonkeyDLuffy-EB02-061/Versions) y [P-038 versions](https://www.cardmarket.com/en/OnePiece/Cards/Trafalgar-Law-P-038/Versions) muestran las familias y versiones relevantes.
- La [card list oficial de Bandai](https://asia-en.onepiece-cardgame.com/cardlist/?freewords=EB02-061&search=true) confirma que `EB02-061` se reutiliza en EB02 y en el producto `ONE PIECE CARD THE BEST vol.2` (`PRB-02`); por tanto, el número sin release no es suficiente.

Seguridad inicial:

```text
DB SHA-256: e155b0776922ac72e191a98b30b6bb44427664cf2ef0ead4f9c6d5e7c53ec225
PRAGMA integrity_check: ok
PRAGMA foreign_key_check: ok
```

## Identidad local completa

Los seis items tienen en `collection_items`: `status=KEEP`, `quantity=1`, `manual_entry=0`, `condition=NULL`, `grade=NULL`, `purchase_price=NULL`, `purchase_date=NULL`, `finish=NULL`, `treatment=NULL`, `notes=NULL`, `match_status=exact`, `match_quality=exact`, `match_reason=catalog_add` y `cardmarket_product_id=NULL`. No se modificó ninguno de esos datos.

| Item | `card_id` | Card | Number | Set / language | Variant / rarity | Release / art | Canonical | CardTrader Blueprint | Historical Cardmarket IDs |
|---:|---:|---|---|---|---|---|---|---|---|
| 134 | 15439 | Dracule Mihawk | OP01-070 | `op01` / `jp` | `Alternate Art \| Fixed Reprint` / Alternate Art | reprint / alternate_art | `one_piece:OP01-070` / 1319 | 244585, exact; `version=Alternate Art \| Fixed Reprint`, `release_id=3332` | 690897, 768325; scope `mixed` |
| 135 | 15437 | Dracule Mihawk | OP01-070 | `op01` / `jp` | `Fixed Reprint` / Super Rare | reprint / base | `one_piece:OP01-070` / 1319 | 244584, exact; `version=Fixed Reprint`, `release_id=3332` | 690896, 768324; scope `mixed` |
| 138 | 21131 | Monkey.D.Luffy | EB02-061A | `eb-02` / `jp` | `Secret Rare \| Alternate Art` / Alternate Art | original / alternate_art | `one_piece:EB02-061A` / 5201 | 330432, exact; `version=Secret Rare \| Alternate Art`, `release_id=4123` | 823516; scope `mixed` |
| 141 | 15290 | Cavendish | OP01-008 | `op01` / `jp` | `Box Topper` / Alternate Art | original / base | `one_piece:OP01-008` / 1244 | 244478, exact; `version=Box Topper`, `release_id=3332` | 690804, 768247; scope `mixed` |
| 152 | 14625 | Trafalgar Law | P-038 | `promo` / `jp` | Base / Promo | promo / base | `one_piece:P-038` / 675 | 256657, exact; `version=NULL`, `release_id=3324` | 722798; scope `mixed` |
| 154 | 15503 | King | OP01-096 | `op01` / `jp` | `Fixed Reprint` / Super Rare | reprint / base | `one_piece:OP01-096` / 1352 | 244639, exact; `version=Fixed Reprint`, `release_id=3332` | 690929, 768358; scope `mixed` |

### Original import fields and legacy sources

- `coleccion-a-cargar.numbers` y `backend/scripts/collection-ambiguous-review.numbers` existen como archivos originales/históricos.
- Ambos son archivos binarios `.numbers` sin `kMDItemTextContent`; la revisión por Numbers no estuvo disponible porque el permiso de Computer Use no fue concedido. No se inventaron valores de importación que no estén conservados en DB o en los reportes derivados.
- `backend/scripts/collection-ambiguous-review.done.csv` contiene **0 rows `one_piece`**; por eso no aporta valores originales para estos seis items.
- Los campos originales recuperables de forma reproducible son los de `collection_one_piece_full.csv` y DB: `local_printing_id`, nombre, número, set, idioma, `local_version`, rareza, `canonical_id`, `blueprint_id`, `stored_cardmarket_id`, candidatos, estado y evidencia/provenance.
- No hay `historical_url_evidence` adicional para estos seis fuera de las URLs Cardmarket reconstruidas/conservadas en el diagnóstico; CardTrader sí aporta provenance exacta de idioma/variante/release, pero no es fuente de pricing.

## Análisis por item

### ITEM 134 — Dracule Mihawk OP01-070

**CURRENT CONFLICT:** `MULTIPLE_FACTORS` (`candidate_count=2`).

**LOCAL EVIDENCE:** `jp`, set `op01`, variant `Alternate Art | Fixed Reprint`, `release_kind=reprint`, `art_kind=alternate_art`; CardTrader Blueprint `244585` exacto para esa variante y `release_id=3332`. Los dos IDs Cardmarket locales son `mixed`, no exact-language.

**FACTORS:**

```text
factor_language: true
factor_set_reprint: false
factor_version: true
factor_promo: false
factor_art_variant: true
factor_other: false
```

**CARDMARKET CANDIDATES:**

| idProduct | Product title | Expansion / family | Version | Promo / reprint / variant | URL |
|---:|---|---|---|---|---|
| 690897 | Dracule Mihawk (OP01-070) (V.2) | Romance Dawn / `OP01` | V.2 | regular OP01 family; V.2 parallel/fixed-reprint family | [Cardmarket](https://www.cardmarket.com/en/OnePiece/Products/Singles/Romance-Dawn/Dracule-Mihawk-OP01-070-V2) |
| 768325 | Dracule Mihawk (OP01-070) (V.2) | Romance Dawn (Japanese) / `OP01-JP` | V.2 | Japanese family; V.2 parallel/fixed-reprint family | [Cardmarket](https://www.cardmarket.com/en/OnePiece/Products/Singles/Romance-Dawn-Japanese/Dracule-Mihawk-OP01-070-V2) |

Cardmarket también muestra vecinos V.1 para la misma carta (`690896` EN y `768324` JP) y familias fuera del release local, como OP01E, PRB01 y STP. No son candidatos de la shortlist local para `Alternate Art | Fixed Reprint`; sirven para demostrar que no se debe usar solo nombre+número.

**ACTUAL DISTINGUISHING FACTORS:** idioma/familia (`OP01` vs `OP01-JP`) y versión `V.2`. La variante local `Alternate Art | Fixed Reprint` es el dato que justifica V.2, pero no aparece como campo explícito equivalente en el catálogo Cardmarket.

**MISSING ATTRIBUTE:** confirmación independiente de que la carta física es la parallel/fixed-reprint que Cardmarket representa como V.2.

**MINIMUM REQUIRED IDENTITY FIELDS:** `language=JP` + `set=OP01` + `card_number=OP01-070` + provenance exacta `Alternate Art | Fixed Reprint` + familia Cardmarket `OP01-JP` + `V.2`.

**DIAGNOSTIC RESULT:** `RULE_CANDIDATE`.

**PROPOSED RULE:** para OP01, `JP + OP01-070 + Alternate Art | Fixed Reprint` puede apuntar a `OP01-JP V.2`; no convertir en regla de producción hasta validar el atributo físico.

**PHYSICAL CHECK:** comparar artwork paralelo, layout de texto/copyright y cualquier marca física del fixed reprint; no elegir por precio.

### ITEM 135 — Dracule Mihawk OP01-070

**CURRENT CONFLICT:** `VERSION` (`candidate_count=4`).

**LOCAL EVIDENCE:** `jp`, set `op01`, variant `Fixed Reprint`, `release_kind=reprint`, `art_kind=base`; CardTrader Blueprint `244584` exacto, `release_id=3332`. El diagnóstico conserva dos familias V.1 y sus contrapartes V.2.

**FACTORS:**

```text
factor_language: true
factor_set_reprint: false
factor_version: true
factor_promo: false
factor_art_variant: false
factor_other: true
```

**CARDMARKET CANDIDATES:**

| idProduct | Product title | Expansion / family | Version | Promo / reprint / variant | URL |
|---:|---|---|---|---|---|
| 690896 | Dracule Mihawk (OP01-070) (V.1) | Romance Dawn / `OP01` | V.1 | regular OP01 family | [Cardmarket](https://www.cardmarket.com/en/OnePiece/Products/Singles/Romance-Dawn/Dracule-Mihawk-OP01-070-V1) |
| 768324 | Dracule Mihawk (OP01-070) (V.1) | Romance Dawn (Japanese) / `OP01-JP` | V.1 | Japanese family | [Cardmarket](https://www.cardmarket.com/en/OnePiece/Products/Singles/Romance-Dawn-Japanese/Dracule-Mihawk-OP01-070-V1) |
| 690930 | Dracule Mihawk (OP01-070) (V.2) | Romance Dawn / `OP01` | V.2 | regular OP01 family; parallel/reprint version | [Cardmarket](https://www.cardmarket.com/en/OnePiece/Products/Singles/Romance-Dawn/Dracule-Mihawk-OP01-070-V2) |
| 768359 | Dracule Mihawk (OP01-070) (V.2) | Romance Dawn (Japanese) / `OP01-JP` | V.2 | Japanese family; parallel/reprint version | [Cardmarket](https://www.cardmarket.com/en/OnePiece/Products/Singles/Romance-Dawn-Japanese/Dracule-Mihawk-OP01-070-V2) |

Cardmarket additionally exposes OP01E `Romance Dawn (Pre-Errata)`, PRB01 and STP families for this card. Esas familias no deben mezclarse con el `op01` fixed reprint local.

**ACTUAL DISTINGUISHING FACTORS:** la familia de idioma separa EN/JP, pero la selección V.1/V.2 requiere distinguir la impresión/reprint física. El número `OP01-070` y el nombre no lo hacen.

**MISSING ATTRIBUTE:** marcador físico de errata/reimpresión, especialmente copyright/text layout que diferencie V.1 de V.2.

**MINIMUM REQUIRED IDENTITY FIELDS:** `language=JP` + `set=OP01` + `card_number=OP01-070` + indicador físico de `Fixed Reprint` que determine V.1 o V.2 + familia Cardmarket `OP01-JP`.

**DIAGNOSTIC RESULT:** `PHYSICAL_CONFIRMATION_REQUIRED`.

**PROPOSED RULE:** no inferir V.1/V.2 desde el número o desde `Fixed Reprint` sin el marcador físico.

**PHYSICAL CHECK:** frente y reverso; copyright line, texto corregido/errata, layout y cualquier diferencia de impresión. No seleccionar por precio.

### ITEM 138 — Monkey.D.Luffy EB02-061A

**CURRENT CONFLICT:** `MULTIPLE_FACTORS` (`candidate_count=10`).

**LOCAL EVIDENCE:** `jp`, set `eb-02`, number `EB02-061A`, variant `Secret Rare | Alternate Art`, `release_kind=original`, `art_kind=alternate_art`; CardTrader Blueprint `330432` exacto, `release_id=4123`. El único ID Cardmarket almacenado es `823516`, familia EB02 regular/EN y scope `mixed`.

**FACTORS:**

```text
factor_language: true
factor_set_reprint: true
factor_version: true
factor_promo: false
factor_art_variant: true
factor_other: true
```

**CARDMARKET CANDIDATES:** Cardmarket muestra diez productos para la identidad visible `Monkey.D.Luffy (EB02-061)`. El catálogo local confirma los diez IDs y expansiones; Cardmarket confirma las familias y versiones.

| idProduct | Product title | Expansion / family | Version | Promo / reprint / variant | URL |
|---:|---|---|---|---|---|
| 808171 | Monkey.D.Luffy (EB02-061) (V.1) | Anime 25th Collection (Non-English) / `EB02-JP` | V.1 | EB02 JP family | [Cardmarket](https://www.cardmarket.com/en/OnePiece/Products/Singles/Anime-25th-Collection-Japanese/MonkeyDLuffy-EB02-061-V1) |
| 808172 | Monkey.D.Luffy (EB02-061) (V.2) | Anime 25th Collection (Non-English) / `EB02-JP` | V.2 | EB02 JP family; alternate-art candidate | [Cardmarket](https://www.cardmarket.com/en/OnePiece/Products/Singles/Anime-25th-Collection-Japanese/MonkeyDLuffy-EB02-061-V2) |
| 808173 | Monkey.D.Luffy (EB02-061) (V.3) | Anime 25th Collection (Non-English) / `EB02-JP` | V.3 | EB02 JP family; high-variant candidate | [Cardmarket](https://www.cardmarket.com/en/OnePiece/Products/Singles/Anime-25th-Collection-Japanese/MonkeyDLuffy-EB02-061-V3) |
| 823515 | Monkey.D.Luffy (EB02-061) (V.1) | Anime 25th Collection / `EB02` | V.1 | EB02 regular family | [Cardmarket](https://www.cardmarket.com/en/OnePiece/Products/Singles/Anime-25th-Collection/MonkeyDLuffy-EB02-061-V1) |
| 823516 | Monkey.D.Luffy (EB02-061) (V.2) | Anime 25th Collection / `EB02` | V.2 | stored product; regular/EN family | [Cardmarket](https://www.cardmarket.com/en/OnePiece/Products/Singles/Anime-25th-Collection/MonkeyDLuffy-EB02-061-V2) |
| 823517 | Monkey.D.Luffy (EB02-061) (V.3) | Anime 25th Collection / `EB02` | V.3 | EB02 regular family | [Cardmarket](https://www.cardmarket.com/en/OnePiece/Products/Singles/Anime-25th-Collection/MonkeyDLuffy-EB02-061-V3) |
| 838704 | Monkey.D.Luffy (EB02-061) (V.1) | The Best Vol. 2 (Non-English) / `PRB02-JP` | V.1 | PRB02 JP reprint family | [Cardmarket](https://www.cardmarket.com/en/OnePiece/Products/Singles/The-Best-Vol-2-Non-English/MonkeyDLuffy-EB02-061-V1) |
| 838705 | Monkey.D.Luffy (EB02-061) (V.2) | The Best Vol. 2 (Non-English) / `PRB02-JP` | V.2 | PRB02 JP reprint family | [Cardmarket](https://www.cardmarket.com/en/OnePiece/Products/Singles/The-Best-Vol-2-Non-English/MonkeyDLuffy-EB02-061-V2) |
| 852319 | Monkey.D.Luffy (EB02-061) (V.1) | The Best Vol.2 / `PRB02` | V.1 | PRB02 regular/EN reprint family | [Cardmarket](https://www.cardmarket.com/en/OnePiece/Products/Singles/The-Best-Vol2/MonkeyDLuffy-EB02-061-V1) |
| 852320 | Monkey.D.Luffy (EB02-061) (V.2) | The Best Vol.2 / `PRB02` | V.2 | PRB02 regular/EN reprint family | [Cardmarket](https://www.cardmarket.com/en/OnePiece/Products/Singles/The-Best-Vol2/MonkeyDLuffy-EB02-061-V2) |

**ACTUAL DISTINGUISHING FACTORS:** release/family (`EB02` vs `PRB02`), language family (`-JP` vs regular) y version (`V.1/V.2/V.3`). El sufijo local `A` y la provenance CardTrader `Secret Rare | Alternate Art` explican por qué el target conceptual es EB02-JP V.2, pero Cardmarket imprime el número visible como `EB02-061`.

**MINIMUM REQUIRED IDENTITY FIELDS:** conservar literalmente `EB02-061A` + `language=JP` + `set=EB02` + `Secret Rare | Alternate Art` + familia Cardmarket `EB02-JP` + `V.2`.

**DIAGNOSTIC RESULT:** `INDIVIDUAL_WEB_RESOLUTION`.

**PROPOSED RULE:** `EB02-061A => EB02-JP V.2`; rechazar `PRB02`, V.1 y V.3. Es una propuesta de diagnóstico para validar manualmente, no una resolución aplicada.

**PHYSICAL CHECK:** no se identifica un atributo físico adicional imprescindible después de conservar el sufijo `A` y la provenance exacta; mantener revisión humana antes de aprobar.

**HISTORICAL WRONG-PRICE ROOT CAUSE:** el producto almacenado `823516` pertenece a la familia regular `EB02` V.2 con idioma `mixed`, mientras la identidad local es JP alternate art con número `EB02-061A`. La pérdida del sufijo/release y el cruce de familias, no el precio, es la causa del mismatch histórico.

### ITEM 141 — Cavendish OP01-008

**CURRENT CONFLICT:** `MULTIPLE_FACTORS` (`candidate_count=2` en el diagnóstico; Cardmarket muestra 5 versiones totales).

**LOCAL EVIDENCE:** `jp`, set `op01`, variant `Box Topper`, `release_kind=original`, `art_kind=base`, rarity Alternate Art; CardTrader Blueprint `244478` exacto, `release_id=3332`. Cardmarket no expone `Box Topper` como un campo equivalente.

**FACTORS:**

```text
factor_language: true
factor_set_reprint: false
factor_version: true
factor_promo: false
factor_art_variant: true
factor_other: true
```

**CARDMARKET CANDIDATES / VERSION UNIVERSE:**

| idProduct | Product title | Expansion / family | Version | Promo / reprint / variant | URL |
|---:|---|---|---|---|---|
| 690802 | Cavendish (OP01-008) (V.1) | Romance Dawn / `OP01` | V.1 | regular OP01 family | [Cardmarket product family](https://www.cardmarket.com/en/OnePiece/Products/Singles/Romance-Dawn/Cavendish-OP01-008-V1) |
| 690804 | Cavendish (OP01-008) (V.2) | Romance Dawn / `OP01` | V.2 | regular OP01 family; parallel candidate | [Cardmarket](https://www.cardmarket.com/en/OnePiece/Products/Singles/Romance-Dawn/Cavendish-OP01-008-V2) |
| 768246 | Cavendish (OP01-008) (V.1) | Romance Dawn (Japanese) / `OP01-JP` | V.1 | Japanese family | [Cardmarket product family](https://www.cardmarket.com/en/OnePiece/Products/Singles/Romance-Dawn-Japanese/Cavendish-OP01-008-V1) |
| 768247 | Cavendish (OP01-008) (V.2) | Romance Dawn (Japanese) / `OP01-JP` | V.2 | Japanese family; parallel candidate | [Cardmarket](https://www.cardmarket.com/en/OnePiece/Products/Singles/Romance-Dawn-Japanese/Cavendish-OP01-008-V2) |
| 874414 | Cavendish (OP01-008) | Demo Decks / `DEMO` | — | Demo Deck product, not OP01 expansion | [Cardmarket](https://www.cardmarket.com/en/OnePiece/Products/Singles/Demo-Decks/Cavendish-OP01-008) |

**ACTUAL DISTINGUISHING FACTORS:** Cardmarket separates `OP01`/`OP01-JP`, V.1/V.2 and `DEMO`. The local `Box Topper` label is not directly represented; therefore `Box Topper => V.2` is not proven by web structure alone.

**MISSING ATTRIBUTE:** physical artwork/treatment confirming that the Box Topper corresponds to the V.2 parallel product rather than V.1 or Demo Deck.

**MINIMUM REQUIRED IDENTITY FIELDS:** `language=JP` + `set=OP01` + `card_number=OP01-008` + physical Box Topper artwork/treatment + `OP01-JP` + selected V.x.

**DIAGNOSTIC RESULT:** `PHYSICAL_CONFIRMATION_REQUIRED`.

**PROPOSED RULE:** do not equate local `Box Topper` with Cardmarket V.2 globally; validate the artwork per release/card.

**PHYSICAL CHECK:** artwork, treatment, card back/front and any Box Topper-specific release marker; compare with Cardmarket V.1/V.2 images where available.

### ITEM 152 — Trafalgar Law P-038

**CURRENT CONFLICT:** `PROMO` (`candidate_count=4`).

**LOCAL EVIDENCE:** `jp`, set `promo`, number `P-038`, rarity Promo, `release_kind=promo`, `art_kind=base`; CardTrader Blueprint `256657` exacto, `release_id=3324`. El ID Cardmarket histórico almacenado es `722798` con scope `mixed`.

**FACTORS:**

```text
factor_language: true
factor_set_reprint: true
factor_version: true
factor_promo: true
factor_art_variant: false
factor_other: true
```

**CARDMARKET CANDIDATES:**

| idProduct | Product title | Expansion / family | Version | Promo / reprint / variant | URL |
|---:|---|---|---|---|---|
| 722798 | Trafalgar Law (P-038) | Promos (Japanese) / `P-JP` | — | Japanese promo family | [Cardmarket](https://www.cardmarket.com/en/OnePiece/Products/Singles/Promos-Japanese/Trafalgar-Law-P-038) |
| 766644 | Trafalgar Law (P-038) | Promos / `P` | — | regular promo family | [Cardmarket](https://www.cardmarket.com/en/OnePiece/Products/Singles/Promos/Trafalgar-Law-P-038) |
| 787443 | Trafalgar Law (P-038) (V.1) | Special Tournament Promos / `STP` | V.1 | special tournament promo | [Cardmarket](https://www.cardmarket.com/en/OnePiece/Products/Singles/Special-Tournaments-Promos/Trafalgar-Law-P-038-V1) |
| 787505 | Trafalgar Law (P-038) (V.2) | Special Tournament Promos / `STP` | V.2 | special tournament promo | [Cardmarket](https://www.cardmarket.com/en/OnePiece/Products/Singles/Special-Tournaments-Promos/Trafalgar-Law-P-038-V2) |

Cardmarket expone exactamente cuatro versiones/familias para P-038: `Promos (Japanese) P-JP`, `Promos P`, `Special Tournament Promos STP V.1` y `STP V.2`; véase [la página de versiones](https://www.cardmarket.com/en/OnePiece/Cards/Trafalgar-Law-P-038/Versions).

**ACTUAL DISTINGUISHING FACTORS:** familia de promo/release y, para STP, V.1/V.2. `P-038` por sí solo no basta.

**MISSING ATTRIBUTE:** confirmación de que el release físico corresponde a la promo japonesa general y no a `STP`; la provenance CardTrader apunta al release correcto, pero no conserva un título textual del release.

**MINIMUM REQUIRED IDENTITY FIELDS:** `language=JP` + `set=promo` + `card_number=P-038` + release/provenance exacta + familia `Promos (Japanese)`.

**DIAGNOSTIC RESULT:** `INDIVIDUAL_WEB_RESOLUTION`.

**PROPOSED RULE:** `P-038 + JP + release promo general => Promos (Japanese)`; no usar `P-038` como regla universal ni aprobar sin confirmar el release físico.

**PHYSICAL CHECK:** sello/evento o material de distribución que distinga promo general de Special Tournament Promo.

### ITEM 154 — King OP01-096

**CURRENT CONFLICT:** `MULTIPLE_FACTORS` (`candidate_count=4`).

**LOCAL EVIDENCE:** `jp`, set `op01`, variant `Fixed Reprint`, `release_kind=reprint`, `art_kind=base`; CardTrader Blueprint `244639` exacto, `release_id=3332`. IDs Cardmarket locales `690929` y `768358` son scope `mixed`; se agregan las contrapartes V.2 para completar la comparación.

**FACTORS:**

```text
factor_language: true
factor_set_reprint: false
factor_version: true
factor_promo: false
factor_art_variant: false
factor_other: true
```

**CARDMARKET CANDIDATES:**

| idProduct | Product title | Expansion / family | Version | Promo / reprint / variant | URL |
|---:|---|---|---|---|---|
| 768358 | King (OP01-096) (V.1) | Romance Dawn (Japanese) / `OP01-JP` | V.1 | Japanese family | [Cardmarket](https://www.cardmarket.com/en/OnePiece/Products/Singles/Romance-Dawn-Japanese/King-OP01-096-V1) |
| 690929 | King (OP01-096) (V.1) | Romance Dawn / `OP01` | V.1 | regular OP01 family | [Cardmarket](https://www.cardmarket.com/en/OnePiece/Products/Singles/Romance-Dawn/King-OP01-096-V1) |
| 690930 | King (OP01-096) (V.2) | Romance Dawn / `OP01` | V.2 | regular OP01 family; parallel/reprint version | [Cardmarket](https://www.cardmarket.com/en/OnePiece/Products/Singles/Romance-Dawn/King-OP01-096-V2) |
| 768359 | King (OP01-096) (V.2) | Romance Dawn (Japanese) / `OP01-JP` | V.2 | Japanese family; parallel/reprint version | [Cardmarket](https://www.cardmarket.com/en/OnePiece/Products/Singles/Romance-Dawn-Japanese/King-OP01-096-V2) |

Cardmarket también muestra OP01E `Romance Dawn (Pre-Errata)` V.1/V.2; queda fuera del set/familia local `op01` JP, pero confirma que el mismo número tiene una dimensión adicional de errata.

**ACTUAL DISTINGUISHING FACTORS:** familia EN/JP y V.1/V.2; `Fixed Reprint` local no determina por sí solo qué versión Cardmarket corresponde.

**MISSING ATTRIBUTE:** marcador físico de errata/reimpresión que diferencie V.1 de V.2 y descarte OP01E Pre-Errata.

**MINIMUM REQUIRED IDENTITY FIELDS:** `language=JP` + `set=OP01` + `card_number=OP01-096` + indicador físico de Fixed Reprint/errata + familia `OP01-JP` + V.x.

**DIAGNOSTIC RESULT:** `PHYSICAL_CONFIRMATION_REQUIRED`.

**PROPOSED RULE:** no inferir V.1/V.2 desde `OP01-096` o desde la etiqueta local `Fixed Reprint` sin evidencia física.

**PHYSICAL CHECK:** copyright line, texto/errata, layout y cualquier marcador visible de impresión; comparar con las imágenes de V.1/V.2 y OP01E.

## Proposed rules summary — no aprobadas

### RULE NAME: OP01_JP_V2_PARALLEL_FIXED_REPRINT

- **SCOPE:** One Piece OP01; variantes parallel/alternate-art fixed reprint como item 134.
- **INPUT ATTRIBUTES:** `language=JP`, `set=OP01`, número exacto, provenance CardTrader exacta de `Alternate Art | Fixed Reprint`, familia Cardmarket y V.x.
- **CARDMARKET BEHAVIOR:** `OP01-JP` + `V.2` separa el producto japonés de `OP01` + `V.2`.
- **SAMPLE SIZE:** 1.
- **MATCHES:** 1 diagnóstico estructural.
- **EXCEPTIONS:** no observadas dentro del item 134; no generalizar a Fixed Reprint base.
- **CONFIDENCE:** medium.
- **WHAT STILL NEEDS HUMAN VALIDATION:** confirmar físicamente artwork/reprint antes de incluirla en una matriz de producción.

### RULE NAME: EB02_061A_EXACT

- **SCOPE:** `Monkey.D.Luffy EB02-061A`.
- **INPUT ATTRIBUTES:** número literal con sufijo `A`, `language=JP`, set `EB02`, `Secret Rare | Alternate Art`, CardTrader Blueprint exacto.
- **CARDMARKET BEHAVIOR:** Cardmarket separa EB02/EB02-JP de PRB02/PRB02-JP y además V.1/V.2/V.3.
- **SAMPLE SIZE:** 1.
- **MATCHES:** 1 diagnóstico estructural.
- **EXCEPTIONS:** el Cardmarket visible elimina el sufijo `A`; no usar `EB02-061` solo.
- **CONFIDENCE:** medium/high para la causa del conflicto; medium para aprobación final.
- **WHAT STILL NEEDS HUMAN VALIDATION:** validar manualmente la equivalencia local `061A -> EB02-JP V.2` antes de cualquier mapping.

### RULE NAME: PROMO_P038_FAMILY

- **SCOPE:** `Trafalgar Law P-038` con release promo general japonés.
- **INPUT ATTRIBUTES:** `language=JP`, `set=promo`, `card_number=P-038`, provenance/release exacto.
- **CARDMARKET BEHAVIOR:** `P-JP`, `P` y `STP V.1/V.2` son familias separadas.
- **SAMPLE SIZE:** 1.
- **MATCHES:** 1 diagnóstico estructural.
- **EXCEPTIONS:** `P-038` aparece también en Promos regular y STP.
- **CONFIDENCE:** medium.
- **WHAT STILL NEEDS HUMAN VALIDATION:** confirmar que el release físico es promo general y no Special Tournament Promo.

### RULE NAME: LANGUAGE_FAMILY_OPXX_JP (contexto previo)

- **SCOPE:** separación estructural de familias de idioma en One Piece.
- **INPUT ATTRIBUTES:** nombre, número, set y familia Cardmarket.
- **CARDMARKET BEHAVIOR:** `OPxx` corresponde a la familia regular/EN y `OPxx-JP` a la familia japonesa/Non-English observada.
- **SAMPLE SIZE:** 6 casos manuales previamente validados.
- **MATCHES:** 6.
- **EXCEPTIONS:** 0 en la muestra.
- **CONFIDENCE:** medium para familia; no equivale a prueba exact-language de todas las fichas mixtas.
- **WHAT STILL NEEDS HUMAN VALIDATION:** exact-language/provenance para cada aplicación productiva.

## Matriz conceptual One Piece — todavía no implementada

```text
LANGUAGE:
JP Collection
+ same name
+ same card number
+ same expansion/release
+ same V.x when present
+ Japanese / Non-English Cardmarket family

VERSION:
exact language family
+ exact set/release
+ physical version marker for V.1/V.2/V.3

PROMO:
exact language
+ exact card number
+ exact promo family/release
+ physical event/release confirmation when P and STP coexist

MULTIPLE_FACTORS:
preserve all dimensions:
language + physical expansion/reprint + V.x + promo family + art/treatment
```

Estas son reglas candidatas de diagnóstico. No se modificaron mappings, estados, Collection, Wishlist ni CSV de aprobación.

## Seguridad final

```text
DB SHA-256 BEFORE: e155b0776922ac72e191a98b30b6bb44427664cf2ef0ead4f9c6d5e7c53ec225
DB SHA-256 AFTER:  e155b0776922ac72e191a98b30b6bb44427664cf2ef0ead4f9c6d5e7c53ec225
DB BYTE-FOR-BYTE IDENTICAL: YES
PRAGMA integrity_check: ok
PRAGMA foreign_key_check: ok
```

- DB modificada: no.
- Mappings modificados: no.
- Collection modificada: no.
- Wishlist modificada: no.
- `collection_manual_review.csv` modificado o aprobado: no.
- Precios insertados: no.
- Resoluciones aprobadas: no.
- `./update-prices --apply --scope collection` ejecutado: no.
- Archivo creado: únicamente este Markdown.
