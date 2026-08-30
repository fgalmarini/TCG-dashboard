# One Piece — Final Physical Reconciliation

Pass read-only. No se modificaron DB, mappings, Collection ni `collection_manual_review.csv`. No se ejecutó `apply`.

## Resultado

Las dos cartas físicas Mihawk están representadas por dos Collection items distintos (`134` y `135`), ambos con `quantity=1`. No existe un problema de modelo de inventario ni una carta Mihawk faltante.

| Physical identity | Collection item | Current card record | Cardmarket product | Status |
|---|---:|---:|---|---|
| Cavendish OP01-008 — Japanese Box Topper | 141 | `card_id=15290`, Box Topper | [768247 — OP01-JP V2](https://www.cardmarket.com/en/OnePiece/Products/Singles/Romance-Dawn-Japanese/Cavendish-OP01-008-V2) | EXACT |
| Dracule Mihawk OP01-070 — Japanese base, V1 | 135 | `card_id=15437`, Fixed Reprint/base | [768324 — OP01-JP V1](https://www.cardmarket.com/en/OnePiece/Products/Singles/Romance-Dawn-Japanese/Dracule-Mihawk-OP01-070-V1) | EXACT |
| Dracule Mihawk OP01-070 — Japanese Alternate Art, V2 | 134 | `card_id=15439`, Alternate Art/Fixed Reprint | [768325 — OP01-JP V2](https://www.cardmarket.com/en/OnePiece/Products/Singles/Romance-Dawn-Japanese/Dracule-Mihawk-OP01-070-V2) | EXACT |
| King OP01-096 — Japanese Alternate Art, Fixed Reprint | 154 | `card_id=15503`, actualmente base/Fixed Reprint | [768359 — OP01-JP V2](https://www.cardmarket.com/en/OnePiece/Products/Singles/Romance-Dawn-Japanese/King-OP01-096-V2) | MANUAL_WEB_REVIEW |

## King: motivo de revisión

La fotografía confirma King Japanese Alternate Art. El registro actual del item 154 apunta a `card_id=15503`, cuya identidad local es `Fixed Reprint` base y cuyo producto asociado es `768358` (OP01-JP V1). El catálogo local contiene el registro compatible `card_id=15505`, `Alternate Art | Fixed Reprint`, y su CardTrader Blueprint exacto `244640` apunta al producto Cardmarket `768359`.

Por lo tanto, `768359` es el único producto Cardmarket compatible con la carta física King Alternate Art. El estado es `MANUAL_WEB_REVIEW` porque el Collection item todavía referencia el registro local base; no se modifica DB ni mapping en este pass. Deben descartarse base art, EN y OP01E Pre-Errata.

## DB read-only: Mihawk inventory

| Collection item | Quantity | card_id | Name | Number | Set | Language | Variant | External identity |
|---:|---:|---:|---|---|---|---|---|---|
| 134 | 1 | 15439 | Dracule Mihawk | OP01-070 | op01 | JP | Alternate Art \| Fixed Reprint | Cardmarket `690897`, `768325`; CardTrader `244585` |
| 135 | 1 | 15437 | Dracule Mihawk | OP01-070 | op01 | JP | Fixed Reprint/base | Cardmarket `690896`, `768324`; CardTrader `244584` |

Physical cards: 2  
Collection identities: 2  
Inventory matches physical cards: YES  
Inventory issue: NONE

## Cardmarket revalidation

The product catalogue and current Cardmarket pages were checked by identity structure only: product title/card number, expansion family, language family and version. Prices, seller listings and cheapest/most expensive results were not used.

- Cavendish: `idProduct 768247`, Romance Dawn (Japanese), V2; local exact CardTrader metadata is `Box Topper`, release `3332`.
- Mihawk base: `idProduct 768324`, Romance Dawn (Japanese), V1; local product catalogue name is Dracule Mihawk OP01-070.
- Mihawk Alternate Art: `idProduct 768325`, Romance Dawn (Japanese), V2; local exact metadata is `Alternate Art | Fixed Reprint`, release `3332`.
- King Alternate Art: `idProduct 768359`, Romance Dawn (Japanese), V2; local exact metadata for `card_id=15505` is `Alternate Art | Fixed Reprint`, release `3332`.

The previous evidence that reused `768359` for two different cards is contaminated. It is rejected: the local catalogue assigns `768359` to King OP01-096, while Mihawk Alternate Art is `768325`. Final duplicate idProduct count across these four identities: `0`.

## Consolidated identity state

| Scope | Total | EXACT | PHYSICAL_CONFIRMATION_REQUIRED | MANUAL_WEB_REVIEW |
|---|---:|---:|---:|---:|
| Magic | 97 | 97 | 0 | 0 |
| One Piece | 23 | 22 | 0 | 1 |
| Collection | 120 | 119 | 0 | 1 |

Provenance gaps: `45`, preserved from the prior audit. No historical provenance was deleted or rewritten.

The collection is not yet 120/120 EXACT because item 154 requires a later identity correction from local base record `15503` to the physically confirmed Alternate Art record `15505` / Cardmarket `768359`.

## Security

DB SHA-256 before: `e155b0776922ac72e191a98b30b6bb44427664cf2ef0ead4f9c6d5e7c53ec225`  
DB SHA-256 after: `e155b0776922ac72e191a98b30b6bb44427664cf2ef0ead4f9c6d5e7c53ec225`

SQLite `PRAGMA integrity_check`: `ok`  
SQLite `PRAGMA foreign_key_check`: no violations  
DB byte-for-byte unchanged: `YES`  
Mappings modified: `NO`  
Review CSV modified: `NO`  
Apply executed: `NO`
