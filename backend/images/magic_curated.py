"""Resolve curated English Magic printings to exact Scryfall images.

Requests use Scryfall's set/collector/language route. Only remote URLs and source
metadata are stored; image files are never downloaded.
"""
from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from backend.images.resolver import ImageResolution, resolve_scryfall_card
from backend.integrations.scryfall.client import ScryfallClient

DB_PATH=ROOT/"backend/db/tcg_dashboard.db"
CSV_PATH=ROOT/"CARDMADNESS_HOB_HOC.csv"
COURTESY_DELAY=0.15
CACHE_DIR:Path|None=None


def normalize_collector_number(value:str)->str:
    value=value.strip()
    return str(int(value)) if value.isdigit() else value.casefold()


@dataclass
class PrintingResult:
    set_code: str
    card_number: str
    treatment: str
    card_id: int | None
    status: str
    scryfall_id: str | None = None
    reason: str | None = None
    faces: int = 0


@dataclass
class Report:
    checked: dict[str,int]=field(default_factory=lambda:{"hob":0,"hoc":0})
    exact: dict[str,int]=field(default_factory=lambda:{"hob":0,"hoc":0})
    missing: list[PrintingResult]=field(default_factory=list)
    ambiguous: list[PrintingResult]=field(default_factory=list)
    errors: list[PrintingResult]=field(default_factory=list)
    no_op: int=0
    writes: int=0
    requests: int=0
    results: list[PrintingResult]=field(default_factory=list)


def load_targets(csv_path:Path) -> list[tuple[str,str,str]]:
    targets=[]
    with csv_path.open(encoding="utf-8-sig",newline="") as f:
        for row in csv.DictReader(f,delimiter=";"):
            code=row["Set"].strip().lower()
            targets.append((code,row["Base #"].strip(),"traditional_foil"))
            if row["Surge #"].strip(): targets.append((code,row["Surge #"].strip(),"surge_foil"))
    return targets


def exact_card(conn:sqlite3.Connection, code:str, number:str, treatment:str)->sqlite3.Row|None:
    rows=conn.execute("""SELECT c.*,l.code language_code,s.code authoritative_set
      FROM cards c JOIN languages l ON l.id=c.language_id JOIN sets s ON s.id=c.set_id
      WHERE c.game_id=(SELECT id FROM games WHERE code='magic')
        AND lower(c.set_code)=? AND lower(s.code)=? AND c.card_number=?
        AND l.code='en' AND c.finish='foil' AND c.treatment=?
        AND c.catalog_source='cardmadness_curated' AND c.catalog_status='active'""",
      (code,code,number,treatment)).fetchall()
    return rows[0] if len(rows)==1 else None


def fetch_card(code:str,number:str)->tuple[dict|None,str|None]:
    request_number=number.lstrip("0") or "0"
    cache_path=CACHE_DIR/f"{code}-{request_number}-en.json" if CACHE_DIR else None
    if cache_path and cache_path.exists():
        cached=json.loads(cache_path.read_text(encoding="utf-8"))
        return cached.get("data"),cached.get("error")
    request=ScryfallClient().card_by_set_number_request(code,request_number,"en")
    try:
        with urllib.request.urlopen(request,timeout=15) as response:
            result=json.loads(response.read())
            if cache_path:
                cache_path.parent.mkdir(parents=True,exist_ok=True); cache_path.write_text(json.dumps({"data":result}),encoding="utf-8")
            return result,None
    except urllib.error.HTTPError as exc:
        error=f"HTTP {exc.code}"
        if cache_path:
            cache_path.parent.mkdir(parents=True,exist_ok=True); cache_path.write_text(json.dumps({"data":None,"error":error}),encoding="utf-8")
        return None,error
    except (urllib.error.URLError,OSError,TimeoutError) as exc:
        error=f"network error: {exc}"
        if cache_path:
            cache_path.parent.mkdir(parents=True,exist_ok=True); cache_path.write_text(json.dumps({"data":None,"error":error}),encoding="utf-8")
        return None,error
    except json.JSONDecodeError as exc:
        error=f"invalid JSON: {exc}"
        if cache_path:
            cache_path.parent.mkdir(parents=True,exist_ok=True); cache_path.write_text(json.dumps({"data":None,"error":error}),encoding="utf-8")
        return None,error


