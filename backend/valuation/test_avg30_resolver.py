import sqlite3

from valuation.avg30_resolver import (
    build_identity_evidence,
    latest_observations,
    resolve_current_valuation,
    resolve_valuation,
)


def _valuation_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE printing_price_resolutions (
            id INTEGER PRIMARY KEY, card_id INTEGER, language_id INTEGER,
            resolution_scope TEXT, collection_item_id INTEGER,
            wishlist_item_id INTEGER, valuation_status TEXT,
            valuation_method TEXT, valuation_value REAL, reason TEXT,
            source_currency TEXT, currency TEXT, source TEXT, resolved_at TEXT
        )"""
    )
    return conn


def test_scope_aware_helper_prefers_item_then_global_without_cross_scope_leak():
    conn = _valuation_db()
    conn.executemany(
        """INSERT INTO printing_price_resolutions
           (id, card_id, language_id, resolution_scope, collection_item_id,
            wishlist_item_id, valuation_status, valuation_method, valuation_value,
            currency, source, resolved_at)
           VALUES (?, 1, 1, ?, ?, ?, 'ESTIMATED', 'CARDMARKET_AVG30', ?, 'EUR', 'cardmarket', ?)""",
        [
            (1, "global", None, None, 10.0, "2026-01-01"),
            (2, "collection", 7, None, 20.0, "2026-01-02"),
            (3, "wishlist", None, 8, 30.0, "2026-01-03"),
        ],
    )
    conn.commit()

    scoped = resolve_current_valuation(conn, card_id=1, language_id=1, scope="collection", scope_item_id=7)
    fallback = resolve_current_valuation(conn, card_id=1, language_id=1, scope="collection", scope_item_id=99)
    wishlist = resolve_current_valuation(conn, card_id=1, language_id=1, scope="wishlist", scope_item_id=8)

    assert (scoped.resolution_id, scoped.valuation_value) == (2, 20.0)
    assert (fallback.resolution_id, fallback.valuation_value) == (1, 10.0)
    assert (wishlist.resolution_id, wishlist.valuation_value) == (3, 30.0)
    conn.close()


def test_scope_item_is_required_for_scoped_helper():
    conn = _valuation_db()
    try:
        try:
            resolve_current_valuation(conn, card_id=1, language_id=1, scope="collection")
        except ValueError:
            pass
        else:
            raise AssertionError("scoped resolution must require scope_item_id")
    finally:
        conn.close()


def test_latest_observation_respects_as_of_and_includes_boundary_day():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        create table market_price_history (
            id integer primary key, cardmarket_product_id integer, observed_at text,
            avg30 real, avg30_alt real
        );
        insert into market_price_history values
          (1, 7, '2026-09-07T10:00:00+00:00', 10, null),
          (2, 7, '2026-09-08T23:59:59+00:00', 12, null),
          (3, 7, '2026-09-09T00:00:00+00:00', 99, null);
    """)
    result = latest_observations(conn, "2026-09-08")
    assert result[7]["id"] == 2
    assert result[7]["avg30"] == 12


def test_resolver_returns_estimated_and_never_zero_for_missing_avg30():
    card = {"id": 1, "canonical_card_id": 1, "finish": "nonfoil"}
    evidence = build_identity_evidence(
        card=card,
        product={"id": 10},
        product_mapping={"status": "mapped", "card_id": 1},
        scope_mapping=None,
        metric_mapping=None,
        language_exact=True,
    )
    decision = resolve_valuation(card=card, product={"id": 10}, observation={"avg30": 12}, identity_evidence=evidence, as_of="2026-09-08")
    assert decision.valuation_status == "ESTIMATED"
    assert decision.valuation_value == 12
    missing = resolve_valuation(card=card, product={"id": 10}, observation={"avg30": None}, identity_evidence=evidence, as_of="2026-09-08")
    assert missing.valuation_value is None
    assert missing.reason == "MISSING_AVG30"


def test_foil_requires_exact_foil_metric_and_never_falls_back_to_base():
    card = {"id": 1, "canonical_card_id": 1, "finish": "foil"}
    evidence = build_identity_evidence(
        card=card,
        product={"id": 10},
        product_mapping={"status": "mapped", "card_id": 1},
        scope_mapping=None,
        metric_mapping=None,
        language_exact=True,
    )
    decision = resolve_valuation(card=card, product={"id": 10}, observation={"avg30": 20, "avg30_alt": None}, identity_evidence=evidence, as_of="2026-09-08")
    assert decision.valuation_value is None
    assert decision.reason == "FINISH_UNRESOLVED"


def test_exact_requires_complete_metric_evidence():
    card = {"id": 1, "canonical_card_id": 1, "finish": "nonfoil"}
    evidence = build_identity_evidence(
        card=card,
        product={"id": 10},
        product_mapping={"status": "mapped", "card_id": 1},
        scope_mapping=None,
        metric_mapping={"metric_family": "base", "metric_mapping_status": "EXACT", "pricing_eligible": 1},
        language_exact=True,
    )
    decision = resolve_valuation(card=card, product={"id": 10}, observation={"avg30": 12}, identity_evidence=evidence, as_of="2026-09-08")
    assert decision.valuation_status == "EXACT"
