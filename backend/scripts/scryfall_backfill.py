"""Backfill de catalogo Magic (scope LOTR) via Scryfall.

Sprint contract: fase5-scryfall-magic-backfill-sprint-contract.md.

Corrida de una sola vez (no es un servicio permanente): para cada
cardmarket_products.cardmarket_id_product ya mapeado a una card dentro del scope de
expansiones (5285, 5308, 5396 -- mismo scope que Fase 2/4), pega contra
GET https://api.scryfall.com/cards/cardmarket/{idProduct} y completa directamente
(no self-heal) expansions.name/set_code y cards.name/card_number/printing_variant/
variant_label/image_url/image_source/data_source/scryfall_raw.

Import strategy (AGENTS.md seccion 24, documentado en el contract seccion 1): este
script NO reusa backend/importer/db.py via manipulacion de sys.path -- deliberadamente
separado de backend/importer/ (no se toca nada de esa carpeta). Duplica su propio
connect() minimo (mismo patron de 4 lineas que backend/importer/db.py) porque acoplar
dos carpetas para reusar 4 lineas de codigo seria mas complejo que duplicarlas.

Uso:
    python3 backend/scripts/scryfall_backfill.py
"""

import json
import sqlite3
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "db" / "tcg_dashboard.db"
SCHEMA_PATH = Path(__file__).resolve().parent.parent / "db" / "schema.sql"

SCRYFALL_TIMEOUT_SECONDS = 10
SCRYFALL_COURTESY_DELAY_SECONDS = 0.12  # ~100-150ms pedido por Scryfall entre requests

# Mismo scope de expansiones que backend/importer/config.py SCOPE["magic"].
SCOPE_EXPANSIONS = (5285, 5308, 5387, 5396, 5489)

# printing_variant es un estado del flujo de self-healing de precios de Fase 4, no de
# catalogo -- este backfill nunca lo pisa (regla confirmada, sprint contract seccion 2.4).
PROTECTED_PRINTING_VARIANTS = {"suggested_parallel", "confirmed_parallel"}

# --- Vocabulario para variant_label -------------------------------------------------
# No es un mapeo exhaustivo (no hace falta, sprint contract seccion 2.4) -- cubre los
# frame_effects/promo_types reales observados en LTR/LTC/Promos (ver verificacion manual
# contra la API real antes de implementar). Valores no listados caen al fallback
# determinístico (replace _ por espacio + title case).

# 'legendary'/'miracle'/'inverted' se excluyen del label: son efectos de frame que Scryfall
# aplica automaticamente segun el TIPO/mecanica de la carta (legendaria, milagro), no
# indican una variante de impresion distinta -- incluirlos seria ruido en todas las cartas
# legendarias (mayoria del set), no una senal util.
FRAME_EFFECT_LABELS = {
    "showcase": "Showcase",
    "extendedart": "Extended Art",
    "etched": "Etched",
    "fullart": "Full Art",
}
FRAME_EFFECT_LABEL_EXCLUDED = {"legendary", "miracle", "inverted"}

BORDER_COLOR_LABELS = {
    "borderless": "Borderless",
    "gold": "Gold Border",
    "silver": "Silver Border",
    "white": "White Border",
}

