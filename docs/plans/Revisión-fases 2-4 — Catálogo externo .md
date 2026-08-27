# Revisión Fases 2-4 — Catálogo externo autoritativo (Magic/Scryfall) + decisión de storage (SQLite vs Supabase)
**Para: Claude Code CLI, ejecutando en el repo `/Users/facundogalmarini/Desktop/TCG DASHBOARD`**
**Estado: decisión tomada en sesión de análisis (Claude/Cowork) el 2026-08-24. Este documento reemplaza, para Magic, el mecanismo de self-healing descrito en `docs/plans/fase2-cardmarket-hallazgos-y-schema.md` sección 6, y es la base para el próximo sprint. No es Fase 5 — es una revisión aditiva de Fases 3-4, que siguen cerradas y no se re-abren. Decisiones estructurales registradas también en `conventions.json` (`TCG-DEC-001`/`TCG-DEC-002`/`TCG-DEC-003`). Implementación operacionalizada en `docs/plans/fase5-scryfall-magic-backfill-sprint-contract.md`.**

---

## 0. Resumen de la decisión

La pregunta original era binaria: ¿seguir con self-healing incremental o pivotar a una base de datos externa completa? La respuesta, después de investigar, es **que no es una decisión única — es una decisión por juego**, porque la disponibilidad de una fuente externa confiable es completamente distinta en cada caso:

| Juego | Decisión | Por qué |
|---|---|---|
| **Magic (LOTR)** | Pivotar a población autoritativa vía **Scryfall** | Fuente gratis, estable, oficial-de-facto, con lookup directo por `idProduct` de Cardmarket. Resuelve exactamente el gap que self-healing no podía: nombre de expansión, card number, variantes ricas (showcase/borderless/foil/art series). Scope ya es chico (757 productos) → costo bajo. |
| **One Piece** | **Mantener self-healing.** No se cambia nada de lo ya implementado. | No existe un equivalente de Scryfall verificado al mismo nivel de confianza (ver sección 2). Además, el problema real detectado en Fase 4 (700 "ambiguous") es de precios empatados entre variantes — no de falta de datos de catálogo. Una fuente externa no resolvería esos 700 casos porque Cardmarket tampoco los distingue en su propia web. El foco debe ser la UX de confirmación en lote para Fase 5, no una integración nueva. |
| **Pokémon** | **Mantener self-healing / alta manual.** Sin cambios. | Colección de ~8 cartas. pokemontcg.io existe y es gratis, pero no tiene lookup por `idProduct` de Cardmarket — requeriría matching por nombre+set, que reintroduce el mismo trabajo manual que ya existe hoy. El costo de integrarlo no se justifica con este volumen. Revisar de nuevo solo si la colección crece a un volumen donde el matching manual duela de verdad (ej. >50 cartas). |

Esto significa que la "re-arquitectura" es mucho más chica de lo que sonaba: es un enriquecimiento aditivo para un juego (Magic), no una reescritura del catálogo completo ni de los otros dos juegos.

**Cardmarket no se reemplaza en ningún caso.** Sigue siendo la única fuente de precios de mercado europeos para los 3 juegos. Scryfall (y cualquier fuente futura para Pokémon/One Piece) es exclusivamente metadata de catálogo — nunca precio. `cardmarket_products` y `market_price_history` no cambian.

Sobre Supabase: es una decisión **separada e independiente** de todo lo anterior (ver sección 4). Se recomienda no bloquear el enriquecimiento de Magic ni la Fase 5 en la migración de storage.

---

## 1. Magic/LOTR — pivot a Scryfall (implementar ahora)

### 1.1 Qué confirma Scryfall

