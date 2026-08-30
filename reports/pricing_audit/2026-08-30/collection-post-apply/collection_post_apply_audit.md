# Collection Pricing — Immediate Post-Apply Audit

Auditoría del estado real persistido después del primer apply de Collection. No se ejecutó otro apply, no se restauró el backup y no se modificaron datos durante esta auditoría.

## POST-APPLY DATABASE

- New SHA-256: `38959ecb8224c9c4e06c00dbc7ccda37d17660c828b72be0418f1419c1437aff`.
- Backup de referencia: `backups/pricing/tcg_dashboard_2026-08-30T14-02-35.608856_00-00.db`.
- `integrity_check`: `ok`.
- `foreign_key_check`: sin filas.

## COLLECTION

- Items: **120**.
- API rows: **120** (Magic 97, One Piece 23).
- Duplicate rows: **0**.
- Persisted current prices: **119 priced + 1 NULL**.
- Zero prices: **0**.
- El único `current_price IS NULL` es item 65; no existe `current_price=0`.

## IDENTITY

- Magic EXACT: **97/97**.
- One Piece EXACT: **23/23**.

## PRICING

- Priced: **119**.
- UNPRICED: **1** (Magic item 65).
- Zero prices: **0**.
- Current Collection resolutions: **120 Cardmarket**; CardTrader current: **0**.

## ONE PIECE

- Low available: **23/23**.
- Persisted priced: **23/23**.
- Calculated `SUM(current_price * quantity)`: **EUR 58.55**.
- Calculated `SUM(Cardmarket Low * quantity)`: **EUR 58.55**.
- Apply reported `Resolved Low value`: **0**.
- Explanation: **bug del agregado del reporte, no de los datos persistidos**. Durante `collection_audit_rows`, la contribución Low se calculaba antes de aplicar las aprobaciones manuales; por eso el resumen quedó en cero aunque DB/API tienen `current_price` y Low válidos.

| Item | Card | Number | idProduct | Metric | Low | Trend | current_price | Currency |
|---:|---|---|---:|---|---:|---:|---:|---|
| 133 | Borsalino | OP05-051 | 733344 | Low | EUR 0.08 | EUR 0.39 | EUR 0.08 | EUR |
| 134 | Dracule Mihawk | OP01-070 | 768325 | Low | EUR 14.00 | EUR 17.23 | EUR 14.00 | EUR |
| 135 | Dracule Mihawk | OP01-070 | 768324 | Low | EUR 0.02 | EUR 1.10 | EUR 0.02 | EUR |
| 136 | Yamato | OP13-054 | 857251 | Low | EUR 0.05 | EUR 0.58 | EUR 0.05 | EUR |
| 137 | Lilith | OP13-113 | 857331 | Low | EUR 5.50 | EUR 7.29 | EUR 5.50 | EUR |
| 138 | Monkey.D.Luffy | EB02-061A | 808172 | Low | EUR 28.00 | EUR 44.59 | EUR 28.00 | EUR |
| 139 | Rob Lucci | OP05-093 | 733430 | Low | EUR 2.95 | EUR 4.23 | EUR 2.95 | EUR |
| 140 | X.Drake | OP05-055 | 733352 | Low | EUR 1.89 | EUR 4.28 | EUR 1.89 | EUR |
| 141 | Cavendish | OP01-008 | 768247 | Low | EUR 0.50 | EUR 0.92 | EUR 0.50 | EUR |
| 142 | Gol.D.Roger | OP13-064 | 857262 | Low | EUR 0.02 | EUR 0.25 | EUR 0.02 | EUR |
| 143 | Nefeltari Vivi | EB02-026 | 808127 | Low | EUR 0.10 | EUR 0.47 | EUR 0.10 | EUR |
| 144 | S-Snake | OP08-112 | 771756 | Low | EUR 0.05 | EUR 0.29 | EUR 0.05 | EUR |
| 145 | Koala | OP05-006 | 733281 | Low | EUR 0.02 | EUR 0.11 | EUR 0.02 | EUR |
| 146 | Monkey.D.Luffy | OP01-024 | 768265 | Low | EUR 0.02 | EUR 0.32 | EUR 0.02 | EUR |
| 147 | Yamato | EB02-006 | 808101 | Low | EUR 0.48 | EUR 1.27 | EUR 0.48 | EUR |
| 148 | Pica | OP05-032 | 733317 | Low | EUR 0.02 | EUR 0.36 | EUR 0.02 | EUR |
| 149 | Kin'emon | OP01-040 | 768285 | Low | EUR 0.05 | EUR 0.42 | EUR 0.05 | EUR |
| 150 | Trafalgar Law | EB02-045 | 808150 | Low | EUR 0.02 | EUR 0.48 | EUR 0.02 | EUR |
| 151 | Uta | OP13-023 | 857215 | Low | EUR 0.02 | EUR 0.20 | EUR 0.02 | EUR |
| 152 | Trafalgar Law | P-038 | 722798 | Low | EUR 1.80 | EUR 2.45 | EUR 1.80 | EUR |
| 153 | Stussy | OP13-110 | 857326 | Low | EUR 0.02 | EUR 0.29 | EUR 0.02 | EUR |
| 154 | King | OP01-096 | 768359 | Low | EUR 2.89 | EUR 6.57 | EUR 2.89 | EUR |
| 155 | Rebecca | OP05-091 | 733426 | Low | EUR 0.05 | EUR 0.17 | EUR 0.05 | EUR |