# 'universesbeyond' se excluye del label: es un flag de todo el set LTR/LTC (marca que es
# un producto crossover), no describe una variante visual de ESTA carta en particular --
# aparece en practicamente el 100% de los productos del scope (verificado contra la API
# real antes de implementar), incluirlo lo volveria ruido, no una senal legible.
# 'alchemy'/'rebalanced' son variantes solo-digitales (MTG Arena), no aplican a un
# producto fisico de Cardmarket.
PROMO_TYPE_LABEL_EXCLUDED = {"universesbeyond", "alchemy", "rebalanced"}
PROMO_TYPE_LABELS = {
    "boosterfun": "Booster Fun",
    "serialized": "Serialized",
    "prerelease": "Prerelease",
    "datestamped": "Datestamped",
    "starterdeck": "Starter Deck",
    "doublerainbow": "Double Rainbow",
    "silverfoil": "Silver Foil",
    "surgefoil": "Surge Foil",
    "thick": "Thick Stock",
    "poster": "Poster",
    "scroll": "Scroll",
    "stamped": "Gold Stamp",
}


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ensure_schema(conn: sqlite3.Connection) -> list[str]:
    """Migracion idempotente: agrega cards.data_source / cards.scryfall_raw si faltan.

    No depende de re-correr schema.sql (es CREATE TABLE IF NOT EXISTS, no-op sobre una
    DB existente) -- lee PRAGMA table_info(cards) y agrega columnas puntuales.
    Devuelve la lista de columnas agregadas en esta corrida (vacia si ya estaban).
    """
    existing_columns = {row[1] for row in conn.execute("PRAGMA table_info(cards)")}
    added = []
    if "data_source" not in existing_columns:
        conn.execute(
            "ALTER TABLE cards ADD COLUMN data_source TEXT "
            "CHECK (data_source IS NULL OR data_source IN ('scryfall', 'cardmarket_heuristic', 'manual'))"
        )
        added.append("data_source")
    if "scryfall_raw" not in existing_columns:
        conn.execute("ALTER TABLE cards ADD COLUMN scryfall_raw TEXT")
        added.append("scryfall_raw")
    if added:
        conn.commit()
    return added


@dataclass
class BackfillReport:
    total_in_scope: int = 0
    resolved_ok: int = 0
    no_local_mapping: list[tuple[int, str]] = field(default_factory=list)  # (id_product, reason)
    scryfall_not_found: list[tuple[int, str]] = field(default_factory=list)  # (id_product, reason)
    update_collisions: list[tuple[int, str]] = field(default_factory=list)  # (id_product, reason)
    unexpected_errors: list[tuple[int, str]] = field(default_factory=list)  # (id_product, reason)
    printing_variant_counts: dict[str, int] = field(default_factory=dict)  # 'normal'/'other' -> count
    protected_skipped: int = 0  # cards con suggested_parallel/confirmed_parallel preexistente

    def print_summary(self) -> None:
        print("=" * 60)
        print("REPORTE DE BACKFILL -- Fase 5 (Scryfall, Magic/LOTR)")
        print("=" * 60)

        print(f"\nProductos en scope (cardmarket_id_expansion in {SCOPE_EXPANSIONS}): {self.total_in_scope}")
        print(f"Resueltos OK (card actualizada con datos de Scryfall): {self.resolved_ok}")

        total_failed = (
            len(self.no_local_mapping)
            + len(self.scryfall_not_found)
            + len(self.update_collisions)
            + len(self.unexpected_errors)
        )
        print(f"\nNo matchearon / no se pudieron actualizar ({total_failed}):")

        if self.no_local_mapping:
            print(f"  Sin mapeo local (cardmarket_product_mappings no 'mapped') ({len(self.no_local_mapping)}):")
            for id_product, reason in self.no_local_mapping:
                print(f"    - idProduct={id_product}: {reason}")

        if self.scryfall_not_found:
            print(f"  Scryfall no devolvio el producto ({len(self.scryfall_not_found)}):")
            for id_product, reason in self.scryfall_not_found:
                print(f"    - idProduct={id_product}: {reason}")

        if self.update_collisions:
            print(f"  Colision UNIQUE al actualizar cards ({len(self.update_collisions)}):")
            for id_product, reason in self.update_collisions:
                print(f"    - idProduct={id_product}: {reason}")

        if self.unexpected_errors:
            print(f"  Errores no previstos (no rompieron la corrida, se saltearon) ({len(self.unexpected_errors)}):")
            for id_product, reason in self.unexpected_errors:
                print(f"    - idProduct={id_product}: {reason}")

        print(f"\nCards con printing_variant protegido preexistente (suggested_parallel/confirmed_parallel, "
              f"no pisado): {self.protected_skipped}")

        print("\nDistribucion de printing_variant asignado por este backfill:")
        for variant, count in sorted(self.printing_variant_counts.items()):
            print(f"  - {variant}: {count}")

        print("=" * 60)


