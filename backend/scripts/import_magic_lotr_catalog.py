"""Import the physical Magic LOTR catalog from Scryfall.

The default mode is a dry run.  Live network access is opt-in with ``--live``;
fixtures and cached search pages are preferred for repeatable runs and tests.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import unicodedata


DB_PATH = Path(__file__).resolve().parent.parent / "db" / "tcg_dashboard.db"
SCRYFALL_SEARCH_URL = "https://api.scryfall.com/cards/search"
USER_AGENT = "TCG-Dashboard/1.0 (+local catalog maintenance)"
COURTESY_DELAY_SECONDS = 0.12
MAX_PAGES = 20
MAX_HTTP_RETRIES = 2
SUPPORTED_SETS = ("ltr", "ltc")
SUPPORTED_FINISHES = {"nonfoil", "foil", "etched"}
CANONICAL_EXPANSION_IDS = {"ltr": 5285, "ltc": 5387}


@dataclass
class SetReport:
    fetched_pages: int = 0
    fetched_records: int = 0
    rejected_non_physical: int = 0
    rejected_reasons: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    accepted_printings: int = 0
    expanded_finishes: int = 0
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    ambiguous: list[str] = field(default_factory=list)


@dataclass
class ImportReport:
    by_set: dict[str, SetReport] = field(default_factory=lambda: {code: SetReport() for code in SUPPORTED_SETS})

    def print_summary(self) -> None:
        print("Magic LOTR catalog import completed")
        for code in SUPPORTED_SETS:
            item = self.by_set[code]
            print(f"\nSet {code.upper()}:")
            print(f"- fetched pages: {item.fetched_pages}")
            print(f"- fetched records: {item.fetched_records}")
            print(f"- rejected non-physical: {item.rejected_non_physical}")
            print(f"- accepted printings: {item.accepted_printings}")
            print(f"- expanded finishes: {item.expanded_finishes}")
            print(f"- inserted: {item.inserted}")
            print(f"- updated: {item.updated}")
            print(f"- skipped: {item.skipped}")
            print(f"- ambiguous: {len(item.ambiguous)}")
            for reason, count in sorted(item.rejected_reasons.items()):
                print(f"  - rejected {reason}: {count}")
        total = sum(
            self.by_set[code].inserted + self.by_set[code].updated
            for code in SUPPORTED_SETS
        )
        print(f"\nTotal catalog records written/updated: {total}")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char)).casefold().strip()


def collector_number_value(value: str) -> int | None:
    try:
        return int(value.split("/")[0])
    except (AttributeError, ValueError):
        return None


def treatment_for(record: dict, set_code: str) -> str | None:
    number = collector_number_value(record.get("collector_number", ""))
    if number is not None and 399 <= number <= 451:
        return "Scene"
    if set_code == "ltc" and number is not None and 348 <= number <= 377:
        return "Realms & Relics"

    promo_types = {str(value).casefold() for value in record.get("promo_types", [])}
    frame_effects = {str(value).casefold() for value in record.get("frame_effects", [])}
    if "surgefoil" in promo_types:
        return "Surge Foil"
    if "prerelease" in promo_types:
        return "Prerelease"
    if "showcase" in frame_effects:
        return "Showcase"
    if record.get("border_color") == "borderless":
        return "Borderless"
    if "extendedart" in frame_effects:
        return "Extended Art"
    return None


def non_physical_reason(record: dict, set_code: str) -> str | None:
    if str(record.get("set", "")).casefold() != set_code:
        return "wrong_set"
    if record.get("digital") is True or "paper" not in record.get("games", []):
        return "digital_or_non_paper"
    if record.get("layout") == "token":
        return "token"
    if record.get("oversized") is True:
        return "oversized"
    if str(record.get("name", "")).casefold().startswith("art series"):
        return "art_series"
    promo_types = {str(value).casefold() for value in record.get("promo_types", [])}
    if promo_types.intersection({"alchemy", "rebalanced"}):
        return "digital_promo"
    if not isinstance(record.get("finishes"), list) or not record["finishes"]:
        return "no_real_finish"
    if not any(finish in SUPPORTED_FINISHES for finish in record["finishes"]):
        return "unsupported_finish"
    return None


def _json_objects(path: Path) -> list[dict]:
    data = json.loads(path.read_text())
    if isinstance(data, dict) and "pages" in data:
        pages = data["pages"]
    elif isinstance(data, dict) and set(data).intersection(SUPPORTED_SETS):
        pages = data
    else:
        pages = [data]
    if isinstance(pages, dict):
        pages = pages.values()
    records: list[dict] = []
    for page in pages:
        if isinstance(page, dict) and isinstance(page.get("data"), list):
            records.extend(page["data"])
        elif isinstance(page, dict) and page.get("object") == "card":
            records.append(page)
    return records


def load_fixture(path: Path, set_code: str) -> list[dict]:
    data = json.loads(path.read_text())
    if isinstance(data, dict) and set_code in data:
        data = data[set_code]
    if isinstance(data, dict) and "pages" in data:
        data = data["pages"]
    pages = data if isinstance(data, list) else [data]
    records: list[dict] = []
    for page in pages:
        if isinstance(page, dict) and isinstance(page.get("data"), list):
            records.extend(page["data"])
        elif isinstance(page, dict) and page.get("object") == "card":
            records.append(page)
    return records


def cached_records(cache_dir: Path, set_code: str) -> list[dict] | None:
    files = sorted(cache_dir.glob(f"{set_code}-*.json"))
    if not files:
        return None
    records: list[dict] = []
    for path in files:
        records.extend(_json_objects(path))
    return records


def fetch_json(url: str) -> dict:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    for attempt in range(MAX_HTTP_RETRIES + 1):
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code == 429 or 500 <= exc.code < 600:
                if attempt >= MAX_HTTP_RETRIES:
                    raise
                retry_after = exc.headers.get("Retry-After")
                delay = min(float(retry_after), 30.0) if retry_after else (attempt + 1) * 2.0
                time.sleep(delay)
                continue
            raise


def fetch_records(
    set_code: str,
    fixture: Path | None,
    cache_dir: Path | None,
    live: bool,
    refresh_cache: bool,
    max_pages: int,
    report: SetReport,
) -> list[dict]:
    if fixture is not None:
        records = load_fixture(fixture, set_code)
        report.fetched_pages = 1
        report.fetched_records = len(records)
        return records
    if cache_dir is not None and not refresh_cache:
        records = cached_records(cache_dir, set_code)
        if records is not None:
            report.fetched_pages = len(list(cache_dir.glob(f"{set_code}-*.json")))
            report.fetched_records = len(records)
            return records
    if not live:
        raise RuntimeError(f"no fixture/cache for {set_code}; pass --live explicitly")

    params = urllib.parse.urlencode({
        "include_extras": "true",
        "include_variations": "true",
        "order": "set",
        "q": f"e:{set_code}",
        "unique": "prints",
    })
    url = f"{SCRYFALL_SEARCH_URL}?{params}"
    records: list[dict] = []
    page_number = 0
    while url:
        page_number += 1
        if page_number > max_pages:
            raise RuntimeError(f"max pages exceeded for {set_code}: {max_pages}")
        if page_number > 1:
            time.sleep(COURTESY_DELAY_SECONDS)
        page = fetch_json(url)
        report.fetched_pages += 1
        page_records = page.get("data", [])
        report.fetched_records += len(page_records)
        records.extend(page_records)
        if cache_dir is not None:
            cache_dir.mkdir(parents=True, exist_ok=True)
            (cache_dir / f"{set_code}-{page_number:03d}.json").write_text(
                json.dumps(page, ensure_ascii=False, indent=2) + "\n"
            )
        url = page.get("next_page") if page.get("has_more") else None
    return records


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def expansion_id(conn: sqlite3.Connection, set_code: str, apply: bool) -> int | None:
    row = conn.execute(
        """SELECT id FROM expansions
           WHERE game_id = 3 AND lower(set_code) = ?
           ORDER BY id LIMIT 1""",
        (set_code,),
    ).fetchone()
    if row:
        return row[0]
    if not apply:
        return None
    cur = conn.execute(
        """INSERT INTO expansions (game_id, cardmarket_id_expansion, name, set_code)
           VALUES (3, ?, ?, ?)""",
        (
            CANONICAL_EXPANSION_IDS[set_code],
            "The Lord of the Rings: Tales of Middle-earth" if set_code == "ltr" else "Tales of Middle-earth Commander",
            set_code,
        ),
    )
    return cur.lastrowid


def language_id(conn: sqlite3.Connection, code: str, apply: bool) -> int | None:
    row = conn.execute("SELECT id FROM languages WHERE lower(code) = ?", (code,)).fetchone()
    if row:
        return row[0]
    if not apply:
        return None
    cur = conn.execute("INSERT INTO languages (code, name) VALUES (?, ?)", (code, code.title()))
    return cur.lastrowid


def find_existing(
    conn: sqlite3.Connection,
    record: dict,
    set_code: str,
    finish: str,
    lang_id: int,
) -> list[sqlite3.Row]:
    rows = conn.execute(
        """SELECT c.* FROM cards c
           WHERE c.scryfall_id = ? AND c.language_id = ? AND c.finish = ?
           ORDER BY c.id""",
        (record.get("id"), lang_id, finish),
    ).fetchall()
    if rows:
        return rows
    return conn.execute(
        """SELECT c.* FROM cards c
           WHERE c.game_id = 3 AND lower(c.set_code) = ?
             AND c.card_number = ? AND c.language_id = ? AND c.finish = ?
           ORDER BY c.id""",
        (set_code, record.get("collector_number"), lang_id, finish),
    ).fetchall()


def image_faces(record: dict) -> list[tuple[int, str | None, str | None]]:
    faces = record.get("card_faces")
    if isinstance(faces, list) and faces:
        result = []
        for index, face in enumerate(faces):
            uris = face.get("image_uris") or {}
            result.append((index, uris.get("small"), uris.get("large")))
        return result
    uris = record.get("image_uris") or {}
    return [(0, uris.get("small"), uris.get("large"))]


def upsert_card(
    conn: sqlite3.Connection,
    record: dict,
    set_code: str,
    expansion: int,
    lang_id: int,
    finish: str,
    apply: bool,
) -> tuple[str, int | None]:
    now = utc_now()
    treatment = treatment_for(record, set_code)
    raw = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
    matches = find_existing(conn, record, set_code, finish, lang_id)
    if len(matches) > 1:
        return "ambiguous", None
    values = (
        record.get("name", ""),
        normalize_name(record.get("name", "")),
        record.get("rarity"),
        finish,
        treatment,
        lang_id,
        record.get("id"),
        record.get("oracle_id"),
        record.get("cardmarket_id"),
        record.get("image_uris", {}).get("normal") if record.get("image_uris") else None,
        raw,
        set_code,
        now,
    )
    if matches:
        card = matches[0]
        if not apply:
            changed = any(card[column] != value for column, value in zip(
                ("name", "normalized_name", "rarity", "finish", "treatment", "language_id", "scryfall_id", "scryfall_oracle_id", "cardmarket_id_metacard", "image_url", "scryfall_raw", "set_code"),
                values[:12],
            ))
            return ("updated" if changed else "skipped"), card["id"]
        conn.execute(
            """UPDATE cards SET name=?, normalized_name=?, rarity=?, finish=?, treatment=?,
               language_id=?, scryfall_id=?, scryfall_oracle_id=?, cardmarket_id_metacard=?,
               image_url=COALESCE(?, image_url), image_source='scryfall', data_source='scryfall',
               scryfall_raw=?, set_code=?, updated_at=? WHERE id=?""",
            (*values[:12], now, card["id"]),
        )
        return "updated", card["id"]

    if expansion is None:
        return "skipped", None
    if not apply:
        return "inserted", None
    try:
        cur = conn.execute(
            """INSERT INTO cards
               (game_id, expansion_id, card_number, name, printing_variant, variant_label,
                cardmarket_id_metacard, image_url, image_source, data_source, scryfall_raw,
                set_code, normalized_name, rarity, finish, treatment, language_id,
                scryfall_id, scryfall_oracle_id, created_at, updated_at)
               VALUES (3, ?, ?, ?, 'normal', ?, ?, ?, 'scryfall', 'scryfall', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                expansion, record.get("collector_number"), *values[:1], treatment,
                record.get("cardmarket_id"), values[9], raw, set_code, values[1],
                values[2], finish, treatment, lang_id, record.get("id"), record.get("oracle_id"), now, now,
            ),
        )
        return "inserted", cur.lastrowid
    except sqlite3.IntegrityError:
        return "ambiguous", None


