# TCG Dashboard

Dashboard personal de coleccion, valuacion y trading de cartas TCG: Pokemon, One
Piece y Magic: The Gathering.

Estado actual: **Fase 7**. Fase 6 cerro el dashboard basico con Overview +
Collection de solo lectura. Fase 7 agrega Catalog + Wishlist Planning Mode para
Magic LOTR. La proxima tarea recomendada es historico de precios y graficos de
tendencia.

## Documentacion

- `AGENTS.md` — reglas operativas cortas para agentes.
- `docs/PRODUCT.md` — vision de producto y roadmap.
- `docs/ARCHITECTURE.md` — stack, flujo de datos y reglas de fuentes.
- `docs/CURRENT_STATE.md` — estado real actual, metricas y restricciones.
- `docs/decisions/` — ADRs migrados desde `conventions.json`.
- `docs/plans/` — sprint contracts y planes historicos.

## Estructura

```text
backend/
  db/         -- schema.sql, seed.sql, tcg_dashboard.db (SQLite)
  importer/   -- importer de catalogo/precios Cardmarket
  scripts/    -- carga manual de coleccion y backfills
  api/        -- FastAPI, lecturas y wishlist acotada
frontend/     -- Vite + React + TypeScript + Tailwind + shadcn/ui + Recharts
docs/         -- documentacion del proyecto
```

## Requisitos

- Python 3.11+ con `fastapi` y `uvicorn[standard]` instalados
  (`pip install -r backend/api/requirements.txt`)
- Node.js 20+ / npm

## Arranque en desarrollo

Dos terminales, uno por proceso:

```bash
# Terminal 1 -- backend (desde la raiz del repo)
cd backend
uvicorn api.main:app --reload --port 8000

# Terminal 2 -- frontend (desde la raiz del repo)
cd frontend
npm install
npm run dev
```

Backend: `http://localhost:8000` (docs interactivas en `/docs`, health check en
`/health`).

Frontend: `http://localhost:3000`.

El frontend apunta a `http://localhost:8000` por default; para cambiarlo, definir
`VITE_API_BASE_URL` en `frontend/.env.local` (no versionado).

## Tests

```bash
# Backend API
python -m pytest backend/api/ -v

# Frontend -- typecheck + build de produccion
cd frontend
npx tsc -b
npm run build

# Documentacion / whitespace
git diff --check
```

## Manual Price Update

El workflow oficial para actualizar precios de Magic y One Piece es:

```bash
./update-prices --dry-run
./update-prices --apply
./update-prices --game magic --dry-run
./update-prices --game one_piece --dry-run
```

`all` es el alcance predeterminado. Cardmarket se usa primero cuando el printing y
el idioma son exactos; One Piece usa CardTrader como fallback median-5 por Blueprint
y separa estrictamente EN/JP. Los precios mixed se conservan como auditoría, pero no
entran en current price ni valoración. `high`, `medium` y `low` indican 5+, 3–4 y
1–2 vendedores CardTrader elegibles.

`--dry-run` no escribe la DB. `--apply` crea un backup SQLite, adquiere un lock de
escritura y aplica todo en una única transacción; Collection y Wishlist no se tocan.
Cada corrida deja un log JSON local en `logs/pricing/`.

## Reglas importantes

- `backend/api/` mantiene Overview/Collection/Catalog como lecturas; Wishlist expone
  filtros, resumen global, Buying Mode, CSV y sus transiciones de planificación.
- La edicion de `collection_items` sigue siendo via `backend/scripts/load_collection.py`
  + CSV, no desde la web.
- Cardmarket es la fuente de precios; Scryfall es metadata de catalogo Magic.
- Nunca se muestra `EUR 0`/`€0` para "sin precio de mercado".
- Para contexto completo, leer `AGENTS.md` y `docs/CURRENT_STATE.md`.