- `GET https://api.scryfall.com/cards/cardmarket/:id` acepta directamente el `idProduct` de Cardmarket (llamado `cardmarket_id` en Scryfall) y devuelve el objeto Card completo de Scryfall.
- El objeto Card de Scryfall trae, entre otros: `set`, `set_name`, `collector_number`, `name`, `frame_effects` (incluye `showcase`, `extendedart`, etc.), `border_color` (`borderless`), `promo_types`, `finishes` (`foil`/`nonfoil`/`etched`), `image_uris`. Esto cubre exactamente las categorías de variante que aparecieron al cargar la colección real (Showcase Foil Ringframe, Borderless, Borderless Foil, Art Series Gold Stamp) — son combinaciones de `frame_effects` + `border_color` + `finishes`, no una taxonomía nueva que haya que inventar.
- Es gratis, sin API key, ampliamente usada en producción por terceros desde hace años (fuente estable — cumple las reglas de fuentes externas de `docs/ARCHITECTURE.md` — Scryfall no es scraper ni undocumented, es la API pública oficial-de-facto del ecosistema Magic).

### 1.2 Cómo se implementa (scope: solo los 757 productos ya importados)

No hace falta descargar el bulk data completo de Scryfall (varios GB, todas las cartas de Magic de la historia) — sería sobre-ingeniería para 757 cartas. En cambio:

1. Nuevo script, **separado** del importer de Fase 4 (no tocar `backend/importer/`): recorre `cardmarket_products` filtrando `cardmarket_id_expansion IN (5285, 5308, 5396)` (los mismos 3 scopeados en Fase 2/4).
2. Por cada `cardmarket_id_product`, `GET https://api.scryfall.com/cards/cardmarket/{id}` con ~100-150ms entre requests (cortesía de rate limit, no es un límite duro pero Scryfall lo pide).
3. Con la respuesta, completar directamente (no self-heal, no esperar a que se agregue a colección):
   - `expansions.name`, `expansions.set_code` (desde `set`/`set_name`)
   - `cards.name`, `cards.card_number` (desde `collector_number`)
   - `cards.printing_variant` (**regla confirmada 2026-08-24**, ver 1.3.1) y `cards.variant_label`: derivar de `frame_effects` + `border_color` + `finishes`
   - `cards.image_url = image_uris.normal` (o el tamaño que se prefiera), `cards.image_source = 'scryfall'`
4. Reporte final: cuántos de los 757 resolvieron OK, cuántos no matchearon (no debería haber ninguno, ya que estos productos vinieron del mismo Cardmarket `idProduct` que Scryfall indexa — pero reportar, no asumir, por la regla de integridad de `docs/ARCHITECTURE.md`).
5. Éste es un script de backfill **de una sola corrida** (no un servicio permanente). Si en el futuro se agregan más expansiones LOTR al scope, se vuelve a correr con el scope ampliado — mismo patrón manual-trigger que el importer de precios.

### 1.3 Cambios de schema necesarios (aditivos, no rompen Fase 3)

- Agregar columna `cards.data_source` NULLABLE (`'scryfall'` / `'cardmarket_heuristic'` / `'manual'`) — trazabilidad de por qué se confía en ese dato. Sin esto, dentro de un año no se sabe si un `printing_variant` viene de una inferencia de precio vieja o de una fuente autoritativa. Esta columna también es lo que evita ambigüedad de significado en `printing_variant='other'` entre juegos (ver 1.3.1).
- **Confirmado, ya no opcional:** agregar `cards.scryfall_raw` NULLABLE (texto JSON) con los campos crudos relevantes de Scryfall (`frame_effects`, `border_color`, `finishes`, `promo_types`) además de `variant_label`. `variant_label` se **genera a partir de** estos campos (no se escribe a mano en el script) — así el texto queda para mostrar en UI, y los campos estructurados quedan disponibles para filtrar/agregar (ej. "cuántas foils tengo", "valor por tipo de variante" — ver `docs/PRODUCT.md`) sin volver a pegarle a la API de Scryfall ni parsear `variant_label` con regex.
- No se toca `cardmarket_products`, `cardmarket_product_mappings`, `market_price_history`, `collection_items`, `want_list_items` — quedan exactamente como en Fase 3.

### 1.3.1 Regla de clasificación de `printing_variant` para Magic (confirmada 2026-08-24)

