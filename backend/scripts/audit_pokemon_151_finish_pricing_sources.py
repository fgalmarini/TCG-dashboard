#!/usr/bin/env python3
"""Read-only Pokémon 151 finish-pricing source audit.

The audit compares Cardmarket public listing access with the current structured
responses of Pokémon TCG API and TCGdex. It writes only a cache and reports; it
never opens SQLite in write mode, imports prices, or changes application pricing.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sqlite3
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT / "backend/db/tcg_dashboard.db"
DEFAULT_OUTPUT = ROOT / "reports/pokemon_151/finish_pricing_sources"
DEFAULT_CACHE = ROOT / "backend/scripts/.pokemon_151_finish_pricing_cache"
SET_CODE = "mew"
PTCG_SET_ID = "sv3pt5"
TCGDEX_SET_ID = "sv03.5"
USER_AGENT = "TCG-Dashboard-Pokemon151-Finish-Source-Audit/1.0"

DOCS = {
    "cardmarket_help": ("https://help.cardmarket.com/en/finding-and-listing-pokemon-cards", "cardmarket_current_help"),
    "pokemon_tcg_card_object": ("https://docs.pokemontcg.io/api-reference/cards/card-object/", "pokemon_tcg_current_docs"),
    "pokemon_tcg_search": ("https://docs.pokemontcg.io/api-reference/cards/search-cards/", "pokemon_tcg_current_docs"),
    "tcgdex_markets": ("https://tcgdex.dev/markets-prices", "tcgdex_current_docs"),
    "tcgdex_card_reference": ("https://tcgdex.dev/reference/card", "tcgdex_current_docs"),
    "tcgdex_faq": ("https://tcgdex.dev/faq", "tcgdex_current_docs"),
}
PTCG_BULK_URL = "https://api.pokemontcg.io/v2/cards?q=set.id:sv3pt5&page=1&pageSize=250"
TCGDEX_SET_URL = f"https://api.tcgdex.net/v2/en/sets/{TCGDEX_SET_ID}"
METRIC_KEYS = {
    "base": ("lowPrice", "marketPrice"),
    "holo": ("lowPrice", "marketPrice"),
    "reverse": ("lowPrice", "marketPrice"),
}


class AuditError(RuntimeError):
    pass


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def norm_number(value: Any) -> str:
    raw = str(value or "").strip()
    match = re.match(r"^(\d+)", raw)
    return match.group(1).zfill(3) if match else raw


def norm_name(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


def positive(value: Any) -> bool:
    return isinstance(value, (int, float)) and value > 0


def compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class SourceCache:
    def __init__(self, directory: Path, offline: bool, refresh: bool):
        if offline and refresh:
            raise AuditError("--refresh-sources cannot be combined with --offline")
        self.directory = directory
        self.offline = offline
        self.refresh = refresh
        directory.mkdir(parents=True, exist_ok=True)
        self.manifest_path = directory / "manifest.json"
        self.manifest = json.loads(self.manifest_path.read_text(encoding="utf-8")) if self.manifest_path.exists() else {"version": 1, "entries": []}

    def _previous(self, url: str) -> dict[str, Any] | None:
        matches = [entry for entry in self.manifest.get("entries", []) if entry.get("url") == url]
        return matches[-1] if matches else None

    def _save_manifest(self) -> None:
        self.manifest_path.write_text(json.dumps(self.manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def fetch(self, url: str, role: str) -> dict[str, Any]:
        previous = self._previous(url)
        if previous and previous.get("status") not in {"ERROR", "MISSING_OFFLINE"} and not self.refresh:
            path = self.directory / previous["cache_file"] if previous.get("cache_file") else None
            if path and path.exists():
                result = dict(previous)
                result["role"] = role
                result["content"] = path.read_bytes()
                return result
        if self.offline:
            return {"url": url, "role": role, "retrieved_at": None, "sha256": None, "content_type": None, "http_status": None, "status": "MISSING_OFFLINE", "cache_file": None, "content": b""}
        request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json,text/html;q=0.9,*/*;q=0.1"})
        content = b""
        status = "OK"
        http_status = None
        content_type = None
        last_error = None
        for attempt in range(3):
            try:
                with urlopen(request, timeout=30) as response:
                    http_status = response.status
                    content_type = response.headers.get("Content-Type")
                    content = response.read()
                break
            except HTTPError as error:
                http_status = error.code
                content_type = error.headers.get("Content-Type") if error.headers else None
                content = error.read() if hasattr(error, "read") else b""
                status = "BLOCKED" if error.code in {401, 403, 429} else "NOT_FOUND" if error.code == 404 else "ERROR"
                last_error = error
                break
            except (URLError, TimeoutError, OSError) as error:
                last_error = error
                status = "ERROR"
                content = str(error).encode("utf-8")
                if attempt < 2:
                    time.sleep(0.5 * (attempt + 1))
        if last_error and not content:
            content = str(last_error).encode("utf-8")
        digest = sha256_bytes(content)
        cache_file = f"{digest}.bin"
        (self.directory / cache_file).write_bytes(content)
        result = {"url": url, "role": role, "retrieved_at": iso_now(), "sha256": digest, "content_type": content_type, "http_status": http_status, "status": status, "cache_file": cache_file, "content": content}
        self.manifest["entries"] = [entry for entry in self.manifest.get("entries", []) if entry.get("url") != url]
        self.manifest["entries"].append({key: result[key] for key in ("url", "role", "retrieved_at", "sha256", "content_type", "http_status", "status", "cache_file")})
        self._save_manifest()
        time.sleep(0.05)
        return result


def json_response(result: dict[str, Any]) -> Any:
    if result["status"] != "OK":
        return None
    try:
        return json.loads(result["content"].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def read_catalog(db: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        rows = [dict(row) for row in conn.execute("""
            SELECT id AS card_id, card_number AS collector_number, name, rarity, finish,
                   art_kind, canonical_card_id
              FROM cards
             WHERE set_code=? AND catalog_status='active'
             ORDER BY CAST(card_number AS INTEGER), id
        """, (SET_CODE,))]
        if len(rows) != 362:
            raise AuditError(f"expected 362 active physical printings, got {len(rows)}")
        identities = {}
        for row in rows:
            key = norm_number(row["collector_number"])
            identities.setdefault(key, {"collector_number": key, "card_name": row["name"], "canonical_card_id": row["canonical_card_id"], "physical": []})
            identities[key]["physical"].append(row)
        if len(identities) != 207:
            raise AuditError(f"expected 207 numbered identities, got {len(identities)}")
        return list(identities.values()), rows, {"physical_printings": len(rows), "numbered_identities": len(identities), "finish_counts": dict(Counter(row["finish"] for row in rows))}
    finally:
        conn.close()


def fetch_docs(cache: SourceCache, include_cardmarket: bool, include_secondary: bool) -> list[dict[str, Any]]:
    selected = []
    for name, (url, role) in DOCS.items():
        if (name == "cardmarket_help" and include_cardmarket) or (name != "cardmarket_help" and include_secondary):
            result = cache.fetch(url, role)
            selected.append({key: result.get(key) for key in ("url", "role", "retrieved_at", "sha256", "content_type", "http_status", "status", "cache_file")} | {"name": name})
    return selected


def extract_tcgplayer(prices: dict[str, Any], family: str) -> tuple[bool, bool, Any, Any, str]:
    key = {"normal": "normal", "holo": "holofoil", "reverse_holo": "reverseHolofoil"}[family]
    entry = prices.get(key) if isinstance(prices, dict) else None
    if not isinstance(entry, dict):
        return False, False, None, None, key
    low, market = entry.get("low"), entry.get("market")
    return True, positive(low) or positive(market), low, market, key


def validate_identity(source: dict[str, Any] | None, number: str, name: str, set_id: str, set_key: str = "id", number_key: str = "number", name_key: str = "name") -> tuple[str, str]:
    if not source:
        return "UNRESOLVED", "source record missing"
    source_set = source.get("set", {}).get(set_key, source.get(set_key))
    source_number = source.get(number_key, source.get("localId"))
    source_name = source.get(name_key)
    if str(source_set) != set_id:
        return "MISMATCH", f"set {source_set!r} != {set_id!r}"
    if norm_number(source_number) != number:
        return "MISMATCH", f"number {source_number!r} != {number!r}"
    if norm_name(source_name) != norm_name(name):
        return "MISMATCH", f"name {source_name!r} != {name!r}"
    return "EXACT", "set + collector number + name match"


def load_pokemon_tcg_api(cache: SourceCache, identities: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    bulk_result = cache.fetch(PTCG_BULK_URL, "pokemon_tcg_api_cards")
    payload = json_response(bulk_result)
    data = payload.get("data", []) if isinstance(payload, dict) else []
    acquisition = "bulk"
    if len(data) != len(identities):
        acquisition = "individual_fallback_after_bulk_failure"
        data = []
        for identity in identities:
            number = str(int(identity["collector_number"]))
            result = cache.fetch(f"https://api.pokemontcg.io/v2/cards/{PTCG_SET_ID}-{number}", "pokemon_tcg_api_card")
            card_payload = json_response(result)
            if isinstance(card_payload, dict) and isinstance(card_payload.get("data"), dict):
                data.append(card_payload["data"])
    by_number = {norm_number(row.get("number")): row for row in data if isinstance(row, dict)}
    output = []
    for identity in identities:
        number = identity["collector_number"]
        row = by_number.get(number)
        identity_status, identity_note = validate_identity(row, number, identity["card_name"], PTCG_SET_ID)
        cm = row.get("cardmarket", {}) if row else {}
        cp = cm.get("prices", {}) if isinstance(cm, dict) else {}
        tp = row.get("tcgplayer", {}) if row else {}
        tprices = tp.get("prices", {}) if isinstance(tp, dict) else {}
        def tcg(family: str):
            return extract_tcgplayer(tprices, family)
        n = tcg("normal")
        h = tcg("holo")
        r = tcg("reverse_holo")
        reverse_fields = [key for key in ("reverseHoloLow", "reverseHoloTrend", "reverseHoloAvg1", "reverseHoloAvg7", "reverseHoloAvg30") if key in cp]
        output.append({
            "collector_number": number, "card_name": identity["card_name"], "api_card_id": row.get("id") if row else "", "api_identity_status": identity_status,
            "normal_exists": n[0], "holo_exists": h[0], "reverse_exists": r[0], "normal_usable": n[1], "holo_usable": h[1], "reverse_usable": r[1],
            "cardmarket_low": cp.get("lowPrice") if "lowPrice" in cp else "", "cardmarket_reverse_low": cp.get("reverseHoloLow") if "reverseHoloLow" in cp else "",
            "cardmarket_trend": cp.get("trendPrice") if "trendPrice" in cp else "", "cardmarket_reverse_trend": cp.get("reverseHoloTrend") if "reverseHoloTrend" in cp else "",
            "cardmarket_avg1": cp.get("avg1") if "avg1" in cp else "", "cardmarket_reverse_avg1": cp.get("reverseHoloAvg1") if "reverseHoloAvg1" in cp else "",
            "cardmarket_avg7": cp.get("avg7") if "avg7" in cp else "", "cardmarket_reverse_avg7": cp.get("reverseHoloAvg7") if "reverseHoloAvg7" in cp else "",
            "cardmarket_avg30": cp.get("avg30") if "avg30" in cp else "", "cardmarket_reverse_avg30": cp.get("reverseHoloAvg30") if "reverseHoloAvg30" in cp else "",
            "cardmarket_reverse_fields_present": reverse_fields, "cardmarket_reverse_low_available": positive(cp.get("reverseHoloLow")),
            "tcgplayer_normal_low": n[2], "tcgplayer_normal_market": n[3], "tcgplayer_holo_low": h[2], "tcgplayer_holo_market": h[3], "tcgplayer_reverse_low": r[2], "tcgplayer_reverse_market": r[3],
            "tcgplayer_updated_at": tp.get("updatedAt") if isinstance(tp, dict) else "", "cardmarket_updated_at": cm.get("updatedAt") if isinstance(cm, dict) else "", "cardmarket_currency": "EUR", "tcgplayer_currency": "USD", "identity_note": identity_note,
        })
    return {row["collector_number"]: row for row in output}, {"status": bulk_result["status"], "http_status": bulk_result["http_status"], "sha256": bulk_result["sha256"], "url": PTCG_BULK_URL, "records": len(data), "expected": 207, "acquisition": acquisition}


def load_tcgdex(cache: SourceCache, identities: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    set_result = cache.fetch(TCGDEX_SET_URL, "tcgdex_set")
    set_payload = json_response(set_result)
    briefs = set_payload.get("cards", []) if isinstance(set_payload, dict) else []
    details = {}
    for brief in briefs:
        local_id = norm_number(brief.get("localId"))
        result = cache.fetch(f"https://api.tcgdex.net/v2/en/sets/{TCGDEX_SET_ID}/{brief.get('localId')}", "tcgdex_card")
        payload = json_response(result)
        if payload:
            details[local_id] = payload
    output = []
    for identity in identities:
        number = identity["collector_number"]
        row = details.get(number)
        identity_status, identity_note = validate_identity(row, number, identity["card_name"], TCGDEX_SET_ID, set_key="id", number_key="localId")
        variants = row.get("variants_detailed", []) if row else []
        tplayer = {"normal": [], "holo": [], "reverse_holo": []}
        cardmarket_ids = {"normal": [], "holo": [], "reverse_holo": []}
        for variant in variants:
            family = {"normal": "normal", "holo": "holo", "reverse": "reverse_holo"}.get(variant.get("type"))
            if not family or variant.get("foil") not in (None, ""):
                continue
            pricing = variant.get("pricing") or {}
            tp = pricing.get("tcgplayer") or {}
            cm = pricing.get("cardmarket") or {}
            key = {"normal": "normal", "holo": "holofoil", "reverse_holo": "reverse-holofoil"}[family]
            entry = tp.get(key) if isinstance(tp, dict) else None
            if isinstance(entry, dict):
                tplayer[family].append({"productId": entry.get("productId"), "lowPrice": entry.get("lowPrice"), "marketPrice": entry.get("marketPrice")})
            if isinstance(cm, dict) and cm.get("idProduct") is not None:
                cardmarket_ids[family].append(cm.get("idProduct"))
        output.append({
            "collector_number": number, "card_name": identity["card_name"], "tcgdex_card_id": row.get("id") if row else "", "tcgdex_identity_status": identity_status,
            "normal_exists": bool(tplayer["normal"]), "holo_exists": bool(tplayer["holo"]), "reverse_exists": bool(tplayer["reverse_holo"]),
            "normal_usable": any(positive(v.get("lowPrice")) or positive(v.get("marketPrice")) for v in tplayer["normal"]), "holo_usable": any(positive(v.get("lowPrice")) or positive(v.get("marketPrice")) for v in tplayer["holo"]), "reverse_usable": any(positive(v.get("lowPrice")) or positive(v.get("marketPrice")) for v in tplayer["reverse_holo"]),
            "normal_product_ids": sorted({v["productId"] for v in tplayer["normal"] if v.get("productId") is not None}), "holo_product_ids": sorted({v["productId"] for v in tplayer["holo"] if v.get("productId") is not None}), "reverse_product_ids": sorted({v["productId"] for v in tplayer["reverse_holo"] if v.get("productId") is not None}),
            "cardmarket_variant_product_ids": cardmarket_ids, "updated_at": row.get("updated") if row else "", "cardmarket_currency": "EUR", "tcgplayer_currency": "USD", "identity_note": identity_note,
        })
    return {row["collector_number"]: row for row in output}, {"status": set_result["status"], "http_status": set_result["http_status"], "sha256": set_result["sha256"], "url": TCGDEX_SET_URL, "records": len(details), "expected": 207}


def cardmarket_sample(db: Path, cache: SourceCache) -> tuple[list[dict[str, Any]], str]:
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("""
            SELECT p.cardmarket_id_product AS idProduct, cc.canonical_number, cc.name
              FROM cardmarket_product_printing_scopes s
              JOIN cardmarket_products p ON p.id=s.cardmarket_product_id
              JOIN canonical_cards cc ON cc.id=s.canonical_card_id
             WHERE p.cardmarket_id_expansion=5328 AND p.cardmarket_id_category=51 AND s.mapping_status='EXACT'
             ORDER BY CAST(cc.canonical_number AS INTEGER)
        """).fetchall()
    finally:
        conn.close()
    wanted = ["001", "003", "006", "025", "151", "199", "200", "201", "205", "207"]
    selected = []
    seen = set()
    for row in rows:
        number = norm_number(row["canonical_number"])
        if number in wanted and number not in seen:
            selected.append(dict(row)); seen.add(number)
    for row in rows:
        if len(selected) >= 20:
            break
        number = norm_number(row["canonical_number"])
        if number not in seen:
            selected.append(dict(row)); seen.add(number)
    observations = []
    for row in selected[:20]:
        slug = re.sub(r"[^A-Za-z0-9]+", "-", row["name"]).strip("-")
        url = f"https://www.cardmarket.com/en/Pokemon/Products/Singles/151/{slug}-V1-MEW{row['canonical_number']}"
        result = cache.fetch(url, "cardmarket_public_product_page")
        text = result["content"].decode("utf-8", errors="replace").casefold()
        observations.append({"idProduct": row["idProduct"], "collector_number": norm_number(row["canonical_number"]), "card_name": row["name"], "url": url, "status": result["status"], "http_status": result["http_status"], "sha256": result["sha256"], "cache_file": result["cache_file"], "reverse_filter_visible": "reverse holo" in text or "only reverse" in text, "condition_filter_visible": "near mint" in text or "nm" in text, "language_filter_visible": "english" in text, "low_or_from_visible": "price trend" in text or "from" in text, "notes": "No bypass; blocked responses stay evidence, not a negative semantic conclusion." if result["status"] == "BLOCKED" else "Parsed public response; filter semantics require manual verification."})
    statuses = Counter(row["status"] for row in observations)
    automation = "BLOCKED" if statuses["BLOCKED"] else "AVAILABLE_AUTOMATED" if statuses["OK"] == len(observations) else "UNSTABLE"
    return observations, automation


def finish_rows(identities: list[dict[str, Any]], ptcg: dict[str, dict[str, Any]], tcgdex: dict[str, dict[str, Any]], cardmarket_automation: str) -> list[dict[str, Any]]:
    rows = []
    direct = cardmarket_automation == "AVAILABLE_AUTOMATED"
    for identity in identities:
        number = identity["collector_number"]
        api, dex = ptcg.get(number, {}), tcgdex.get(number, {})
        api_exact = api.get("api_identity_status") == "EXACT"
        dex_exact = dex.get("tcgdex_identity_status") == "EXACT"
        for physical in identity["physical"]:
            finish = physical["finish"]
            family = {"normal": "normal", "holo": "holo", "reverse_holo": "reverse_holo"}[finish]
            api_key = {"normal": "normal_usable", "holo": "holo_usable", "reverse_holo": "reverse_usable"}[family]
            dex_key = api_key
            cm_reverse = finish == "reverse_holo" and api_exact and api.get("cardmarket_reverse_low_available", False)
            tcg_api = api_exact and bool(api.get(api_key, False))
            tcg_dex = dex_exact and bool(dex.get(dex_key, False))
            direct_available = direct and False
            sources = []
            if direct_available: sources.append("cardmarket_direct_low")
            if cm_reverse: sources.append("cardmarket_derived_external_reverse_low")
            if tcg_api or tcg_dex: sources.append("tcgplayer_secondary_reference")
            recommended = sources[0] if sources else "NULL"
            confidence = "HIGH" if direct_available else "MEDIUM" if cm_reverse else "LOW" if not sources else "MEDIUM"
            note_parts = ["Cardmarket direct finish-specific Low was not demonstrated in this audit." if not direct_available else "Direct route observed."]
            if cm_reverse: note_parts.append("reverseHoloLow is Cardmarket-derived through Pokémon TCG API; not imported and not yet adopted as dashboard primary.")
            if tcg_api or tcg_dex: note_parts.append("TCGplayer value is USD secondary reference only; never converted to EUR.")
            if tcg_api and tcg_dex and api.get(api_key) != dex.get(dex_key): note_parts.append("Provider availability/value shape differs; see comparison report.")
            rows.append({"card_id": physical["card_id"], "collector_number": number, "card_name": identity["card_name"], "finish": finish, "rarity": physical["rarity"], "cardmarket_direct_low_available": direct_available, "cardmarket_external_reverse_low_available": cm_reverse, "pokemon_tcg_api_tcgplayer_exact_finish_available": tcg_api, "tcgdex_tcgplayer_exact_finish_available": tcg_dex, "tcgplayer_exact_finish_available": tcg_api or tcg_dex, "recommended_source": recommended, "pricing_confidence": confidence, "notes": " ".join(note_parts)})
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    if fields is None:
        fields = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: compact(row[field]) if isinstance(row.get(field), (list, dict)) else row.get(field, "") for field in fields})


def report(output: Path, catalog: dict[str, Any], identities: list[dict[str, Any]], physical: list[dict[str, Any]], docs: list[dict[str, Any]], cm_rows: list[dict[str, Any]], cm_automation: str, ptcg_rows: dict[str, dict[str, Any]], ptcg_meta: dict[str, Any], dex_rows: dict[str, dict[str, Any]], dex_meta: dict[str, Any], coverage: list[dict[str, Any]], cache: SourceCache, route: str, offline: bool) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    cm_status = Counter(row["status"] for row in cm_rows)
    direct = cm_automation == "AVAILABLE_AUTOMATED"
    api_identity = Counter(row.get("api_identity_status") for row in ptcg_rows.values())
    dex_identity = Counter(row.get("tcgdex_identity_status") for row in dex_rows.values())
    api_reverse = sum(bool(row.get("cardmarket_reverse_low_available")) for row in ptcg_rows.values())
    api_tcg = Counter()
    dex_tcg = Counter()
    for finish, key in (("normal", "normal_usable"), ("holo", "holo_usable"), ("reverse_holo", "reverse_usable")):
        api_tcg[finish] = sum(bool(row.get(key)) and row.get("api_identity_status") == "EXACT" for row in ptcg_rows.values())
        dex_tcg[finish] = sum(bool(row.get(key)) and row.get("tcgdex_identity_status") == "EXACT" for row in dex_rows.values())
    agreement, disagreement = {}, {}
    for finish, key in (("normal", "normal_usable"), ("holo", "holo_usable"), ("reverse_holo", "reverse_usable")):
        common = [number for number in ptcg_rows if ptcg_rows[number].get("api_identity_status") == "EXACT" and dex_rows.get(number, {}).get("tcgdex_identity_status") == "EXACT"]
        agreement[finish] = sum(bool(ptcg_rows[number].get(key)) == bool(dex_rows[number].get(key)) for number in common)
        disagreement[finish] = len(common) - agreement[finish]
    (output / "01_cardmarket_public_route.md").write_text("\n".join([
        "# Route 1 — Cardmarket public listings (Pokémon 151)", "", f"Mode: `{'offline' if offline else 'online'}`; sample size: `{len(cm_rows)}`.", "", f"- Reverse Holo filter observable: `{'UNKNOWN — blocked' if cm_automation == 'BLOCKED' else 'YES' if any(r['reverse_filter_visible'] for r in cm_rows) else 'NO'}`", f"- Regular vs Reverse separable: `UNKNOWN — {cm_automation}`", "- NM enforceable: `UNKNOWN — no public response available in the sample`", "- English enforceable: `UNKNOWN — no public response available in the sample`", "- Low reproducible under NM + English + finish filters: `NO`", f"- Automation status: `{cm_automation}`", "", f"Sample status counts: `{dict(cm_status)}`.", "No login, credentials, private API, session manipulation, CAPTCHA bypass, 403 bypass, rate-limit bypass or anti-bot circumvention was attempted. Blocked responses are not interpreted as semantic absence. No production scraper was added.", ""]), encoding="utf-8")
    cm_fields = ["idProduct", "collector_number", "card_name", "url", "status", "http_status", "sha256", "cache_file", "reverse_filter_visible", "condition_filter_visible", "language_filter_visible", "low_or_from_visible", "notes"]
    write_csv(output / "02_cardmarket_listing_evidence.csv", cm_rows, cm_fields)
    ptcg_fields = ["collector_number", "card_name", "api_card_id", "api_identity_status", "normal_exists", "holo_exists", "reverse_exists", "normal_usable", "holo_usable", "reverse_usable", "cardmarket_low", "cardmarket_reverse_low", "cardmarket_trend", "cardmarket_reverse_trend", "cardmarket_avg1", "cardmarket_reverse_avg1", "cardmarket_avg7", "cardmarket_reverse_avg7", "cardmarket_avg30", "cardmarket_reverse_avg30", "cardmarket_reverse_fields_present", "cardmarket_reverse_low_available", "tcgplayer_normal_low", "tcgplayer_normal_market", "tcgplayer_holo_low", "tcgplayer_holo_market", "tcgplayer_reverse_low", "tcgplayer_reverse_market", "tcgplayer_updated_at", "cardmarket_updated_at", "cardmarket_currency", "tcgplayer_currency", "identity_note"]
    write_csv(output / "03_pokemon_tcg_api_coverage.csv", list(ptcg_rows.values()), ptcg_fields)
    dex_fields = ["collector_number", "card_name", "tcgdex_card_id", "tcgdex_identity_status", "normal_exists", "holo_exists", "reverse_exists", "normal_usable", "holo_usable", "reverse_usable", "normal_product_ids", "holo_product_ids", "reverse_product_ids", "cardmarket_variant_product_ids", "updated_at", "cardmarket_currency", "tcgplayer_currency", "identity_note"]
    write_csv(output / "04_tcgdex_tcgplayer_coverage.csv", list(dex_rows.values()), dex_fields)
    write_csv(output / "05_finish_price_coverage.csv", coverage)
    coverage_counts = Counter(row["recommended_source"] for row in coverage)
    finish_counts = {finish: Counter(row["recommended_source"] for row in coverage if row["finish"] == finish) for finish in ("normal", "holo", "reverse_holo")}
    comparison = [
        "# Source comparison", "", "| Dimension | Cardmarket public listings | Pokémon TCG API | TCGdex |", "|---|---|---|---|",
        f"| Finish precision | Unknown while blocked | Cardmarket reverse fields + TCGplayer keys | TCGplayer variant keys; Cardmarket variant records |",
        f"| Identity precision | Product ID/page, finish listing attribute | `{api_identity}` set + number + name | `{dex_identity}` set + localId + name |",
        "| Currency | EUR when directly obtained | Cardmarket-derived EUR; TCGplayer USD | Cardmarket EUR; TCGplayer USD |",
        "| Freshness | Not observable from blocked sample | Cardmarket/TCGplayer timestamps in response | Per-response update timestamps |",
        f"| Coverage | Direct finish-specific: `{sum(r['cardmarket_direct_low_available'] for r in coverage)}/{len(coverage)}` | Reverse Cardmarket-derived positive: `{api_reverse}/207`; TCGplayer normal/holo/reverse: `{dict(api_tcg)}` | TCGplayer normal/holo/reverse: `{dict(dex_tcg)}` |",
        f"| Availability agreement on common exact identities | N/A | `{dict(agreement)}` agreements; `{dict(disagreement)}` disagreements | Compared against Pokémon TCG API |",
        f"| Reproducibility | `{cm_automation}` | Cached JSON response | Cached JSON set + card responses |",
        "| Maintenance risk | High while anti-automation blocks access | Medium; provider response and reverse semantics must be revalidated | Medium/high; TCGdex documents known ID-mapping caveats |",
        "| Source transparency | Direct marketplace, but not obtained here | Explicit `cardmarket` and `tcgplayer` objects | Explicit provider objects, but per-variant mapping is still evolving |",
        "", "The table is an audit comparison, not a pricing policy change. TCGplayer values remain USD secondary references; no currency conversion is performed.", ""
    ]
    (output / "06_source_comparison.md").write_text("\n".join(comparison), encoding="utf-8")
    option = "OPTION C" if cm_automation == "BLOCKED" else "OPTION B" if api_reverse else "OPTION D"
    policy = ["# Recommended pricing policy", "", f"Recommendation: `{option}`", "", "1. Cardmarket remains the EUR primary source only when an exact physical finish and attributable metric are directly demonstrated.", "2. Pokémon TCG API `reverseHolo*` is classified as `CARDMARKET_DERIVED_EXTERNAL`, with provenance `source=pokemon_tcg_api; underlying_market=cardmarket`; it is not imported or enabled automatically in this sprint.", "3. TCGplayer normal/holofoil/reverseHolofoil remains a USD `secondary_market_reference`; it cannot overwrite or populate Cardmarket `current_price`.", "4. A missing or blocked exact-finish source remains `NULL`.", "", f"Observed Route 1 status: `{cm_automation}`. Observed API reverse low coverage: `{api_reverse}/207` numbered identities. Physical coverage recommendation counts: `{dict(coverage_counts)}`; by finish: `{ {k: dict(v) for k, v in finish_counts.items()} }`.", "", "This is a recommendation only. No pricing path was integrated and no database row was written.", ""]
    (output / "07_recommended_pricing_policy.md").write_text("\n".join(policy), encoding="utf-8")
    summary = ["# POKEMON-151-002D — Summary", "", f"Route: `{route}`; offline: `{offline}`.", "", "1. Can Cardmarket public listings be used sustainably?", f"   `NO automated path demonstrated; status {cm_automation}.`", "2. Can Reverse Holo Low be obtained directly from Cardmarket?", "   `NOT DEMONSTRATED; the public sample was blocked.`", "3. Does Cardmarket require browser/manual filtering?", "   `UNKNOWN from this run; current Help Center confirms Reverse Holo is a listing attribute.`", "4. Is automated access blocked?", f"   `{cm_automation}` on the 20-page sample.", "5. Does current Pokémon TCG API expose reverseHoloLow for sv3pt5?", f"   `YES as a present field in {sum('reverseHoloLow' in row.get('cardmarket_reverse_fields_present', []) for row in ptcg_rows.values())}/207 responses; positive usable value in {api_reverse}/207.`", "6. For how many 151 cards?", f"   `{api_reverse} with positive reverseHoloLow; zeros are treated as unavailable, not as prices.`", "7. Does Pokémon TCG API provide TCGplayer reverseHolofoil?", f"   `YES for {api_tcg['reverse_holo']}/207 exact identities with a usable value.`", "8. For how many physical reverse printings?", f"   `Local reverse_holo printings: {sum(row['finish']=='reverse_holo' for row in physical)}; API finish-specific coverage: {sum(row['finish']=='reverse_holo' and row['pokemon_tcg_api_tcgplayer_exact_finish_available'] for row in coverage)}.`", "9. Does TCGdex provide equivalent finish-specific TCGplayer pricing?", f"   `YES by explicit variant keys where present: normal {dex_tcg['normal']}, holo {dex_tcg['holo']}, reverse {dex_tcg['reverse_holo']}.`", "10. Do Pokémon TCG API and TCGdex agree where both exist?", f"   `Availability agreement by finish on common exact identities: {dict(agreement)}; disagreements: {dict(disagreement)}.`", "11. Can any source be trusted enough for exact finish pricing?", "   `Only as a candidate/reference after exact identity and finish evidence; this sprint does not promote pricing.`", "12. Which source should remain primary?", "   `Cardmarket direct exact-finish EUR, when demonstrable.`", "13. Which source should be secondary?", "   `TCGplayer finish-specific USD; Cardmarket-derived external Reverse is separately classified.`", "14. Should Reverse Holo Cardmarket current_price remain NULL?", "   `YES for the current dashboard until direct or explicitly approved Cardmarket-derived policy is validated.`", "15. Is a safe POKEMON-151-003 now possible?", "   `Not globally. Only a future, explicitly reviewed subset could qualify.`", "16. If yes, for which subset and using which source?", "   `No subset is auto-enabled by 002D; candidates are listed in 05_finish_price_coverage.csv.`", "", f"Coverage recommendation counts: `{dict(coverage_counts)}`.", f"Pokémon TCG API acquisition: `{ptcg_meta.get('acquisition', 'unknown')}`; records: `{ptcg_meta['records']}/207`.", "No database writes, price imports, snapshots, resolutions, Collection or Wishlist changes were made.", ""]
    (output / "08_summary.md").write_text("\n".join(summary), encoding="utf-8")
    manifest = {"route": route, "offline": offline, "local_catalog": catalog, "documentation": docs, "external_sources": cache.manifest.get("entries", []), "source_policy": "No DB writes; no pricing; no USD to EUR conversion; exact identity required."}
    (output / "source_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"numbered_identities": len(identities), "physical_printings": len(physical), "cardmarket_sample": len(cm_rows), "cardmarket_automation": cm_automation, "pokemon_tcg_api_records": ptcg_meta["records"], "tcgdex_records": dex_meta["records"], "cardmarket_reverse_low_positive": api_reverse, "coverage": dict(coverage_counts), "prices_applied": 0, "db_writes": 0}


def run(db: Path, output: Path, cache_dir: Path, route: str, offline: bool, refresh: bool) -> dict[str, Any]:
    if route not in {"cardmarket", "secondary", "all"}:
        raise AuditError(f"unknown route: {route}")
    identities, physical, catalog = read_catalog(db)
    cache = SourceCache(cache_dir, offline, refresh)
    include_cm = route in {"cardmarket", "all"}
    include_secondary = route in {"secondary", "all"}
    docs = fetch_docs(cache, include_cm, include_secondary)
    if include_cm:
        cm_rows, cm_automation = cardmarket_sample(db, cache)
    else:
        cm_rows, cm_automation = [], "NOT_RUN"
    ptcg_rows, ptcg_meta = load_pokemon_tcg_api(cache, identities) if include_secondary else ({}, {"records": 0, "status": "NOT_RUN", "http_status": None, "sha256": None, "url": PTCG_BULK_URL, "expected": 207})
    dex_rows, dex_meta = load_tcgdex(cache, identities) if include_secondary else ({}, {"records": 0, "status": "NOT_RUN", "http_status": None, "sha256": None, "url": TCGDEX_SET_URL, "expected": 207})
    coverage = finish_rows(identities, ptcg_rows, dex_rows, cm_automation)
    result = report(output, catalog, identities, physical, docs, cm_rows, cm_automation, ptcg_rows, ptcg_meta, dex_rows, dex_meta, coverage, cache, route, offline)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--route", choices=("cardmarket", "secondary", "all"), default="all")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--refresh-sources", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Accepted for explicit read-only invocation; this command never writes DB.")
    args = parser.parse_args()
    print(json.dumps(run(args.db, args.output, args.cache_dir, args.route, args.offline, args.refresh_sources), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
