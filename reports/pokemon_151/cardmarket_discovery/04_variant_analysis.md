# Pokémon 151 — Cardmarket Variant Analysis

Scope: source `idExpansion=5328`; `210` products; `167` `(idMetacard, normalized_card_name)` groups.

## Evidence boundary

The Product Catalogue exposes `idProduct`, `name`, `idCategory`, `categoryName`, `idExpansion`, `idMetacard` and `dateAdded`. It does not expose official collector number, rarity, language, version, finish, URL or listing-level attributes. Therefore this report detects multiplicity but does not name a finish or variant unless the source explicitly says so.

## Observed patterns

- Pattern A — one Product ID per source group: `133` groups.
- Pattern B — multiple Product IDs per source group: `34` groups covering `77` products.
- Pattern C — exact duplicate product names under one source group: `34` groups; the name alone cannot explain the difference.
- Pattern D — product-name metadata: only the card name and attack/rules bracket are exposed; `ex` and attack text are not interpreted as rarity or finish.
- Pattern E — insufficient Cardmarket evidence: all scoped rows lack a safe source-backed finish/variant classification.

## Critical conclusion

`idMetacard` is useful evidence that Cardmarket groups related products, but it is not sufficient as a printing identity: some source groups contain multiple Product IDs and some duplicate names are indistinguishable in these files. Product multiplicity cannot be safely labeled normal, holo, reverse holo, Illustration Rare or another variant from this source cut.

## Concrete multi-product examples