- `'normal'`: `finishes` = solo `nonfoil`, `border_color` = `black`, `frame_effects` vacío, sin `promo_types`.
- `'other'`: cualquier otra combinación (foil, borderless, showcase, extended art, art series, promo, etc.) — **sin distinguir cuál es "la rara"**, a diferencia del mecanismo de precio-heurística que sigue usándose para One Piece. No hace falta porque acá no estamos adivinando: la fuente es autoritativa, así que separar sub-categorías de `other` no resuelve ninguna ambigüedad real, solo agrega mantenimiento de enum.
- El detalle real de qué combinación específica es queda en `variant_label` (legible) + `cards.scryfall_raw` (estructurado, ver 1.3) — no en el enum de `printing_variant`.
- Con `data_source='scryfall'`, `printing_variant='other'` significa "variante confirmada, no sub-categorizada" — distinto de `printing_variant='ambiguous'`/`'other'` en One Piece con `data_source='cardmarket_heuristic'`, que sigue significando "pendiente de revisión manual". No hace falta un valor de enum nuevo para separar estos dos significados; el join con `data_source` alcanza.

### 1.4 Fuera de scope de esta revisión

- Ampliar a todo Magic (no solo LOTR). Se revisita el día que el usuario compre cartas de otras expansiones — mismo criterio incremental que ya se usó para decidir el scope de Fase 2.
- Backfill de imágenes/metadata para Pokémon u One Piece.
- Cualquier cambio a la lógica de precios.

---

## 2. One Piece — por qué NO se cambia nada

Se investigaron alternativas (optcgapi.com, apitcg.com, JustTCG, TCGdex, Limitless TCG) buscando un equivalente de Scryfall. Ninguna confirmó, con el mismo nivel de certeza que Scryfall, las tres cosas que hacen falta: (a) gratis y estable, (b) lookup directo por `idProduct` de Cardmarket, (c) cobertura completa de variantes/expansiones. Algunas son de pago (JustTCG), otras no documentan públicamente su granularidad de variantes ni vínculo con Cardmarket (apitcg.com, optcgapi.com).

Más importante: el problema real que dejó Fase 4 (700 productos `ambiguous`) **no es un problema de falta de catálogo** — es un problema de que ~544 de esos 700 son pares de variantes con precios genuinamente parecidos, donde ni Cardmarket ni (probablemente) ninguna fuente externa distingue cuál es la "rara". Traer una base de datos externa no resuelve una ambigüedad que la fuente de precios tampoco resuelve. El resultado sería el mismo: confirmación manual — solo que con una dependencia nueva encima.

Recomendación: no invertir en esto ahora. Si en el futuro aparece una fuente que explícitamente confirme tener el mismo patrón de lookup por `idProduct` que Scryfall (verificarlo, no asumirlo — regla de `docs/ARCHITECTURE.md`), se puede reconsiderar puntualmente para One Piece. Hasta entonces, el esfuerzo va a la UI de confirmación en lote de Fase 5 (ya prevista en `docs/plans/fase4-importer-sprint-contract.md` sección 5).

## 3. Pokémon — por qué NO se cambia nada

pokemontcg.io existe, es gratis, y tiene datos de set/card number/rareza razonablemente buenos. Pero no ofrece lookup por `idProduct` de Cardmarket (solo referencia TCGPlayer en sus precios) — habría que matchear por nombre+set+número, con el riesgo de falsos positivos que ya se evitó deliberadamente en Fase 2. Con ~8 cartas reales en la colección, ese trabajo de integración (matching, QA, mantenimiento) cuesta más que cargar 8 cartas a mano. Se mantiene la decisión original de Fase 2 sección 5 sin cambios. Revisar si la colección de Pokémon crece a un volumen donde valga la pena (sugerido: >50 cartas).

---

## 4. Supabase — decisión separada, no bloqueante

Esta es una decisión de **storage engine**, no de catálogo. Son ortogonales: se puede hacer el enriquecimiento de Magic (sección 1) sobre SQLite sin tocar Supabase, y se puede migrar a Supabase sin cambiar nada de cómo se puebla el catálogo. Vale la pena separarlas explícitamente para no tomar las dos decisiones a la vez como si fueran una sola.