def validate_identity(data:dict,code:str,number:str,treatment:str)->str|None:
    if str(data.get("set","")).lower()!=code: return "set mismatch"
    source_number=str(data.get("collector_number","")).strip()
    if normalize_collector_number(source_number)!=normalize_collector_number(number):
        return "collector number mismatch"
    if str(data.get("lang","")).lower()!="en": return "language mismatch"
    is_surge="surgefoil" in {str(x).lower() for x in data.get("promo_types") or []}
    if treatment=="surge_foil" and not is_surge: return "Scryfall record is not Surge Foil"
    if treatment=="traditional_foil" and is_surge: return "Scryfall record is Surge Foil"
    return None


def image_rows(resolution:ImageResolution,card_id:int,code:str,number:str,treatment:str,checked_at:str):
    for face in resolution.faces:
        yield (card_id,"scryfall",resolution.source_card_id,treatment,number,"en",face.face_index,
               face.small_url,face.large_url,"en",0,"exact","resolved")


def persist(conn:sqlite3.Connection,card:sqlite3.Row,data:dict|None,resolution:ImageResolution|None,
            code:str,number:str,treatment:str,checked_at:str)->tuple[str,int]:
    card_id=card["id"]
    source_id=(data or {}).get("id")
    if source_id:
        owner=conn.execute("SELECT id FROM cards WHERE scryfall_id=? AND id<>? AND language_id=? AND finish='foil'",
                           (source_id,card_id,card["language_id"])).fetchone()
        if owner: return "conflict",0
        if card["scryfall_id"] not in (None,source_id): return "conflict",0
        if card["scryfall_id"] is None:
            conn.execute("UPDATE cards SET scryfall_id=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(source_id,card_id))
    source_number=str((data or {}).get("collector_number") or number)
    rows=list(image_rows(resolution,card_id,code,source_number,treatment,checked_at)) if resolution and resolution.status=="resolved" else []
    if not rows:
        rows=[(card_id,"scryfall",source_id,treatment,source_number,"en",0,None,None,"en",0,"exact","missing")]
    writes=0
    for values in rows:
        old=conn.execute("""SELECT source_card_id,source_variant,source_collector_number,language,face_index,
          image_url_small,image_url_large,image_language_scope,is_language_fallback,match_quality,status
          FROM card_images WHERE card_id=? AND source='scryfall' AND language='en' AND face_index=?""",
          (card_id,values[6])).fetchone()
        expected=values[2:13]
        if old and tuple(old)==expected: continue
        if old and (old[0] not in (None,source_id) or (old[2] is not None and normalize_collector_number(old[2]) != normalize_collector_number(source_number))):
            return "conflict",writes
        conn.execute("""INSERT INTO card_images(card_id,source,source_card_id,source_variant,source_collector_number,
          language,face_index,image_url_small,image_url_large,image_language_scope,is_language_fallback,
          match_quality,status,last_checked_at,updated_at)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
          ON CONFLICT(card_id,source,language,face_index) DO UPDATE SET
            source_card_id=excluded.source_card_id,source_variant=excluded.source_variant,
            source_collector_number=excluded.source_collector_number,image_url_small=excluded.image_url_small,
            image_url_large=excluded.image_url_large,image_language_scope=excluded.image_language_scope,
            is_language_fallback=excluded.is_language_fallback,match_quality=excluded.match_quality,
            status=excluded.status,last_checked_at=excluded.last_checked_at,updated_at=excluded.updated_at""",
          (*values,checked_at,checked_at))
        writes+=1
    return ("exact" if rows[0][12]=="resolved" else "missing"),writes


def resolve(db_path:Path=DB_PATH,csv_path:Path=CSV_PATH,apply:bool=False,
            fetcher=fetch_card,delay:float=COURTESY_DELAY)->Report:
    conn=sqlite3.connect(db_path); conn.row_factory=sqlite3.Row
    report=Report(); client=ScryfallClient(); checked_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    try:
        if apply: conn.execute("BEGIN IMMEDIATE")
        for index,(code,number,treatment) in enumerate(load_targets(csv_path)):
            report.checked[code]+=1
            card=exact_card(conn,code,number,treatment)
            if card is None:
                result=PrintingResult(code,number,treatment,None,"ambiguous",reason="DB exact printing lookup was not unique")
                report.ambiguous.append(result); report.results.append(result); continue
            existing=conn.execute("""SELECT source_card_id,source_collector_number,source_variant,match_quality,status,
              image_url_small,image_url_large FROM card_images WHERE card_id=? AND source='scryfall' AND language='en' AND face_index=0""",(card["id"],)).fetchone()
            if existing and card["scryfall_id"]==existing[0] and existing[1] is not None and normalize_collector_number(existing[1])==normalize_collector_number(number) and existing[2]==treatment and existing[3]=="exact" and existing[4]=="resolved" and (existing[5] or existing[6]):
                report.no_op+=1; report.exact[code]+=1
                result=PrintingResult(code,number,treatment,card["id"],"exact",card["scryfall_id"],faces=1)
                report.results.append(result); continue
            if report.requests and delay: time.sleep(delay)
            data,error=fetcher(code,number); report.requests+=1
            reason=error or (validate_identity(data,code,number,treatment) if data else "no Scryfall record")
            resolution=resolve_scryfall_card(data) if data and not reason else None
            if resolution and resolution.status!="resolved": reason=resolution.reason or resolution.status
            if reason:
                result=PrintingResult(code,number,treatment,card["id"],"missing",(data or {}).get("id"),reason)
                report.missing.append(result)
                if apply:
                    validated=data is not None and validate_identity(data,code,number,treatment) is None
                    outcome,writes=persist(conn,card,data if validated else None,None,code,number,treatment,checked_at)
                    report.writes+=writes
                    if outcome=="conflict":
                        result.status="ambiguous"; result.reason="existing Scryfall identity/image conflicts with exact lookup"
                        report.missing.remove(result); report.ambiguous.append(result)
                report.results.append(result); continue
            if not resolution or resolution.match_quality!="exact" or resolution.language!="en":
                result=PrintingResult(code,number,treatment,card["id"],"ambiguous",(data or {}).get("id"),"resolver did not confirm exact English image")
                report.ambiguous.append(result); report.results.append(result); continue
            result=PrintingResult(code,number,treatment,card["id"],"exact",resolution.source_card_id,faces=len(resolution.faces))
            if apply:
                outcome,writes=persist(conn,card,data,resolution,code,number,treatment,checked_at)
                report.writes+=writes
                if outcome=="conflict":
                    result.status="ambiguous"; result.reason="existing Scryfall identity/image conflicts with exact lookup"
                    report.ambiguous.append(result)
                else: report.exact[code]+=1
            else: report.exact[code]+=1
            report.results.append(result)
        if apply: conn.commit()
        return report
    except Exception:
        if apply: conn.rollback()
        raise
    finally: conn.close()


def main()->None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db",type=Path,default=DB_PATH); parser.add_argument("--csv",type=Path,default=CSV_PATH)
    parser.add_argument("--apply",action="store_true"); parser.add_argument("--delay",type=float,default=COURTESY_DELAY)
    parser.add_argument("--cache-dir",type=Path)
    parser.add_argument("--report",type=Path)
    args=parser.parse_args()
    global CACHE_DIR
    CACHE_DIR=args.cache_dir
    report=resolve(args.db,args.csv,args.apply,delay=max(0,args.delay))
    payload=asdict(report); payload.pop("results")
    payload["unresolved"]=[asdict(x) for x in report.missing+report.ambiguous+report.errors]
    rendered=json.dumps(payload,indent=2,ensure_ascii=False)
    print(rendered)
    if args.report: args.report.write_text(rendered+"\n",encoding="utf-8")

if __name__=="__main__": main()