def upsert_images(conn: sqlite3.Connection, card_id: int | None, record: dict, lang_code: str, apply: bool) -> None:
    if card_id is None or not apply:
        return
    now = utc_now()
    for face_index, small_url, large_url in image_faces(record):
        if not small_url and not large_url:
            continue
        conn.execute(
            """INSERT INTO card_images
               (card_id, source, source_card_id, language, face_index, image_url_small,
                image_url_large, match_quality, status, last_checked_at, updated_at)
               VALUES (?, 'scryfall', ?, ?, ?, ?, ?, 'exact', 'resolved', ?, ?)
               ON CONFLICT(card_id, source, language, face_index) DO UPDATE SET
                 source_card_id=excluded.source_card_id,
                 image_url_small=excluded.image_url_small,
                 image_url_large=excluded.image_url_large,
                 match_quality=excluded.match_quality,
                 status=excluded.status,
                 last_checked_at=excluded.last_checked_at,
                 updated_at=excluded.updated_at""",
            (card_id, record.get("id"), lang_code, face_index, small_url, large_url, now, now),
        )


def import_catalog(
    db_path: Path,
    fixture: Path | None = None,
    cache_dir: Path | None = None,
    live: bool = False,
    refresh_cache: bool = False,
    apply: bool = False,
    max_pages: int = MAX_PAGES,
) -> ImportReport:
    conn = connect(db_path)
    report = ImportReport()
    try:
        if apply:
            conn.execute("BEGIN")
        for set_code in SUPPORTED_SETS:
            set_report = report.by_set[set_code]
            records = fetch_records(set_code, fixture, cache_dir, live, refresh_cache, max_pages, set_report)
            expansion = expansion_id(conn, set_code, apply)
            for record in records:
                reason = non_physical_reason(record, set_code)
                if reason:
                    set_report.rejected_non_physical += 1
                    set_report.rejected_reasons[reason] += 1
                    continue
                set_report.accepted_printings += 1
                finishes = [finish for finish in record["finishes"] if finish in SUPPORTED_FINISHES]
                if len(finishes) != len(record["finishes"]):
                    set_report.rejected_reasons["unsupported_finish"] += len(record["finishes"]) - len(finishes)
                lang_code = str(record.get("lang", "en")).casefold()
                lang_id = language_id(conn, lang_code, apply)
                if lang_id is None:
                    set_report.skipped += len(finishes)
                    continue
                for finish in finishes:
                    set_report.expanded_finishes += 1
                    outcome, card_id = upsert_card(conn, record, set_code, expansion, lang_id, finish, apply)
                    if outcome == "inserted":
                        set_report.inserted += 1
                    elif outcome == "updated":
                        set_report.updated += 1
                    elif outcome == "ambiguous":
                        set_report.ambiguous.append(f"{record.get('id')}:{finish}")
                    else:
                        set_report.skipped += 1
                    upsert_images(conn, card_id, record, lang_code, apply)
        if apply:
            conn.commit()
        return report
    except Exception:
        if apply:
            conn.rollback()
        raise
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--refresh-cache", action="store_true")
    parser.add_argument("--max-pages", type=int, default=MAX_PAGES)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.apply and args.dry_run:
        parser.error("use either --apply or --dry-run")
    report = import_catalog(
        args.db, args.fixture, args.cache_dir, args.live, args.refresh_cache,
        args.apply, args.max_pages,
    )
    report.print_summary()


if __name__ == "__main__":
    main()
