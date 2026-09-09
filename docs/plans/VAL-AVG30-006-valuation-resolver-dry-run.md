# VAL-AVG30-006 — Valuation Resolver Dry Run

## Contrato

Implementar un resolver determinístico, local, read-only y reproducible para evaluar
Avg30 contra la identidad ya almacenada. El comando no llama APIs, no escribe snapshots
y no modifica la DB productiva. Genera `summary.md` y `results.json` bajo
`reports/valuation/avg30_resolver/YYYY-MM-DD/`.

La selección temporal es efectiva: por cada Product ID se usa la observación más reciente
de `market_price_history` observada hasta `as_of`, inclusive. Si no existe, la decisión es
`NULL + MISSING_AVG30`. Se registran `observation_observed_at`, `as_of` y
`observation_age_days`; la antigüedad es informativa mientras no exista una política de
freshness normativa.

El resolver reutiliza mappings, scopes, `match_status` y `language_scope` existentes. Avg30
base solo se asigna con identidad/producto/set compatibles. Avg30 alternativo se usa para
foil únicamente con mapping foil `EXACT`, elegible y evidencia compatible; nunca se usa el
Avg30 base como fallback. `EXACT` exige evidencia completa de printing, idioma, finish,
variante/arte y métrica. Los resultados nulos usan un único motivo normalizado.

Se evalúan Collection, Wishlist, Pokémon 151 y Magic LOTR. Los reportes incluyen cobertura
por scope/juego, motivos, antigüedad, ejemplos, comparación legacy y simulación en memoria.
`current_price` no se modifica ni se convierte en alias.

## Recomendación

Se separan `technical resolver correctness` y `actual backfill usefulness`. Se informa el
subconjunto elegible, filas no elegibles, cobertura, scopes y juegos afectados. No hay
porcentaje mínimo arbitrario. `READY_FOR_BACKFILL` exige clasificación completa, motivos
válidos, ausencia de bloqueos/promociones inseguras y al menos una valuación utilizable en
cada scope/juego propuesto; en caso contrario se emite `NOT_READY_FOR_BACKFILL`.

## Validación

Se cubren selección temporal, antigüedad, identidad, idioma, finish, variante, foil/base,
EXACT, ausencia de Avg30, compatibilidad legacy, cantidades, cobertura, recomendación,
DB unchanged, ausencia de HTTP y JSON reproducible.
