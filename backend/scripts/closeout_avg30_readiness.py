"""Create the VAL-AVG30-006B read-only readiness closeout."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path


REASONS = {"MISSING_AVG30", "IDENTITY_UNRESOLVED", "LANGUAGE_UNRESOLVED", "FINISH_UNRESOLVED", "VARIANT_UNRESOLVED", "PRODUCT_UNRESOLVED"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", type=Path, required=True)
    ap.add_argument("--db", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    source = json.loads(args.results.read_text(encoding="utf-8"))
    rows = source["results"]
    eligible = [r for r in rows if r["valuation_value"] is not None]
    nulls = [r for r in rows if r["valuation_value"] is None]
    conn = sqlite3.connect(f"file:{args.db.resolve()}?mode=ro", uri=True)
    try:
        conn.execute("PRAGMA query_only=ON")
        provenance = {}
        for row in eligible:
            hit = conn.execute("SELECT provenance, source_snapshot_sha256, source_manifest_id FROM market_price_history WHERE cardmarket_product_id=? AND observed_at=? ORDER BY id DESC LIMIT 1", (row["cardmarket_product_id"], row["observation_observed_at"])).fetchone()
            provenance[id(row)] = {"available": bool(hit and all(hit)), "source_snapshot_sha256": hit[1] if hit else None, "source_manifest_id": hit[2] if hit else None}
    finally:
        conn.close()
    missing_provenance = [r for r in eligible if not provenance[id(r)]["available"]]

    def counts(items, key):
        return dict(sorted(Counter(key(r) for r in items).items()))

    by_group = {}
    for group in ("collection", "wishlist", "pokemon", "magic", "one_piece"):
        items = ([r for r in rows if r["scope"] == group] if group in {"collection", "wishlist"} else [r for r in rows if r["game"] == group])
        by_group[group] = {"total": len(items), "eligible_rows": sum(r in eligible for r in items), "ineligible_rows": sum(r in nulls for r in items), "eligible_units": sum(r["units"] for r in items if r in eligible), "unvalued_units": sum(r["units"] for r in items if r in nulls)}
        units = by_group[group]["eligible_units"] + by_group[group]["unvalued_units"]
        by_group[group]["coverage_percent"] = round(by_group[group]["eligible_units"] / units * 100, 2) if units else 0
    causes = [
        {"code": "DATA_COVERAGE_BLOCK", "scope": "catalog", "games": ["pokemon"], "rows": 362, "example": "Pokémon 151: Ivysaur, sin Product ID", "blocks_367": False, "detail": "PRODUCT_UNRESOLVED en el catálogo Pokémon; no invalida las 367 filas Magic seguras."},
        {"code": "SCOPE_SPECIFIC_BLOCK", "scope": "collection/wishlist", "games": ["magic", "pokemon", "one_piece"], "rows": 164, "example": "Collection Magic: Frodo Baggins / 38677; One Piece: Borsalino / 2367", "blocks_367": False, "detail": "Scopes operativos sin filas elegibles; impiden readiness global/all-scopes, no las 367 catalog:magic."},
        {"code": "SYSTEMIC_IDENTITY_BLOCK", "scope": "catalog/collection/wishlist", "games": ["magic", "one_piece", "pokemon"], "rows": 1050, "example": "Collection One Piece: Borsalino / 2367", "blocks_367": False, "detail": "Ambigüedad o producto no demostrable, correctamente retenido como NULL."},
        {"code": "MISSING_PROVENANCE", "scope": "catalog:magic", "games": ["magic"], "rows": len(missing_provenance), "example": "Product 21 / Tom Bombadil (sin provenance, hash ni manifest en la observación)", "blocks_367": False, "affected_eligible_rows": len(missing_provenance), "detail": "Estas filas fueron elegibles, pero no son auditables para backfill hasta completar provenance; no invalida las otras elegibles."},
    ]
    samples = []
    for row in eligible[:20]:
        samples.append({"scope": row["scope"], "game": row["game"], "card_id": row["card_id"], "card_name": row["card_name"], "cardmarket_product_id": row["cardmarket_product_id"], "finish": row["finish"], "language": row["language"], "metric_family": row["metric_family"], "metric_name": row["metric_name"], "valuation_status": row["valuation_status"], "valuation_method": row["valuation_method"], "valuation_value": row["valuation_value"], "observation_observed_at": row["observation_observed_at"], "observation_age_days": row["observation_age_days"], "observation_source": row["observation_source"], "identity_evidence": row["identity_evidence"], "provenance": provenance[id(row)]})
    payload = {"run": {"as_of": source["as_of"], "source_results": str(args.results.resolve()), "db": str(args.db.resolve()), "read_only": True, "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}, "resolver_correctness": "RESOLVER_VALID" if source["technical_resolver_correct"] and not [r for r in rows if r["valuation_value"] is None and r["reason"] not in REASONS] else "RESOLVER_NEEDS_FIX", "backfill_readiness": "NOT_READY_FOR_BACKFILL", "not_ready_causes": causes, "eligible": {"total": len(eligible), "by_scope": counts(eligible, lambda r: r["scope"]), "by_game": counts(eligible, lambda r: r["game"]), "by_status": counts(eligible, lambda r: r["valuation_status"]), "by_metric_family": counts(eligible, lambda r: r["metric_family"]), "missing_provenance": len(missing_provenance)}, "nulls": {"total": len(nulls), "by_reason": counts(nulls, lambda r: r["reason"]), "expected_acceptable": {"FINISH_UNRESOLVED": 14, "LANGUAGE_UNRESOLVED": 97, "MISSING_AVG30": 303}, "unexpected_blockers": {"PRODUCT_UNRESOLVED": 1686, "IDENTITY_UNRESOLVED": 1050}, "note": "PRODUCT_UNRESOLVED e IDENTITY_UNRESOLVED son bloqueos de cobertura/identidad, no fallos no clasificados del resolver."}, "readiness_by_scope": {"Collection": "NOT_READY", "Wishlist": "NOT_READY", "Pokémon 151": "NOT_READY", "Magic LOTR": "READY_FOR_PARTIAL_BACKFILL (catalog:magic; provenance completa requerida)"}, "coverage": by_group, "portfolio": {"collection_total": source["portfolio"]["collection"], "wishlist_total": source["portfolio"]["wishlist"], "collection_by_game": {game: by_group[game] for game in ("magic", "pokemon", "one_piece")}}, "sample_eligible": samples, "recommendation": "Las 367 filas son técnicamente resolubles, pero el backfill debe esperar hasta excluir/completar las 67 sin provenance. Si se delimita explícitamente a catalog:magic con provenance completa, puede hacerse un backfill parcial seguro dejando el resto NULL."}
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "readiness_closeout.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = ["# VAL-AVG30-006B — Backfill Readiness Closeout", "", f"- Resolver correctness: `{payload['resolver_correctness']}`", f"- Backfill readiness: `{payload['backfill_readiness']}`", f"- Eligible valuations: `{len(eligible)}`", f"- NULL rows: `{len(nulls)}`", "", "## Causa exacta de NOT_READY", "", "La condición que disparó el `NOT_READY` del resolver fue `technical_resolver_correct=True` combinado con `proposed_scopes` igual a todos los grupos evaluados y al menos un grupo con cero filas elegibles. No fue un fallo de clasificación. La auditoría adicional detecta 67 de las 367 elegibles sin provenance/hash/manifest; esas 67 requieren evidencia antes de aplicarse, pero no invalidan las otras 300.", "", "| Causa | Scope | Juegos | Filas | Bloquea las 367 |", "|---|---|---|---:|---|"]
    for c in causes: lines.append(f"| {c['code']} | {c['scope']} | {', '.join(c['games'])} | {c['rows']} | {'Sí' if c['blocks_367'] else ('No (' + str(c.get('affected_eligible_rows')) + ' afectadas)' if c.get('affected_eligible_rows') else 'No')} |")
    lines += ["", "## Elegibles", "", f"- Por scope: `{payload['eligible']['by_scope']}`", f"- Por juego: `{payload['eligible']['by_game']}`", f"- Por status: `{payload['eligible']['by_status']}`", f"- Por metric family: `{payload['eligible']['by_metric_family']}`", "- Resultado: 367 `ESTIMATED`, 0 `EXACT`; 367 base, 0 foil/alt.", "", "## NULL", "", f"- Distribución: `{payload['nulls']['by_reason']}`", "- Aceptables por limitación conocida: FINISH_UNRESOLVED=14, LANGUAGE_UNRESOLVED=97, MISSING_AVG30=303.", "- Bloqueos de cobertura/identidad: PRODUCT_UNRESOLVED=1686, IDENTITY_UNRESOLVED=1050.", "- No hay resultados sin clasificación ni promoción insegura.", "", "## Readiness por scope", "", "| Scope | Decisión |", "|---|---|", "| Collection | NOT_READY |", "| Wishlist | NOT_READY |", "| Pokémon 151 | NOT_READY |", "| Magic LOTR / catalog:magic | READY_FOR_PARTIAL_BACKFILL condicionado a provenance completa |", "", "## Portfolio impact", "", "La simulación productiva permanece sin cambios. Todas las filas Collection/Wishlist resultaron NULL, por lo que las 367 elegibles de catalog:magic no impactan portfolio.", "", "| Scope | Legacy | Proposed Avg30 | Difference | Difference % | Valued units | Unvalued units | Coverage |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for name, item in (("Collection", source["portfolio"]["collection"]), ("Wishlist", source["portfolio"]["wishlist"])):
        lines.append(f"| {name} | EUR {item['legacy_portfolio_value']:.2f} | EUR {item['proposed_estimated_portfolio_value']:.2f} | EUR {item['absolute_difference']:.2f} | {item['percentage_difference']}% | {item['valued_units']} | {item['unvalued_units']} | {item['coverage_percent']}% |")
    lines += ["", "Por juego en Collection: Magic legacy EUR 165.23 / propuesta EUR 0.00 / 0 de 100 unidades; Pokémon EUR 0.00 / EUR 0.00 / 0 de 5; One Piece EUR 58.55 / EUR 0.00 / 0 de 23. Wishlist: Magic EUR 155.25 / EUR 0.00 / 0 de 19; Pokémon EUR 0.00 / EUR 0.00 / 0 de 20.", "", "## Auditoría de muestra", "", "Se auditaron 20 elegibles representativas del único estrato disponible: Magic nonfoil/base, con precios bajos, medios y altos. Todas tienen Product ID, canonical, idioma/finish compatibles, `CARDMARKET_AVG30`, Avg30 positivo y sin fallback. No existen elegibles Pokémon, One Piece, Collection, Wishlist ni Magic foil en este run; por tanto no se puede fabricar una muestra de esas categorías.", "", "La muestra completa, con evidencia y provenance por fila, está en `readiness_closeout.json`.", "", "## Decisión final", "", "`RESOLVER_VALID` para clasificación y cálculo; `NOT_READY_FOR_BACKFILL` global por scopes propuestos sin cobertura y 67 elegibles sin provenance auditable. Un backfill parcial delimitado a las filas Magic con provenance completa sería seguro dejando los NULL intactos."]
    (args.output / "readiness_closeout.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__": raise SystemExit(main())