### 4.1 Límites reales del free tier de Supabase (verificado, no asumido)

- 500 MB de base de datos, 5 GB de egress + 5 GB de egress cacheado por mes, 1 GB de file storage.
- Proyectos se pausan automáticamente tras 1 semana de inactividad (hay que "despertarlos" manualmente o con un ping periódico).
- Límite de 2 proyectos activos simultáneos en la cuenta free.
- Sin backups automáticos en el plan free.
- API requests: ilimitadas.

Para el volumen de este proyecto (catálogo de 3 juegos + colección personal — del orden de decenas de miles de filas, no millones), 500 MB alcanza sobrando. El riesgo real no es capacidad, es el pausado semanal (si no se usa el dashboard por una semana, la primera carga después va a tardar más) y la ausencia de backups (para datos que representan valor de colección real, conviene un export/backup propio periódico, sea cual sea el engine).

### 4.2 El argumento real a favor de Supabase (más allá de "experimentar")

El usuario ya lo tiene como objetivo explícito de aprendizaje, lo cual es válido por sí mismo. Pero hay además un argumento de producto concreto: el evento CARDMADNESS Düsseldorf es a fines de septiembre 2026 (~5 semanas desde hoy) y `docs/PRODUCT.md` ya prevé un "modo CARDMADNESS" para usarse en el evento físico. Si el dashboard corre solo local (ver `README.md`), en el evento solo se puede consultar llevando la Mac. Una base hosteada (Supabase u otra) es lo que habilitaría consultarlo desde el celular en Düsseldorf sin depender de la laptop — eso sí es una razón de producto, no solo de aprendizaje.

### 4.3 El argumento en contra (a tener en cuenta, no necesariamente para frenar)

`AGENTS.md` pide evitar dependencias innecesarias y `docs/ARCHITECTURE.md` mantiene SQLite como storage actual. Agregar un servicio hosteado con auth, red y un modelo de pausado introduce una dependencia externa nueva donde hoy hay un archivo `.db` sin partes móviles. Esto no es motivo para no hacerlo — es motivo para hacerlo con los ojos abiertos y no como un efecto secundario de arreglar el catálogo.

### 4.4 Recomendación de secuencia

1. **Ahora:** enriquecimiento de Magic vía Scryfall sobre SQLite (sección 1) + arrancar Fase 5 (alta manual de colección) como estaba planeado. Esto es rápido, no depende de nada nuevo, y desbloquea lo que hace falta para preparar Cardmadness.
2. **En paralelo o después, como su propio track:** migración a Supabase, tratada como una fase propia (sugerido: documentarla y numerarla explícitamente cuando se decida arrancarla — no reemplaza Fase 5, corre en paralelo o después). Definir antes de arrancarla: (a) si Supabase reemplaza el rol de FastAPI (Supabase ya da REST/GraphQL autogenerado vía PostgREST) o si FastAPI se mantiene como capa intermedia — esto es una decisión de arquitectura de backend que no estaba en el alcance de esta revisión y conviene resolverla explícitamente antes de escribir código, no asumirla; (b) estrategia de backup propio, dado que el free tier no lo incluye.
3. Dar margen real antes del evento: si Supabase se empieza a implementar, dejarlo con al menos 1-2 semanas de colchón antes de fines de septiembre, con la versión local/SQLite como fallback funcional si algo no cierra a tiempo.

---

## 5. Checklist de lo próximo a ejecutar

1. Migración de schema aditiva: columna `cards.data_source` (y `cards.scryfall_raw` si hace falta) — no tocar tablas de precios/colección.
2. Script nuevo de backfill Magic→Scryfall (sección 1.2), corrido una vez sobre los 757 productos ya importados.
3. Reporte de resultados (cuántos resolvieron, cuántos no).
4. Seguir con Fase 5 (alta manual de colección) tal como estaba planeada — sin cambios por esta revisión, salvo que la UI de confirmación de variantes de One Piece soporte revisión por lote (ya lo pedía `docs/plans/fase4-importer-sprint-contract.md`).
5. Decisión de Supabase: tratarla aparte, no como parte de este sprint.