def fetch_scryfall_card(cardmarket_id_product: int) -> tuple[dict | None, str | None]:
    """GET https://api.scryfall.com/cards/cardmarket/{id}.

    Devuelve (data, None) en exito, o (None, motivo) si Scryfall no tiene el producto
    mapeado (404) o la llamada falla -- nunca silencioso, el llamador reporta el motivo.

    Scryfall exige explicitamente User-Agent y Accept en cada request (sin esos headers
    devuelve 400 bad_request, aunque la URL/id sean validos -- verificado contra la API
    real antes de dejar esto en el script; backend/importer/images.py:20-43 pega al mismo
    endpoint sin headers explicitos y tiene el mismo problema latente, pero esta fuera de
    scope tocarlo aca).
    """
    url = f"https://api.scryfall.com/cards/cardmarket/{cardmarket_id_product}"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "TCGDashboard/1.0 (personal collection tool; scryfall_backfill.py)",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=SCRYFALL_TIMEOUT_SECONDS) as resp:
            return json.loads(resp.read()), None
    except urllib.error.HTTPError as exc:
        return None, f"HTTP {exc.code}"
    except (urllib.error.URLError, OSError) as exc:
        return None, f"network error: {exc}"
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON: {exc}"


def extract_image_url(data: dict) -> str | None:
    image_uris = data.get("image_uris")
    if image_uris:
        return image_uris.get("normal") or image_uris.get("large") or image_uris.get("small")

    # Cartas de dos caras: Scryfall las devuelve en card_faces, cada cara con su propia imagen.
    for face in data.get("card_faces") or []:
        face_images = face.get("image_uris")
        if face_images:
            return face_images.get("normal") or face_images.get("large") or face_images.get("small")

    return None


def _humanize(token: str) -> str:
    return token.replace("_", " ").title()


def build_variant_label(
    frame_effects: list, border_color: str | None, finishes: list, promo_types: list, full_art: bool
) -> str | None:
    """String legible desde frame_effects + border_color + finishes + promo_types + full_art.

    Orden: frame_effects, border_color, full_art, foil/etched (finishes), promo_types. No
    hace falta un mapeo exhaustivo (sprint contract seccion 2.4) -- determinístico y
    legible alcanza; terminos desconocidos caen al fallback _humanize().
    """
    terms: list[str] = []

    for effect in frame_effects:
        if effect in FRAME_EFFECT_LABEL_EXCLUDED:
            continue
        terms.append(FRAME_EFFECT_LABELS.get(effect, _humanize(effect)))

    if border_color and border_color != "black":
        terms.append(BORDER_COLOR_LABELS.get(border_color, _humanize(border_color)))

    if full_art and "Full Art" not in terms:
        terms.append("Full Art")

    if "etched" in finishes and "Etched" not in terms:
        terms.append("Etched")
    if "foil" in finishes:
        terms.append("Foil")

    for promo in promo_types:
        if promo in PROMO_TYPE_LABEL_EXCLUDED:
            continue
        terms.append(PROMO_TYPE_LABELS.get(promo, _humanize(promo)))

    if not terms:
        return None

    seen: list[str] = []
    for t in terms:
        if t not in seen:
            seen.append(t)
    return " ".join(seen)


