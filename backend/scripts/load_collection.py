"""Carga manual de coleccion desde CSV -- Fase 5.

Sprint contract: fase5-alta-manual-coleccion-sprint-contract.md.
Corrida de prueba acotada 2026-08-25 (98 filas, 100% magic, dentro del scope LOTR ya
importado por fase5-scryfall-magic-backfill-sprint-contract.md) -- ver el reporte de
esa sesion para el resultado real. No cierra la Fase 5 completa (falta one_piece,
pokemon, y el flujo --apply-review no se ejercito todavia en esa corrida).

Import strategy (AGENTS.md seccion 24, mismo patron que scryfall_backfill.py): este
script NO reusa backend/importer/db.py via manipulacion de sys.path -- deliberadamente
separado de backend/importer/ (no se toca nada de esa carpeta). Duplica su propio
connect() minimo.

--- Diseno de matching para Magic (seccion 2a del contract) -----------------------
El contract original dice "name + expansion (via set_hint/card_number) + variant",
pero verificar contra la DB real (AGENTS.md seccion 20) antes de escribir el matcher
encontro tres cosas que el contract no anticipaba:

1. `set_hint` (LTR/LTC del CSV) NO alcanza para filtrar a un unico expansion_id: los
   cardmarket_id_expansion 5285 y 5308 comparten el mismo Scryfall set_code 'ltr', y
   5396 tiene set_code 'pltc' (no 'ltc' literal). Como el scope de esta corrida ya
   esta confirmado 100% dentro de las 3 expansiones (5285/5308/5396), el matcher
   busca directamente contra las 3 sin usar set_hint como filtro -- set_hint queda
   como dato informativo en manual_entry_note/reportes, no como WHERE.

2. `card_number` del CSV (formato "<Rareza> <numero con padding>", ej. "U 0812") SI
   resuelve a una unica card cuando existe en la DB (normalizando: sacar la letra +
   ceros a la izquierda), sin necesitar tocar variant_label -- confirmado contra
   varios ejemplos reales antes de codear. Pero el UNIQUE real de `cards` es
   (expansion_id, card_number, printing_variant), no (expansion_id, card_number) --
   una combinacion nombre+card_number puede resolver a 2+ candidatas (mismo problema
   que gold_stamp mas abajo), no asumir que esta rama es inmune.

3. El campo `variant` del CSV (gold_stamp/showcase_foil/borderless/etc.) usa un
   vocabulario totalmente distinto al de `cards.printing_variant`
   (normal/suggested_parallel/confirmed_parallel/other) y `cards.variant_label`
   (texto libre estilo Scryfall). Comparalos literalmente como si fueran el mismo
   vocabulario producia falsos negativos y positivos (ej. "normal" del CSV
   matcheando por card_number a una card con variant_label='Foil' real -- caso
   "Shadowfax, Lord of Horses" en la corrida de prueba). Por eso `variant` nunca se
   usa como filtro de matching -- solo como cross-check informativo en el reporte
   (se loguea si no comparte ninguna palabra clave con el variant_label real, sin
   bloquear el match).

Algoritmo final (una sola regla, sin mecanismos distintos por variante):
  - Base: buscar candidatas por `name` + expansion in scope (probando tambien el
    nombre con prefijo "Art Series: ", que es como el catalogo nombra esos
    productos -- caso gold_stamp). `card_number` NUNCA se usa como filtro
    independiente de `name` -- no es globalmente unico dentro de una expansion, y
    usarlo solo produjo un falso positivo real en la primera corrida de prueba
    (card_number "14" del CSV, numeracion propia de Art Series para "Bilbo, Retired
    Burglar", coincidio por casualidad con el card_number real de "Faramir, Field
    Commander" en el set base -- se inserto el card_id equivocado hasta que se
    detecto y se corrigio antes de dejar la corrida como valida).
  - Si `card_number` viene poblado en el CSV y angosta el conjunto por nombre (algun
    candidato tiene ese card_number): usar el conjunto angostado.
  - Si no angosta nada (card_number vacio en el CSV, o ningun candidato por nombre
    lo tiene -- caso Art Series/gold_stamp, con card_number=NULL en la DB): usar el
    conjunto por nombre sin angostar.
  - 0 candidatas -> alta manual (producto fuera del catalogo importado).
  - 1 candidata -> match directo, manual_entry=false.
  - 2+ candidatas sin senal para desempatar -> cola de revision generica (ver mas
    abajo), NUNCA una alta manual automatica ni una eleccion silenciosa.

--- Cola de revision generica (seccion 3 del contract, generalizada) ---------------
El contract original describe esta cola solo para One Piece `ambiguous`. Decision de
Facundo (sesion 2026-08-25, extiende TCG-DEC-004): generalizarla para cualquier fila
de cualquier juego que resuelva a 2+ candidatas sin senal distintiva -- no es una
arquitectura nueva, es el mismo mecanismo aplicado a un disparador mas amplio. Se
disparo primero con el caso Magic `gold_stamp` (Art Series, expansion 5308): cada
carta Art Series tiene 2 filas identicas en `cards` salvo printing_variant
(normal/suggested_parallel), sin ninguna senal en la DB para saber cual es la version
gold-stamped -- el link de Cardmarket del CSV si lo distingue via su slug de URL,
pero la DB no guarda ninguna columna de URL para resolverlo, y scrapear la pagina de
Cardmarket para inferirlo esta descartado (choca con la regla de no scraping del
proyecto). Facundo completa `chosen_card_id` a mano (puede abrir el cardmarket_link
ya cargado en el CSV para decidir -- verificacion suya, no scraping del sistema).

--- Idempotencia (seccion 4 del contract) ------------------------------------------
collection_items no tiene unique key natural (a proposito -- permite copias
multiples de la misma carta, AGENTS.md seccion 18). Estado local con hash por fila
(game+card_name+variant+set_hint+card_number+quantity+purchase_date) en
.collection_import_state.json (gitignoreado) para no duplicar entre corridas.

Uso:
    python3 backend/scripts/load_collection.py
    python3 backend/scripts/load_collection.py --apply-review
"""

