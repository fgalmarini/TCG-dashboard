# TCG-DEC-010 — Avg30 resolver dry-run

## Estado

Aceptada para VAL-AVG30-006.

## Decisiones nuevas

- `--as-of` es normativo: cada Product ID selecciona la observación local más reciente
  con fecha/hora no posterior al día límite, incluyendo observaciones del propio día.
- Cada resultado conserva `observation_observed_at`, `as_of` y `observation_age_days`.
  La antigüedad se reporta y no invalida por sí sola la valuación sin una política de
  freshness aprobada posteriormente.
- `READY_FOR_BACKFILL` requiere utilidad real: al menos una valuación elegible por cada
  scope/juego propuesto, cobertura cuantificada, clasificación completa y ausencia de
  bloqueos sistémicos o promociones inseguras. No se impone un umbral porcentual.

Las decisiones previas sobre Avg30, `valuation_value`, `current_price`, identidad, finish,
idioma y mappings permanecen en VAL-AVG30-005 y no se duplican aquí.

VAL-AVG30-007 agrega el gate de apply: el manifest es la única fuente autorizada, el
currentness de valuación no reutiliza `is_current` legacy y cualquier falta de columnas
valuation-only o cambio de evidencia aborta antes de escribir.
