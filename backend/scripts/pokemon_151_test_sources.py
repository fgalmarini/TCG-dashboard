"""Build reproducible local Cardmarket source payloads for Pokémon 151 tests."""

from __future__ import annotations

import csv
import json
from pathlib import Path


PRICE_FIELDS = {
    "low": "price_low",
    "trend": "price_trend",
    "avg1": "price_avg1",
    "avg7": "price_avg7",
    "avg30": "price_avg30",
    "low-holo": "price_low_holo",
    "trend-holo": "price_trend_holo",
    "avg1-holo": "price_avg1_holo",
    "avg7-holo": "price_avg7_holo",
    "avg30-holo": "price_avg30_holo",
}


def make_cardmarket_sources(root: Path, discovery_dir: Path) -> tuple[Path, Path]:
    mapping_path = discovery_dir / "03_cardmarket_mapping.csv"
    rows = list(csv.DictReader(mapping_path.open(encoding="utf-8", newline="")))
    products = []
    price_guides = []
    for row in rows:
        product_id = int(row["cardmarket_product_id"])
        products.append({
            "idProduct": product_id,
            "name": row["cardmarket_product_name"],
            "idCategory": 51,
            "idExpansion": 5328,
            "idMetacard": int(row["idMetacard"]),
            "dateAdded": "2026-01-01 00:00:00",
        })
        guide = {"idProduct": product_id}
        for target, source in PRICE_FIELDS.items():
            value = row.get(source, "")
            guide[target] = float(value) if value not in (None, "") else None
        price_guides.append(guide)

    products_path = root / "products.json"
    prices_path = root / "prices.json"
    products_path.write_text(json.dumps({"createdAt": "2026-01-01T00:00:00Z", "products": products}), encoding="utf-8")
    prices_path.write_text(json.dumps({"createdAt": "2026-01-01T00:00:00Z", "priceGuides": price_guides}), encoding="utf-8")
    return products_path, prices_path
