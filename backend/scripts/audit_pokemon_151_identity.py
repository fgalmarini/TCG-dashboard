#!/usr/bin/env python3
"""Read-only identity and variant discovery audit for Pokémon 151.

This command reads the two local Cardmarket snapshots and fetches/caches public
metadata sources. It writes deterministic CSV/Markdown reports only. It never
opens SQLite, imports catalog data, applies prices, or mutates the source files.

External marketplace ids are evidence only. A Cardmarket product can be EXACT
only when the local product id, target expansion, numbered printing and finish
are all supported by compatible evidence.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


OFFICIAL_URL = "https://assets.pokemon.com/assets/cms2/pdf/trading-card-game/checklist/mew_web_cardlist_en.pdf"
TCGDEX_SET_URL = "https://api.tcgdex.net/v2/en/sets/{set_id}"
TCGDEX_CARD_URL = "https://api.tcgdex.net/v2/en/cards/{card_id}"
POKEMON_TCG_API_URL = "https://api.pokemontcg.io/v2/cards?q=set.id:{set_id}&pageSize=250"
DEFAULT_CACHE = Path("backend/scripts/.pokemon_151_identity_cache")
EXPECTED_NUMBERS = [f"{n:03d}" for n in range(1, 208)]
CASE_STUDIES = {
    "Mew ex", "Charizard ex", "Venusaur ex", "Blastoise ex", "Alakazam ex",
    "Zapdos ex", "Erika's Invitation", "Giovanni's Charisma",
}
PRICE_FIELDS = ("low", "trend", "avg1", "avg7", "avg30", "low-holo", "trend-holo", "avg1-holo", "avg7-holo", "avg30-holo")


class AuditError(Exception):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AuditError(f"No se pudo leer JSON válido: {path}: {exc}") from exc


def load_snapshot(path: Path, key: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    data = json_load(path)
    if not isinstance(data, dict) or not isinstance(data.get(key), list):
        raise AuditError(f"{path} debe contener un objeto con la lista `{key}`")
    rows = data[key]
    if not all(isinstance(row, dict) for row in rows):
        raise AuditError(f"{path} contiene registros no-objeto en `{key}`")
    return data, rows


def csv_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return value


def write_csv(path: Path, columns: list[str], rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: csv_value(row.get(column)) for column in columns})


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def normalize_text(value: Any) -> str:
    text = str(value or "").replace("’", "'").replace("♀", " F").replace("♂", " M")
    text = unicodedata.normalize("NFKC", text).casefold()
    text = re.sub(r"[^\w]+", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def normalize_card_name(value: Any) -> str:
    return normalize_text(value).replace(" ex", " ex")


def local_product_parts(raw_name: str) -> tuple[str, tuple[str, ...]]:
    text = str(raw_name or "").strip()
    match = re.match(r"^(.*?)\s+\[([^\]]*)\]$", text)
    if not match:
        return normalize_card_name(text), ()
    base = match.group(1).strip()
    attacks = tuple(
        normalize_text(part) for part in match.group(2).split("|")
        if normalize_text(part) and normalize_text(part) != "151"
    )
    return normalize_card_name(base), attacks


def card_attack_signature(card: dict[str, Any]) -> tuple[str, ...]:
    return tuple(normalize_text(attack.get("name")) for attack in card.get("attacks", []) if isinstance(attack, dict) and attack.get("name"))


def normalized_finish(variant_type: str) -> str:
    return {"reverse": "reverse_holo", "holo": "holo", "normal": "normal"}.get(variant_type, variant_type or "unknown")


def rarity_group(value: Any) -> str:
    text = normalize_text(value)
    groups = {
        "common": "Common", "uncommon": "Uncommon", "rare": "Rare",
        "double rare": "Double Rare", "illustration rare": "Illustration Rare",
        "ultra rare": "Ultra Rare", "special illustration rare": "Special Illustration Rare",
        "hyper rare": "Hyper Rare",
    }
    return groups.get(text, str(value or ""))


def treatment_from_variant(variant: dict[str, Any]) -> str:
    pieces: list[str] = []
    stamp = variant.get("stamp")
    if stamp:
        pieces.append("stamp=" + ",".join(str(item) for item in stamp) if isinstance(stamp, list) else f"stamp={stamp}")
    if variant.get("foil"):
        pieces.append(f"foil={variant['foil']}")
    return "; ".join(pieces)


def read_official_pdf(pdf_path: Path) -> tuple[list[dict[str, Any]], str]:
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", str(pdf_path), "-"],
            check=True, capture_output=True, text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise AuditError(f"No se pudo extraer el checklist oficial con pdftotext: {exc}") from exc
    text = result.stdout
    if "Scarlet & Violet" not in text or "151" not in text:
        raise AuditError("El PDF oficial no valida explícitamente Scarlet & Violet—151")
    rows: list[dict[str, Any]] = []
    row_pattern = re.compile(r"(?P<number>\d{3})\s+■\s+(?P<name>.*?)(?=\s{2,}\d{3}\s+■\s+|$)")
    for line in text.splitlines():
        for match in row_pattern.finditer(line):
            rows.append({"collector_number": match.group("number"), "card_name": re.sub(r"\s+", " ", match.group("name")).strip()})
    by_number: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_number[row["collector_number"]].append(row)
    missing = [number for number in EXPECTED_NUMBERS if number not in by_number]
    duplicates = [number for number, matches in by_number.items() if len(matches) > 1]
    if missing or duplicates or len(rows) != 207:
        raise AuditError(f"Checklist oficial inválido: rows={len(rows)}, missing={missing}, duplicates={duplicates}")
    return [by_number[number][0] for number in EXPECTED_NUMBERS], text


def http_bytes(url: str, retries: int = 3) -> bytes:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "TCG-DASHBOARD-pokemon-151-audit/1.0"})
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read()
        except (OSError, urllib.error.URLError, urllib.error.HTTPError) as exc:
            last = exc
            if attempt + 1 < retries:
                time.sleep(0.5 * (attempt + 1))
    raise AuditError(f"Fuente externa no disponible: {url}: {last}")


def cached_source(cache_dir: Path, relative: str, url: str, manifest: list[dict[str, Any]], source_name: str, identifier: str, refresh: bool = False) -> tuple[bytes | None, str]:
    path = cache_dir / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    status = "cached"
    if refresh or not path.exists():
        try:
            payload = http_bytes(url)
            path.write_bytes(payload)
            status = "fetched"
        except AuditError as exc:
            manifest.append({"source": source_name, "source_url": url, "source_identifier": identifier, "sha256": "", "retrieval_status": f"unavailable: {exc}"})
            return None, "unavailable"
    payload = path.read_bytes()
    manifest.append({"source": source_name, "source_url": url, "source_identifier": identifier, "sha256": sha256_bytes(payload), "retrieval_status": status})
    return payload, status


def validate_tcgdex_set(data: dict[str, Any], set_id: str) -> None:
    if data.get("id") != set_id or normalize_text(data.get("name")) != "151":
        raise AuditError(f"TCGdex set inválido: id={data.get('id')!r}, name={data.get('name')!r}")
    if data.get("cardCount", {}).get("total") != 207:
        raise AuditError(f"TCGdex set no declara total=207: {data.get('cardCount')!r}")
    cards = data.get("cards")
    if not isinstance(cards, list) or sorted(str(card.get("localId")) for card in cards) != EXPECTED_NUMBERS:
        raise AuditError("TCGdex no contiene exactamente localId 001–207")


def load_external_sources(cache_dir: Path, tcgdex_set_id: str, pokemon_tcg_set_id: str, refresh: bool, skip_api: bool, official_url: str, official_file: Path | None) -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, dict[str, Any]], list[dict[str, Any]], dict[str, str]]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, Any]] = []
    statuses: dict[str, str] = {}
    official_path = cache_dir / "official" / "mew_web_cardlist_en.pdf"
    official_source_url = official_url
    if official_file is not None:
        official_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            official_path.write_bytes(official_file.read_bytes())
        except OSError as exc:
            raise AuditError(f"No se pudo leer el checklist local: {official_file}: {exc}") from exc
        official_source_url = f"file:{official_file}"
        statuses["official"] = "local_override"
    elif refresh or not official_path.exists():
        try:
            official_path.parent.mkdir(parents=True, exist_ok=True)
            official_path.write_bytes(http_bytes(official_url))
            statuses["official"] = "fetched"
        except AuditError as exc:
            statuses["official"] = f"unavailable: {exc}"
    else:
        statuses["official"] = "cached"
    if official_path.exists():
        manifest.append({"source": "official_pokemon_checklist", "source_url": official_source_url, "source_identifier": "mew_web_cardlist_en.pdf", "sha256": sha256_file(official_path), "retrieval_status": statuses["official"]})
    if not official_path.exists():
        raise AuditError("No está disponible el checklist oficial Pokémon")

    set_bytes, statuses["tcgdex_set"] = cached_source(cache_dir, f"tcgdex/{tcgdex_set_id}/set.json", TCGDEX_SET_URL.format(set_id=tcgdex_set_id), manifest, "tcgdex_set", tcgdex_set_id, refresh)
    if set_bytes is None:
        raise AuditError("TCGdex set no disponible; no se puede validar la referencia secundaria")
    try:
        set_data = json.loads(set_bytes.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise AuditError(f"TCGdex set inválido: {exc}") from exc
    validate_tcgdex_set(set_data, tcgdex_set_id)

    cards: dict[str, dict[str, Any]] = {}
    for brief in sorted(set_data["cards"], key=lambda item: str(item.get("localId"))):
        card_id = str(brief.get("id"))
        payload, status = cached_source(cache_dir, f"tcgdex/{tcgdex_set_id}/cards/{card_id}.json", TCGDEX_CARD_URL.format(card_id=card_id), manifest, "tcgdex_card", card_id, refresh)
        statuses[f"tcgdex:{card_id}"] = status
        if payload is None:
            continue
        try:
            detail = json.loads(payload.decode("utf-8"))
        except json.JSONDecodeError:
            statuses[f"tcgdex:{card_id}"] = "invalid_json"
            continue
        if detail.get("id") != card_id or detail.get("set", {}).get("id") != tcgdex_set_id:
            statuses[f"tcgdex:{card_id}"] = "invalid_identity"
            continue
        cards[str(detail.get("localId"))] = detail

    api_cards: dict[str, dict[str, Any]] = {}
    if not skip_api:
        api_bytes, statuses["pokemon_tcg_api"] = cached_source(cache_dir, f"pokemon_tcg_api/{pokemon_tcg_set_id}.json", POKEMON_TCG_API_URL.format(set_id=pokemon_tcg_set_id), manifest, "pokemon_tcg_api", pokemon_tcg_set_id, refresh)
        if api_bytes:
            try:
                api_data = json.loads(api_bytes.decode("utf-8"))
                if api_data.get("totalCount") == 207 and all(card.get("set", {}).get("id") == pokemon_tcg_set_id for card in api_data.get("data", [])):
                    api_cards = {str(card.get("number")).zfill(3): card for card in api_data.get("data", []) if card.get("number")}
                else:
                    statuses["pokemon_tcg_api"] = "invalid_set_validation"
            except json.JSONDecodeError:
                statuses["pokemon_tcg_api"] = "invalid_json"
    else:
        statuses["pokemon_tcg_api"] = "skipped_by_cli"
    return set_data, cards, api_cards, manifest, statuses


def price_index(prices: list[dict[str, Any]]) -> dict[Any, list[dict[str, Any]]]:
    index: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for row in prices:
        index[row.get("idProduct")].append(row)
    return index


def source_cardmarket_variants(cards: dict[str, dict[str, Any]]) -> tuple[dict[Any, list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    by_product: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    by_number: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for number, card in cards.items():
        for variant in card.get("variants_detailed", []) or []:
            cm = ((variant.get("pricing") or {}).get("cardmarket") or {})
            product_id = cm.get("idProduct")
            if product_id is None:
                continue
            entry = {
                "collector_number": number,
                "card_name": card.get("name"),
                "finish": normalized_finish(str(variant.get("type") or "")),
                "detected_treatment": treatment_from_variant(variant),
                "source_variant_id": variant.get("variantId"),
                "external_product_id": product_id,
                "external_expansion": card.get("set", {}).get("id"),
            }
            by_product[product_id].append(entry)
            by_number[number].append(entry)
    return by_product, by_number


def official_rows(official: list[dict[str, Any]], tcgdex: dict[str, dict[str, Any]], api: dict[str, dict[str, Any]], tcgdex_set_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for official_card in official:
        number = official_card["collector_number"]
        card = tcgdex.get(number, {})
        api_card = api.get(number, {})
        name = official_card["card_name"]
        tcgdex_name = card.get("name")
        api_name = api_card.get("name")
        metadata_sources = ["official_pokemon_checklist"]
        if card:
            metadata_sources.append("tcgdex")
        if api_card:
            metadata_sources.append("pokemon_tcg_api")
        attacks = [attack.get("name") for attack in card.get("attacks", []) if isinstance(attack, dict) and attack.get("name")]
        pokemon = card.get("category") == "Pokemon"
        rows.append({
            "collector_number": number,
            "printed_set_number": number,
            "card_name": name,
            "tcgdex_name": tcgdex_name,
            "category": card.get("category") or api_card.get("supertype"),
            "pokemon_species": re.sub(r"\s+ex$", "", str(tcgdex_name or name), flags=re.IGNORECASE) if pokemon else "",
            "dex_number": card.get("dexId") or api_card.get("nationalPokedexNumbers"),
            "rarity": card.get("rarity") or api_card.get("rarity"),
            "rarity_group": rarity_group(card.get("rarity") or api_card.get("rarity")),
            "hp": card.get("hp") or api_card.get("hp"),
            "pokemon_type": card.get("types") or api_card.get("types"),
            "stage": card.get("stage") or (api_card.get("subtypes") or [None])[0],
            "evolves_from": card.get("evolveFrom") or api_card.get("evolvesFrom"),
            "is_ex": bool(str(tcgdex_name or name).lower().endswith(" ex")) or "ex" in [str(x).lower() for x in card.get("suffix", []) if x],
            "artist": card.get("illustrator") or api_card.get("artist"),
            "regulation_mark": card.get("regulationMark") or api_card.get("regulationMark"),
            "abilities": [item.get("name") for item in card.get("abilities", []) if isinstance(item, dict) and item.get("name")],
            "attacks": attacks or [item.get("name") for item in api_card.get("attacks", []) if isinstance(item, dict) and item.get("name")],
            "weaknesses": card.get("weaknesses") or api_card.get("weaknesses"),
            "retreat": card.get("retreat") if card.get("retreat") is not None else api_card.get("convertedRetreatCost"),
            "has_normal": bool((card.get("variants") or {}).get("normal")),
            "has_holo": bool((card.get("variants") or {}).get("holo")),
            "has_reverse_holo": bool((card.get("variants") or {}).get("reverse")),
            "variant_confidence": "SUPPORTED" if card else "UNKNOWN",
            "official_source": OFFICIAL_URL,
            "metadata_sources": ";".join(metadata_sources),
            "source_confidence": "HIGH for number/name/set membership; MEDIUM for metadata from structured secondary sources",
            "source_notes": "Official PDF extraction does not expose per-row rarity icons as text; rarity is sourced from TCGdex/API and remains separately attributed.",
            "tcgdex_id": card.get("id") or f"{tcgdex_set_id}-{number}",
            "pokemon_tcg_api_id": api_card.get("id"),
            "image": card.get("image") or (api_card.get("images") or {}).get("large"),
        })
    return rows


def variant_rows(official_rows_data: list[dict[str, Any]], tcgdex: dict[str, dict[str, Any]], local_product_ids: set[Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for official in official_rows_data:
        number = official["collector_number"]
        card = tcgdex.get(number, {})
        variants = card.get("variants") or {}
        for source_key, finish in (("normal", "normal"), ("holo", "holo"), ("reverse", "reverse_holo")):
            if not variants.get(source_key):
                continue
            detailed = [v for v in card.get("variants_detailed", []) if normalized_finish(str(v.get("type") or "")) == finish]
            ids = [((v.get("pricing") or {}).get("cardmarket") or {}).get("idProduct") for v in detailed]
            ids = [value for value in ids if value is not None]
            rows.append({
                "collector_number": number,
                "card_name": official["card_name"],
                "rarity": official.get("rarity"),
                "finish": finish,
                "variant_status": "CONFIRMED" if detailed else "SUPPORTED",
                "variant_source": "tcgdex.variants + tcgdex.variants_detailed" if detailed else "tcgdex.variants",
                "variant_confidence": "HIGH" if detailed else "MEDIUM",
                "variant_notes": f"Cardmarket candidate ids={','.join(map(str, ids)) or 'none'}; local_target_ids={','.join(str(i) for i in ids if i in local_product_ids) or 'none'}; finish is separate from rarity.",
                "detected_treatment": "; ".join(sorted({treatment_from_variant(v) for v in detailed if treatment_from_variant(v)})),
                "treatment_source": "tcgdex.variants_detailed" if any(treatment_from_variant(v) for v in detailed) else "",
                "treatment_confidence": "SUPPORTED" if any(treatment_from_variant(v) for v in detailed) else "",
            })
        for detailed in card.get("variants_detailed", []) or []:
            treatment = treatment_from_variant(detailed)
            if not treatment:
                continue
            finish = normalized_finish(str(detailed.get("type") or ""))
            rows.append({
                "collector_number": number,
                "card_name": official["card_name"],
                "rarity": official.get("rarity"),
                "finish": finish,
                "variant_status": "SUPPORTED",
                "variant_source": "tcgdex.variants_detailed",
                "variant_confidence": "MEDIUM",
                "variant_notes": "Treatment is preserved separately and is not promoted to a persisted catalog variant in this sprint.",
                "detected_treatment": treatment,
                "treatment_source": "tcgdex.variants_detailed",
                "treatment_confidence": "MEDIUM",
            })
    return rows


def choose_candidates(product: dict[str, Any], official_rows_data: list[dict[str, Any]], tcgdex: dict[str, dict[str, Any]], direct_variants: dict[Any, list[dict[str, Any]]]) -> tuple[list[dict[str, Any]], str, list[str]]:
    name_sig, attacks = local_product_parts(str(product.get("name") or ""))
    by_name = [row for row in official_rows_data if normalize_card_name(row.get("card_name")) == name_sig]
    by_signature: list[dict[str, Any]] = []
    if attacks:
        for row in by_name:
            card = tcgdex.get(row["collector_number"], {})
            if card_attack_signature(card) == attacks:
                by_signature.append(row)
    candidates = by_signature or by_name
    if not candidates and "energy" in name_sig:
        energy_rows = [row for row in official_rows_data if row.get("category") == "Energy" and row.get("collector_number") == "207"]
        if energy_rows:
            candidates = energy_rows
    evidence: list[str] = [f"name_signature={name_sig}"]
    if attacks:
        evidence.append(f"attack_signature={' | '.join(attacks)}")
    direct = direct_variants.get(product.get("idProduct"), [])
    if direct:
        evidence.append("external_tcg_cardmarket_id_matches_local_product")
        direct_numbers = {entry["collector_number"] for entry in direct}
        direct_candidates = [row for row in candidates if row["collector_number"] in direct_numbers]
        if direct_candidates:
            candidates = direct_candidates
    else:
        evidence.append("no_direct_external_id_match")
    if not candidates:
        return [], "none", evidence
    method = "exact_name_and_attack_signature" if by_signature else ("official_energy_name_alias" if candidates and not by_name else "exact_name_only")
    return candidates, method, evidence


def finish_evidence(number: str, card: dict[str, Any], product_id: Any, direct_variants: dict[Any, list[dict[str, Any]]]) -> tuple[str, str, str, str]:
    direct = direct_variants.get(product_id, [])
    if direct:
        finishes = sorted({item["finish"] for item in direct})
        treatments = sorted({item["detected_treatment"] for item in direct if item.get("detected_treatment")})
        if len(finishes) == 1:
            return finishes[0], "SUPPORTED", "; ".join(treatments), "direct TCGdex variant evidence; local idProduct validated"
        return "", "AMBIGUOUS", "; ".join(treatments), "same local idProduct appears in multiple TCGdex finish records"
    variants = card.get("variants") or {}
    finishes = [finish for key, finish in (("normal", "normal"), ("holo", "holo"), ("reverse", "reverse_holo")) if variants.get(key)]
    if len(finishes) == 1:
        return finishes[0], "SUPPORTED", "", "TCGdex card-level variant set has one supported finish; Cardmarket finish not directly linked"
    if len(finishes) > 1:
        return "", "AMBIGUOUS", "", "TCGdex supports multiple finishes and local Product Catalogue does not expose finish"
    return "", "UNKNOWN", "", "no finish evidence"


def mapping_rows(products: list[dict[str, Any]], official_rows_data: list[dict[str, Any]], tcgdex: dict[str, dict[str, Any]], direct_variants: dict[Any, list[dict[str, Any]]], prices_by_product: dict[Any, list[dict[str, Any]]], expansion_id: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for product in sorted(products, key=lambda row: int(row.get("idProduct") or 0)):
        product_id = product.get("idProduct")
        candidates, method, evidence = choose_candidates(product, official_rows_data, tcgdex, direct_variants)
        direct = direct_variants.get(product_id, [])
        selected = candidates[0] if len(candidates) == 1 else None
        card = tcgdex.get(selected["collector_number"], {}) if selected else {}
        matched_finish, finish_status, treatment, finish_note = (finish_evidence(selected["collector_number"], card, product_id, direct_variants) if selected else ("", "UNKNOWN", "", "no unique numbered printing candidate"))
        target_direct = [item for item in direct if item.get("external_expansion") == "sv03.5"]
        if len(candidates) > 1:
            status, confidence = "AMBIGUOUS", "LOW"
        elif not candidates:
            status, confidence = "UNRESOLVED", "NONE"
        elif target_direct and len({item["collector_number"] for item in target_direct}) == 1 and finish_status not in {"UNKNOWN", "AMBIGUOUS"}:
            status, confidence = "EXACT", "HIGH"
        elif selected:
            status, confidence = "PROBABLE", "MEDIUM"
        else:
            status, confidence = "UNRESOLVED", "NONE"
        price_rows = prices_by_product.get(product_id, [])
        price = price_rows[0] if len(price_rows) == 1 else {}
        notes = [finish_note, "idMetacard retained as Cardmarket grouping evidence; never used as numbered identity"]
        if len(price_rows) != 1:
            notes.append(f"Price Guide join count={len(price_rows)}; pricing copied only when one-to-one")
        if direct and not target_direct:
            notes.append("external TCGdex Cardmarket id exists locally but belongs to another expansion; not sufficient for EXACT target mapping")
        rows.append({
            "cardmarket_product_id": product_id,
            "idMetacard": product.get("idMetacard"),
            "cardmarket_product_name": product.get("name"),
            "matched_collector_number": selected.get("collector_number") if selected else "",
            "matched_card_name": selected.get("card_name") if selected else "",
            "matched_rarity": selected.get("rarity") if selected else "",
            "matched_finish": matched_finish,
            "numbered_identity_status": status,
            "finish_status": finish_status,
            "treatment_status": "SUPPORTED" if treatment else "UNKNOWN",
            "mapping_status": status,
            "mapping_confidence": confidence,
            "mapping_method": method,
            "mapping_evidence": "; ".join(evidence),
            "notes": "; ".join(note for note in notes if note),
            "price_low": price.get("low"),
            "price_trend": price.get("trend"),
            "price_avg1": price.get("avg1"),
            "price_avg7": price.get("avg7"),
            "price_avg30": price.get("avg30"),
            "price_low_holo": price.get("low-holo"),
            "price_trend_holo": price.get("trend-holo"),
            "price_avg1_holo": price.get("avg1-holo"),
            "price_avg7_holo": price.get("avg7-holo"),
            "price_avg30_holo": price.get("avg30-holo"),
            "candidate_count": len(candidates),
            "candidate_numbers": ",".join(row["collector_number"] for row in candidates),
            "detected_treatment": treatment,
            "source_expansion_id": product.get("idExpansion"),
            "target_expansion_id": expansion_id,
        })
    return rows


def extras_rows(mapping: list[dict[str, Any]], official_rows_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    official_by_name: dict[str, list[str]] = defaultdict(list)
    for row in official_rows_data:
        official_by_name[normalize_card_name(row["card_name"])].append(row["collector_number"])
    groups: dict[tuple[Any, str], list[dict[str, Any]]] = defaultdict(list)
    for row in mapping:
        name_sig, _ = local_product_parts(str(row.get("cardmarket_product_name") or ""))
        groups[(row.get("idMetacard"), name_sig)].append(row)
    extras: list[dict[str, Any]] = []
    for (metacard, name_sig), members in sorted(groups.items(), key=lambda item: (str(item[0][1]), str(item[0][0]))):
        expected_numbers = sorted(official_by_name.get(name_sig, []))
        if not expected_numbers and "energy" in name_sig:
            expected_numbers = [row["collector_number"] for row in official_rows_data if row.get("category") == "Energy" and row.get("collector_number") == "207"]
        surplus = max(0, len(members) - len(expected_numbers))
        if not surplus:
            continue
        # Cardmarket has no explicit version/finish field. Highest ids are only
        # a deterministic review representative, never a resolved variant.
        for row in sorted(members, key=lambda item: int(item["cardmarket_product_id"]), reverse=True)[:surplus]:
            extras.append({
                "idProduct": row["cardmarket_product_id"],
                "product_name": row["cardmarket_product_name"],
                "idMetacard": metacard,
                "candidate_numbered_printing": ",".join(expected_numbers),
                "candidate_finish": "",
                "reason": f"apparent surplus in source group: {len(members)} local products versus {len(expected_numbers)} official numbered printings with this name; deterministic highest-id review representative only",
                "evidence": f"name_signature={name_sig}; group_product_ids={','.join(str(item['cardmarket_product_id']) for item in sorted(members, key=lambda item: int(item['cardmarket_product_id'])))}; idMetacard={metacard}",
                "confidence": "LOW — apparent surplus, finish/variant unresolved",
            })
    return sorted(extras, key=lambda row: int(row["idProduct"]))


def metacard_rows(mapping: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for row in mapping:
        groups[row.get("idMetacard")].append(row)
    output: list[dict[str, Any]] = []
    for metacard, members in sorted(groups.items(), key=lambda item: str(item[0])):
        numbers = sorted({row["matched_collector_number"] for row in members if row.get("matched_collector_number")})
        names = sorted({row.get("matched_card_name") or "" for row in members})
        finishes = sorted({row.get("matched_finish") for row in members if row.get("matched_finish")})
        if len(numbers) > 1:
            behavior = "multiple_number_candidates"
        elif len(members) > 1:
            behavior = "one_number_multiple_products" if numbers else "multiple_products_unresolved"
        else:
            behavior = "one_product"
        output.append({
            "idMetacard": metacard, "product_count": len(members),
            "product_ids": ",".join(str(row["cardmarket_product_id"]) for row in members),
            "product_names": " || ".join(str(row["cardmarket_product_name"]) for row in members),
            "matched_numbers": ",".join(numbers), "matched_names": " || ".join(names),
            "matched_finishes": ",".join(finishes), "grouping_behavior": behavior,
            "mapping_statuses": ",".join(sorted({row["mapping_status"] for row in members})),
            "notes": "idMetacard is a Cardmarket grouping key, not a catalog card identity; duplicate names/products require finish or numbered evidence.",
        })
    return output


def metadata_coverage(official_rows_data: list[dict[str, Any]], mapping: list[dict[str, Any]], variant_matrix: list[dict[str, Any]], statuses: dict[str, str]) -> list[dict[str, Any]]:
    fields = ["collector_number", "card_name", "rarity", "category", "pokemon_species", "hp", "pokemon_type", "stage", "evolves_from", "artist", "regulation_mark", "attacks", "has_normal", "has_holo", "has_reverse_holo"]
    rows: list[dict[str, Any]] = []
    total = len(official_rows_data)
    for field in fields:
        populated = sum(bool(row.get(field)) or row.get(field) is False for row in official_rows_data)
        rows.append({"metric_type": "official_207_field", "field": field, "total": total, "populated": populated, "missing": total - populated, "coverage_percent": round(populated * 100 / total, 2) if total else 0, "source": "official + TCGdex/API as available", "notes": "Null is preserved when a field is inapplicable or unavailable."})
    for field, label in (("mapping_status", "Cardmarket mapping status"), ("finish_status", "finish status"), ("treatment_status", "treatment status")):
        counts = Counter(row[field] for row in mapping)
        for value, count in sorted(counts.items()):
            rows.append({"metric_type": label, "field": value, "total": len(mapping), "populated": count, "missing": len(mapping) - count, "coverage_percent": round(count * 100 / len(mapping), 2), "source": "computed audit", "notes": "One row per Cardmarket product."})
    rows.append({"metric_type": "variant_matrix", "field": "supported_variant_rows", "total": total, "populated": len(variant_matrix), "missing": "", "coverage_percent": "", "source": "TCGdex", "notes": "Rows are emitted only for explicitly supported/confirmed variants."})
    for key, value in sorted(statuses.items()):
        if key not in {"official", "tcgdex_set", "pokemon_tcg_api"}:
            continue
        rows.append({"metric_type": "source_status", "field": key, "total": 1, "populated": 1 if value in {"cached", "fetched"} else 0, "missing": 0 if value in {"cached", "fetched"} else 1, "coverage_percent": 100 if value in {"cached", "fetched"} else 0, "source": key, "notes": value})
    return rows


def ambiguous_rows(mapping: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for row in mapping:
        if row["mapping_status"] != "AMBIGUOUS":
            continue
        candidates = row.get("candidate_numbers", "").split(",")[:3]
        output.append({
            "product_name": row["cardmarket_product_name"],
            "cardmarket_product_id": row["cardmarket_product_id"],
            "candidates_1_to_3": ",".join(candidates),
            "reason": "more than one reasonable numbered-printing candidate after name/attack matching",
            "missing_evidence": "official-to-Cardmarket product/finish linkage or distinguishing artwork/finish field",
            "review": "Do not force a numbered identity or pricing mapping; require explicit evidence/manual decision.",
        })
    return output


def markdown_table(headers: list[str], rows: Iterable[Iterable[Any]]) -> str:
    def cell(value: Any) -> str:
        return str(value if value is not None else "").replace("|", "\\|").replace("\n", "<br>")
    output = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    output.extend("| " + " | ".join(cell(value) for value in row) + " |" for row in rows)
    return "\n".join(output)


def render_reports(output: Path, official: list[dict[str, Any]], official_rows_data: list[dict[str, Any]], variant_matrix: list[dict[str, Any]], mapping: list[dict[str, Any]], extras: list[dict[str, Any]], metacards: list[dict[str, Any]], coverage: list[dict[str, Any]], ambiguous: list[dict[str, Any]], manifest: list[dict[str, Any]], statuses: dict[str, str], products_path: Path, prices_path: Path, expansion_id: int, tcgdex_set_id: str, api_set_id: str) -> None:
    output.mkdir(parents=True, exist_ok=True)
    official_columns = ["collector_number", "printed_set_number", "card_name", "tcgdex_name", "category", "pokemon_species", "dex_number", "rarity", "rarity_group", "hp", "pokemon_type", "stage", "evolves_from", "is_ex", "artist", "regulation_mark", "abilities", "attacks", "weaknesses", "retreat", "has_normal", "has_holo", "has_reverse_holo", "variant_confidence", "official_source", "metadata_sources", "source_confidence", "source_notes", "tcgdex_id", "pokemon_tcg_api_id", "image"]
    variant_columns = ["collector_number", "card_name", "rarity", "finish", "variant_status", "variant_source", "variant_confidence", "variant_notes", "detected_treatment", "treatment_source", "treatment_confidence"]
    mapping_columns = ["cardmarket_product_id", "idMetacard", "cardmarket_product_name", "matched_collector_number", "matched_card_name", "matched_rarity", "matched_finish", "numbered_identity_status", "finish_status", "treatment_status", "mapping_status", "mapping_confidence", "mapping_method", "mapping_evidence", "notes", "price_low", "price_trend", "price_avg1", "price_avg7", "price_avg30", "price_low_holo", "price_trend_holo", "price_avg1_holo", "price_avg7_holo", "price_avg30_holo", "candidate_count", "candidate_numbers", "detected_treatment", "source_expansion_id", "target_expansion_id"]
    extras_columns = ["idProduct", "product_name", "idMetacard", "candidate_numbered_printing", "candidate_finish", "reason", "evidence", "confidence"]
    metacard_columns = ["idMetacard", "product_count", "product_ids", "product_names", "matched_numbers", "matched_names", "matched_finishes", "grouping_behavior", "mapping_statuses", "notes"]
    coverage_columns = ["metric_type", "field", "total", "populated", "missing", "coverage_percent", "source", "notes"]
    ambiguous_columns = ["product_name", "cardmarket_product_id", "candidates_1_to_3", "reason", "missing_evidence", "review"]
    write_csv(output / "01_official_207_cards.csv", official_columns, official_rows_data)
    write_csv(output / "02_variant_matrix.csv", variant_columns, variant_matrix)
    write_csv(output / "03_cardmarket_mapping.csv", mapping_columns, mapping)
    write_csv(output / "04_cardmarket_extra_products.csv", extras_columns, extras)
    write_csv(output / "05_idmetacard_analysis.csv", metacard_columns, metacards)
    write_csv(output / "06_metadata_coverage.csv", coverage_columns, coverage)
    write_csv(output / "07_ambiguous_mappings.csv", ambiguous_columns, ambiguous)

    status_counts = Counter(row["mapping_status"] for row in mapping)
    finish_counts = {
        "normal": sum(bool(row.get("has_normal")) for row in official_rows_data),
        "holo": sum(bool(row.get("has_holo")) for row in official_rows_data),
        "reverse_holo": sum(bool(row.get("has_reverse_holo")) for row in official_rows_data),
    }
    complete_identity = sum(bool(row.get("collector_number")) and bool(row.get("card_name")) and bool(row.get("rarity")) and bool(row.get("category")) for row in official_rows_data)
    all_reviewed = len(mapping) == 210 and all(row.get("mapping_status") for row in mapping)
    ready = complete_identity == 207 and len(official_rows_data) == 207 and all_reviewed
    source_lines = [f"- `{item['source']}` / `{item['source_identifier']}`: `{item['retrieval_status']}`, SHA-256 `{item['sha256']}`" for item in manifest]
    case_rows = [row for row in mapping if any(name.casefold() in str(row.get("cardmarket_product_name", "")).casefold() for name in CASE_STUDIES)]
    case_table = markdown_table(["Product", "idMetacard", "number", "status", "finish", "evidence"], ((row["cardmarket_product_name"], row["idMetacard"], row["matched_collector_number"], row["mapping_status"], row["matched_finish"], row["mapping_method"]) for row in case_rows[:30]))
    findings = [
        "# Pokémon 151 — Identity and Variant Findings", "", "## Scope and provenance", "",
        f"- Local Products: `{products_path}`; SHA-256 `{sha256_file(products_path)}`.", f"- Local Price Guide: `{prices_path}`; SHA-256 `{sha256_file(prices_path)}`.", f"- Target local `idExpansion`: `{expansion_id}`; Cardmarket rows audited: `{len(mapping)}`.", "- DB, catalog, imports, pricing apply, frontend, Magic, One Piece, Collection and Wishlist were not touched.", "", "## External source manifest", "", *source_lines, "", "## Authority and inference boundary", "", "- Official checklist controls set membership, official number and official name. Its PDF rarity symbols are not machine-readable through the extraction used here; rarity is attributed to TCGdex/API when present.", "- TCGdex supplies structured metadata and explicit variant evidence. Its Cardmarket IDs are candidates only and are never treated as local identity without validation.", "- Local Cardmarket files control `idProduct`, `idMetacard`, expansion and price fields.", "- Every computed mapping method/confidence is separate from source fields.", "", "## Numbered identity", "", f"- Official reference: `{len(official)}/207`; missing numbers: `{','.join(number for number in EXPECTED_NUMBERS if number not in {row['collector_number'] for row in official}) or 'none'}`; duplicates: `none` after validation.", "- Numbers `166–207` remain independent numbered printings; same-name groups are navigation hypotheses only.", "", "## Variant and treatment findings", "", f"- Explicit variant rows: `{len(variant_matrix)}`; normal: `{finish_counts['normal']}`, holo: `{finish_counts['holo']}`, reverse holo: `{finish_counts['reverse_holo']}`.", "- Variant rows are emitted only from explicit TCGdex `variants`/`variants_detailed` evidence.", "- Treatments such as stamps/cosmos are structured in discovery output and are not promoted to persisted catalog variants.", "- A same-product normal/reverse occurrence is reported as grouped commercial evidence; it does not create a synthetic second Product ID.", "", "## Mandatory case studies", "", case_table, "", "## 210 versus 207", "", f"- Distinct official numbered printings: `207`; local Cardmarket products: `{len(mapping)}`; computed surplus rows: `{len(extras)}`.", "- Surplus rows are derived from duplicate/non-one-to-one assignments and are not automatically labeled reverse, holo, promo or stamped.", "", "## idMetacard", "", f"- Observed groups: `{len(metacards)}`.", "- `idMetacard` is a source grouping key. It can contain multiple Product IDs and cannot replace `game/set/collector_number` identity.", "", "## Price boundary", "", "- Price fields are copied from strict local `idProduct` joins for reporting only.", "- No price was applied, normalized into DB, or used as identity evidence.", "", "## Limitations", "", f"- Pokémon TCG API status: `{statuses.get('pokemon_tcg_api')}`; API failure is non-blocking.", "- `EXACT` requires direct target-expansion product evidence. Name/attack matches without direct local Product ID evidence remain `PROBABLE`.",
    ]
    (output / "08_identity_and_variant_findings.md").write_text("\n".join(findings) + "\n", encoding="utf-8")

    model = ["# Pokémon 151 — Recommended Discovery Model", "", "This is a discovery recommendation only. No schema, DB or catalog change was made.", "", "## Identity hierarchy", "", "```text", "game / set / collector_number", "  -> numbered printing identity", "  -> finish (normal / holo / reverse_holo)", "  -> treatment (stamped / cosmos / other, nullable and source-backed)", "  -> Cardmarket idProduct", "```", "", "## Rules", "", "- `collector_number` is mandatory for numbered printing identity.", "- `rarity` is separate from finish.", "- `idProduct` is provider identity; `idMetacard` is grouping evidence only.", "- Same-name cards with different numbers never share uniqueness.", "- A single provider Product ID may carry multiple finish evidences; the model must not invent products.", "- Ambiguous mappings remain unresolved and cannot feed automatic pricing/import.", "", "## Provenance", "", "Keep source, method, confidence and notes per important derived datum. Retain external candidate IDs without promoting them to local Cardmarket identity until validated.", "", "Suggested next-step input: `POKEMON-151-001` may be designed only from the explicit statuses and blockers in this audit; this sprint does not execute it."]
    (output / "09_recommended_model.md").write_text("\n".join(model) + "\n", encoding="utf-8")

    summary = [
        "# POKEMON 151 IDENTITY DISCOVERY", "", f"Official numbered printings: {len(official)}/207", "", "Metadata coverage:", f"- Identity-complete core rows: {complete_identity}/207", f"- Explicit variant rows: {len(variant_matrix)}", f"- Normal variants: {finish_counts['normal']}", f"- Holo variants: {finish_counts['holo']}", f"- Reverse holo variants: {finish_counts['reverse_holo']}", "", f"Cardmarket products: {len(mapping)}", f"EXACT mappings: {status_counts['EXACT']}", f"PROBABLE mappings: {status_counts['PROBABLE']}", f"AMBIGUOUS mappings: {status_counts['AMBIGUOUS']}", f"MISMATCH mappings: {status_counts['MISMATCH']}", f"UNRESOLVED mappings: {status_counts['UNRESOLVED']}", "", f"Extra Cardmarket products: {len(extras)}", *(f"- {row['idProduct']}: {row['product_name']} — {row['reason']}" for row in extras), "", "idMetacard conclusion:", f"- {len(metacards)} source groups; grouping is not numbered-card identity.", "", "Alternate-art conclusion:", "- Cards 166–207 are independent numbered printings. Same-name relationships are navigation-only.", "", "Variant conclusion:", "- Only explicit TCGdex normal/holo/reverse evidence was emitted. Finish and treatment remain separate; no ambiguous variant was forced.", "", "## Contract questions", "", f"1. All 207 identified? {'YES' if len(official) == 207 else 'NO'}.", f"2. Complete metadata count? {complete_identity}/207 core identity rows; optional fields are reported per-field.", f"3. Confirmed normal count? {finish_counts['normal']} explicit rows.", f"4. Confirmed holo count? {finish_counts['holo']} explicit rows.", f"5. Confirmed reverse count? {finish_counts['reverse_holo']} explicit rows.", f"6. Uncertain finish cards? {sum(1 for row in mapping if row['finish_status'] in {'UNKNOWN', 'AMBIGUOUS'})} Cardmarket products.", f"7. EXACT count? {status_counts['EXACT']}.", f"8. PROBABLE count? {status_counts['PROBABLE']}.", f"9. AMBIGUOUS count? {status_counts['AMBIGUOUS']}.", f"10. UNRESOLVED count? {status_counts['UNRESOLVED']}.", f"11. Apparent extra products? {len(extras)} computed; no hardcoded assumption.", f"12. idMetacard grouping? {len(metacards)} groups; it groups commercial products and is not internal card identity.", "13. Separate reverse Product IDs? Not established globally; TCGdex includes same Product IDs for normal/reverse in observed cards.", "14. Separate holo Product IDs? Not established globally; foil pricing is not Product ID proof.", "15. Can one Product represent multiple finish listings? YES, explicitly observed in TCGdex evidence for some cards.", "16. Strongest finish source? TCGdex `variants` + `variants_detailed`, cross-checked locally where possible.", "17. Strongest numbered-card source? Official Pokémon checklist.", "18. Alternate arts safely different numbers? YES, 166–207 are separate official numbers.", "19. Uniqueness rule? game + set + collector_number for numbered printing; finish/treatment/product remain separate dimensions.", f"20. Evidence sufficient to start POKEMON-151-001? {'YES' if ready else 'NO'} — all source-backed rows and statuses are generated; unresolved/ambiguous mappings remain blockers for any import.", "", "Ready for POKEMON-151-001:", f"{'YES' if ready else 'NO'}", "", "Blocking issues:", f"- {status_counts['AMBIGUOUS']} ambiguous and {status_counts['UNRESOLVED']} unresolved Cardmarket mappings require explicit review before import.", f"- Pokémon TCG API status: {statuses.get('pokemon_tcg_api')}; non-blocking by contract.", "- No DB/catalog/import/pricing change was performed.", "", "Source identifiers:", f"- TCGdex: `{tcgdex_set_id}`", f"- Pokémon TCG API: `{api_set_id}`", f"- Local Cardmarket expansion: `{expansion_id}`", "", "DB modified: NO", "Pricing applied: NO", "POKEMON-151-001 executed: NO",
    ]
    (output / "10_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    manifest_path = output / "source_manifest.json"
    manifest_path.write_text(json.dumps({"sources": sorted(manifest, key=lambda item: (item["source"], item["source_identifier"])), "statuses": dict(sorted(statuses.items()))}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--products", type=Path, required=True)
    parser.add_argument("--prices", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--refresh-sources", action="store_true")
    parser.add_argument("--skip-pokemon-tcg-api", action="store_true")
    parser.add_argument("--official-checklist-url", default=OFFICIAL_URL)
    parser.add_argument("--official-checklist-file", type=Path)
    parser.add_argument("--expansion-id", type=int, default=5328)
    parser.add_argument("--tcgdex-set-id", default="sv03.5")
    parser.add_argument("--pokemon-tcg-set-id", default="sv3pt5")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.products.exists() or not args.prices.exists():
        raise AuditError("Los archivos Cardmarket indicados no existen")
    _, products = load_snapshot(args.products, "products")
    _, prices = load_snapshot(args.prices, "priceGuides")
    selected = [row for row in products if row.get("idExpansion") == args.expansion_id]
    if not selected:
        raise AuditError(f"No hay productos locales para idExpansion={args.expansion_id}")
    if len(selected) != 210:
        raise AuditError(f"El alcance esperado de POKEMON-151-000B es 210 productos; se encontraron {len(selected)}")
    set_data, tcgdex, api, manifest, statuses = load_external_sources(args.cache_dir, args.tcgdex_set_id, args.pokemon_tcg_set_id, args.refresh_sources, args.skip_pokemon_tcg_api, args.official_checklist_url, args.official_checklist_file)
    official_pdf = args.cache_dir / "official" / "mew_web_cardlist_en.pdf"
    official, _ = read_official_pdf(official_pdf)
    official_data = official_rows(official, tcgdex, api, args.tcgdex_set_id)
    local_ids = {row.get("idProduct") for row in selected}
    variants = variant_rows(official_data, tcgdex, local_ids)
    direct_variants, _ = source_cardmarket_variants(tcgdex)
    mapping = mapping_rows(selected, official_data, tcgdex, direct_variants, price_index(prices), args.expansion_id)
    extras = extras_rows(mapping, official_data)
    metacards = metacard_rows(mapping)
    coverage = metadata_coverage(official_data, mapping, variants, statuses)
    ambiguous = ambiguous_rows(mapping)
    render_reports(args.output, official, official_data, variants, mapping, extras, metacards, coverage, ambiguous, manifest, statuses, args.products, args.prices, args.expansion_id, args.tcgdex_set_id, args.pokemon_tcg_set_id)
    print(f"POKEMON-151-000B completed: {len(official_data)}/207 official rows, {len(mapping)}/210 Cardmarket rows, {len(variants)} variant rows")
    print(f"Reports: {args.output}")
    print(f"DB modified: NO; pricing applied: NO; POKEMON-151-001 executed: NO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AuditError as exc:
        print(f"AUDIT ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
