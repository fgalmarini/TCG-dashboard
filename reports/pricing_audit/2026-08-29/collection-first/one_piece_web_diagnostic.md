# One Piece Collection — Manual Web Diagnostic

Fecha del diagnóstico: **2026-08-29**  
Scope: únicamente los 23 `collection_items` clasificados como `MANUAL_WEB_REVIEW` en `collection_provenance_audit.csv` (`133–155`).

## Seguridad y fuentes

- DB abierta en modo read-only: `PRAGMA integrity_check=ok`; `PRAGMA foreign_key_check` sin filas.
- DB antes/después del diagnóstico: `e155b0776922ac72e191a98b30b6bb44427664cf2ef0ead4f9c6d5e7c53ec225`.
- Snapshots locales usados: `price-history/one-piece/products_singles_18.json` y `price-history/one-piece/price_guide_18.json`.
- Los 23 rows tienen idioma local `jp`; los IDs Cardmarket locales tienen `language_scope=mixed` y `allowed_languages=[en,jp,zh-CN,kr,fr]`. Los Blueprints CardTrader son evidencia exacta de idioma/artwork, no fuente de pricing.
- Se consultó Cardmarket web públicamente en modo read-only. Los precios se observaron únicamente como contexto y **no se usaron para seleccionar identidades**.
- `coleccion-a-cargar.numbers` y `collection-ambiguous-review.numbers` existen como fuentes históricas, pero no hay un campo textual histórico por fila que agregue una URL Cardmarket para estos 23 items. La provenance derivada no encontró URLs históricas.

## Resultado ejecutivo

Cardmarket expone una convención repetible: una misma carta se separa por familia de expansión (`OP05` vs `OP05-JP`, `EB02` vs `EB02-JP`, etc.) y por `V.1/V.2/V.3`. Sin embargo, el Product Catalogue local y la provenance guardada no prueban que una familia `Non-English/Japanese` sea exclusivamente japonesa: sus metadatos admiten varios idiomas. Por eso la convención es evidencia diagnóstica, no una regla de producción todavía.

El riesgo más alto es `EB02-061A`: el sufijo físico/local `A` se pierde si se normaliza a `EB02-061`, y entonces el mismo número aparece también en `PRB02` con versiones V1/V2/V3. Esa combinación puede llevar a un producto de reprint/versión distinta y a un valor de mercado completamente incorrecto.

## Resultado por item

La tabla completa, con URLs e IDs de todos los candidatos principales, está en [one_piece_web_diagnostic.csv](./one_piece_web_diagnostic.csv). El `candidate_count` cuenta los candidatos razonables identificados en el snapshot local y la revisión web; cuando hay más de tres, el CSV conserva los adicionales en `notes`.