def classify_variant(data: dict) -> tuple[str, str | None]:
    """Regla de mapeo (sprint contract seccion 2.4, ajustada -- aprobado por Facundo tras
    el hallazgo de la primera corrida de verificacion contra la API real):

    'normal' si border_color negro + frame_effects vacio + no full_art + sin promo_types
    "reales" (impresion estandar sin variante visual). 'other' para cualquier otra
    combinacion -- sin distinguir cual es "la rara".

    Ajuste sobre la regla original: se saco 'finishes incluye foil' del OR (el objeto
    Card de Scryfall reporta los acabados DISPONIBLES para la impresion, no el acabado
    puntual de ESTE producto de Cardmarket -- practicamente todas las impresiones
    modernas admiten foil, asi que ese chequeo clasificaba ~100% como 'other'). Tambien
    se excluye 'universesbeyond' del chequeo de promo_types: es un flag de TODO el set
    LTR/LTC (marca "esto es Universes Beyond"), no de la impresion particular -- aparece
    en practicamente el 100% de los productos del scope (verificado contra la API real).
    'etched' se mantiene en finishes (si es un acabado real distinto, no ambiguo como
    foil/nonfoil). 'full_art' se agrega como chequeo propio (campo separado de
    frame_effects/border_color) -- confirmado contra datos reales que aparece en 76/551
    productos del scope (basic lands full-art de LTR).
    """
    frame_effects = data.get("frame_effects") or []
    border_color = data.get("border_color")
    finishes = data.get("finishes") or []
    promo_types = data.get("promo_types") or []
    full_art = bool(data.get("full_art"))

    real_promo_types = [p for p in promo_types if p != "universesbeyond"]

    is_other = (
        bool(frame_effects)
        or border_color != "black"
        or "etched" in finishes
        or full_art
        or bool(real_promo_types)
    )
    printing_variant = "other" if is_other else "normal"
    variant_label = (
        build_variant_label(frame_effects, border_color, finishes, promo_types, full_art) if is_other else None
    )
    return printing_variant, variant_label


@dataclass
class ScopedProduct:
    id_product: int
    card_id: int | None
    expansion_id: int | None
    mapping_status: str | None


def fetch_scope(conn: sqlite3.Connection) -> list[ScopedProduct]:
    placeholders = ",".join("?" for _ in SCOPE_EXPANSIONS)
    rows = conn.execute(
        f"""SELECT p.cardmarket_id_product, m.card_id, c.expansion_id, m.status
              FROM cardmarket_products p
              LEFT JOIN cardmarket_product_mappings m ON m.cardmarket_product_id = p.id
              LEFT JOIN cards c ON c.id = m.card_id
             WHERE p.cardmarket_id_expansion IN ({placeholders})""",
        SCOPE_EXPANSIONS,
    ).fetchall()
    return [ScopedProduct(id_product=r[0], card_id=r[1], expansion_id=r[2], mapping_status=r[3]) for r in rows]


def _write_expansion_metadata(
    conn: sqlite3.Connection, expansion_id: int, set_code: str | None, set_name: str | None, is_token: bool
) -> None:
    """Actualiza expansions.name/set_code, prefiriendo siempre un candidato no-token
    (fix aprobado por Facundo): un mismo cardmarket_id_expansion puede agrupar cartas
    reales (layout != 'token') y tokens (layout == 'token') que resuelven a sets de
    Scryfall distintos -- ej. cardmarket_id_expansion=5308 mezcla cartas del set 'ltr'
    con tokens del set 'tltr'. Un producto no-token siempre puede escribir/actualizar el
    valor. Un producto token solo escribe si el campo todavia esta sin valor (name IS
    NULL) -- asi nunca pisa un nombre ya resuelto por un no-token, sea en esta misma
    corrida o en una corrida anterior (la guarda usa el estado real en DB, no memoria
    de proceso, asi que tambien cubre "un candidato no-token que va a aparecer en una
    corrida posterior", como pide el sprint contract).
    """
    if is_token:
        conn.execute(
            "UPDATE expansions SET name = ?, set_code = ? WHERE id = ? AND name IS NULL",
            (set_name, set_code, expansion_id),
        )
    else:
        conn.execute(
            "UPDATE expansions SET name = ?, set_code = ? WHERE id = ?",
            (set_name, set_code, expansion_id),
        )