## MAGIC ITEM 65

- Identity: **EXACT** — `738134`.
- Finish: **foil**.
- Selected metric: **Foil Low**.
- Foil Low: **None**.
- Base Low: **EUR 0.05** (otro finish; no utilizado).
- `current_price`: **None**.
- Pricing: **UNPRICED**.
- Correct: **YES**.
- El apply mostró `Unpriced: 0` porque ese contador cuenta estados de identidad (`match_status`) y no ausencia del metric/precio seleccionado. Es una inconsistencia de definición del resumen, no una asignación de precio.

## CRITICAL IDENTITIES

- EB02-061A: **SAFE** — 808172 — Low EUR 28.00 — Trend EUR 44.59 — current EUR 28.00.
- Mihawk Base: **SAFE** — 768324 — current EUR 0.02.
- Mihawk Alternate Art: **SAFE** — 768325 — current EUR 14.00.
- Cavendish: **SAFE** — 768247 — current EUR 0.50.
- King: **SAFE** — 768359 — current EUR 2.89.
- Magic Gold-Stamped: **SAFE** — 44 manual approvals exact; Art Series total persisted exact: 45.
- EB02-061A → 808172; PRB02 no fue seleccionado.

## CARDTRADER

- Current prices sourced from CardTrader: **0**.

## HISTORICALS

- Historical price resurrection: **0**.
- No se borraron históricos. Las resoluciones vigentes son Cardmarket y prevalecen sobre fuentes anteriores.

## HISTORY

- One Piece inserted: **23**.
- Magic inserted: **3**.
- Magic 3-row explanation: comportamiento esperado e idempotente. El backup tenía 97 productos Magic con histórico para el snapshot actual salvo 3; 94 chocaron con la unicidad `(cardmarket_product_id, observed_at)` y se omitieron, mientras 3 se insertaron. No hubo pérdida de historial.

## CONVENTION VALUES (API)

- Muestra API item 138: Low EUR 28.00; Dealer Cash EUR 19.60 = Low × 70%; rango EUR 16.80–21.00; Trade EUR 22.40 = Low × 80%; rango EUR 19.60–23.80.
- Item 65 devuelve `market_value` y derivados Dealer/Trade como `NULL`; no se deriva desde el Low base 0.05.

## API VALIDATION

- `/api/collection`: 120 rows, 120 IDs únicos.
- Magic: 97; One Piece: 23.
- `market_value`/current price: 119 no nulos, 1 nulo.
- `market_value=0`: 0.
- Item 65: `market_value=NULL`.

## VERDICT

**POST-APPLY VERDICT: SAFE**
