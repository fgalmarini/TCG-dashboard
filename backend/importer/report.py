"""Reporte final de la corrida -- nada silencioso (regla AGENTS.md secciones 4-5, 20)."""

from dataclasses import dataclass, field


@dataclass
class ImportReport:
    products_seen: dict[str, dict] = field(default_factory=dict)  # game -> {total, singles, in_scope}
    products_imported: dict[str, int] = field(default_factory=dict)  # game -> count
    new_expansions: list[tuple[str, int]] = field(default_factory=list)  # (game, idExpansion)
    variant_groups: list[tuple[str, tuple, list]] = field(default_factory=list)  # (game, key, decisions)
    unmapped: list[tuple[str, int, str, str]] = field(default_factory=list)  # (game, idProduct, status, notes)
    one_piece_unparsed_names: list[str] = field(default_factory=list)
    date_sentinel_substitutions: dict[str, int] = field(default_factory=dict)
    download_failures: list[str] = field(default_factory=list)
    games_skipped: list[tuple[str, str]] = field(default_factory=list)  # (game, reason)
    price_history_inserted: dict[str, int] = field(default_factory=dict)

    def print_summary(self) -> None:
        print("=" * 60)
        print("REPORTE DE IMPORTACION -- Fase 4 (Cardmarket)")
        print("=" * 60)

        if self.download_failures:
            print("\nDescargas fallidas:")
            for f in self.download_failures:
                print(f"  - {f}")

        if self.games_skipped:
            print("\nJuegos salteados:")
            for game, reason in self.games_skipped:
                print(f"  - {game}: {reason}")

        print("\nProductos vistos por juego:")
        for game, counts in self.products_seen.items():
            print(f"  - {game}: total={counts['total']} singles={counts['singles']} in_scope={counts['in_scope']}")

        print("\nProductos importados (upsert a cardmarket_products) por juego:")
        for game, count in self.products_imported.items():
            print(f"  - {game}: {count}")

        print(f"\nExpansiones nuevas sin nombre ({len(self.new_expansions)}):")
        for game, id_expansion in self.new_expansions:
            print(f"  - {game}: idExpansion={id_expansion}")

        multi_groups = [g for g in self.variant_groups if len(g[2]) > 1]
        print(f"\nGrupos de variantes detectados ({len(multi_groups)} con 2+ productos):")
        for game, key, decisions in multi_groups:
            classification = decisions[0].classification_note
            variants = ", ".join(f"{d.id_product}:{d.printing_variant}" for d in decisions)
            print(f"  - {game} {key} [{classification}]: {variants}")

        print(f"\nProductos sin mapeo limpio ({len(self.unmapped)}):")
        for game, id_product, status, notes in self.unmapped:
            print(f"  - {game} idProduct={id_product} status={status}: {notes}")

        if self.one_piece_unparsed_names:
            print(f"\nNombres de One Piece que no matchearon el regex de card_number ({len(self.one_piece_unparsed_names)}):")
            for name in self.one_piece_unparsed_names[:20]:
                print(f"  - {name!r}")
            if len(self.one_piece_unparsed_names) > 20:
                print(f"  ... y {len(self.one_piece_unparsed_names) - 20} mas")

        if self.date_sentinel_substitutions:
            print("\nFechas invalidas (sentinel 0000-00-00) sustituidas por createdAt del snapshot:")
            for game, count in self.date_sentinel_substitutions.items():
                print(f"  - {game}: {count}")

        print("\nFilas insertadas en market_price_history por juego:")
        for game, count in self.price_history_inserted.items():
            print(f"  - {game}: {count}")

        print("=" * 60)