| card name | idMetacard | products | Product IDs | product names | price Low present | interpretation |
| --- | --- | --- | --- | --- | --- | --- |
| Alakazam ex | 421144 | 3 | 719507, 719643, 719656 | Alakazam ex [Mind Jack \| Dimensional Hand] \|\| Alakazam ex [Mind Jack \| Dimensional Hand] \|\| Alakazam ex [Mind Jack \| Dimensional Hand] | yes | unresolved; no finish/version/rarity evidence |
| Arbok ex | 421103 | 2 | 719466, 719640 | Arbok ex [Bind Down \| Menacing Fangs] \|\| Arbok ex [Bind Down \| Menacing Fangs] | yes | unresolved; no finish/version/rarity evidence |
| Bill's Transfer | 421242 | 2 | 719617, 719652 | Bill's Transfer \|\| Bill's Transfer | yes | unresolved; no finish/version/rarity evidence |
| Blastoise ex | 421088 | 3 | 719451, 719639, 719655 | Blastoise ex [Solid Shell \| Twin Cannons] \|\| Blastoise ex [Solid Shell \| Twin Cannons] \|\| Blastoise ex [Solid Shell \| Twin Cannons] | yes | unresolved; no finish/version/rarity evidence |
| Bulbasaur | 421079 | 2 | 719442, 719619 | Bulbasaur [Leech Seed \| 151] \|\| Bulbasaur [Leech Seed \| 151] | yes | unresolved; no finish/version/rarity evidence |
| Caterpie | 421089 | 2 | 719452, 719625 | Caterpie [Leaf Munch] \|\| Caterpie [Leaf Munch] | yes | unresolved; no finish/version/rarity evidence |
| Charizard ex | 421085 | 3 | 719448, 719638, 719654 | Charizard ex [Brave Wing \| Explosive Vortex] \|\| Charizard ex [Brave Wing \| Explosive Vortex] \|\| Charizard ex [Brave Wing \| Explosive Vortex] | yes | unresolved; no finish/version/rarity evidence |
| Charmander | 421083 | 2 | 719446, 719621 | Charmander [Blazing Destruction \| Steady Firebreathing] \|\| Charmander [Blazing Destruction \| Steady Firebreathing] | yes | unresolved; no finish/version/rarity evidence |
| Charmeleon | 421084 | 2 | 719447, 719622 | Charmeleon [Combustion \| Fire Blast] \|\| Charmeleon [Combustion \| Fire Blast] | yes | unresolved; no finish/version/rarity evidence |
| Daisy's Help | 421241 | 2 | 719616, 719651 | Daisy's Help \|\| Daisy's Help | yes | unresolved; no finish/version/rarity evidence |
| Dragonair | 421227 | 2 | 719601, 719635 | Dragonair [Beat \| Aqua Slash] \|\| Dragonair [Beat \| Aqua Slash] | yes | unresolved; no finish/version/rarity evidence |
| Erika's Invitation | 421239 | 3 | 719614, 719649, 719659 | Erika's Invitation \|\| Erika's Invitation \|\| Erika's Invitation | yes | unresolved; no finish/version/rarity evidence |
| Giovanni's Charisma | 421240 | 3 | 719615, 719650, 719660 | Giovanni's Charisma \|\| Giovanni's Charisma \|\| Giovanni's Charisma | yes | unresolved; no finish/version/rarity evidence |
| Golem ex | 421155 | 2 | 719518, 719644 | Golem ex [Dynamic Roll \| Rock Blaster] \|\| Golem ex [Dynamic Roll \| Rock Blaster] | yes | unresolved; no finish/version/rarity evidence |
| Ivysaur | 421081 | 2 | 719444, 719620 | Ivysaur [Leech Seed \| Vine Whip \| 151] \|\| Ivysaur [Leech Seed \| Vine Whip \| 151] | yes | unresolved; no finish/version/rarity evidence |
| Jynx ex | 421203 | 2 | 719577, 719646 | Jynx ex [Heart-Stopping Kiss \| Icy Wind] \|\| Jynx ex [Heart-Stopping Kiss \| Icy Wind] | yes | unresolved; no finish/version/rarity evidence |
| Kangaskhan ex | 421194 | 2 | 719568, 719645 | Kangaskhan ex [Triple Draw \| Incessant Punching] \|\| Kangaskhan ex [Triple Draw \| Incessant Punching] | yes | unresolved; no finish/version/rarity evidence |
| Machoke | 421146 | 2 | 719509, 719630 | Machoke [Mountain Ramming] \|\| Machoke [Mountain Ramming] | yes | unresolved; no finish/version/rarity evidence |
| Mew ex | 421230 | 4 | 719604, 719648, 719658, 719661 | Mew ex [Restart \| Genome Hacking] \|\| Mew ex [Restart \| Genome Hacking] \|\| Mew ex [Restart \| Genome Hacking] \|\| Mew ex [Restart \| Genome Hacking] | yes | unresolved; no finish/version/rarity evidence |
| Mewtwo | 421229 | 2 | 719603, 719636 | Mewtwo [Reflective Barrier \| Psyslash] \|\| Mewtwo [Reflective Barrier \| Psyslash] | yes | unresolved; no finish/version/rarity evidence |
| Mr. Mime | 421201 | 2 | 719575, 719632 | Mr. Mime [Mimic Barrier \| Psypower] \|\| Mr. Mime [Mimic Barrier \| Psypower] | yes | unresolved; no finish/version/rarity evidence |
| Nidoking | 421113 | 2 | 719476, 719627 | Nidoking [Enthusiastic King \| Venom Impact] \|\| Nidoking [Enthusiastic King \| Venom Impact] | yes | unresolved; no finish/version/rarity evidence |
| Ninetales ex | 421117 | 2 | 719480, 719641 | Ninetales ex [Heat Wave \| Mirrored Flames] \|\| Ninetales ex [Heat Wave \| Mirrored Flames] | yes | unresolved; no finish/version/rarity evidence |
| Omanyte | 421217 | 2 | 719591, 719633 | Omanyte [Tentacular Return] \|\| Omanyte [Tentacular Return] | yes | unresolved; no finish/version/rarity evidence |
| Pikachu | 421104 | 2 | 719467, 719626 | Pikachu [Charge \| Pika Punch] \|\| Pikachu [Charge \| Pika Punch] | yes | unresolved; no finish/version/rarity evidence |
| Poliwhirl | 421140 | 2 | 719503, 719629 | Poliwhirl [Wave Splash \| Frog Hop] \|\| Poliwhirl [Wave Splash \| Frog Hop] | yes | unresolved; no finish/version/rarity evidence |
| Psyduck | 421133 | 2 | 719496, 719628 | Psyduck [Overthinking \| Water Gun] \|\| Psyduck [Overthinking \| Water Gun] | yes | unresolved; no finish/version/rarity evidence |
| Snorlax | 421222 | 2 | 719596, 719634 | Snorlax [Voraciousness \| Thudding Press] \|\| Snorlax [Voraciousness \| Thudding Press] | yes | unresolved; no finish/version/rarity evidence |
| Squirtle | 421086 | 2 | 719449, 719623 | Squirtle [Withdraw \| Skull Bash] \|\| Squirtle [Withdraw \| Skull Bash] | yes | unresolved; no finish/version/rarity evidence |
| Tangela | 421193 | 2 | 719567, 719631 | Tangela [Tactful Tangling] \|\| Tangela [Tactful Tangling] | yes | unresolved; no finish/version/rarity evidence |
| Venusaur ex | 421082 | 3 | 719445, 719637, 719653 | Venusaur ex [Tranquil Flower \| Dangerous Toxwhip] \|\| Venusaur ex [Tranquil Flower \| Dangerous Toxwhip] \|\| Venusaur ex [Tranquil Flower \| Dangerous Toxwhip] | yes | unresolved; no finish/version/rarity evidence |
| Wartortle | 421087 | 2 | 719450, 719624 | Wartortle [Free Diving \| Spinning Attack] \|\| Wartortle [Free Diving \| Spinning Attack] | yes | unresolved; no finish/version/rarity evidence |
| Wigglytuff ex | 421119 | 2 | 719482, 719642 | Wigglytuff ex [Expanding Body \| Friend Tackle] \|\| Wigglytuff ex [Expanding Body \| Friend Tackle] | yes | unresolved; no finish/version/rarity evidence |
| Zapdos ex | 421224 | 3 | 719598, 719647, 719657 | Zapdos ex [Voltaic Float \| Multishot Lightning] \|\| Zapdos ex [Voltaic Float \| Multishot Lightning] \|\| Zapdos ex [Voltaic Float \| Multishot Lightning] | yes | unresolved; no finish/version/rarity evidence |

The complete per-group evidence is in `03_products_by_collector_number.csv`; the complete per-product evidence is in `02_cardmarket_products.csv`.

## Related source groups excluded from the selected scope

The full source contains other groups with overlapping 151 card names. They are excluded because they have weaker source fingerprints, contain code cards, have materially different product counts, or represent related/reprint/additional products. They must not be merged into the selected expansion without an explicit external identity decision.

| idExpansion | products | unique metacards | anchors | 151 markers | code cards | reason not selected |
| --- | --- | --- | --- | --- | --- | --- |
| 6099 | 192 | 151 | 9 | 3 | 0 | related/alternative source group; not silently merged |
| 5402 | 242 | 175 | 9 | 10 | 8 | related/alternative source group; not silently merged |
| 6311 | 202 | 187 | 8 | 2 | 0 | related/alternative source group; not silently merged |
| 6168 | 141 | 80 | 8 | 2 | 0 | related/alternative source group; not silently merged |
| 5525 | 52 | 48 | 6 | 3 | 0 | related/alternative source group; not silently merged |
| 6219 | 306 | 153 | 5 | 6 | 0 | related/alternative source group; not silently merged |
| 6127 | 302 | 256 | 4 | 6 | 0 | related/alternative source group; not silently merged |
