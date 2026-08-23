"""Descarga los 6 archivos de Cardmarket (bucket S3 publico, sin auth) con urllib.request."""

import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from config import CARDMARKET_BASE_URL, GAMES, PRICE_HISTORY_DIR

TIMEOUT_SECONDS = 30

FILE_KINDS = (
    ("price_guide", "priceGuide", "price_guide"),
    ("products", "productList", "products_singles"),
)


@dataclass
class DownloadResult:
    key: str
    url: str
    path: Path
    ok: bool
    size_bytes: int
    error: str | None


def _url_for(kind_path_segment: str, filename_prefix: str, cardmarket_game_id: int) -> str:
    return f"{CARDMARKET_BASE_URL}/{kind_path_segment}/{filename_prefix}_{cardmarket_game_id}.json"


def download_file(url: str, dest: Path, timeout: int = TIMEOUT_SECONDS) -> DownloadResult:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            data = resp.read()
        tmp.write_bytes(data)
        tmp.replace(dest)  # write atomico simple: evita dejar un archivo a medio escribir
        return DownloadResult(url, url, dest, True, len(data), None)
    except (urllib.error.URLError, OSError) as exc:
        tmp.unlink(missing_ok=True)
        return DownloadResult(url, url, dest, False, 0, str(exc))


def download_all() -> dict[str, DownloadResult]:
    """Descarga los 6 archivos (price_guide + products, x3 juegos) a price-history/{juego}/."""
    results: dict[str, DownloadResult] = {}
    for game_key, game_cfg in GAMES.items():
        folder = PRICE_HISTORY_DIR / game_cfg["folder"]
        cardmarket_game_id = game_cfg["cardmarket_game_id"]
        for file_kind, url_segment, filename_prefix in FILE_KINDS:
            url = _url_for(url_segment, filename_prefix, cardmarket_game_id)
            dest = folder / f"{filename_prefix}_{cardmarket_game_id}.json"
            key = f"{game_key}:{file_kind}"
            results[key] = download_file(url, dest)
    return results
