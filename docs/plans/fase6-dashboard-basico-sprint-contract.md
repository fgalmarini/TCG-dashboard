# Fase 6 — Dashboard básico (Sprint Contract)

**Para: agente `developer` (Claude Code CLI), ejecutando en el repo
`/Users/facundogalmarini/Desktop/TCG DASHBOARD`. Depende de Fase 5 (alta manual de
colección), CERRADA — ver `docs/plans/fase5-alta-manual-coleccion-sprint-contract.md`
sección 9 (98/98 filas, 0 pendientes). Especifica el "Phase 6: Build basic dashboard"
del roadmap de `docs/PRODUCT.md`. Decisiones de alcance confirmadas con Facundo el
2026-08-25 (sesión Cowork), registradas en `conventions.json` → `TCG-DEC-005`.**

---

## 0. Punto de partida

No existe todavía ningún código de aplicación web en el repo: solo
`backend/importer/` (importer Cardmarket, Fase 4), `backend/scripts/` (loader de
colección, Fase 5) y `backend/db/` (schema + `tcg_dashboard.db`). Esta fase arranca
`backend/api/` y `frontend/` desde cero.

Estado real de la data al momento de escribir este contract (`tcg_dashboard.db`,
verificado con `PRAGMA integrity_check` = `ok`):

- `collection_items`: 98 filas. 79 con `card_id`/`cardmarket_product_id` seteados
  (100% Magic/LOTR), 19 con `card_id IS NULL` (`manual_entry=1`, sin precio de mercado
  posible — Pokémon + Magic fuera de catálogo).
- Las 79 filas con producto sí tienen al menos 1 fila en `market_price_history` cada
  una (backfill de Fase 5 corrió 1:1 sobre la colección ya cargada) — no hay caso de
  "tiene producto pero no tiene precio" hoy, pero el código no debe asumir que eso se
  mantiene así (Fase 7 va a traer snapshots repetidos, y un producto puede quedar sin
  precio nuevo temporalmente).
- `purchase_currency` es `NULL` en las 98 filas — no hay dato de multi-moneda real
  todavía. Tratar todo como EUR implícito por ahora (Cardmarket es EUR), no construir
  lógica de conversión de moneda en esta fase.
- One Piece y Pokémon: 0 filas en `collection_items` (colección real es 100% Magic por
  ahora — ver `docs/CURRENT_STATE.md` y decisión previa de esta sesión, no es un bug).

## 1. Alcance de esta fase (confirmado con Facundo)

Del roadmap completo de `docs/PRODUCT.md`, esta fase implementa **solo**:

- **Overview**: valor total de mercado, costo total, P/L, ROI, cantidad de cartas,
  valor por TCG.
- **Collection**: buscar, filtrar, ordenar, ver detalle de una carta. **Solo
  lectura** — no hay edición desde la web todavía (se sigue editando por
  `load_collection.py`/CSV como hasta ahora). Editar collection_items desde la UI
  queda para una fase posterior, cuando además haya que decidir validación de
  formularios y una API de escritura.

Explícitamente **fuera de alcance** de esta fase (fases posteriores del roadmap,
`docs/PRODUCT.md`):

- Gráficos de tendencia de precio / históricos (Fase 7 — hoy cada producto tiene 1
  solo snapshot de precio, no hay serie para graficar todavía).
- Analytics (mejores/peores performers, evolución de portfolio) — Fase 8.
- Trading (Trade Binder, Want List, Trade Calculator) — Fase 9. `want_list_items`
  sigue sin usarse.
- CARDMADNESS Mode — Fase 10.
- Autenticación / multi-usuario — es una herramienta personal local, no hace falta.
- Conversión de moneda — ver sección 0.

## 2. Métrica de valor de mercado (confirmado con Facundo)