import csv
import hashlib
import json
import sqlite3
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = Path(__file__).resolve().parent.parent / "db" / "tcg_dashboard.db"
INPUT_CSV_PATH = REPO_ROOT / "coleccion-a-cargar.csv"
REVIEW_CSV_PATH = Path(__file__).resolve().parent / "collection-ambiguous-review.csv"
REVIEW_DONE_CSV_PATH = Path(__file__).resolve().parent / "collection-ambiguous-review.done.csv"
STATE_PATH = Path(__file__).resolve().parent / ".collection_import_state.json"

# Mismo scope que scryfall_backfill.py / backend/importer/config.py SCOPE["magic"].
MAGIC_SCOPE_EXPANSIONS = (5285, 5308, 5387, 5396, 5489)

CSV_FIELDS = [
    "game", "card_name", "variant", "set_hint", "card_number", "language", "condition",
    "quantity", "purchase_price", "purchase_date", "status", "cardmarket_link", "notes",
]

REVIEW_FIELDS = [
    "source_row", *CSV_FIELDS,
    "candidate_card_id", "candidate_name", "candidate_card_number",
    "candidate_printing_variant", "candidate_variant_label", "candidate_price_trend",
    "chosen_card_id",
]

VALID_CONDITIONS = {"NM", "EX", "GD", "LP", "PL", "PO"}


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# --- CSV / hashing helpers ----------------------------------------------------------

def normalize_card_number(raw: str) -> str | None:
    """"U 0812" -> "812"; "2.0" -> "2"; "304" -> "304"; "" -> None."""
    raw = (raw or "").strip()
    if not raw:
        return None
    token = raw.split()[-1]
    if token.endswith(".0"):
        token = token[:-2]
    stripped = token.lstrip("0")
    return stripped or "0"