| Item | Identidad local | Conflict type | Candidatos Cardmarket principales | Diferencia que bloquea | Diagnóstico |
| ---: | --- | --- | --- | --- | --- |
| 133 | Borsalino OP05-051 | `LANGUAGE` | 733344 / 747506 | OP05-JP V1 vs OP05 V1 | `WEB_RULE_CANDIDATE` |
| 134 | Dracule Mihawk OP01-070 AA/fixed reprint | `MULTIPLE_FACTORS` | 690897 / 768325 | OP01 V2 vs OP01-JP V2 | `WEB_RULE_CANDIDATE` |
| 135 | Dracule Mihawk OP01-070 fixed reprint | `VERSION` | 690896 / 768324; V2 counterparts | V1/V2 + idioma | `LIKELY_PHYSICAL_CONFIRMATION` |
| 136 | Yamato OP13-054 | `LANGUAGE` | 857251 / 845324 | OP13-JP V1 vs OP13 V1 | `WEB_RULE_CANDIDATE` |
| 137 | Lilith OP13-113 alternate art | `LANGUAGE` | 857331 / 845665 | OP13-JP V2 vs OP13 V2 | `WEB_RULE_CANDIDATE` |
| 138 | Monkey.D.Luffy EB02-061A | `MULTIPLE_FACTORS` | 808172 / 823516 / 838705 | EB02 vs PRB02 + JP/EN + V1/V2/V3 | `INDIVIDUAL_WEB_RESOLUTION` |
| 139 | Rob Lucci OP05-093 AA | `LANGUAGE` | 733430 / 747782 | OP05-JP V2 vs OP05 V2 | `WEB_RULE_CANDIDATE` |
| 140 | X.Drake OP05-055 AA | `LANGUAGE` | 733352 / 747512 | OP05-JP V2 vs OP05 V2 | `WEB_RULE_CANDIDATE` |
| 141 | Cavendish OP01-008 Box Topper | `MULTIPLE_FACTORS` | 768247 / 690804 | OP01-JP V2 vs OP01 V2; Box Topper no explicit field | `LIKELY_PHYSICAL_CONFIRMATION` |
| 142 | Gol.D.Roger OP13-064 | `LANGUAGE` | 857262 / 845596 | OP13-JP V1 vs OP13 V1 | `WEB_RULE_CANDIDATE` |
| 143 | Nefeltari Vivi EB02-026 | `LANGUAGE` | 808127 / 823455 | EB02-JP V1 vs EB02 V1 | `WEB_RULE_CANDIDATE` |
| 144 | S-Snake OP08-112 | `LANGUAGE` | 771756 / 788021 | OP08-JP V1 vs OP08 V1 | `WEB_RULE_CANDIDATE` |
| 145 | Koala OP05-006 | `LANGUAGE` | 733281 / 747444 | OP05-JP V1 vs OP05 V1 | `WEB_RULE_CANDIDATE` |
| 146 | Monkey.D.Luffy OP01-024 | `LANGUAGE` | 768265 / 690823 | OP01-JP V1 vs OP01 V1 | `WEB_RULE_CANDIDATE` |
| 147 | Yamato EB02-006 | `LANGUAGE` | 808101 / 823429 | EB02-JP V1 vs EB02 V1 | `WEB_RULE_CANDIDATE` |
| 148 | Pica OP05-032 | `LANGUAGE` | 733317 / 747476 | OP05-JP V1 vs OP05 V1 | `WEB_RULE_CANDIDATE` |
| 149 | Kin'emon OP01-040 | `LANGUAGE` | 768285 / 690844 | OP01-JP V1 vs OP01 V1 | `WEB_RULE_CANDIDATE` |
| 150 | Trafalgar Law EB02-045 | `LANGUAGE` | 808150 / 823481 | EB02-JP V1 vs EB02 V1 | `WEB_RULE_CANDIDATE` |
| 151 | Uta OP13-023 | `LANGUAGE` | 857215 / 845271 | OP13-JP V1 vs OP13 V1 | `WEB_RULE_CANDIDATE` |
| 152 | Trafalgar Law P-038 | `PROMO` | 722798 / 766644 / 787443 | Promos JP vs Promos vs STP | `INDIVIDUAL_WEB_RESOLUTION` |
| 153 | Stussy OP13-110 | `LANGUAGE` | 857326 / 845660 | OP13-JP V1 vs OP13 V1 | `WEB_RULE_CANDIDATE` |
| 154 | King OP01-096 fixed reprint | `MULTIPLE_FACTORS` | 768358 / 690929 / V2 counterparts | OP01-JP/OP01 + fixed-reprint V1/V2 | `LIKELY_PHYSICAL_CONFIRMATION` |
| 155 | Rebecca OP05-091 | `LANGUAGE` | 733426 / 747775 | OP05-JP V1 vs OP05 V1 | `WEB_RULE_CANDIDATE` |

## Conflict types

- `LANGUAGE`: **17**
- `VERSION`: **1**
- `PROMO`: **1**
- `MULTIPLE_FACTORS`: **4**
- `SET_REPRINT`: **0**
- `ART_VARIANT`: **0**
- `UNKNOWN`: **0**

`ART_VARIANT` aparece como factor dentro de `MULTIPLE_FACTORS` cuando Cardmarket lo expresa como `V.2` pero la provenance local lo llama `Alternate Art` o `Box Topper`.

