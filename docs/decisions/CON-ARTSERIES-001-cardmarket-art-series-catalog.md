# CON-ARTSERIES-001 — Cardmarket Art Series como catálogo activo

Fecha: 2026-08-28

## Decisión

Promover en el mismo `cards.id` las filas legacy de Magic LOTR Art Series que
tengan correspondencia Cardmarket 1:1 y evidencia verificable de variante. No se
crean cards nuevas ni se cambia el esquema.

Cardmarket Product ID es la identidad principal de una entrada Art Series.
Scryfall no es una dependencia de Art Series y no se inventan `scryfall_id` ni
`scryfall_raw`. CardTrader se usa únicamente para verificar la variante y aportar
imágenes ya existentes.

Las filas verificadas usan `catalog_status='active'`, `finish='nonfoil'`,
`release_kind='special'`, `art_kind='special'` y `catalog_source='cardmarket'`.
La variante normal usa `treatment='Art Series'` y `source_variant='art_series'`;
Gold-Stamped usa `treatment='Art Series Gold-Stamped'` y
`source_variant='art_series_gold_stamped'`. `finish='nonfoil'` representa ambas
variantes porque Gold-Stamped no es foil técnico.

Las 45 Art Series presentes actualmente en Collection fueron confirmadas
físicamente por el usuario como Gold-Stamped. Por eso, Collection usa
Gold-Stamped como fuente de verdad para esas 45 entradas, sin promover
automáticamente las 117 filas Art Series legacy no verificadas restantes.

## Evidencia y ambigüedad

La evidencia se evalúa primero desde un export local de CardTrader y después desde
metadata exacta de `card_images`. Gold-Stamped requiere `version='Gold-Stamped'`
o un collector terminado en `g`; no se usa `printing_variant` legacy como fallback.
Sin evidencia suficiente la fila permanece `legacy` y se reporta como
`ambiguous`. Los números `ART-n` existentes se conservan y no se derivan desde
códigos `Axx`.

## Matching manual

El resolver busca primero el mapping exacto de `collection_items.cardmarket_product_id`.
El fallback Art Series exige set, nombre Art Series y `ART-n` compatibles. Todos
los candidatos deben tener `catalog_status='active'`. Esto evita exponer filas
legacy duplicadas y evita que, por ejemplo, `Art Series: Fog on the Barrow-Downs`
coincida con la carta jugable `Fog on the Barrow-Downs`.

No se elimina simplemente el filtro defensivo `finish IS NOT NULL`: se mantiene
junto con el estado activo y las restricciones Magic/LTR. El endpoint
`resolve-match` vuelve a validar actividad, compatibilidad Art Series y mapping
exacto cuando existe producto Cardmarket.

## Preservación y operación

La promoción no modifica mappings Cardmarket, snapshots de precio, imágenes
CardTrader, cantidades, purchase prices, fechas, Wishlist ni datos Scryfall.
Las filas de Collection se marcan resueltas solo cuando su `card_id` fue
promovido correctamente.

`--apply` copia la SQLite real a una ubicación temporal, aplica una transacción,
ejecuta `PRAGMA integrity_check` y `PRAGMA foreign_key_check`, crea un backup y
solo entonces copia la DB validada de vuelta. `--dry-run` no escribe. No se usan
llamadas externas.
