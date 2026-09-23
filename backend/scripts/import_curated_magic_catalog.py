"""Import an explicitly curated Magic CSV and its manual price observations."""
from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CSV = ROOT / "CARDMADNESS_HOB_HOC.csv"
SETS = {"HOB": "The Hobbit", "HOC": "The Hobbit Commander"}
SNAPSHOT = "cardmadness-2026-09-23"


def parse_price(raw: str) -> float | None:
    value = raw.strip()
    return None if not value else float(value.replace(".", "").replace(",", "."))


def ensure_event_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS events (
      id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
      starts_at TEXT, ends_at TEXT, status TEXT NOT NULL DEFAULT 'planned',
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS event_wishlist_items (
      event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
      wishlist_item_id INTEGER NOT NULL REFERENCES wishlist_items(id) ON DELETE CASCADE,
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE(event_id,wishlist_item_id)
    );
    INSERT OR IGNORE INTO events(code,name) VALUES ('cardmadness-2026','CARDMADNESS EVENT');
    """)


def ensure_expansion_id_nullable(conn: sqlite3.Connection) -> None:
    info={r[1]:r for r in conn.execute("PRAGMA table_info(expansions)")}
    if not info or not info["cardmarket_id_expansion"][3]: return
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.executescript("""
      CREATE TABLE expansions_nullable_cm (
        id INTEGER PRIMARY KEY AUTOINCREMENT, game_id INTEGER NOT NULL REFERENCES games(id),
        cardmarket_id_expansion INTEGER UNIQUE, name TEXT, set_code TEXT, release_date TEXT,
        set_id INTEGER REFERENCES sets(id));
      INSERT INTO expansions_nullable_cm SELECT * FROM expansions;
      DROP TABLE expansions;
      ALTER TABLE expansions_nullable_cm RENAME TO expansions;
    """)
    conn.execute("PRAGMA foreign_keys=ON")


def import_csv(db_path: Path, csv_path: Path, apply: bool) -> dict:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    report = {"inserted": 0, "updated": 0, "no_op": 0, "conflicts": [], "observations_inserted": 0,
              "observations_no_op": 0, "logical": {}, "printings": 0}
    try:
        rows = list(csv.DictReader(csv_path.open(encoding="utf-8-sig", newline=""), delimiter=";"))
        if len(rows) != 116 or sum(r["Set"] == "HOB" for r in rows) != 50 or sum(r["Set"] == "HOC" for r in rows) != 66:
            raise ValueError("CSV selection count does not match approved 50 HOB / 66 HOC contract")
        ctx = conn if apply else sqlite3.connect(":memory:")
        if not apply:
            conn.backup(ctx)
            ctx.row_factory = sqlite3.Row
        ctx.execute("PRAGMA foreign_keys=ON")
        ensure_expansion_id_nullable(ctx)
        if apply:
            ctx.execute("BEGIN IMMEDIATE")
        ensure_event_tables(ctx)
        game_id = ctx.execute("SELECT id FROM games WHERE code='magic'").fetchone()[0]
        lang_id = ctx.execute("SELECT id FROM languages WHERE code='en'").fetchone()[0]
        set_ids, expansion_ids = {}, {}
        for code, name in SETS.items():
            row = ctx.execute("SELECT id FROM sets WHERE game_id=? AND lower(code)=lower(?)", (game_id, code)).fetchone()
            if row:
                set_ids[code] = row[0]
            else:
                cur = ctx.execute("INSERT INTO sets(game_id,code,name) VALUES(?,?,?)", (game_id,code.lower(),name))
                set_ids[code] = cur.lastrowid
            ex = ctx.execute("SELECT id FROM expansions WHERE game_id=? AND lower(set_code)=lower(?)",(game_id,code)).fetchone()
            if ex:
                expansion_ids[code] = ex[0]
            else:
                cur = ctx.execute("INSERT INTO expansions(game_id,cardmarket_id_expansion,name,set_code,set_id) VALUES(?,NULL,?,?,?)",(game_id,name,code.lower(),set_ids[code]))
                expansion_ids[code] = cur.lastrowid
        for row in rows:
            code, base, name = row["Set"], row["Base #"].strip(), row["Carta"].strip()
            canon_key = f"curated:{code.lower()}:{base}"
            existing = ctx.execute("SELECT id,name FROM canonical_cards WHERE game_id=? AND identity_key=?",(game_id,canon_key)).fetchone()
            if existing:
                canonical_id = existing[0]
                if existing[1] != name:
                    report["conflicts"].append(f"canonical name conflict {code} #{base}: {existing[1]} / {name}")
                    continue
                report["no_op"] += 1
            else:
                cur=ctx.execute("INSERT INTO canonical_cards(game_id,identity_key,canonical_number,name,normalized_name,metadata) VALUES(?,?,?,?,?,?)",
                    (game_id,canon_key,base,name,name.casefold(),json.dumps({"source":"CARDMADNESS_HOB_HOC.csv","set":code},ensure_ascii=False)))
                canonical_id=cur.lastrowid
                report["inserted"] += 1
            printing_ids = {}
            variants=[(base,"traditional_foil","normal")]
            surge=row["Surge #"].strip()
            if surge: variants.append((surge,"surge_foil","confirmed_parallel"))
            for number,treatment,printing_variant in variants:
                found=ctx.execute("SELECT id,treatment,canonical_card_id,name FROM cards WHERE game_id=? AND lower(set_code)=lower(?) AND card_number=? AND language_id=? AND finish='foil'",(game_id,code.lower(),number,lang_id)).fetchone()
                if found:
                    if found[1] != treatment or found[2] != canonical_id or found[3] != name:
                        report["conflicts"].append(f"printing conflict {code} #{number} ({treatment})")
                        continue
                    card_id=found[0]
                    report["no_op"] += 1
                else:
                    cur=ctx.execute("""INSERT INTO cards(game_id,expansion_id,card_number,name,printing_variant,variant_label,
                      data_source,set_code,normalized_name,finish,treatment,language_id,canonical_card_id,set_id,
                      release_kind,art_kind,catalog_status,catalog_source)
                      VALUES(?,?,?,?,?,NULL,'manual',?,?, 'foil',?,?,?,?,'special','parallel','active','cardmadness_curated')""",
                      (game_id,expansion_ids[code],number,name,printing_variant,code.lower(),name.casefold(),treatment,lang_id,canonical_id,set_ids[code]))
                    card_id=cur.lastrowid
                    report["inserted"] += 1
                printing_ids[treatment]=card_id
                report["printings"] += 1
            metrics=[]
            if surge and printing_ids.get("surge_foil"):
                metrics.extend(((printing_ids["surge_foil"],"low",row["Surge Low €"],"surge_foil",surge),
                                (printing_ids["surge_foil"],"avg30",row["Surge Avg 30d €"],"surge_foil",surge)))
            if printing_ids.get("traditional_foil"):
                metrics.append((printing_ids["traditional_foil"],"low",row["Traditional Foil Low €"],"traditional_foil",base))
            for card_id,metric,raw,treatment,number in metrics:
                value=parse_price(raw)
                if value is None: continue
                provenance=json.dumps({"file":csv_path.name,"set":code,"collector_number":number,"treatment":treatment,"snapshot_date":"2026-09-23"},ensure_ascii=False,separators=(",",":"))
                old=ctx.execute("SELECT value,provenance FROM market_price_observations WHERE card_id=? AND provider='cardmarket_manual' AND market='cardmarket' AND metric=? AND currency='EUR' AND snapshot_key=?",(card_id,metric,SNAPSHOT)).fetchone()
                if old:
                    if old[0] == value and old[1] == provenance: report["observations_no_op"] += 1
                    else:
                        ctx.execute("UPDATE market_price_observations SET value=?,observed_at='2026-09-23',provenance=? WHERE card_id=? AND provider='cardmarket_manual' AND market='cardmarket' AND metric=? AND currency='EUR' AND snapshot_key=?",(value,provenance,card_id,metric,SNAPSHOT))
                        report["updated"] += 1
                else:
                    ctx.execute("INSERT INTO market_price_observations(card_id,provider,market,metric,value,currency,observed_at,snapshot_key,provenance) VALUES(?,'cardmarket_manual','cardmarket',?,?,'EUR','2026-09-23',?,?)",(card_id,metric,value,SNAPSHOT,provenance))
                    report["observations_inserted"] += 1
        if report["conflicts"]: raise ValueError("conflicts: " + "; ".join(report["conflicts"]))
        if apply: conn.commit()
        else: ctx.close()
        report["logical"]={code:sum(r["Set"]==code for r in rows) for code in SETS}
        return report
    except Exception:
        if apply: conn.rollback()
        raise
    finally: conn.close()


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db",type=Path,default=ROOT/"backend/db/tcg_dashboard.db")
    parser.add_argument("--csv",type=Path,default=DEFAULT_CSV)
    parser.add_argument("--apply",action="store_true")
    args=parser.parse_args()
    print(json.dumps(import_csv(args.db,args.csv,args.apply),indent=2))

if __name__ == "__main__": main()
