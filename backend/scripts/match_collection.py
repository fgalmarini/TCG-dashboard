"""Audit and safely backfill Collection printing/finish identity."""
from __future__ import annotations
import argparse, json, sqlite3
from collections import Counter
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from matching import resolve_collection_item

DB_PATH = Path(__file__).resolve().parents[1] / "db" / "tcg_dashboard.db"

def run(db_path: Path, apply: bool) -> dict:
    conn=sqlite3.connect(db_path); conn.row_factory=sqlite3.Row; conn.execute("PRAGMA foreign_keys=ON")
    report=Counter(); details=[]
    try:
        if apply: conn.execute("BEGIN IMMEDIATE")
        rows=conn.execute("SELECT ci.id FROM collection_items ci JOIN cards c ON c.id=ci.card_id JOIN games g ON g.id=c.game_id WHERE g.code='magic'").fetchall()
        for row in rows:
            result=resolve_collection_item(conn,row["id"]); report["total_scanned"]+=1; report[result.status]+=1
            if result.status == "exact":
                report["already_complete"] += 1
                if apply:
                    conn.execute("UPDATE collection_items SET finish=?, treatment=?, match_status='exact', match_quality='exact', match_reason=? WHERE id=?", (result.finish,result.treatment,result.match_reason,row["id"]))
            elif result.status == "ambiguous":
                report["finish_unresolved"] += 1
                details.append({"collection_item_id":row["id"],"reason":result.match_reason,"finish":result.finish})
        if apply: conn.commit()
        return {"metrics":dict(report),"details":details}
    except Exception:
        if apply: conn.rollback()
        raise
    finally: conn.close()

def main():
    p=argparse.ArgumentParser(); p.add_argument("--db",type=Path,default=DB_PATH); g=p.add_mutually_exclusive_group(required=True); g.add_argument("--dry-run",action="store_true"); g.add_argument("--apply",action="store_true"); a=p.parse_args()
    print(json.dumps(run(a.db,a.apply),ensure_ascii=False,indent=2))
if __name__ == "__main__": main()
