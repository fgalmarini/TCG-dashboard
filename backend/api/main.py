"""FastAPI app -- backend/api/, dashboard, catalog and wishlist.

Arranque: `uvicorn api.main:app --reload --port 8000` desde `backend/`.
Collection editing via API is limited to ownership metadata; catalog identity remains
protected. The resolver manual de matches de catálogo is a separate operation.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import catalog, collection, events, overview, wishlist

app = FastAPI(
    title="TCG Dashboard API",
    description="Dashboard personal Multi-TCG con catálogo Magic/One Piece y wishlist por printing.",
    version="0.9.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(overview.router)
app.include_router(collection.router)
app.include_router(catalog.router)
app.include_router(wishlist.router)
app.include_router(events.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


if __name__ == "__main__":
    # Fallback para `python -m backend.api.main` desde la raiz del repo (mantiene el
    # import relativo valido). El comando documentado en README.md es la CLI de
    # uvicorn (con --reload), no esta ejecucion directa.
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