## Diagnostic result

- `WEB_RULE_CANDIDATE`: **18**
- `INDIVIDUAL_WEB_RESOLUTION`: **2**
- `LIKELY_PHYSICAL_CONFIRMATION`: **3**
- `UNRESOLVED`: **0**

Estas categorías son diagnósticas. No aprueban mappings, no insertan resoluciones y no autorizan pricing/apply.

## Patrones Cardmarket detectados

### GROUP 1 — Language family: English vs Non-English/Japanese

**Items:** 133, 136, 137, 139, 140, 142–151, 153, 155; también es un factor en 134, 135, 138, 141, 152 y 154.  
**Pattern:** Cardmarket separa familias como `OP05` / `OP05-JP`, `OP13` / `OP13-JP`, `EB02` / `EB02-JP`, `OP01` / `OP01-JP` y `OP08` / `OP08-JP`.  
**Evidence:** [Borsalino versions](https://www.cardmarket.com/en/OnePiece/Cards/Borsalino-OP05-051/Versions), [Yamato OP13-054 versions](https://www.cardmarket.com/en/OnePiece/Cards/Yamato-OP13-054/Versions), [S-Snake versions](https://www.cardmarket.com/en/OnePiece/Cards/S-Snake-OP08-112) y [Koala versions](https://www.cardmarket.com/en/OnePiece/Cards/Koala-OP05-006/Versions).  
**Cardmarket convention:** la familia `Non-English/Japanese` es una señal repetible para el lado JP, pero no demuestra por sí sola idioma japonés porque la metadata local admite `en`, `jp`, `zh-CN`, `kr` y `fr`.  
**Sample size:** 17 casos primarios de idioma; **exceptions:** ninguna observada en este scope; **confidence:** medium para separar familia, low/medium para probar idioma exacto.  
**Proposed next step:** validar contra un conjunto de cartas físicamente confirmadas que `OPxx-JP` sea suficiente para el flujo local; hasta entonces exigir evidencia exact-language o confirmación física.

### GROUP 2 — Cardmarket versions V.1 / V.2 / V.3

**Items:** 134, 135, 137, 138, 139, 140, 141 y 154.  
**Pattern:** dentro de una misma familia Cardmarket reutiliza `V.1`, `V.2` y, para `EB02-061`, `V.3`. La web muestra estas versiones como productos distintos, no como una variación de precio.  
**Evidence:** [Monkey.D.Luffy EB02-061 versions](https://www.cardmarket.com/en/OnePiece/Cards/MonkeyDLuffy-EB02-061/Versions), [Dracule Mihawk OP01-070 versions](https://www.cardmarket.com/en/OnePiece/Cards/Dracule-Mihawk-OP01-070), [Rob Lucci OP05-093 versions](https://www.cardmarket.com/en/OnePiece/Cards/Rob-Lucci-OP05-093/Versions) y [King OP01-096 versions](https://www.cardmarket.com/en/OnePiece/Cards/King-OP01-096/Versions).  
**Cardmarket convention:** `V.2` suele coincidir con la variante alternate-art del conjunto revisado, pero no es una regla global para todos los nombres; `Fixed Reprint` y `Box Topper` necesitan comprobación física.  
**Sample size:** 8 casos con factor de versión; **exceptions:** Box Topper/fixed reprint no tienen campo equivalente visible en el Product Catalogue; **confidence:** medium.  
**Proposed next step:** construir una tabla humana de equivalencias `local variant -> Cardmarket version` por carta o por release, con excepciones explícitas.

### GROUP 3 — EB02 vs PRB02 reprint collision

**Items:** 138 (`EB02-061A`).  
**Pattern:** Cardmarket muestra diez productos para `Monkey.D.Luffy (EB02-061)`: EB02 y PRB02, cada uno con familia English/Non-English y V.1/V.2/V.3.  
**Evidence:** [Cardmarket EB02-061 versions](https://www.cardmarket.com/en/OnePiece/Cards/MonkeyDLuffy-EB02-061/Versions).  
**Cardmarket convention:** `EB02` y `PRB02` aparecen como familias explícitas; el sufijo local `061A` debe conservarse como señal de variante antes de traducirlo a V.2.  
**Sample size:** 1 caso de alto riesgo; **exceptions:** no aplica; **confidence:** high sobre la causa de ambigüedad, medium sobre la equivalencia final hasta validación humana.  
**Proposed next step:** usar una regla específica de diagnóstico `set + language family + physical suffix/art`, nunca `name + stripped number`.

### GROUP 4 — Promo family vs Special Tournament Promo

**Items:** 152 (`P-038`).  
**Pattern:** Cardmarket mantiene `Promos`, `Promos (Japanese)` y `Special Tournament Promos` como familias distintas para el mismo número `P-038`; además existe una V.1/V.2 dentro de STP.  
**Evidence:** [Promos Japanese P-038](https://www.cardmarket.com/en/OnePiece/Products/Singles/Promos-Japanese/Trafalgar-Law-P-038), [Promos P-038](https://www.cardmarket.com/en/OnePiece/Products/Singles/Promos/Trafalgar-Law-P-038) y [Special Tournament Promos P-038 V.1](https://www.cardmarket.com/en/OnePiece/Products/Singles/Special-Tournaments-Promos/Trafalgar-Law-P-038-V1).  
**Cardmarket convention:** el nombre `P-038` no basta: la familia de promo/release es el atributo decisivo.  
**Sample size:** 1; **exceptions:** STP V.2 también está presente en el catálogo local; **confidence:** high para detectar el conflicto, medium para la resolución final.  
**Proposed next step:** confirmar físicamente el evento/producto de la promo y conservar la familia Cardmarket completa.

## EB02-061 ROOT CAUSE

La identidad local es `Monkey.D.Luffy`, `EB02-061A`, `jp`, `Secret Rare | Alternate Art`. Cardmarket, en cambio, lista el producto con nombre `Monkey.D.Luffy (EB02-061)` y usa `V.1/V.2/V.3` dentro de varias familias: `EB02`, `EB02-JP`, `PRB02` y `PRB02-JP`.

La causa del posible precio equivocado de aproximadamente **€200** es la pérdida del sufijo `A` y del release al reducir la identidad a nombre+número. Ese matching puede cruzar el producto EB02 con un reprint PRB02, o cruzar V.1/V.2/V.3, y terminar leyendo un producto de otra impresión. El precio no puede corregir ese error: usarlo como selector solo consolida el mismatch.

La condición futura que debe impedirlo es:

```text
candidate.set_family == EB02
AND candidate.language_family == EB02-JP / exact JP
AND candidate.version_or_art == V.2 / 061A
AND candidate.name == Monkey.D.Luffy
```

Si cualquiera de esas dimensiones falta o es mixta, el resultado debe ser `NULL`/manual y nunca un candidato elegido por precio. `PRB02`, V.1 y V.3 deben rechazarse explícitamente para este item.

## Proposed rules summary

| Rule | Sample size | Matches | Exceptions | Confidence | Status |
| --- | ---: | ---: | --- | --- | --- |
| Cardmarket `OPxx-JP/Non-English` separates the JP product family from `OPxx` English | 17 primary language cases | 17 | Non-English is not exact JP in local metadata | Medium | Proposal only |
| Cardmarket `V.2` can represent the alternate-art family for selected cards | 8 factor cases | 6 clear | Fixed Reprint and Box Topper require physical confirmation | Medium | Proposal only |
| `EB02-061A` requires EB02 + JP + V.2 and rejects PRB02/V1/V3 | 1 | 1 diagnostic match | Human validation still required | Medium/High | Proposal only |
| `P-038` must retain promo family (`Promos Japanese` vs `Promos` vs `STP`) | 1 | 1 diagnostic match | STP V.2 also present | Medium | Proposal only |

## Scope protection

- No DB was modified.
- No mappings were modified.
- No Collection or Wishlist data was modified.
- `collection_manual_review.csv` was not modified or approved.
- No resolution or price was inserted.
- `./update-prices --apply --scope collection` was not executed.