def row_hash(row: dict) -> str:
    key = "|".join(
        (row.get(f) or "").strip()
        for f in ("game", "card_name", "variant", "set_hint", "card_number", "quantity", "purchase_date")
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def load_state() -> set[str]:
    if not STATE_PATH.exists():
        return set()
    return set(json.loads(STATE_PATH.read_text(encoding="utf-8")))


def save_state(hashes: set[str]) -> None:
    STATE_PATH.write_text(json.dumps(sorted(hashes), indent=2), encoding="utf-8")


def read_input_csv() -> list[dict]:
    with INPUT_CSV_PATH.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = [row for row in reader if any((v or "").strip() for v in row.values())]
    return rows


# --- Card matching (Magic) -----------------------------------------------------------

ART_SERIES_PREFIX = "art series: "


def normalize_name(name: str) -> str:
    """casefold + sin diacriticos, para comparar nombres del CSV contra `cards.name`.

    Necesario porque el CSV trae inconsistencias reales de tipeo/acentuacion contra el
    nombre oficial en la DB (verificado en la corrida de prueba: "Nazgul" en el CSV vs
    "Nazgûl" en la DB, "Gandalf The White" vs "Gandalf the White", "King of The
    Oathbrakers" vs "King of the Oathbreakers" -- un match case/acento-sensible mandaba
    estas filas a alta manual como si el producto no existiera en el catalogo, cuando en
    realidad si esta importado). SQLite `COLLATE NOCASE` no alcanza: solo pliega ASCII
    A-Z, no diacriticos (É/E), por eso el indice se arma en Python.
    """
    import unicodedata

    stripped = "".join(c for c in unicodedata.normalize("NFKD", name or "") if not unicodedata.combining(c))
    return stripped.strip().casefold()


@dataclass
class NameIndex:
    """Dos indices separados a proposito (ver match_magic_candidates): `by_name` solo
    tiene cards bajo su propio nombre real; `art_series_alias` solo tiene cards "Art
    Series: X" accesibles bajo la clave corta "x" (sin el prefijo). Mezclarlos en un
    solo indice metia candidatas Art Series irrelevantes en filas que no son
    gold_stamp -- confirmado durante la corrida de prueba, ver el comentario en
    match_magic_candidates."""

    by_name: dict[str, list[tuple]] = field(default_factory=dict)
    art_series_alias: dict[str, list[tuple]] = field(default_factory=dict)


def build_name_index(conn: sqlite3.Connection) -> NameIndex:
    """Arma NameIndex una sola vez por corrida (no una query por fila)."""
    placeholders = ",".join("?" for _ in MAGIC_SCOPE_EXPANSIONS)
    rows = conn.execute(
        f"""SELECT c.id, c.expansion_id, c.card_number, c.printing_variant, c.variant_label, c.name
              FROM cards c JOIN expansions e ON e.id = c.expansion_id
             WHERE e.cardmarket_id_expansion IN ({placeholders})""",
        MAGIC_SCOPE_EXPANSIONS,
    ).fetchall()

    index = NameIndex()
    for card_row in rows:
        key = normalize_name(card_row[5])
        index.by_name.setdefault(key, []).append(card_row)
        if key.startswith(ART_SERIES_PREFIX):
            short_key = key[len(ART_SERIES_PREFIX):]
            index.art_series_alias.setdefault(short_key, []).append(card_row)
    return index


def match_magic_candidates(name_index: NameIndex, row: dict) -> tuple[list[tuple], str]:
    """Devuelve (candidatas, metodo), metodo describe como se llego para el reporte.

    IMPORTANTE: `card_number` nunca se usa como filtro independiente de `name` -- no es
    globalmente unico dentro de una expansion (el card_number de un producto Art Series
    del CSV puede coincidir por casualidad con el card_number REAL de una carta distinta
    del set base, ej. el card_number "14" del CSV para "Bilbo, Retired Burglar"
    (numeracion propia de Art Series) coincide con el card_number real de "Faramir,
    Field Commander" en el set base -- verificado durante la primera corrida de prueba,
    que insertaba el card_id equivocado por esto). El match siempre parte de `name`
    (obligatorio); `card_number`, si viene poblado, solo se usa para ANGOSTAR ese
    resultado cuando efectivamente lo angosta.

    El alias "Art Series: X" -> "x" (NameIndex.art_series_alias) SOLO se suma al
    conjunto de candidatas cuando variant == 'gold_stamp'. Sumarlo para cualquier
    variante metia candidatas Art Series irrelevantes en las colas de revision de
    otras variantes (ej. filas `borderless` mostrando candidatas Art Series que nada
    tienen que ver) -- verificado y corregido en la corrida de prueba 2026-08-25.

    Si `card_number` viene poblado y NO angosta nada dentro de las candidatas:
    - variant == 'gold_stamp' -> se devuelve el conjunto completo sin angostar (es la
      ambiguedad real y esperada de Art Series: sin card_number en la DB para
      desambiguar entre printing_variant normal/suggested_parallel).
    - cualquier otra variante -> candidatas vacias (alta manual). NO se cae al
      conjunto sin angostar -- un card_number presente que no matchea ninguna
      candidata real es señal de que esa impresion puntual no esta en el catalogo
      importado (mismo patron que las promos Holiday Release/Surge Foil, que tienen
      su propio card_number y no existen en absoluto en `cards`), no de que haya que
      adivinar entre las candidatas que sí existen.
    """
    csv_name = (row.get("card_name") or "").strip()
    variant = (row.get("variant") or "").strip()
    key = normalize_name(csv_name)
    is_gold_stamp = variant == "gold_stamp"

    candidates = list(name_index.by_name.get(key, []))
    if is_gold_stamp:
        candidates += name_index.art_series_alias.get(key, [])

    card_number_norm = normalize_card_number(row.get("card_number"))
    if card_number_norm:
        narrowed = [c for c in candidates if c[2] == card_number_norm]
        if narrowed:
            return narrowed, "name+card_number"
        if not is_gold_stamp:
            return [], "name+card_number (sin match -> alta manual, no fallback)"
        return candidates, "name (gold_stamp, card_number no angosto)"

    # LIMITACION CONOCIDA (encontrada en la corrida de prueba 2026-08-25, filas 44/93/94
    # -- "Shortcut to Mushrooms"/"Long List of the Ents"/"The Bath Song"): una misma
    # carta puede tener UN SOLO producto en Cardmarket/`cards` pero representar
    # fisicamente mas de una edicion real -- la impresion base "Extras" y ademas una
    # promo "Holiday Release/Surge Foil" separada que si existe fisicamente (Facundo la
    # tiene) pero nunca se importo al catalogo (no esta ni en cardmarket_products).
    # Cuando la fila del CSV no trae `card_number` (columna vacia, no un intento de
    # match fallido), este fallback no tiene forma de distinguir "la unica card que
    # existe es realmente la correcta" de "la unica card que existe es la base, y la
    # promo que describe esta fila no esta en el catalogo en absoluto" -- ambos casos
    # se ven identicos aca (nombre matchea, 1 sola candidata, se acepta como match
    # directo). Si el CSV vuelve a traer filas de edicion promocional sin card_number
    # (Holiday Release, Surge Foil, u otra coleccion especial de Cardmarket detectable
    # por notes/cardmarket_link), van a matchear "bien" a la carta base equivocada sin
    # que nada lo marque -- requiere revision manual puntual, no asumir que "matcheo a
    # 1 candidata" alcanza. La solucion de fondo es pedir `card_number` siempre que se
    # pueda para esas filas (no un heuristico nuevo aca que adivine por texto libre).
    return candidates, "name"


def variant_cross_check(csv_variant: str, variant_label: str | None) -> str | None:
    """Chequeo informativo, nunca bloquea el match (vocabularios distintos, ver docstring)."""
    csv_variant = (csv_variant or "").strip()
    if not csv_variant:
        return None
    keywords = [w for w in csv_variant.split("_") if w]
    label = (variant_label or "")
    if not any(kw.lower() in label.lower() for kw in keywords):
        return (
            f"variant CSV={csv_variant!r} no comparte palabra clave con "
            f"variant_label DB={label!r}"
        )
    return None


def resolve_cardmarket_product_id(conn: sqlite3.Connection, card_id: int) -> int | None:
    row = conn.execute(
        "SELECT cardmarket_product_id FROM cardmarket_product_mappings WHERE card_id = ? AND status = 'mapped'",
        (card_id,),
    ).fetchone()
    return row[0] if row else None


def resolve_price_trend(conn: sqlite3.Connection, card_id: int) -> float | None:
    row = conn.execute(
        """SELECT h.trend
             FROM market_price_history h
             JOIN cardmarket_product_mappings m ON m.cardmarket_product_id = h.cardmarket_product_id
            WHERE m.card_id = ? AND m.status = 'mapped'
            ORDER BY h.observed_at DESC LIMIT 1""",
        (card_id,),
    ).fetchone()
    return row[0] if row else None


def resolve_language_id(conn: sqlite3.Connection, code: str) -> int:
    code = (code or "en").strip() or "en"
    row = conn.execute("SELECT id FROM languages WHERE code = ?", (code,)).fetchone()
    return row[0] if row else 1


# --- Insertion -------------------------------------------------------------------

def build_manual_entry_note(reason: str, row: dict) -> str:
    parts = [reason]
    notes = (row.get("notes") or "").strip()
    if notes:
        parts.append(notes)
    link = (row.get("cardmarket_link") or "").strip()
    if link:
        parts.append(f"link: {link}")
    return " | ".join(parts)


def insert_collection_item(
    conn: sqlite3.Connection,
    row: dict,
    card_id: int | None,
    cardmarket_product_id: int | None,
    manual_entry: bool,
    manual_entry_note: str | None,
) -> None:
    condition = (row.get("condition") or "").strip() or None
    if condition and condition not in VALID_CONDITIONS:
        condition = None
    quantity_raw = (row.get("quantity") or "").strip()
    quantity = int(float(quantity_raw)) if quantity_raw else 1
    price_raw = (row.get("purchase_price") or "").strip()
    purchase_price = float(price_raw) if price_raw else None
    purchase_date = (row.get("purchase_date") or "").strip() or None
    status = (row.get("status") or "KEEP").strip() or "KEEP"
    notes = (row.get("notes") or "").strip() or None

    conn.execute(
        """INSERT INTO collection_items
               (card_id, cardmarket_product_id, language_id, condition, quantity,
                purchase_price, purchase_date, status, manual_entry, manual_entry_note, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            card_id,
            cardmarket_product_id,
            resolve_language_id(conn, row.get("language")),
            condition,
            quantity,
            purchase_price,
            purchase_date,
            status,
            1 if manual_entry else 0,
            manual_entry_note,
            notes,
        ),
    )


# --- Report ------------------------------------------------------------------------

@dataclass
class ImportReport:
    total_rows: int = 0
    inserted_direct: list[tuple[int, str, str]] = field(default_factory=list)  # (row, name, note)
    review_queue: list[tuple[int, str, int]] = field(default_factory=list)  # (row, name, n_candidates)
    manual_entries: list[tuple[int, str, str]] = field(default_factory=list)  # (row, name, reason)
    incomplete: list[int] = field(default_factory=list)
    already_imported: list[tuple[int, str]] = field(default_factory=list)  # (row, name)
    variant_mismatches: list[tuple[int, str, str]] = field(default_factory=list)  # (row, name, note)

    def print_summary(self, mode: str) -> None:
        print("=" * 60)
        print(f"REPORTE DE CARGA DE COLECCION -- Fase 5 ({mode})")
        print("=" * 60)

        print(f"\nTotal filas del CSV: {self.total_rows}")

        print(f"\nInsertadas directas ({len(self.inserted_direct)}):")
        for row_n, name, note in self.inserted_direct:
            suffix = f" -- {note}" if note else ""
            print(f"  - fila {row_n}: {name}{suffix}")

        print(f"\nEn cola de revision ({len(self.review_queue)} filas origen"
              f", {sum(n for _, _, n in self.review_queue)} lineas candidatas):")
        for row_n, name, n_candidates in self.review_queue:
            print(f"  - fila {row_n}: {name} ({n_candidates} candidatas)")
        if self.review_queue:
            print(f"  -> generado: {REVIEW_CSV_PATH.relative_to(REPO_ROOT)}")
        else:
            print("  -> no se generó collection-ambiguous-review.csv (no hizo falta)")

        print(f"\nAltas manuales ({len(self.manual_entries)}):")
        for row_n, name, reason in self.manual_entries:
            print(f"  - fila {row_n}: {name} -- {reason}")

        print(f"\nFilas incompletas/saltadas ({len(self.incomplete)}): {self.incomplete}")

        print(f"\nYa importadas (skip por idempotencia) ({len(self.already_imported)}):")
        for row_n, name in self.already_imported:
            print(f"  - fila {row_n}: {name}")

        if self.variant_mismatches:
            print(f"\nDiscrepancias variant(CSV) vs variant_label(DB) -- no bloquean el match "
                  f"({len(self.variant_mismatches)}):")
            for row_n, name, note in self.variant_mismatches:
                print(f"  - fila {row_n}: {name} -- {note}")

        # Cada fila origen cuenta una vez (no las lineas candidatas de la cola de revision).
        total_accounted = (
            len(self.inserted_direct)
            + len(self.review_queue)
            + len(self.manual_entries)
            + len(self.incomplete)
            + len(self.already_imported)
        )
        print(f"\nTotal contabilizado: {total_accounted} (debe ser igual a total filas del CSV: {self.total_rows})")
        print("=" * 60)


# --- Main: initial run --------------------------------------------------------------

def run_initial_load() -> ImportReport:
    report = ImportReport()
    rows = read_input_csv()
    report.total_rows = len(rows)

    state = load_state()
    new_hashes: set[str] = set()

    conn = connect()
    name_index = build_name_index(conn)
    review_lines: list[dict] = []
    try:
        for idx, row in enumerate(rows, start=2):  # fila 2 = primera fila de datos (fila 1 = header)
            card_name = (row.get("card_name") or "").strip()
            if not card_name:
                report.incomplete.append(idx)
                continue

            h = row_hash(row)
            if h in state or h in new_hashes:
                report.already_imported.append((idx, card_name))
                continue

            game = (row.get("game") or "").strip().lower()

            if game == "magic":
                candidates, method = match_magic_candidates(name_index, row)

                if len(candidates) == 1:
                    card_id, expansion_id, card_number, printing_variant, variant_label, name = candidates[0]
                    cardmarket_product_id = resolve_cardmarket_product_id(conn, card_id)
                    insert_collection_item(conn, row, card_id, cardmarket_product_id, False, None)
                    mismatch = variant_cross_check(row.get("variant"), variant_label)
                    note = f"match por {method}, card_id={card_id}"
                    report.inserted_direct.append((idx, card_name, note))
                    if mismatch:
                        report.variant_mismatches.append((idx, card_name, mismatch))
                    new_hashes.add(h)

                elif len(candidates) == 0:
                    reason = "sin candidatas en cards (producto fuera del catalogo importado)"
                    note = build_manual_entry_note(reason, row)
                    insert_collection_item(conn, row, None, None, True, note)
                    report.manual_entries.append((idx, card_name, reason))
                    new_hashes.add(h)

                else:
                    for card_id, expansion_id, card_number, printing_variant, variant_label, name in candidates:
                        price_trend = resolve_price_trend(conn, card_id)
                        review_lines.append(
                            {
                                "source_row": idx,
                                **{f: row.get(f, "") for f in CSV_FIELDS},
                                "candidate_card_id": card_id,
                                "candidate_name": name,
                                "candidate_card_number": card_number,
                                "candidate_printing_variant": printing_variant,
                                "candidate_variant_label": variant_label or "",
                                "candidate_price_trend": price_trend if price_trend is not None else "",
                                "chosen_card_id": "",
                            }
                        )
                    report.review_queue.append((idx, card_name, len(candidates)))
                    # NO se agrega el hash a new_hashes aca -- la fila queda encolada en
                    # collection-ambiguous-review.csv, todavia no se inserto nada en
                    # collection_items. Marcarla "importada" en este punto bloqueaba
                    # --apply-review despues (idempotencia por row_hash confundia "fila
                    # ya procesada/encolada" con "fila ya insertada" -- bug encontrado y
                    # corregido en la corrida de aplicacion de la cola de revision,
                    # 2026-08-25). El hash se agrega recien en run_apply_review() cuando
                    # el insert real ocurre (linea con new_hashes.add(h) dentro del loop
                    # de --apply-review).

            elif game == "one_piece":
                # No se ejercita en esta corrida (CSV de prueba es 100% magic) -- implementado
                # para no dejar el script a medias (contract seccion 2b). ATENCION antes de
                # ejercitar este branch con datos reales: usa `c.name = ?` exacto (case/acento
                # sensible), el mismo problema que tenia el branch Magic antes de esta corrida
                # (ver normalize_name/build_name_index) -- no esta verificado que los nombres
                # de One Piece en el CSV real vengan a salvo de ese problema, revisar antes de
                # confiar en el resultado.
                mapped = conn.execute(
                    """SELECT c.id, c.expansion_id, c.card_number, c.printing_variant, c.variant_label, c.name,
                              m.status
                         FROM cardmarket_product_mappings m
                         JOIN cards c ON c.id = m.card_id
                        WHERE c.name = ?""",
                    (card_name,),
                ).fetchall()
                mapped_ok = [r for r in mapped if r[6] == "mapped"]
                ambiguous = [r for r in mapped if r[6] == "ambiguous"]

                if len(mapped_ok) == 1:
                    card_id = mapped_ok[0][0]
                    cardmarket_product_id = resolve_cardmarket_product_id(conn, card_id)
                    insert_collection_item(conn, row, card_id, cardmarket_product_id, False, None)
                    report.inserted_direct.append((idx, card_name, f"one_piece mapped, card_id={card_id}"))
                    new_hashes.add(h)
                elif ambiguous:
                    for card_id, expansion_id, card_number, printing_variant, variant_label, name, _status in ambiguous:
                        price_trend = resolve_price_trend(conn, card_id)
                        review_lines.append(
                            {
                                "source_row": idx,
                                **{f: row.get(f, "") for f in CSV_FIELDS},
                                "candidate_card_id": card_id,
                                "candidate_name": name,
                                "candidate_card_number": card_number,
                                "candidate_printing_variant": printing_variant,
                                "candidate_variant_label": variant_label or "",
                                "candidate_price_trend": price_trend if price_trend is not None else "",
                                "chosen_card_id": "",
                            }
                        )
                    report.review_queue.append((idx, card_name, len(ambiguous)))
                    # Ver comentario equivalente en la rama magic mas arriba: no marcar
                    # "importada" una fila que solo quedo encolada para revision.
                else:
                    reason = "sin match en catalogo One Piece (no deberia pasar, AGENTS.md §20)"
                    note = build_manual_entry_note(reason, row)
                    insert_collection_item(conn, row, None, None, True, note)
                    report.manual_entries.append((idx, card_name, reason))
                    new_hashes.add(h)

            elif game == "pokemon":
                # Sin catalogo importado (decision Fase 2 §5) -- siempre alta manual.
                reason = "pokemon sin catalogo importado (decision Fase 2 §5)"
                note = build_manual_entry_note(reason, row)
                insert_collection_item(conn, row, None, None, True, note)
                report.manual_entries.append((idx, card_name, reason))
                new_hashes.add(h)

            else:
                reason = f"game={game!r} no reconocido"
                note = build_manual_entry_note(reason, row)
                insert_collection_item(conn, row, None, None, True, note)
                report.manual_entries.append((idx, card_name, reason))
                new_hashes.add(h)

        conn.commit()
    finally:
        conn.close()

    if review_lines:
        with REVIEW_CSV_PATH.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=REVIEW_FIELDS)
            writer.writeheader()
            writer.writerows(review_lines)

    save_state(state | new_hashes)
    return report


# --- Main: --apply-review -----------------------------------------------------------

def run_apply_review() -> ImportReport:
    report = ImportReport()
    if not REVIEW_CSV_PATH.exists():
        print(f"No existe {REVIEW_CSV_PATH.relative_to(REPO_ROOT)} -- nada que aplicar.")
        return report

    with REVIEW_CSV_PATH.open(newline="", encoding="utf-8") as fh:
        lines = list(csv.DictReader(fh))

    groups: dict[str, list[dict]] = {}
    for line in lines:
        groups.setdefault(line["source_row"], []).append(line)

    report.total_rows = len(groups)
    state = load_state()
    new_hashes: set[str] = set()

    conn = connect()
    unresolved: list[tuple[int, str, str]] = []

    try:
        for source_row, group_lines in groups.items():
            base = group_lines[0]
            card_name = base.get("card_name", "")
            chosen = next((ln["chosen_card_id"].strip() for ln in group_lines if ln["chosen_card_id"].strip()), "")

            if not chosen:
                note = (int(source_row), card_name, "chosen_card_id vacio, sin aplicar (--apply-review)")
                report.manual_entries.append(note)
                unresolved.append(note)
                continue

            # Sentinel "MANUAL" (case-insensitive): ninguna de las candidatas listadas
            # corresponde a la edicion real (ej. Surge Foil que no existe en el catalogo
            # importado, ver notes/cardmarket_link de la fila) -- mismo patron que la
            # rama "0 candidatas" de run_initial_load (card_id=NULL, manual_entry=true),
            # pero disparado a mano desde la cola de revision en vez de automatico.
            if chosen.upper() == "MANUAL":
                row = {f: base.get(f, "") for f in CSV_FIELDS}
                h = row_hash(row)
                if h in state or h in new_hashes:
                    report.already_imported.append((int(source_row), card_name))
                    continue

                reason = "candidatas de catalogo no corresponden a la edicion real (chosen_card_id=MANUAL en --apply-review)"
                note_text = build_manual_entry_note(reason, row)
                insert_collection_item(conn, row, None, None, True, note_text)
                report.manual_entries.append((int(source_row), card_name, reason))
                new_hashes.add(h)
                continue

            valid_ids = {ln["candidate_card_id"] for ln in group_lines}
            if chosen not in valid_ids:
                note = (int(source_row), card_name, f"chosen_card_id={chosen} no es una de las candidatas listadas")
                report.manual_entries.append(note)
                unresolved.append(note)
                continue

            card_id = int(chosen)
            row = {f: base.get(f, "") for f in CSV_FIELDS}
            h = row_hash(row)
            if h in state or h in new_hashes:
                report.already_imported.append((int(source_row), card_name))
                continue

            cardmarket_product_id = resolve_cardmarket_product_id(conn, card_id)
            insert_collection_item(conn, row, card_id, cardmarket_product_id, False, None)
            report.inserted_direct.append((int(source_row), card_name, f"--apply-review, card_id={card_id}"))
            new_hashes.add(h)

        conn.commit()
    finally:
        conn.close()

    save_state(state | new_hashes)

    if not unresolved:
        REVIEW_CSV_PATH.rename(REVIEW_DONE_CSV_PATH)
        print(f"Renombrado a {REVIEW_DONE_CSV_PATH.relative_to(REPO_ROOT)} (todas las filas aplicadas).")
    else:
        print(f"{REVIEW_CSV_PATH.relative_to(REPO_ROOT)} no se renombro -- quedan filas sin chosen_card_id.")

    return report


if __name__ == "__main__":
    if "--apply-review" in sys.argv[1:]:
        run_apply_review().print_summary("apply-review")
    else:
        run_initial_load().print_summary("carga inicial")
