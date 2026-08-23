"""Orquestador / entrypoint CLI del importer de Fase 4.

Uso: python3 backend/importer/run_import.py
"""

import datetime

import card_mapper
import categories
import db
import downloader
import expansions
import mappings
import parser
import price_history
import products
import variants
from config import ALT_SUFFIX, GAMES, SCOPE
from report import ImportReport

PROCESSED_GAMES = ("magic", "one_piece")  # pokemon: SCOPE="skip", nunca entra al loop


def _load_game_data(game_key: str, download_results: dict, report: ImportReport):
    products_result = download_results[f"{game_key}:products"]
    price_guide_result = download_results[f"{game_key}:price_guide"]
    if not products_result.ok or not price_guide_result.ok:
        report.games_skipped.append((game_key, "download failed"))
        return None

    products_created_at, products = parser.load_products(products_result.path)
    price_guide_created_at, price_guide_entries = parser.load_price_guide(price_guide_result.path)
    price_index = parser.index_price_guide_by_product(price_guide_entries)
    return products_created_at, products, price_guide_created_at, price_index


def _filter_in_scope(game_key: str, products: list[dict]) -> tuple[list[dict], list[dict]]:
    singles = [p for p in products if "single" in p.get("categoryName", "").lower()]
    scope = SCOPE[game_key]
    in_scope = singles if scope is None else [p for p in singles if p["idExpansion"] in scope]
    return singles, in_scope


def _load_products_and_categories(
    conn, game_key: str, local_game_id: int, in_scope: list[dict], products_created_at: str, report: ImportReport
) -> dict[int, int]:
    seen_categories: dict[int, str] = {}
    for p in in_scope:
        seen_categories[p["idCategory"]] = p["categoryName"]
    for cat_id, cat_name in seen_categories.items():
        categories.upsert_category(conn, local_game_id, cat_id, cat_name)

    local_product_id_by_cardmarket_id: dict[int, int] = {}
    for p in in_scope:
        date_added = parser.parse_date_added(p.get("dateAdded"))
        if date_added is None:
            date_added = products_created_at
            report.date_sentinel_substitutions[game_key] = report.date_sentinel_substitutions.get(game_key, 0) + 1
        local_id = products.upsert_product(
            conn,
            cardmarket_id_product=p["idProduct"],
            raw_name=p["name"],
            cardmarket_id_category=p["idCategory"],
            cardmarket_id_expansion=p["idExpansion"],
            cardmarket_id_metacard=p.get("idMetacard"),
            date_added=date_added,
            last_seen_at=products_created_at,
        )
        local_product_id_by_cardmarket_id[p["idProduct"]] = local_id
    report.products_imported[game_key] = len(local_product_id_by_cardmarket_id)
    return local_product_id_by_cardmarket_id


def _classify_variants(game_key: str, in_scope: list[dict], price_index: dict, report: ImportReport) -> dict:
    groups = variants.group_products(in_scope)
    decision_by_id_product = {}
    for key, group in groups.items():
        decisions = variants.classify_variant_group(group, price_index)
        report.variant_groups.append((game_key, key, decisions))
        for d in decisions:
            decision_by_id_product[d.id_product] = d
    return decision_by_id_product


def _map_cards(
    conn,
    game_key: str,
    local_game_id: int,
    in_scope: list[dict],
    local_product_id_by_cardmarket_id: dict[int, int],
    decision_by_id_product: dict,
    report: ImportReport,
) -> None:
    expansion_cache: dict[int, int] = {}
    for p in in_scope:
        id_product = p["idProduct"]
        local_product_id = local_product_id_by_cardmarket_id[id_product]

        existing = mappings.get_existing_mapping(conn, local_product_id)
        if existing is not None and existing.status == "mapped":
            continue  # ya resuelto en una corrida anterior

        decision = decision_by_id_product[id_product]

        if game_key == "one_piece":
            card_number, name = parser.parse_one_piece_name(p["name"])
            if card_number is None:
                report.one_piece_unparsed_names.append(p["name"])
        else:
            card_number, name = None, p["name"]

        expansion_id = expansions.get_or_create_expansion(
            conn, local_game_id, p["idExpansion"], expansion_cache, report, game_key
        )

        card_id, status, notes = card_mapper.get_or_create_card(
            conn,
            local_game_id,
            expansion_id,
            card_number,
            name,
            decision.printing_variant,
            decision.variant_label,
            p.get("idMetacard"),
        )
        mappings.upsert_mapping(conn, local_product_id, card_id, status, notes)
        if status != "mapped":
            report.unmapped.append((game_key, id_product, status, notes))


def run_import() -> ImportReport:
    report = ImportReport()
    conn = db.connect()

    download_results = downloader.download_all()
    for key, result in download_results.items():
        if not result.ok:
            report.download_failures.append(f"{key}: {result.error}")

    imported_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    for game_key in PROCESSED_GAMES:
        local_game_id = GAMES[game_key]["local_game_id"]

        loaded = _load_game_data(game_key, download_results, report)
        if loaded is None:
            continue
        products_created_at, products, price_guide_created_at, price_index = loaded

        singles, in_scope = _filter_in_scope(game_key, products)
        report.products_seen[game_key] = {
            "total": len(products),
            "singles": len(singles),
            "in_scope": len(in_scope),
        }

        local_product_id_by_cardmarket_id = _load_products_and_categories(
            conn, game_key, local_game_id, in_scope, products_created_at, report
        )

        decision_by_id_product = _classify_variants(game_key, in_scope, price_index, report)

        _map_cards(
            conn, game_key, local_game_id, in_scope, local_product_id_by_cardmarket_id,
            decision_by_id_product, report,
        )

        price_history.insert_for_referenced_products(
            conn, price_index, ALT_SUFFIX[game_key], price_guide_created_at, imported_at, game_key, report
        )

    conn.commit()
    conn.close()
    return report


if __name__ == "__main__":
    run_import().print_summary()