def apply_scryfall_data(conn: sqlite3.Connection, card_id: int, expansion_id: int, data: dict, report: BackfillReport) -> None:
    set_code = data.get("set")
    set_name = data.get("set_name")
    is_token = "token" in (data.get("layout") or "")  # cubre 'token' y 'double_faced_token'
    _write_expansion_metadata(conn, expansion_id, set_code, set_name, is_token)

    name = data.get("name")
    card_number = data.get("collector_number")
    image_url = extract_image_url(data)
    printing_variant, variant_label = classify_variant(data)
    raw_json = json.dumps(data)

    current_row = conn.execute("SELECT printing_variant FROM cards WHERE id = ?", (card_id,)).fetchone()
    protected = current_row is not None and current_row[0] in PROTECTED_PRINTING_VARIANTS

    if protected:
        conn.execute(
            """UPDATE cards
                 SET name = ?, card_number = ?, image_url = ?, image_source = 'scryfall',
                     data_source = 'scryfall', scryfall_raw = ?
               WHERE id = ?""",
            (name, card_number, image_url, raw_json, card_id),
        )
        report.protected_skipped += 1
        report.printing_variant_counts[current_row[0]] = report.printing_variant_counts.get(current_row[0], 0) + 1
    else:
        conn.execute(
            """UPDATE cards
                 SET name = ?, card_number = ?, printing_variant = ?, variant_label = ?,
                     image_url = ?, image_source = 'scryfall', data_source = 'scryfall',
                     scryfall_raw = ?
               WHERE id = ?""",
            (name, card_number, printing_variant, variant_label, image_url, raw_json, card_id),
        )
        report.printing_variant_counts[printing_variant] = report.printing_variant_counts.get(printing_variant, 0) + 1


def run_backfill(db_path: Path = DB_PATH) -> BackfillReport:
    report = BackfillReport()
    conn = connect(db_path)
    try:
        ensure_schema(conn)

        scope = fetch_scope(conn)
        report.total_in_scope = len(scope)

        for entry in scope:
            if entry.mapping_status != "mapped" or entry.card_id is None or entry.expansion_id is None:
                report.no_local_mapping.append(
                    (entry.id_product, f"cardmarket_product_mappings.status={entry.mapping_status!r}")
                )
                continue

            data, error = fetch_scryfall_card(entry.id_product)
            time.sleep(SCRYFALL_COURTESY_DELAY_SECONDS)

            if data is None:
                report.scryfall_not_found.append((entry.id_product, error or "unknown error"))
                continue

            try:
                apply_scryfall_data(conn, entry.card_id, entry.expansion_id, data, report)
            except sqlite3.IntegrityError as exc:
                # No conn.rollback() aca: por default SQLite solo revierte la sentencia que
                # violo el constraint, no toda la transaccion (mismo patron que
                # backend/importer/card_mapper.py).
                report.update_collisions.append((entry.id_product, str(exc)))
                continue
            except Exception as exc:
                # Cualquier otra excepcion no prevista (ej. sqlite3.OperationalError, o un
                # TypeError/AttributeError si Scryfall alguna vez devuelve un shape de JSON
                # distinto al esperado) no debe propagarse: cortaria el loop antes del
                # conn.commit() final y, por el rollback implicito de SQLite al cerrar sin
                # commit, se perderian TODAS las actualizaciones ya aplicadas en esta
                # corrida, no solo la de este producto (hallazgo de security review).
                # Se reporta (AGENTS.md seccion 20: nunca silencioso) y se sigue con el
                # resto del scope.
                report.unexpected_errors.append((entry.id_product, f"{type(exc).__name__}: {exc}"))
                continue

            report.resolved_ok += 1

        conn.commit()
    finally:
        conn.close()

    return report


if __name__ == "__main__":
    run_backfill().print_summary()
