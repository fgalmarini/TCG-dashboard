# Sprint Contract — Reestructurar documentación del proyecto TCG Dashboard

## Objetivo

Reorganizar la documentación del proyecto para que Codex y humanos puedan entender el contexto del dashboard sin cargar un `AGENTS.md` gigante.

El resultado debe separar:

- reglas operativas permanentes para agentes;
- objetivos de producto;
- arquitectura y modelo de datos;
- estado actual real;
- decisiones técnicas;
- contratos/planes de ejecución.

Esta tarea es solo de documentación y organización. No debe cambiar lógica de backend, frontend, importer, scripts, base de datos ni tests salvo que sea estrictamente necesario para actualizar referencias documentales.

## Contexto

El proyecto es un dashboard personal de colección, valuación y trading de TCGs:

- Pokémon TCG;
- One Piece Card Game;
- Magic: The Gathering, actualmente enfocado en LOTR.

Cardmarket es la fuente primaria de precios europeos.

Scryfall puede usarse solo como fuente de metadata/catálogo para Magic cuando exista lookup directo por `cardmarket_id_product`.

El proyecto ya tiene fases cerradas:

- Fase 1: documentación/arquitectura inicial;
- Fase 2: investigación Cardmarket;
- Fase 3: schema SQLite;
- Fase 4: importer Cardmarket;
- revisión aditiva Magic/Scryfall;
- Fase 5: carga manual de colección;
- Fase 6: dashboard básico Overview + Collection read-only.

Fase actual: 7.

No construir todavía:

- Trading;
- Analytics;
- CARDMADNESS Mode;
- edición web de colección;
- Supabase;
- scrapers;
- integración privada de Cardmarket API.

## Estructura deseada

Crear o actualizar esta estructura:

```text
AGENTS.md
docs/PRODUCT.md
docs/ARCHITECTURE.md
docs/CURRENT_STATE.md
docs/decisions/
docs/plans/
```

### `AGENTS.md`

Debe quedar corto, práctico y operativo.

Debe contener:

- mapa de docs importantes;
- scope actual;
- comandos de desarrollo/verificación;
- reglas de seguridad de datos;
- reglas de fuentes externas;
- restricciones de implementación;
- definition of done.

No debe contener narrativa larga de producto, roadmap completo, historia extensa de fases ni decisiones detalladas.

Debe apuntar a los docs nuevos cuando el agente necesite más contexto.

### `docs/PRODUCT.md`

Debe contener la visión de producto:

- qué es el TCG Dashboard;
- objetivos principales;
- TCGs soportados;
- Market Value vs Trade Value;
- Collection;
- Condition y grading;
- Portfolio calculations;
- Historical data;
- CARDMADNESS Mode;
- Trade Calculator;
- Want List;
- Dashboard sections;
- UI principles;
- future possibilities.

Este archivo puede tomar contenido del `AGENTS.md` actual, pero debe limpiarse para que sea un documento de producto, no instrucciones para agentes.

### `docs/ARCHITECTURE.md`

Debe contener:

- stack técnico actual;
- frontend;
- backend;
- base de datos;
- principios relacionales;
- flujo Cardmarket → importer → DB → API → dashboard;
- estrategia de histórico de precios;
- identificación de cartas;
- integridad de datos;
- reglas de fuentes externas;
- rol exacto de Cardmarket;
- rol exacto de Scryfall;
- límites actuales;
- posibilidad futura de PostgreSQL/Supabase sin convertirlo en scope actual.

Importante: `conventions.json` no debe copiarse entero acá. Sus decisiones deben resumirse o migrarse a `docs/decisions/`.

### `docs/CURRENT_STATE.md`

Debe contener el estado real actual del proyecto:

- fase actual;
- fases cerradas;
- resultados reales conocidos;
- métricas actuales del dashboard/API;
- datos importantes de la DB;
- restricciones heredadas;
- incidente FUSE/bridge con SQLite;
- qué NO está en scope todavía;
- siguiente tarea recomendada.

Este archivo reemplaza la sección larga “Current Phase” del `AGENTS.md` actual.

### `docs/decisions/`

Convertir el contenido útil de `conventions.json` en ADRs Markdown.

Crear al menos:

```text
docs/decisions/README.md
docs/decisions/TCG-DEC-001-scryfall-magic-catalog.md
docs/decisions/TCG-DEC-002-cards-data-source-scryfall-raw.md
docs/decisions/TCG-DEC-003-supabase-deferred.md
docs/decisions/TCG-DEC-004-manual-collection-review-csv.md
docs/decisions/TCG-DEC-005-dashboard-basic-scope.md
```

Cada ADR debe incluir:

- ID;
- fecha;
- tipo;
- estado;
- decisión;
- contexto;
- consecuencia;
- referencias internas si existen.