Para "valor de mercado actual" de una carta, usar **`trend`** de
`market_price_history` (Trend Price de Cardmarket) — es la métrica que usa el propio
ejemplo de `docs/PRODUCT.md` y la que Cardmarket trata como estimación estándar de valor
justo. No usar `avg`/`low`/`avg30` como valor principal en esta fase (quedan
disponibles en el detalle de carta como dato informativo si se quiere mostrar, pero no
entran en los totales de Overview).

Snapshot a usar por producto: la fila de `market_price_history` con `observed_at`
máximo para ese `cardmarket_product_id` (no asumir que hay una sola fila — aunque hoy
sea así para las 79, el query debe ser correcto igual si mañana hay más).

Cartas con `card_id IS NULL` (manual entries, 19 hoy) **no tienen valor de mercado
posible** — no inventar un precio ni asignarles 0 silenciosamente (`docs/ARCHITECTURE.md`
y `AGENTS.md`). Tratamiento:

- Excluir del cálculo de "valor de mercado total" en Overview.
- Mostrar en Overview cuántas cartas quedaron fuera de ese total (ej. "19 de 98 cartas
  sin precio de mercado — alta manual").
- En la lista de Collection, mostrar esas filas con el valor de mercado como
  `—` / "sin precio" (nunca `€0`), pero sí incluidas en el conteo total de cartas y en
  el costo total (si tienen `purchase_price`).

## 3. Backend — `backend/api/`

Carpeta nueva, **no tocar** `backend/importer/` ni `backend/scripts/`. FastAPI, mismo
principio de conexión simple a SQLite que ya usan `scryfall_backfill.py`/
`load_collection.py` (sin ORM pesado — no hace falta SQLAlchemy para esto, queries
directas con `sqlite3` alcanzan y son más fáciles de auditar). Solo lectura — no
exponer ningún endpoint `POST`/`PUT`/`DELETE` todavía (alcance sección 1).

Endpoints mínimos:

- `GET /api/overview`
  - `total_cost` (`SUM(purchase_price * quantity)` sobre filas con `purchase_price`
    no nulo; reportar aparte cuántas filas no tienen `purchase_price` — no asumir 0).
  - `total_market_value` (`SUM(trend_mas_reciente * quantity)` solo sobre filas con
    `cardmarket_product_id` no nulo).
  - `unrealized_pl` = `total_market_value - total_cost` (dejar explícito en la
    respuesta qué subconjunto de filas entra en cada término — no son necesariamente
    el mismo subconjunto, ver arriba).
  - `roi` = `unrealized_pl / total_cost` (manejar `total_cost == 0` sin dividir por
    cero).
  - `total_cards` (`SUM(quantity)`), `unique_cards` (`COUNT(*)`).
  - `cards_without_market_value` (count + lista de ids, para la sección 2).
  - `value_by_tcg`: agrupado por `games.code` (hoy solo `magic` va a tener datos +
    un bucket para las 19 manuales que no tienen `game_id` resoluble porque
    `card_id IS NULL` — dejarlo aparte como "sin catalogar", no descartarlo
    silenciosamente).

- `GET /api/collection`
  - Query params: `game`, `status` (`KEEP`/`HOLD`/`TRADE`/`SELL`/`WANT`), `search`
    (nombre, `ILIKE`/`LIKE` case-insensitive), `sort` (nombre / valor / fecha compra),
    `page`/`page_size`.
  - Cada fila: nombre, set (`expansions.name`), card_number, condition, quantity,
    `purchase_price`, valor de mercado actual (`trend` más reciente o `null`),
    `manual_entry`, `status`.
  - Join `collection_items` → `cards` (nullable) → `expansions`, y
    `collection_items` → `cardmarket_products` (nullable) →
    `market_price_history` (latest).

- `GET /api/collection/{id}`
  - Detalle completo de una fila: todos los campos de `collection_items` +
    `cards`/`expansions` si aplica + las métricas de precio disponibles
    (`trend`/`avg`/`low`/`avg30`) del snapshot más reciente, con `observed_at` visible
    (`AGENTS.md`: mostrar siempre fuente + métrica + fecha).

Levantar en `http://localhost:8000` (`README.md`).

## 4. Frontend — `frontend/`

Vite + React + TypeScript + Tailwind CSS + shadcn/ui + Recharts (`docs/ARCHITECTURE.md`).
Vite en vez de Next.js: es una herramienta personal local sin necesidad de SSR/rutas
server-side, Vite es el setup estándar de shadcn/ui y mantiene la complejidad al
mínimo (`AGENTS.md`, evitar overengineering) — si en algún momento hace falta
SSR/multi-usuario esto se reevalúa, no antes.

Páginas:

- **Overview** (`/`): tarjetas de resumen (costo total, valor de mercado total, P/L,
  ROI, total de cartas), aviso visible de cuántas cartas quedan fuera del valor de
  mercado (sección 2), un gráfico simple de valor por TCG (Recharts, barra o dona —
  con los datos de hoy va a ser casi 100% Magic, el gráfico tiene que soportar que
  aparezcan más TCGs sin cambios cuando haya colección real de One Piece/Pokémon).
- **Collection** (`/collection`): tabla/grid con búsqueda, filtro por TCG y por
  status, orden por columna, paginación, click a detalle de carta. Filas sin precio
  de mercado se muestran con `—`, no `€0` (sección 2).
- Detalle de carta (`/collection/:id`): toda la info de `GET /api/collection/{id}`,
  con la fecha del snapshot de precio visible.

Levantar en `http://localhost:3000` (`README.md`). Dark mode y diseño responsive
desde el arranque (`docs/PRODUCT.md`) — no como retrofit después.

## 5. Principios a respetar (ya definidos en docs operativos, no reabrir)

- §20 Data Integrity: nunca inventar un precio faltante, nunca mostrar `€0` para "sin
  dato".
- §25 Financial Accuracy: toda cifra de valor de mercado visible en la UI debe dejar
  claro que es Trend Price de Cardmarket, no un precio de venta garantizado, con fecha
  del snapshot.
- §24 Coding Principles: sin microservicios, sin dependencias innecesarias (no
  agregar ORM, state management pesado, etc. si no hace falta para este alcance).
- §28: si aparece una decisión de arquitectura no cubierta por este contract
  (ej. cómo paginar, cómo manejar errores de red en el frontend), no decidirla en
  silencio — dejarla planteada en el reporte de cierre para revisar.

## 6. Verificación

1. `backend/api` levanta en `:8000`, `frontend` en `:3000`, ambos con un solo comando
   documentado en `README.md`.
2. `GET /api/overview` contra la DB real: `total_cards` = 98 (`SUM(quantity)`, no
   necesariamente 98 si alguna fila tiene `quantity > 1` — verificar cuál es el
   número real), `cards_without_market_value` = 19.
3. `GET /api/collection` sin filtros devuelve 98 filas paginadas correctamente; con
   `game=magic` devuelve 79.
4. Spot-check manual: abrir el detalle de 2-3 cartas al azar (una con precio, una de
   las 19 manuales) y confirmar que la UI no muestra `€0` para la manual.
5. Confirmar que no se tocó ninguna tabla ni archivo de `backend/importer/` o
   `backend/scripts/` — esta fase es 100% aditiva (`backend/api/`, `frontend/`,
   `README.md`).
6. Correr el proyecto localmente y confirmar dark mode + layout responsive básico
   (`docs/PRODUCT.md`) antes de dar la fase por cerrada.

## 7. Cierre

- Actualizar `docs/CURRENT_STATE.md` a Fase 7 al cerrar este sprint.
- Documentar el resultado real en este mismo archivo, agregando una sección
  "Resultado real de la corrida" (mismo patrón que los contracts anteriores).
- Actualizar `conventions.json` → `TCG-DEC-005` con `status: "implementado"`.

---

## 8. Resultado real de la corrida

Cerrado 2026-08-25 por el agente `developer`. Verificado contra `tcg_dashboard.db`
real (`PRAGMA integrity_check` = `ok`, 98 filas en `collection_items`).

### Archivos creados

- `backend/api/`: `__init__.py`, `db.py`, `queries.py`, `schemas.py`, `main.py`,
  `routers/__init__.py`, `routers/overview.py`, `routers/collection.py`,
  `test_support.py`, `test_queries.py`, `test_api.py`, `requirements.txt`.
- `frontend/`: proyecto Vite completo (`src/lib/{types,format,api,useApi,useDarkMode}.ts`,
  `src/components/{layout,overview,collection,shared,ui}/`,
  `src/pages/{OverviewPage,CollectionPage,CardDetailPage}.tsx`, `App.tsx`, `main.tsx`,
  `vite.config.ts`, `tsconfig*.json`, `components.json`).
- `README.md` (raíz del repo — no existía antes de esta fase).

### Archivos modificados

- `.gitignore` (aditivo: `frontend/node_modules/`, `frontend/dist/`, `.env`,
  `.env.local`, `.DS_Store`).
- `docs/CURRENT_STATE.md` (Current Phase → 7, párrafo de cierre de Fase 6).
- `conventions.json` (`TCG-DEC-005.status` → `"implementado"`, detalle real agregado).
- `docs/plans/fase6-dashboard-basico-sprint-contract.md` (esta sección).

### Verificación (checklist §6, en orden)

1. **Arranque con un solo comando por proceso.** `README.md` documenta dos terminales
   (`uvicorn api.main:app --reload --port 8000` desde `backend/`; `npm run dev` desde
   `frontend/`). Confirmado real: backend respondió en `:8000`
   (`curl http://127.0.0.1:8000/health` → `{"status":"ok"}`), frontend respondió en
   `:3000` (`curl -o /dev/null -w "%{http_code}" http://localhost:3000/` → `200`).

2. **`GET /api/overview` contra la DB real:**
   `total_cards=101` (no 98 — `SUM(quantity)`, confirmado que difiere de
   `unique_cards`), `unique_cards=98`, `cards_without_market_value.count=19`,
   `roi=-0.5212` (no nulo). Además: `total_cost=419.34`, `total_market_value=200.78`,
   `cost_basis_row_count=86`, `rows_without_cost=12`, `value_by_tcg` con dos buckets
   (`magic`: 79 filas/200.78 de valor; `sin_catalogar`: 19 filas/0.0 de valor, sin
   descartarse).

3. **`GET /api/collection`:** sin filtros `total=98` (confirmado); `?game=magic` →
   `total=79` (confirmado). Fila manual de ejemplo (`id=33`) devuelve
   `market_value: null` (nunca `0`).

4. **Spot-check de detalle en el navegador (Chrome headless, `--dump-dom` +
   Puppeteer sobre Chrome instalado):** `/collection/33` (alta manual, sin producto)
   muestra "— sin precio de mercado" y badge "Alta manual", sin ningún `€0` en el
   HTML renderizado. `/collection/34` (fila con precio, "Frodo, Sauron's Bane") muestra
   "Trend Price de Cardmarket · snapshot del 25 ago 2026, 2:48 a. m." con
   `avg`/`low`/`avg30` como dato secundario, tampoco con `€0` en ningún campo.

5. **`git status`/`git diff --stat`:** confirmado — únicos cambios: `backend/api/`
   (nuevo), `frontend/` (nuevo), `README.md` (nuevo), `.gitignore`, `AGENTS.md`,
   `conventions.json`, `docs/plans/fase6-dashboard-basico-sprint-contract.md`. Nada en
   `backend/importer/` ni `backend/scripts/`.

6. **Dark mode + resize a mobile width:** verificado con Puppeteer contra Chrome
   instalado localmente. Toggle de tema cambia la clase `dark` en `<html>` y persiste
   tras reload (vía `localStorage`). A 375px de ancho (`/collection`), el `<table>`
   dentro de su contenedor `overflow-x-auto` no generó scroll horizontal en `<body>`
   (`scrollWidth === clientWidth === 375`). Gráfico de `value_by_tcg` (Recharts)
   renderizó ambas barras (`Magic` y `Sin catalogar`) con sus labels en el eje X, sin
   ocultar el bucket sin catalogar aunque su valor sea `0.0`.

7. **`python -m pytest backend/api/`:** 20/20 tests pasaron (`test_queries.py` +
   `test_api.py`), cubriendo los 4 casos requeridos (fila mapeada con precio, fila con
   producto sin snapshot todavía, fila manual, fila con `purchase_price IS NULL`),
   `roi=None` sin excepción con `total_cost==0`, `cards_without_market_value` incluye
   ambos casos sin precio, orden por `valor` no intercala `NULL`, `404` en id
   inexistente, fila manual con `market_price: null`.

### Desvíos del plan

- **Tailwind v4 + shadcn CLI ("radix-nova" preset):** `create-vite` instaló
  Tailwind v4 por default (no v3). El setup de shadcn/ui para v4 usa
  `@tailwindcss/vite` (plugin de Vite, sin `tailwind.config.js`) en vez del setup
  clásico de v3 — se siguió la guía oficial vigente de shadcn para Vite+Tailwind v4.
  Dark mode sigue el mismo patrón de clase (`.dark` en `<html>`), solo cambia el
  mecanismo interno (`@custom-variant dark` en CSS en vez de `darkMode: "class"` en
  `tailwind.config.js`) — no afecta el requisito de `docs/PRODUCT.md`.
- **Bug del CLI de `shadcn init`:** con alias `@/*` configurado en `tsconfig.app.json`
  + `vite.config.ts`, el comando `shadcn add` escribió los archivos generados en una
  carpeta literal `./@/` en la raíz del proyecto en vez de resolver el alias a
  `./src/`. Se movieron manualmente los archivos a `src/components/ui/` y
  `src/lib/utils.ts` (mismo contenido, los imports internos ya usaban `@/lib/utils` y
  siguen resolviendo correctamente vía el alias real). Reportado acá por transparencia,
  no bloqueante.
- **Router:** se usó `BrowserRouter` (no mencionado explícitamente en el contract)
  para que las rutas coincidan literalmente con `/`, `/collection`, `/collection/:id`
  tal como las especifica la sección 4 — la alternativa (`HashRouter`) hubiera
  producido `/#/collection`.
- **Verificación visual sin acceso a un navegador interactivo:** se usó Google Chrome
  instalado localmente en modo headless (vía CLI y vía Puppeteer con
  `puppeteer-core`, instalado temporalmente en el directorio de scratchpad de la
  sesión, fuera del repo, no commiteado) para los puntos 4 y 6 del checklist, en vez
  de una revisión manual de Facundo en el navegador. Facundo puede repetir la
  verificación visual manualmente antes de aprobar.

### Decisiones §28 dejadas abiertas (documentadas, no bloqueantes, revisar en fases futuras)

- **Errores de red en el frontend:** hook `useApi<T>` mínimo (`{data, error,
  loading}`, `frontend/src/lib/useApi.ts`) + `ErrorState` genérico con botón
  "Reintentar" (`frontend/src/components/shared/ErrorState.tsx`). Sin React
  Query/SWR, sin retry automático.
- **Paginación UI:** controles Anterior/Siguiente + selector de `page_size` +
  "Página X de Y" (`frontend/src/components/collection/Pagination.tsx`), página en
  estado local de React (no en la URL). Sin infinite scroll ni virtualización.
- **Nombre de filas manuales:** `display_name` con fallback (`card_name` →
  `manual_entry_note` → `notes`), calculado en `backend/api/queries.py`
  (`CollectionRow.display_name`), sin parsear URLs.

### Confirmación

`backend/importer/` y `backend/scripts/` quedaron intactos — no se modificó ni un
archivo de esas carpetas durante esta fase.