No inventar decisiones nuevas. Si falta evidencia para completar una sección, dejarlo explícito como “No documentado en la fuente actual”.

Se puede conservar `conventions.json` como snapshot histórico/machine-readable, pero el índice humano principal debe ser Markdown.

### `docs/plans/`

Debe quedar como carpeta para sprint contracts y planes de ejecución.

Mover o copiar ahí los contratos existentes si ya están en el repo, sin romper referencias.

Si existen archivos tipo:

- `fase5-*.md`;
- `fase6-*.md`;
- planes de reparación de Magic;
- contratos de importación;

proponer su ubicación en `docs/plans/`.

No eliminar archivos históricos si no estás 100% seguro. Preferir mover con cuidado o dejar un índice con referencias.

## Reglas de ejecución

1. Inspeccionar el repo antes de editar:

```bash
pwd
git status --short
find . -maxdepth 3 -type f | sort | sed 's#^\./##'
```

2. Leer como mínimo:

- `AGENTS.md`;
- `conventions.json`, si existe;
- docs de fases existentes relevantes;
- README si existe.

3. Crear una propuesta breve de cambios antes de aplicar si el repo tiene documentos no esperados o nombres ambiguos.

4. Aplicar cambios solo de documentación.

5. Mantener compatibilidad con Codex:

- `AGENTS.md` debe seguir estando en la raíz;
- debe ser corto y accionable;
- debe linkear a docs más largos;
- debe incluir comandos de verificación.

6. No tocar:

- `backend/`;
- `frontend/`;
- `data/`;
- archivos SQLite;
- archivos `.env`;
- catálogos/price guides descargados;
- scripts de importación.

Excepto si solo se actualizan referencias documentales obvias y seguras.

## Contenido mínimo esperado para `AGENTS.md`

El nuevo `AGENTS.md` debe tener una estructura parecida a esta:

```md
# AGENTS.md

## Project context

Personal TCG collection, valuation and trading dashboard.

Read these docs before large changes:

- docs/PRODUCT.md
- docs/ARCHITECTURE.md
- docs/CURRENT_STATE.md
- docs/decisions/
- docs/plans/

## Current scope

Current phase: Phase 7.

Phase 6 is closed. Do not reopen closed phases unless new evidence requires it.

Do not build Trading, Analytics, CARDMADNESS Mode, collection web editing, Supabase migration or scrapers unless explicitly requested.

## Commands

Backend tests:

```bash
python3 -m pytest backend/api/ backend/db backend/importer backend/scripts -q
```

Frontend build:

```bash
npm run build
```

## Data safety

SQLite writes against the mounted DB must be done on a local temporary copy, then copied back after:

- PRAGMA integrity_check
- PRAGMA foreign_key_check

Do not write directly to the mounted DB if the bridge/FUSE issue applies.

## External data rules

Cardmarket remains the source for prices.

Scryfall may be used only for Magic metadata/catalog enrichment.

Do not assume Cardmarket API credentials.

Do not implement scrapers or undocumented access.

If mapping is ambiguous, report it. Do not guess.

## Definition of done

A change is done only when:

- relevant tests pass;
- frontend builds if frontend changed;
- DB integrity checks pass if DB changed;
- ambiguous mappings are reported;
- docs/current state are updated when phase behavior changes.
```

Adjust wording to match the real repo, but preserve the intent.

## Verificación

Como esta tarea es documental, la verificación mínima es:

```bash
git diff --check
```

Si el repo tiene tests rápidos/documentation lint, correr también.

Si no se tocó código, no hace falta correr toda la suite, pero sí reportar que no se corrió por ser documentación-only.

Si alguna referencia a rutas queda dudosa, reportarla.

## Resultado esperado

Al final, entregar:

1. lista de archivos creados/modificados;
2. resumen corto de qué se movió a cada documento;
3. confirmación de que `AGENTS.md` quedó más corto y operativo;
4. resultado de `git diff --check`;
5. cualquier ambigüedad o archivo histórico que se decidió no mover.

## Criterios de aceptación

- `AGENTS.md` ya no funciona como documento total del proyecto.
- La visión del producto está en `docs/PRODUCT.md`.
- La arquitectura está en `docs/ARCHITECTURE.md`.
- El estado real está en `docs/CURRENT_STATE.md`.
- Las decisiones de `conventions.json` están representadas como ADRs Markdown.
- Los planes/sprint contracts tienen carpeta propia.
- No se toca lógica de la app.
- No se pierden decisiones históricas.
- Un Codex nuevo puede entrar al repo, leer `AGENTS.md`, seguir los enlaces, y entender qué hacer sin tragarse una biblia de 700 líneas.
