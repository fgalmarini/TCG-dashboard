# Collection provenance audit — 2026-08-29

Auditoría estrictamente read-only de los 76 Collection items pendientes. No se usó red; no se ejecutó pricing apply; no se modificaron fuentes ni el CSV de revisión.

## Safety and reproducibility

- DB: `backend/db/tcg_dashboard.db`
- DB SHA-256 at audit start: `e155b0776922ac72e191a98b30b6bb44427664cf2ef0ead4f9c6d5e7c53ec225` (expected `e155b0776922ac72e191a98b30b6bb44427664cf2ef0ead4f9c6d5e7c53ec225`)
- Scope CSV: `reports/pricing_audit/2026-08-29/collection-first/collection_manual_review.csv`; SHA-256: `e330bbb85fa319d8a0bc451bcc3f8ffd04acd5ad9490327788c12a1bf45d4aac`; 76 rows; not modified.
- Historical import artifact: `coleccion-a-cargar.numbers`; SHA-256: `edeb4c62d21efa1cda75d6cbcf96dfcce7a65774c4d375423511fb2c516bda5e`.
- Historical derived import review: `backend/scripts/collection-ambiguous-review.done.csv`; SHA-256: `0eb7327d2152b210bd2a3b152105f731186e2650a74cf723ce0c511afed88a86`.
- SQLite connection: URI `mode=ro` plus `PRAGMA query_only=1`.
- Classification is identity provenance only. Prices, price differences and candidate ordering were not used.
- `provenance_gap=true` means a historical Cardmarket link exists in import evidence but no equivalent URL/provenance-link field exists in current `collection_items/cards`.

### One Piece

- pending_before: **23**
- recoverable_without_web: **0**
- requires_web: **23**
- requires_physical: **0**
- EXACT_RECOVERED: **0**
- MANUAL_WEB_REVIEW: **23**
- PHYSICAL_CONFIRMATION_REQUIRED: **0**
- PROVENANCE_GAP: **0**

### Magic

- original_manual_review: **53**
- resolved_by_web_or_explicit_manual: **44**
- Magic Collection identities: **97 / 97 EXACT**

- pending_before: **53**
- recoverable_without_web: **9**
- requires_web: **0**
- requires_physical: **0**
- EXACT_RECOVERED: **53**
- MANUAL_WEB_REVIEW: **0**
- PHYSICAL_CONFIRMATION_REQUIRED: **0**
- PROVENANCE_GAP: **45**

### Magic treatment buckets

| Bucket | Items | EXACT_RECOVERED | MANUAL_WEB_REVIEW | PHYSICAL_CONFIRMATION_REQUIRED | PROVENANCE_GAP |
|---|---:|---:|---:|---:|---:|
| Art Series Gold-Stamped | 45 | 45 | 0 | 0 | 45 |
| Showcase | 6 | 6 | 0 | 0 | 0 |
| Surge Foil | 1 | 1 | 0 | 0 | 0 |
| Scene | 1 | 1 | 0 | 0 | 0 |
| Other | 0 | 0 | 0 | 0 | 0 |

## EXACT_RECOVERED

- item `34` — Frodo, Sauron's Bane — Cardmarket idProduct=701765
  - evidencia: Unique Scryfall printing and scalar Cardmarket id identify one product.
- item `41` — Aragorn, Company Leader — Cardmarket idProduct=717763
  - evidencia: Unique Scryfall printing and scalar Cardmarket id identify one product.
- item `42` — Aragorn, the Uniter — Cardmarket idProduct=716022
  - evidencia: Unique Scryfall printing and scalar Cardmarket id identify one product.
- item `46` — Gimli, Mournful Avenger — Cardmarket idProduct=737034
  - evidencia: Unique Scryfall printing and scalar Cardmarket id identify one product.
- item `47` — Boromir, Warden of the Tower — Cardmarket idProduct=716042
  - evidencia: Unique Scryfall printing and scalar Cardmarket id identify one product.
- item `65` — Shortcut to Mushrooms — Cardmarket idProduct=738134
  - evidencia: Unique Scryfall printing and scalar Cardmarket id identify one product.
- item `70` — The Bath Song — Cardmarket idProduct=737571
  - evidencia: Unique Scryfall printing and scalar Cardmarket id identify one product.
- item `82` — Gimli, Mournful Avenger — Cardmarket idProduct=716059
  - evidencia: Unique Scryfall printing and scalar Cardmarket id identify one product.
- item `84` — Art Series: Fog on the Barrow-Downs — Cardmarket idProduct=718546
  - evidencia: Cardmarket V2 + A2 + Gold-Stamped matched to unique local catalog idProduct=718546; provenance_gap=true.
- item `86` — Art Series: Goldberry, River-Daughter — Cardmarket idProduct=718554
  - evidencia: Cardmarket V2 + A6 + Gold-Stamped matched to unique local catalog idProduct=718554; provenance_gap=true.
- item `87` — Art Series: The Watcher in the Water — Cardmarket idProduct=718555
  - evidencia: Cardmarket V2 + A7 + Gold-Stamped matched to unique local catalog idProduct=718555; provenance_gap=true.
- item `88` — Art Series: Éomer of the Riddermark — Cardmarket idProduct=718559
  - evidencia: Cardmarket V2 + A9 + Gold-Stamped matched to unique local catalog idProduct=718559; provenance_gap=true.
- item `89` — Art Series: Gimli, Counter of Kills — Cardmarket idProduct=718561
  - evidencia: Cardmarket V2 + A10 + Gold-Stamped matched to unique local catalog idProduct=718561; provenance_gap=true.
- item `90` — Art Series: Generous Ent — Cardmarket idProduct=718563
  - evidencia: Cardmarket V2 + A11 + Gold-Stamped matched to unique local catalog idProduct=718563; provenance_gap=true.
- item `91` — Art Series: Mirrormere Guardian — Cardmarket idProduct=718565
  - evidencia: Historical direct Cardmarket URL plus local catalog identify unique Gold-Stamped product; provenance_gap=true.
- item `92` — Art Series: Bilbo, Retired Burglar — Cardmarket idProduct=718575
  - evidencia: Cardmarket V2 + A14 + Gold-Stamped matched to unique local catalog idProduct=718575; provenance_gap=true.
- item `93` — Art Series: Legolas, Counter of Kills — Cardmarket idProduct=718582
  - evidencia: Cardmarket V2 + A17 + Gold-Stamped matched to unique local catalog idProduct=718582; provenance_gap=true.
- item `94` — Art Series: Saruman of Many Colors — Cardmarket idProduct=718601
  - evidencia: Cardmarket V2 + A20 + Gold-Stamped matched to unique local catalog idProduct=718601; provenance_gap=true.
- item `95` — Art Series: Sharkey, Tyrant of the Shire — Cardmarket idProduct=718605
  - evidencia: Cardmarket V2 + A22 + Gold-Stamped matched to unique local catalog idProduct=718605; provenance_gap=true.
- item `96` — Art Series: Shelob, Child of Ungoliant — Cardmarket idProduct=718606
  - evidencia: Cardmarket V2 + A23 + Gold-Stamped matched to unique local catalog idProduct=718606; provenance_gap=true.
- item `97` — Art Series: Théoden, King of Rohan — Cardmarket idProduct=718610
  - evidencia: Cardmarket V2 + A25 + Gold-Stamped matched to unique local catalog idProduct=718610; provenance_gap=true.
- item `98` — Art Series: Tom Bombadil — Cardmarket idProduct=718613
  - evidencia: Cardmarket V2 + A26 + Gold-Stamped matched to unique local catalog idProduct=718613; provenance_gap=true.
- item `99` — Art Series: Uglúk of the White Hand — Cardmarket idProduct=718614
  - evidencia: Cardmarket V2 + A27 + Gold-Stamped matched to unique local catalog idProduct=718614; provenance_gap=true.
- item `100` — Art Series: Plains — Cardmarket idProduct=718621
  - evidencia: Cardmarket V2 + A30 + Gold-Stamped matched to unique local catalog idProduct=718621; provenance_gap=true.
- item `101` — Art Series: Mountain — Cardmarket idProduct=718622
  - evidencia: Cardmarket V2 + A31 + Gold-Stamped matched to unique local catalog idProduct=718622; provenance_gap=true.
- item `102` — Art Series: Elanor Gardner — Cardmarket idProduct=718625
  - evidencia: Cardmarket V2 + A32 + Gold-Stamped matched to unique local catalog idProduct=718625; provenance_gap=true.
- item `103` — Art Series: Aragorn and Arwen, Wed — Cardmarket idProduct=718626
  - evidencia: Cardmarket V2 + A33 + Gold-Stamped matched to unique local catalog idProduct=718626; provenance_gap=true.
- item `104` — Art Series: Bilbo's Ring — Cardmarket idProduct=718640
  - evidencia: Cardmarket V2 + A37 + Gold-Stamped matched to unique local catalog idProduct=718640; provenance_gap=true.
- item `105` — Art Series: Faramir, Field Commander — Cardmarket idProduct=718643
  - evidencia: Cardmarket V2 + A38 + Gold-Stamped matched to unique local catalog idProduct=718643; provenance_gap=true.
- item `106` — Art Series: Elrond, Lord of Rivendell — Cardmarket idProduct=718646
  - evidencia: Cardmarket V2 + A40 + Gold-Stamped matched to unique local catalog idProduct=718646; provenance_gap=true.
- item `107` — Art Series: Witch-king of Angmar — Cardmarket idProduct=718652
  - evidencia: Cardmarket V2 + A43 + Gold-Stamped matched to unique local catalog idProduct=718652; provenance_gap=true.
- item `108` — Art Series: Frodo Baggins — Cardmarket idProduct=718580
  - evidencia: Decisión humana explícita: A47/47 of 81, Gold-Stamped, Cardmarket V.4; idProduct=718580 único en catálogo local. A16g era provenance conflictiva incorrecta; provenance_gap=true.
- item `109` — Art Series: Galadriel of Lothlórien — Cardmarket idProduct=718662
  - evidencia: Cardmarket V2 + A48 + Gold-Stamped matched to unique local catalog idProduct=718662; provenance_gap=true.
- item `110` — Art Series: Merry, Esquire of Rohan — Cardmarket idProduct=718666
  - evidencia: Cardmarket V2 + A50 + Gold-Stamped matched to unique local catalog idProduct=718666; provenance_gap=true.
- item `111` — Art Series: Pippin, Guard of the Citadel — Cardmarket idProduct=718669
  - evidencia: Cardmarket V2 + A51 + Gold-Stamped matched to unique local catalog idProduct=718669; provenance_gap=true.
- item `112` — Art Series: Mines of Moria — Cardmarket idProduct=718683
  - evidencia: Cardmarket V2 + A56 + Gold-Stamped matched to unique local catalog idProduct=718683; provenance_gap=true.
- item `113` — Art Series: Aragorn, King of Gondor — Cardmarket idProduct=718685
  - evidencia: Cardmarket V2 + A57 + Gold-Stamped matched to unique local catalog idProduct=718685; provenance_gap=true.
- item `114` — Art Series: Gwaihir, Greatest of the Eagles — Cardmarket idProduct=718693
  - evidencia: Cardmarket V2 + A59 + Gold-Stamped matched to unique local catalog idProduct=718693; provenance_gap=true.
- item `115` — Art Series: Call for Aid — Cardmarket idProduct=718694
  - evidencia: Cardmarket V2 + A60 + Gold-Stamped matched to unique local catalog idProduct=718694; provenance_gap=true.
- item `116` — Art Series: Cavern-Hoard Dragon — Cardmarket idProduct=718700
  - evidencia: Cardmarket V2 + A61 + Gold-Stamped matched to unique local catalog idProduct=718700; provenance_gap=true.
- item `117` — Art Series: Gríma, Saruman's Footman — Cardmarket idProduct=718708
  - evidencia: Cardmarket V2 + A63 + Gold-Stamped matched to unique local catalog idProduct=718708; provenance_gap=true.
- item `118` — Art Series: Merry, Warden of Isengard — Cardmarket idProduct=718715
  - evidencia: Cardmarket V2 + A65 + Gold-Stamped matched to unique local catalog idProduct=718715; provenance_gap=true.
- item `119` — Art Series: Treebeard, Gracious Host — Cardmarket idProduct=718719
  - evidencia: Cardmarket V2 + A67 + Gold-Stamped matched to unique local catalog idProduct=718719; provenance_gap=true.
- item `120` — Art Series: Asceticism — Cardmarket idProduct=718740
  - evidencia: Cardmarket V2 + A72 + Gold-Stamped matched to unique local catalog idProduct=718740; provenance_gap=true.
- item `121` — Art Series: Realm Seekers — Cardmarket idProduct=718747
  - evidencia: Cardmarket V2 + A74 + Gold-Stamped matched to unique local catalog idProduct=718747; provenance_gap=true.
- item `122` — Art Series: Ghost Quarter — Cardmarket idProduct=718757
  - evidencia: Cardmarket V2 + A78 + Gold-Stamped matched to unique local catalog idProduct=718757; provenance_gap=true.
- item `123` — Art Series: Valley of Gorgoroth — Cardmarket idProduct=718763
  - evidencia: Cardmarket V2 + A80 + Gold-Stamped matched to unique local catalog idProduct=718763; provenance_gap=true.
- item `124` — Art Series: Faramir, Steward of Gondor — Cardmarket idProduct=718704
  - evidencia: Cardmarket V2 + A62 + Gold-Stamped matched to unique local catalog idProduct=718704; provenance_gap=true.
- item `125` — Art Series: Nazgûl — Cardmarket idProduct=718672
  - evidencia: Cardmarket V2 + A53 + Gold-Stamped matched to unique local catalog idProduct=718672; provenance_gap=true.
- item `126` — Art Series: Sauron, the Dark Lord — Cardmarket idProduct=718602
  - evidencia: Cardmarket V2 + A21 + Gold-Stamped matched to unique local catalog idProduct=718602; provenance_gap=true.
- item `127` — Art Series: Éowyn, Fearless Knight — Cardmarket idProduct=718577
  - evidencia: Cardmarket V2 + A15 + Gold-Stamped matched to unique local catalog idProduct=718577; provenance_gap=true.
- item `128` — Art Series: Samwise Gamgee — Cardmarket idProduct=718671
  - evidencia: Decisión humana explícita: A19/19 of 81, Gold-Stamped, Cardmarket V.2; idProduct=718671 único en catálogo local. A52g era provenance conflictiva incorrecta; provenance_gap=true.
- item `131` — Art Series: Gandalf the White — Cardmarket idProduct=718547
  - evidencia: Cardmarket V2 + A3 + Gold-Stamped matched to unique local catalog idProduct=718547; provenance_gap=true.

## Per-item findings

### One Piece

#### Item `133` — Borsalino

- **collection_item_id:** 133
- **game:** One Piece
- **card:** Borsalino
- **current_status:** AMBIGUOUS
- **classification:** MANUAL_WEB_REVIEW
- **recovered_cardmarket_id:** None
- **candidate_cardmarket_ids:** 733344|747506
- **original_import_evidence:** coleccion-a-cargar.numbers exists as historical source; no matching row-level record is present in the derived review CSV.
- **legacy_evidence:** cards.id=17163; collection_items.card_id=17163; printing_variant=normal; variant_label=NULL; finish=NULL; treatment=NULL; source_variant=Base; release_kind=original; art_kind=base; catalog_status=active
- **external_id_evidence:** cardmarket_product idProduct=733344; scope=mixed; metadata={"allowed_languages":["en","jp","zh-CN","kr","fr"]} || cardmarket_product idProduct=747506; scope=mixed; metadata={"allowed_languages":["en","jp","zh-CN","kr","fr"]}
- **scryfall_evidence:** Not applicable to One Piece.
- **cardtrader_evidence:** Blueprint id=268604; scope=exact; metadata={"release_id":3461,"version":null} || card_images source_card_id=268604; source_variant=Base; source_collector_number=OP05-051; image_language_scope=en; fallback=1
- **historical_url_evidence:** No historical Cardmarket URL found in local provenance.
- **provenance_gap:** false
- **lost_fields:** NULL
- **original_value:** NULL
- **current_value:** Not detected
- **confidence_reason:** Local provenance identifies op05 + OP05-051 + jp + variant=Base; Cardmarket candidates remain language_scope=mixed and no unique Cardmarket idProduct is locally proven. CardTrader is auxiliary only.
- **remaining_blocker:** Verify externally which candidate is the exact JP set/release/version/variant; no price-based selection.
- **next_action:** Inspect Cardmarket candidates 733344|747506 and verify JP + op05 + Base / release; record one idProduct only after evidence.

#### Item `134` — Dracule Mihawk

- **collection_item_id:** 134
- **game:** One Piece
- **card:** Dracule Mihawk
- **current_status:** AMBIGUOUS
- **classification:** MANUAL_WEB_REVIEW
- **recovered_cardmarket_id:** None
- **candidate_cardmarket_ids:** 690897|768325
- **original_import_evidence:** coleccion-a-cargar.numbers exists as historical source; no matching row-level record is present in the derived review CSV.
- **legacy_evidence:** cards.id=15439; collection_items.card_id=15439; printing_variant=confirmed_parallel; variant_label=Alternate Art | Fixed Reprint; finish=NULL; treatment=NULL; source_variant=Alternate Art | Fixed Reprint; release_kind=reprint; art_kind=alternate_art; catalog_status=active
- **external_id_evidence:** cardmarket_product idProduct=690897; scope=mixed; metadata={"allowed_languages":["en","jp","zh-CN","kr","fr"]} || cardmarket_product idProduct=768325; scope=mixed; metadata={"allowed_languages":["en","jp","zh-CN","kr","fr"]}
- **scryfall_evidence:** Not applicable to One Piece.
- **cardtrader_evidence:** Blueprint id=244585; scope=exact; metadata={"release_id":3332,"version":"Alternate Art | Fixed Reprint"} || card_images source_card_id=244585; source_variant=Alternate Art | Fixed Reprint; source_collector_number=OP01-070a; image_language_scope=en; fallback=1
- **historical_url_evidence:** No historical Cardmarket URL found in local provenance.
- **provenance_gap:** false
- **lost_fields:** NULL
- **original_value:** NULL
- **current_value:** Not detected
- **confidence_reason:** Local provenance identifies op01 + OP01-070 + jp + variant=Alternate Art | Fixed Reprint; Cardmarket candidates remain language_scope=mixed and no unique Cardmarket idProduct is locally proven. CardTrader is auxiliary only.
- **remaining_blocker:** Verify externally which candidate is the exact JP set/release/version/variant; no price-based selection.
- **next_action:** Inspect Cardmarket candidates 690897|768325 and verify JP + op01 + Alternate Art | Fixed Reprint / release; record one idProduct only after evidence.

#### Item `135` — Dracule Mihawk

- **collection_item_id:** 135
- **game:** One Piece
- **card:** Dracule Mihawk
- **current_status:** AMBIGUOUS
- **classification:** MANUAL_WEB_REVIEW
- **recovered_cardmarket_id:** None
- **candidate_cardmarket_ids:** 690896|768324
- **original_import_evidence:** coleccion-a-cargar.numbers exists as historical source; no matching row-level record is present in the derived review CSV.
- **legacy_evidence:** cards.id=15437; collection_items.card_id=15437; printing_variant=normal; variant_label=Fixed Reprint; finish=NULL; treatment=NULL; source_variant=Fixed Reprint; release_kind=reprint; art_kind=base; catalog_status=active
- **external_id_evidence:** cardmarket_product idProduct=690896; scope=mixed; metadata={"allowed_languages":["en","jp","zh-CN","kr","fr"]} || cardmarket_product idProduct=768324; scope=mixed; metadata={"allowed_languages":["en","jp","zh-CN","kr","fr"]}
- **scryfall_evidence:** Not applicable to One Piece.
- **cardtrader_evidence:** Blueprint id=244584; scope=exact; metadata={"release_id":3332,"version":"Fixed Reprint"} || card_images source_card_id=244584; source_variant=Fixed Reprint; source_collector_number=OP01-070; image_language_scope=en; fallback=1
- **historical_url_evidence:** No historical Cardmarket URL found in local provenance.
- **provenance_gap:** false
- **lost_fields:** NULL
- **original_value:** NULL
- **current_value:** Not detected
- **confidence_reason:** Local provenance identifies op01 + OP01-070 + jp + variant=Fixed Reprint; Cardmarket candidates remain language_scope=mixed and no unique Cardmarket idProduct is locally proven. CardTrader is auxiliary only.
- **remaining_blocker:** Verify externally which candidate is the exact JP set/release/version/variant; no price-based selection.
- **next_action:** Inspect Cardmarket candidates 690896|768324 and verify JP + op01 + Fixed Reprint / release; record one idProduct only after evidence.

#### Item `136` — Yamato

- **collection_item_id:** 136
- **game:** One Piece
- **card:** Yamato
- **current_status:** AMBIGUOUS
- **classification:** MANUAL_WEB_REVIEW
- **recovered_cardmarket_id:** None
- **candidate_cardmarket_ids:** 845324|857251
- **original_import_evidence:** coleccion-a-cargar.numbers exists as historical source; no matching row-level record is present in the derived review CSV.
- **legacy_evidence:** cards.id=22263; collection_items.card_id=22263; printing_variant=normal; variant_label=NULL; finish=NULL; treatment=NULL; source_variant=Base; release_kind=original; art_kind=base; catalog_status=active
- **external_id_evidence:** cardmarket_product idProduct=845324; scope=mixed; metadata={"allowed_languages":["en","jp","zh-CN","kr","fr"]} || cardmarket_product idProduct=857251; scope=mixed; metadata={"allowed_languages":["en","jp","zh-CN","kr","fr"]}
- **scryfall_evidence:** Not applicable to One Piece.
- **cardtrader_evidence:** Blueprint id=354348; scope=exact; metadata={"release_id":4241,"version":null} || card_images source_card_id=354348; source_variant=Base; source_collector_number=OP13-054; image_language_scope=en; fallback=1
- **historical_url_evidence:** No historical Cardmarket URL found in local provenance.
- **provenance_gap:** false
- **lost_fields:** NULL
- **original_value:** NULL
- **current_value:** Not detected
- **confidence_reason:** Local provenance identifies op13 + OP13-054 + jp + variant=Base; Cardmarket candidates remain language_scope=mixed and no unique Cardmarket idProduct is locally proven. CardTrader is auxiliary only.
- **remaining_blocker:** Verify externally which candidate is the exact JP set/release/version/variant; no price-based selection.
- **next_action:** Inspect Cardmarket candidates 845324|857251 and verify JP + op13 + Base / release; record one idProduct only after evidence.

#### Item `137` — Lilith

- **collection_item_id:** 137
- **game:** One Piece
- **card:** Lilith
- **current_status:** AMBIGUOUS
- **classification:** MANUAL_WEB_REVIEW
- **recovered_cardmarket_id:** None
- **candidate_cardmarket_ids:** 845665|857331
- **original_import_evidence:** coleccion-a-cargar.numbers exists as historical source; no matching row-level record is present in the derived review CSV.
- **legacy_evidence:** cards.id=22215; collection_items.card_id=22215; printing_variant=confirmed_parallel; variant_label=Alternate Art; finish=NULL; treatment=NULL; source_variant=Alternate Art; release_kind=original; art_kind=alternate_art; catalog_status=active
- **external_id_evidence:** cardmarket_product idProduct=845665; scope=mixed; metadata={"allowed_languages":["en","jp","zh-CN","kr","fr"]} || cardmarket_product idProduct=857331; scope=mixed; metadata={"allowed_languages":["en","jp","zh-CN","kr","fr"]}
- **scryfall_evidence:** Not applicable to One Piece.
- **cardtrader_evidence:** Blueprint id=354323; scope=exact; metadata={"release_id":4241,"version":"Alternate Art"} || card_images source_card_id=354323; source_variant=Alternate Art; source_collector_number=OP13-113a; image_language_scope=en; fallback=1
- **historical_url_evidence:** No historical Cardmarket URL found in local provenance.
- **provenance_gap:** false
- **lost_fields:** NULL
- **original_value:** NULL
- **current_value:** Not detected
- **confidence_reason:** Local provenance identifies op13 + OP13-113 + jp + variant=Alternate Art; Cardmarket candidates remain language_scope=mixed and no unique Cardmarket idProduct is locally proven. CardTrader is auxiliary only.
- **remaining_blocker:** Verify externally which candidate is the exact JP set/release/version/variant; no price-based selection.
- **next_action:** Inspect Cardmarket candidates 845665|857331 and verify JP + op13 + Alternate Art / release; record one idProduct only after evidence.

#### Item `138` — Monkey.D.Luffy

- **collection_item_id:** 138
- **game:** One Piece
- **card:** Monkey.D.Luffy
- **current_status:** MISMATCH
- **classification:** MANUAL_WEB_REVIEW
- **recovered_cardmarket_id:** None
- **candidate_cardmarket_ids:** 808171|808172|808173|823515|823516|823517|838704|838705|852319|852320
- **original_import_evidence:** coleccion-a-cargar.numbers exists as historical source; no matching row-level record is present in the derived review CSV.
- **legacy_evidence:** cards.id=21131; collection_items.card_id=21131; printing_variant=confirmed_parallel; variant_label=Secret Rare | Alternate Art; finish=NULL; treatment=NULL; source_variant=Secret Rare | Alternate Art; release_kind=original; art_kind=alternate_art; catalog_status=active
- **external_id_evidence:** cardmarket_product idProduct=823516; scope=mixed; metadata={"allowed_languages":["en","jp","zh-CN","kr","fr"]}
- **scryfall_evidence:** Not applicable to One Piece.
- **cardtrader_evidence:** Blueprint id=330432; scope=exact; metadata={"release_id":4123,"version":"Secret Rare | Alternate Art"} || card_images source_card_id=330432; source_variant=Secret Rare | Alternate Art; source_collector_number=EB02-061a; image_language_scope=en; fallback=1
- **historical_url_evidence:** No historical Cardmarket URL found in local provenance.
- **provenance_gap:** false
- **lost_fields:** NULL
- **original_value:** NULL
- **current_value:** Not detected
- **confidence_reason:** Local provenance identifies eb-02 + EB02-061A + jp + variant=Secret Rare | Alternate Art; Cardmarket candidates remain language_scope=mixed and no unique Cardmarket idProduct is locally proven. EB02-061A has 10 candidates across EB02/PRB02 and Cardmarket bulk omits V1/V2/V3. CardTrader is auxiliary only.
- **remaining_blocker:** Verify externally which candidate is the exact JP set/release/version/variant; no price-based selection.
- **next_action:** Inspect Cardmarket candidates 808171|808172|808173|823515|823516|823517|838704|838705|852319|852320 and verify JP + eb-02 + Secret Rare | Alternate Art / release; record one idProduct only after evidence.

#### Item `139` — Rob Lucci

- **collection_item_id:** 139
- **game:** One Piece
- **card:** Rob Lucci
- **current_status:** AMBIGUOUS
- **classification:** MANUAL_WEB_REVIEW
- **recovered_cardmarket_id:** None
- **candidate_cardmarket_ids:** 733430|747782
- **original_import_evidence:** coleccion-a-cargar.numbers exists as historical source; no matching row-level record is present in the derived review CSV.
- **legacy_evidence:** cards.id=17143; collection_items.card_id=17143; printing_variant=confirmed_parallel; variant_label=093 | Alternate Art; finish=NULL; treatment=NULL; source_variant=093 | Alternate Art; release_kind=original; art_kind=alternate_art; catalog_status=active
- **external_id_evidence:** cardmarket_product idProduct=733430; scope=mixed; metadata={"allowed_languages":["en","jp","zh-CN","kr","fr"]} || cardmarket_product idProduct=747782; scope=mixed; metadata={"allowed_languages":["en","jp","zh-CN","kr","fr"]}
- **scryfall_evidence:** Not applicable to One Piece.
- **cardtrader_evidence:** Blueprint id=268464; scope=exact; metadata={"release_id":3461,"version":"093 | Alternate Art"} || card_images source_card_id=268464; source_variant=093 | Alternate Art; source_collector_number=OP05-093a; image_language_scope=en; fallback=1
- **historical_url_evidence:** No historical Cardmarket URL found in local provenance.
- **provenance_gap:** false
- **lost_fields:** NULL
- **original_value:** NULL
- **current_value:** Not detected
- **confidence_reason:** Local provenance identifies op05 + OP05-093 + jp + variant=093 | Alternate Art; Cardmarket candidates remain language_scope=mixed and no unique Cardmarket idProduct is locally proven. CardTrader is auxiliary only.
- **remaining_blocker:** Verify externally which candidate is the exact JP set/release/version/variant; no price-based selection.
- **next_action:** Inspect Cardmarket candidates 733430|747782 and verify JP + op05 + 093 | Alternate Art / release; record one idProduct only after evidence.

#### Item `140` — X.Drake

- **collection_item_id:** 140
- **game:** One Piece
- **card:** X.Drake
- **current_status:** AMBIGUOUS
- **classification:** MANUAL_WEB_REVIEW
- **recovered_cardmarket_id:** None
- **candidate_cardmarket_ids:** 733352|747512
- **original_import_evidence:** coleccion-a-cargar.numbers exists as historical source; no matching row-level record is present in the derived review CSV.
- **legacy_evidence:** cards.id=17185; collection_items.card_id=17185; printing_variant=confirmed_parallel; variant_label=Alternate Art; finish=NULL; treatment=NULL; source_variant=Alternate Art; release_kind=original; art_kind=alternate_art; catalog_status=active
- **external_id_evidence:** cardmarket_product idProduct=733352; scope=mixed; metadata={"allowed_languages":["en","jp","zh-CN","kr","fr"]} || cardmarket_product idProduct=747512; scope=mixed; metadata={"allowed_languages":["en","jp","zh-CN","kr","fr"]}
- **scryfall_evidence:** Not applicable to One Piece.
- **cardtrader_evidence:** Blueprint id=269569; scope=exact; metadata={"release_id":3461,"version":"Alternate Art"} || card_images source_card_id=269569; source_variant=Alternate Art; source_collector_number=OP05-055a; image_language_scope=en; fallback=1
- **historical_url_evidence:** No historical Cardmarket URL found in local provenance.
- **provenance_gap:** false
- **lost_fields:** NULL
- **original_value:** NULL
- **current_value:** Not detected
- **confidence_reason:** Local provenance identifies op05 + OP05-055 + jp + variant=Alternate Art; Cardmarket candidates remain language_scope=mixed and no unique Cardmarket idProduct is locally proven. CardTrader is auxiliary only.
- **remaining_blocker:** Verify externally which candidate is the exact JP set/release/version/variant; no price-based selection.
- **next_action:** Inspect Cardmarket candidates 733352|747512 and verify JP + op05 + Alternate Art / release; record one idProduct only after evidence.

#### Item `141` — Cavendish

- **collection_item_id:** 141
- **game:** One Piece
- **card:** Cavendish
- **current_status:** AMBIGUOUS
- **classification:** MANUAL_WEB_REVIEW
- **recovered_cardmarket_id:** None
- **candidate_cardmarket_ids:** 690804|768247
- **original_import_evidence:** coleccion-a-cargar.numbers exists as historical source; no matching row-level record is present in the derived review CSV.
- **legacy_evidence:** cards.id=15290; collection_items.card_id=15290; printing_variant=normal; variant_label=Box Topper; finish=NULL; treatment=NULL; source_variant=Box Topper; release_kind=original; art_kind=base; catalog_status=active
- **external_id_evidence:** cardmarket_product idProduct=690804; scope=mixed; metadata={"allowed_languages":["en","jp","zh-CN","kr","fr"]} || cardmarket_product idProduct=768247; scope=mixed; metadata={"allowed_languages":["en","jp","zh-CN","kr","fr"]}
- **scryfall_evidence:** Not applicable to One Piece.
- **cardtrader_evidence:** Blueprint id=244478; scope=exact; metadata={"release_id":3332,"version":"Box Topper"} || card_images source_card_id=244478; source_variant=Box Topper; source_collector_number=OP01-008b; image_language_scope=en; fallback=1
- **historical_url_evidence:** No historical Cardmarket URL found in local provenance.
- **provenance_gap:** false
- **lost_fields:** NULL
- **original_value:** NULL
- **current_value:** Not detected
- **confidence_reason:** Local provenance identifies op01 + OP01-008 + jp + variant=Box Topper; Cardmarket candidates remain language_scope=mixed and no unique Cardmarket idProduct is locally proven. CardTrader is auxiliary only.
- **remaining_blocker:** Verify externally which candidate is the exact JP set/release/version/variant; no price-based selection.
- **next_action:** Inspect Cardmarket candidates 690804|768247 and verify JP + op01 + Box Topper / release; record one idProduct only after evidence.

#### Item `142` — Gol.D.Roger

- **collection_item_id:** 142
- **game:** One Piece
- **card:** Gol.D.Roger
- **current_status:** AMBIGUOUS
- **classification:** MANUAL_WEB_REVIEW
- **recovered_cardmarket_id:** None
- **candidate_cardmarket_ids:** 845596|857262
- **original_import_evidence:** coleccion-a-cargar.numbers exists as historical source; no matching row-level record is present in the derived review CSV.
- **legacy_evidence:** cards.id=22265; collection_items.card_id=22265; printing_variant=normal; variant_label=NULL; finish=NULL; treatment=NULL; source_variant=Base; release_kind=original; art_kind=base; catalog_status=active
- **external_id_evidence:** cardmarket_product idProduct=845596; scope=mixed; metadata={"allowed_languages":["en","jp","zh-CN","kr","fr"]} || cardmarket_product idProduct=857262; scope=mixed; metadata={"allowed_languages":["en","jp","zh-CN","kr","fr"]}
- **scryfall_evidence:** Not applicable to One Piece.
- **cardtrader_evidence:** Blueprint id=354349; scope=exact; metadata={"release_id":4241,"version":null} || card_images source_card_id=354349; source_variant=Base; source_collector_number=OP13-064; image_language_scope=en; fallback=1
- **historical_url_evidence:** No historical Cardmarket URL found in local provenance.
- **provenance_gap:** false
- **lost_fields:** NULL
- **original_value:** NULL
- **current_value:** Not detected
- **confidence_reason:** Local provenance identifies op13 + OP13-064 + jp + variant=Base; Cardmarket candidates remain language_scope=mixed and no unique Cardmarket idProduct is locally proven. CardTrader is auxiliary only.
- **remaining_blocker:** Verify externally which candidate is the exact JP set/release/version/variant; no price-based selection.
- **next_action:** Inspect Cardmarket candidates 845596|857262 and verify JP + op13 + Base / release; record one idProduct only after evidence.

#### Item `143` — Nefeltari Vivi

- **collection_item_id:** 143
- **game:** One Piece
- **card:** Nefeltari Vivi
- **current_status:** AMBIGUOUS
- **classification:** MANUAL_WEB_REVIEW
- **recovered_cardmarket_id:** None
- **candidate_cardmarket_ids:** 823455
- **original_import_evidence:** coleccion-a-cargar.numbers exists as historical source; no matching row-level record is present in the derived review CSV.
- **legacy_evidence:** cards.id=21085; collection_items.card_id=21085; printing_variant=normal; variant_label=NULL; finish=NULL; treatment=NULL; source_variant=Base; release_kind=original; art_kind=base; catalog_status=active
- **external_id_evidence:** cardmarket_product idProduct=823455; scope=mixed; metadata={"allowed_languages":["en","jp","zh-CN","kr","fr"]}
- **scryfall_evidence:** Not applicable to One Piece.
- **cardtrader_evidence:** Blueprint id=330373; scope=exact; metadata={"release_id":4123,"version":null} || card_images source_card_id=330373; source_variant=Base; source_collector_number=EB02-026; image_language_scope=en; fallback=1
- **historical_url_evidence:** No historical Cardmarket URL found in local provenance.
- **provenance_gap:** false
- **lost_fields:** NULL
- **original_value:** NULL
- **current_value:** Not detected
- **confidence_reason:** Local provenance identifies eb-02 + EB02-026 + jp + variant=Base; Cardmarket candidates remain language_scope=mixed and no unique Cardmarket idProduct is locally proven. CardTrader is auxiliary only.
- **remaining_blocker:** Verify externally which candidate is the exact JP set/release/version/variant; no price-based selection.
- **next_action:** Inspect Cardmarket candidates 823455 and verify JP + eb-02 + Base / release; record one idProduct only after evidence.

#### Item `144` — S-Snake

- **collection_item_id:** 144
- **game:** One Piece
- **card:** S-Snake
- **current_status:** AMBIGUOUS
- **classification:** MANUAL_WEB_REVIEW
- **recovered_cardmarket_id:** None
- **candidate_cardmarket_ids:** 771756|788021
- **original_import_evidence:** coleccion-a-cargar.numbers exists as historical source; no matching row-level record is present in the derived review CSV.
- **legacy_evidence:** cards.id=19531; collection_items.card_id=19531; printing_variant=normal; variant_label=NULL; finish=NULL; treatment=NULL; source_variant=Base; release_kind=original; art_kind=base; catalog_status=active
- **external_id_evidence:** cardmarket_product idProduct=771756; scope=mixed; metadata={"allowed_languages":["en","jp","zh-CN","kr","fr"]} || cardmarket_product idProduct=788021; scope=mixed; metadata={"allowed_languages":["en","jp","zh-CN","kr","fr"]}
- **scryfall_evidence:** Not applicable to One Piece.
- **cardtrader_evidence:** Blueprint id=299411; scope=exact; metadata={"release_id":3828,"version":null} || card_images source_card_id=299411; source_variant=Base; source_collector_number=OP08-112; image_language_scope=en; fallback=1
- **historical_url_evidence:** No historical Cardmarket URL found in local provenance.
- **provenance_gap:** false
- **lost_fields:** NULL
- **original_value:** NULL
- **current_value:** Not detected
- **confidence_reason:** Local provenance identifies op08 + OP08-112 + jp + variant=Base; Cardmarket candidates remain language_scope=mixed and no unique Cardmarket idProduct is locally proven. CardTrader is auxiliary only.
- **remaining_blocker:** Verify externally which candidate is the exact JP set/release/version/variant; no price-based selection.
- **next_action:** Inspect Cardmarket candidates 771756|788021 and verify JP + op08 + Base / release; record one idProduct only after evidence.

#### Item `145` — Koala

- **collection_item_id:** 145
- **game:** One Piece
- **card:** Koala
- **current_status:** AMBIGUOUS
- **classification:** MANUAL_WEB_REVIEW
- **recovered_cardmarket_id:** None
- **candidate_cardmarket_ids:** 733281|747444
- **original_import_evidence:** coleccion-a-cargar.numbers exists as historical source; no matching row-level record is present in the derived review CSV.
- **legacy_evidence:** cards.id=17141; collection_items.card_id=17141; printing_variant=normal; variant_label=NULL; finish=NULL; treatment=NULL; source_variant=Base; release_kind=original; art_kind=base; catalog_status=active
- **external_id_evidence:** cardmarket_product idProduct=733281; scope=mixed; metadata={"allowed_languages":["en","jp","zh-CN","kr","fr"]} || cardmarket_product idProduct=747444; scope=mixed; metadata={"allowed_languages":["en","jp","zh-CN","kr","fr"]}
- **scryfall_evidence:** Not applicable to One Piece.
- **cardtrader_evidence:** Blueprint id=268463; scope=exact; metadata={"release_id":3461,"version":null} || card_images source_card_id=268463; source_variant=Base; source_collector_number=OP05-006; image_language_scope=en; fallback=1
- **historical_url_evidence:** No historical Cardmarket URL found in local provenance.
- **provenance_gap:** false
- **lost_fields:** NULL
- **original_value:** NULL
- **current_value:** Not detected
- **confidence_reason:** Local provenance identifies op05 + OP05-006 + jp + variant=Base; Cardmarket candidates remain language_scope=mixed and no unique Cardmarket idProduct is locally proven. CardTrader is auxiliary only.
- **remaining_blocker:** Verify externally which candidate is the exact JP set/release/version/variant; no price-based selection.
- **next_action:** Inspect Cardmarket candidates 733281|747444 and verify JP + op05 + Base / release; record one idProduct only after evidence.

#### Item `146` — Monkey.D.Luffy

- **collection_item_id:** 146
- **game:** One Piece
- **card:** Monkey.D.Luffy
- **current_status:** AMBIGUOUS
- **classification:** MANUAL_WEB_REVIEW
- **recovered_cardmarket_id:** None
- **candidate_cardmarket_ids:** 690823|768265
- **original_import_evidence:** coleccion-a-cargar.numbers exists as historical source; no matching row-level record is present in the derived review CSV.
- **legacy_evidence:** cards.id=15326; collection_items.card_id=15326; printing_variant=normal; variant_label=NULL; finish=NULL; treatment=NULL; source_variant=Base; release_kind=original; art_kind=base; catalog_status=active
- **external_id_evidence:** cardmarket_product idProduct=690823; scope=mixed; metadata={"allowed_languages":["en","jp","zh-CN","kr","fr"]} || cardmarket_product idProduct=768265; scope=mixed; metadata={"allowed_languages":["en","jp","zh-CN","kr","fr"]}
- **scryfall_evidence:** Not applicable to One Piece.
- **cardtrader_evidence:** Blueprint id=244509; scope=exact; metadata={"release_id":3332,"version":null} || card_images source_card_id=244509; source_variant=Base; source_collector_number=OP01-024; image_language_scope=en; fallback=1
- **historical_url_evidence:** No historical Cardmarket URL found in local provenance.
- **provenance_gap:** false
- **lost_fields:** NULL
- **original_value:** NULL
- **current_value:** Not detected
- **confidence_reason:** Local provenance identifies op01 + OP01-024 + jp + variant=Base; Cardmarket candidates remain language_scope=mixed and no unique Cardmarket idProduct is locally proven. CardTrader is auxiliary only.
- **remaining_blocker:** Verify externally which candidate is the exact JP set/release/version/variant; no price-based selection.
- **next_action:** Inspect Cardmarket candidates 690823|768265 and verify JP + op01 + Base / release; record one idProduct only after evidence.

#### Item `147` — Yamato

- **collection_item_id:** 147
- **game:** One Piece
- **card:** Yamato
- **current_status:** AMBIGUOUS
- **classification:** MANUAL_WEB_REVIEW
- **recovered_cardmarket_id:** None
- **candidate_cardmarket_ids:** 823429
- **original_import_evidence:** coleccion-a-cargar.numbers exists as historical source; no matching row-level record is present in the derived review CSV.
- **legacy_evidence:** cards.id=21059; collection_items.card_id=21059; printing_variant=normal; variant_label=NULL; finish=NULL; treatment=NULL; source_variant=Base; release_kind=original; art_kind=base; catalog_status=active
- **external_id_evidence:** cardmarket_product idProduct=823429; scope=mixed; metadata={"allowed_languages":["en","jp","zh-CN","kr","fr"]}
- **scryfall_evidence:** Not applicable to One Piece.
- **cardtrader_evidence:** Blueprint id=330347; scope=exact; metadata={"release_id":4123,"version":null} || card_images source_card_id=330347; source_variant=Base; source_collector_number=EB02-006; image_language_scope=en; fallback=1
- **historical_url_evidence:** No historical Cardmarket URL found in local provenance.
- **provenance_gap:** false
- **lost_fields:** NULL
- **original_value:** NULL
- **current_value:** Not detected
- **confidence_reason:** Local provenance identifies eb-02 + EB02-006 + jp + variant=Base; Cardmarket candidates remain language_scope=mixed and no unique Cardmarket idProduct is locally proven. CardTrader is auxiliary only.
- **remaining_blocker:** Verify externally which candidate is the exact JP set/release/version/variant; no price-based selection.
- **next_action:** Inspect Cardmarket candidates 823429 and verify JP + eb-02 + Base / release; record one idProduct only after evidence.

#### Item `148` — Pica

- **collection_item_id:** 148
- **game:** One Piece
- **card:** Pica
- **current_status:** AMBIGUOUS
- **classification:** MANUAL_WEB_REVIEW
- **recovered_cardmarket_id:** None
- **candidate_cardmarket_ids:** 733317|747476
- **original_import_evidence:** coleccion-a-cargar.numbers exists as historical source; no matching row-level record is present in the derived review CSV.
- **legacy_evidence:** cards.id=17335; collection_items.card_id=17335; printing_variant=normal; variant_label=NULL; finish=NULL; treatment=NULL; source_variant=Base; release_kind=original; art_kind=base; catalog_status=active
- **external_id_evidence:** cardmarket_product idProduct=733317; scope=mixed; metadata={"allowed_languages":["en","jp","zh-CN","kr","fr"]} || cardmarket_product idProduct=747476; scope=mixed; metadata={"allowed_languages":["en","jp","zh-CN","kr","fr"]}
- **scryfall_evidence:** Not applicable to One Piece.
- **cardtrader_evidence:** Blueprint id=270404; scope=exact; metadata={"release_id":3461,"version":null} || card_images source_card_id=270404; source_variant=Base; source_collector_number=OP05-032; image_language_scope=en; fallback=1
- **historical_url_evidence:** No historical Cardmarket URL found in local provenance.
- **provenance_gap:** false
- **lost_fields:** NULL
- **original_value:** NULL
- **current_value:** Not detected
- **confidence_reason:** Local provenance identifies op05 + OP05-032 + jp + variant=Base; Cardmarket candidates remain language_scope=mixed and no unique Cardmarket idProduct is locally proven. CardTrader is auxiliary only.
- **remaining_blocker:** Verify externally which candidate is the exact JP set/release/version/variant; no price-based selection.
- **next_action:** Inspect Cardmarket candidates 733317|747476 and verify JP + op05 + Base / release; record one idProduct only after evidence.

#### Item `149` — Kin'emon

- **collection_item_id:** 149
- **game:** One Piece
- **card:** Kin'emon
- **current_status:** AMBIGUOUS
- **classification:** MANUAL_WEB_REVIEW
- **recovered_cardmarket_id:** None
- **candidate_cardmarket_ids:** 690844|768285
- **original_import_evidence:** coleccion-a-cargar.numbers exists as historical source; no matching row-level record is present in the derived review CSV.
- **legacy_evidence:** cards.id=15366; collection_items.card_id=15366; printing_variant=normal; variant_label=NULL; finish=NULL; treatment=NULL; source_variant=Base; release_kind=original; art_kind=base; catalog_status=active
- **external_id_evidence:** cardmarket_product idProduct=690844; scope=mixed; metadata={"allowed_languages":["en","jp","zh-CN","kr","fr"]} || cardmarket_product idProduct=768285; scope=mixed; metadata={"allowed_languages":["en","jp","zh-CN","kr","fr"]}
- **scryfall_evidence:** Not applicable to One Piece.
- **cardtrader_evidence:** Blueprint id=244548; scope=exact; metadata={"release_id":3332,"version":null} || card_images source_card_id=244548; source_variant=Base; source_collector_number=OP01-040; image_language_scope=en; fallback=1
- **historical_url_evidence:** No historical Cardmarket URL found in local provenance.
- **provenance_gap:** false
- **lost_fields:** NULL
- **original_value:** NULL
- **current_value:** Not detected
- **confidence_reason:** Local provenance identifies op01 + OP01-040 + jp + variant=Base; Cardmarket candidates remain language_scope=mixed and no unique Cardmarket idProduct is locally proven. CardTrader is auxiliary only.
- **remaining_blocker:** Verify externally which candidate is the exact JP set/release/version/variant; no price-based selection.
- **next_action:** Inspect Cardmarket candidates 690844|768285 and verify JP + op01 + Base / release; record one idProduct only after evidence.

#### Item `150` — Trafalgar Law

- **collection_item_id:** 150
- **game:** One Piece
- **card:** Trafalgar Law
- **current_status:** AMBIGUOUS
- **classification:** MANUAL_WEB_REVIEW
- **recovered_cardmarket_id:** None
- **candidate_cardmarket_ids:** 823481
- **original_import_evidence:** coleccion-a-cargar.numbers exists as historical source; no matching row-level record is present in the derived review CSV.
- **legacy_evidence:** cards.id=21108; collection_items.card_id=21108; printing_variant=normal; variant_label=NULL; finish=NULL; treatment=NULL; source_variant=Base; release_kind=original; art_kind=base; catalog_status=active
- **external_id_evidence:** cardmarket_product idProduct=823481; scope=mixed; metadata={"allowed_languages":["en","jp","zh-CN","kr","fr"]}
- **scryfall_evidence:** Not applicable to One Piece.
- **cardtrader_evidence:** Blueprint id=330404; scope=exact; metadata={"release_id":4123,"version":null} || card_images source_card_id=330404; source_variant=Base; source_collector_number=EB02-045; image_language_scope=en; fallback=1
- **historical_url_evidence:** No historical Cardmarket URL found in local provenance.
- **provenance_gap:** false
- **lost_fields:** NULL
- **original_value:** NULL
- **current_value:** Not detected
- **confidence_reason:** Local provenance identifies eb-02 + EB02-045 + jp + variant=Base; Cardmarket candidates remain language_scope=mixed and no unique Cardmarket idProduct is locally proven. CardTrader is auxiliary only.
- **remaining_blocker:** Verify externally which candidate is the exact JP set/release/version/variant; no price-based selection.
- **next_action:** Inspect Cardmarket candidates 823481 and verify JP + eb-02 + Base / release; record one idProduct only after evidence.

#### Item `151` — Uta

- **collection_item_id:** 151
- **game:** One Piece
- **card:** Uta
- **current_status:** AMBIGUOUS
- **classification:** MANUAL_WEB_REVIEW
- **recovered_cardmarket_id:** None
- **candidate_cardmarket_ids:** 845271|857215
- **original_import_evidence:** coleccion-a-cargar.numbers exists as historical source; no matching row-level record is present in the derived review CSV.
- **legacy_evidence:** cards.id=22257; collection_items.card_id=22257; printing_variant=normal; variant_label=NULL; finish=NULL; treatment=NULL; source_variant=Base; release_kind=original; art_kind=base; catalog_status=active
- **external_id_evidence:** cardmarket_product idProduct=845271; scope=mixed; metadata={"allowed_languages":["en","jp","zh-CN","kr","fr"]} || cardmarket_product idProduct=857215; scope=mixed; metadata={"allowed_languages":["en","jp","zh-CN","kr","fr"]}
- **scryfall_evidence:** Not applicable to One Piece.
- **cardtrader_evidence:** Blueprint id=354345; scope=exact; metadata={"release_id":4241,"version":null} || card_images source_card_id=354345; source_variant=Base; source_collector_number=OP13-023; image_language_scope=en; fallback=1
- **historical_url_evidence:** No historical Cardmarket URL found in local provenance.
- **provenance_gap:** false
- **lost_fields:** NULL
- **original_value:** NULL
- **current_value:** Not detected
- **confidence_reason:** Local provenance identifies op13 + OP13-023 + jp + variant=Base; Cardmarket candidates remain language_scope=mixed and no unique Cardmarket idProduct is locally proven. CardTrader is auxiliary only.
- **remaining_blocker:** Verify externally which candidate is the exact JP set/release/version/variant; no price-based selection.
- **next_action:** Inspect Cardmarket candidates 845271|857215 and verify JP + op13 + Base / release; record one idProduct only after evidence.

#### Item `152` — Trafalgar Law

- **collection_item_id:** 152
- **game:** One Piece
- **card:** Trafalgar Law
- **current_status:** AMBIGUOUS
- **classification:** MANUAL_WEB_REVIEW
- **recovered_cardmarket_id:** None
- **candidate_cardmarket_ids:** 722798
- **original_import_evidence:** coleccion-a-cargar.numbers exists as historical source; no matching row-level record is present in the derived review CSV.
- **legacy_evidence:** cards.id=14625; collection_items.card_id=14625; printing_variant=normal; variant_label=NULL; finish=NULL; treatment=NULL; source_variant=Base; release_kind=promo; art_kind=base; catalog_status=active
- **external_id_evidence:** cardmarket_product idProduct=722798; scope=mixed; metadata={"allowed_languages":["en","jp","zh-CN","kr","fr"]}
- **scryfall_evidence:** Not applicable to One Piece.
- **cardtrader_evidence:** Blueprint id=256657; scope=exact; metadata={"release_id":3324,"version":null} || card_images source_card_id=256657; source_variant=NULL; source_collector_number=P-038; image_language_scope=jp; fallback=0
- **historical_url_evidence:** No historical Cardmarket URL found in local provenance.
- **provenance_gap:** false
- **lost_fields:** NULL
- **original_value:** NULL
- **current_value:** Not detected
- **confidence_reason:** Local provenance identifies promo + P-038 + jp + variant=Base; Cardmarket candidates remain language_scope=mixed and no unique Cardmarket idProduct is locally proven. CardTrader is auxiliary only.
- **remaining_blocker:** Verify externally which candidate is the exact JP set/release/version/variant; no price-based selection.
- **next_action:** Inspect Cardmarket candidates 722798 and verify JP + promo + Base / release; record one idProduct only after evidence.

#### Item `153` — Stussy

- **collection_item_id:** 153
- **game:** One Piece
- **card:** Stussy
- **current_status:** AMBIGUOUS
- **classification:** MANUAL_WEB_REVIEW
- **recovered_cardmarket_id:** None
- **candidate_cardmarket_ids:** 845660|857326
- **original_import_evidence:** coleccion-a-cargar.numbers exists as historical source; no matching row-level record is present in the derived review CSV.
- **legacy_evidence:** cards.id=22273; collection_items.card_id=22273; printing_variant=normal; variant_label=NULL; finish=NULL; treatment=NULL; source_variant=Base; release_kind=original; art_kind=base; catalog_status=active
- **external_id_evidence:** cardmarket_product idProduct=845660; scope=mixed; metadata={"allowed_languages":["en","jp","zh-CN","kr","fr"]} || cardmarket_product idProduct=857326; scope=mixed; metadata={"allowed_languages":["en","jp","zh-CN","kr","fr"]}
- **scryfall_evidence:** Not applicable to One Piece.
- **cardtrader_evidence:** Blueprint id=354353; scope=exact; metadata={"release_id":4241,"version":null} || card_images source_card_id=354353; source_variant=Base; source_collector_number=OP13-110; image_language_scope=en; fallback=1
- **historical_url_evidence:** No historical Cardmarket URL found in local provenance.
- **provenance_gap:** false
- **lost_fields:** NULL
- **original_value:** NULL
- **current_value:** Not detected
- **confidence_reason:** Local provenance identifies op13 + OP13-110 + jp + variant=Base; Cardmarket candidates remain language_scope=mixed and no unique Cardmarket idProduct is locally proven. CardTrader is auxiliary only.
- **remaining_blocker:** Verify externally which candidate is the exact JP set/release/version/variant; no price-based selection.
- **next_action:** Inspect Cardmarket candidates 845660|857326 and verify JP + op13 + Base / release; record one idProduct only after evidence.

#### Item `154` — King

- **collection_item_id:** 154
- **game:** One Piece
- **card:** King
- **current_status:** AMBIGUOUS
- **classification:** MANUAL_WEB_REVIEW
- **recovered_cardmarket_id:** None
- **candidate_cardmarket_ids:** 690929|768358
- **original_import_evidence:** coleccion-a-cargar.numbers exists as historical source; no matching row-level record is present in the derived review CSV.
- **legacy_evidence:** cards.id=15503; collection_items.card_id=15503; printing_variant=normal; variant_label=Fixed Reprint; finish=NULL; treatment=NULL; source_variant=Fixed Reprint; release_kind=reprint; art_kind=base; catalog_status=active
- **external_id_evidence:** cardmarket_product idProduct=690929; scope=mixed; metadata={"allowed_languages":["en","jp","zh-CN","kr","fr"]} || cardmarket_product idProduct=768358; scope=mixed; metadata={"allowed_languages":["en","jp","zh-CN","kr","fr"]}
- **scryfall_evidence:** Not applicable to One Piece.
- **cardtrader_evidence:** Blueprint id=244639; scope=exact; metadata={"release_id":3332,"version":"Fixed Reprint"} || card_images source_card_id=244639; source_variant=Fixed Reprint; source_collector_number=OP01-096; image_language_scope=en; fallback=1
- **historical_url_evidence:** No historical Cardmarket URL found in local provenance.
- **provenance_gap:** false
- **lost_fields:** NULL
- **original_value:** NULL
- **current_value:** Not detected
- **confidence_reason:** Local provenance identifies op01 + OP01-096 + jp + variant=Fixed Reprint; Cardmarket candidates remain language_scope=mixed and no unique Cardmarket idProduct is locally proven. CardTrader is auxiliary only.
- **remaining_blocker:** Verify externally which candidate is the exact JP set/release/version/variant; no price-based selection.
- **next_action:** Inspect Cardmarket candidates 690929|768358 and verify JP + op01 + Fixed Reprint / release; record one idProduct only after evidence.

#### Item `155` — Rebecca

- **collection_item_id:** 155
- **game:** One Piece
- **card:** Rebecca
- **current_status:** AMBIGUOUS
- **classification:** MANUAL_WEB_REVIEW
- **recovered_cardmarket_id:** None
- **candidate_cardmarket_ids:** 733426|747775
- **original_import_evidence:** coleccion-a-cargar.numbers exists as historical source; no matching row-level record is present in the derived review CSV.
- **legacy_evidence:** cards.id=17179; collection_items.card_id=17179; printing_variant=normal; variant_label=NULL; finish=NULL; treatment=NULL; source_variant=Base; release_kind=original; art_kind=base; catalog_status=active
- **external_id_evidence:** cardmarket_product idProduct=733426; scope=mixed; metadata={"allowed_languages":["en","jp","zh-CN","kr","fr"]} || cardmarket_product idProduct=747775; scope=mixed; metadata={"allowed_languages":["en","jp","zh-CN","kr","fr"]}
- **scryfall_evidence:** Not applicable to One Piece.
- **cardtrader_evidence:** Blueprint id=269205; scope=exact; metadata={"release_id":3461,"version":null} || card_images source_card_id=269205; source_variant=Base; source_collector_number=OP05-091; image_language_scope=en; fallback=1
- **historical_url_evidence:** No historical Cardmarket URL found in local provenance.
- **provenance_gap:** false
- **lost_fields:** NULL
- **original_value:** NULL
- **current_value:** Not detected
- **confidence_reason:** Local provenance identifies op05 + OP05-091 + jp + variant=Base; Cardmarket candidates remain language_scope=mixed and no unique Cardmarket idProduct is locally proven. CardTrader is auxiliary only.
- **remaining_blocker:** Verify externally which candidate is the exact JP set/release/version/variant; no price-based selection.
- **next_action:** Inspect Cardmarket candidates 733426|747775 and verify JP + op05 + Base / release; record one idProduct only after evidence.

### Magic

#### Item `34` — Frodo, Sauron's Bane

- **collection_item_id:** 34
- **game:** Magic
- **card:** Frodo, Sauron's Bane
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 701765
- **candidate_cardmarket_ids:** 701765
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=31; variant=borderless; set_hint=LTR; card_number=NULL; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Frodo-Saurons-Bane-V2 || collection-ambiguous-review.done.csv source_row=31; variant=borderless; set_hint=LTR; card_number=NULL; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Frodo-Saurons-Bane-V2 || collection-ambiguous-review.done.csv source_row=31; variant=borderless; set_hint=LTR; card_number=NULL; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Frodo-Saurons-Bane-V2 || collection-ambiguous-review.done.csv source_row=31; variant=borderless; set_hint=LTR; card_number=NULL; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Frodo-Saurons-Bane-V2
- **legacy_evidence:** cards.id=12872; collection_items.card_id=12872; printing_variant=normal; variant_label=Showcase; finish=foil; treatment=Showcase; source_variant=6d08e637-c2b3-4b38-9b07-5bba1f13efc3:foil; release_kind=original; art_kind=alternate_art; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=701765; status=mapped
- **scryfall_evidence:** scryfall_id=6d08e637-c2b3-4b38-9b07-5bba1f13efc3; scryfall_raw={"booster":false,"border_color":"borderless","cardmarket_id":701765,"collector_number":"304","finishes":["nonfoil","foil"],"frame_effects":["legendary","showcase"],"full_art":false,"id":"6d08e637-c2b3-4b38-9b07-5bba1f13efc3","promo_types":["universesbeyond","boosterfun"],"set":"ltr","variation":false}
- **cardtrader_evidence:** No relevant CardTrader Blueprint/image provenance.
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Frodo-Saurons-Bane-V2 || https://www.cardmarket.com/en/Magic/Products?idProduct=701765&referrer=scryfall&utm_campaign=card_prices&utm_medium=text&utm_source=scryfall
- **provenance_gap:** false
- **lost_fields:** NULL
- **original_value:** NULL
- **current_value:** Not detected
- **confidence_reason:** Unique Scryfall printing id=6d08e637-c2b3-4b38-9b07-5bba1f13efc3; raw set=ltr + collector_number=304 + cardmarket_id=701765; finish=foil is present; treatment=Showcase is compatible because frame_effects contains showcase; scalar raw cardmarket_id is the unique recovered product.
- **remaining_blocker:** None for identity recovery; this report does not authorize pricing/apply/approval.
- **next_action:** Retain idProduct 701765 as audit evidence; do not modify the review CSV or approve this row.

#### Item `41` — Aragorn, Company Leader

- **collection_item_id:** 41
- **game:** Magic
- **card:** Aragorn, Company Leader
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 717763
- **candidate_cardmarket_ids:** 717763
- **original_import_evidence:** coleccion-a-cargar.numbers exists as historical source; no matching row-level record is present in the derived review CSV.
- **legacy_evidence:** cards.id=12896; collection_items.card_id=12896; printing_variant=normal; variant_label=Showcase; finish=foil; treatment=Showcase; source_variant=142c3004-fe39-4ca3-bf14-f4af8b20fa80:foil; release_kind=original; art_kind=alternate_art; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=717763; status=mapped
- **scryfall_evidence:** scryfall_id=142c3004-fe39-4ca3-bf14-f4af8b20fa80; scryfall_raw={"booster":false,"border_color":"borderless","cardmarket_id":717763,"collector_number":"316","finishes":["nonfoil","foil"],"frame_effects":["legendary","showcase"],"full_art":false,"id":"142c3004-fe39-4ca3-bf14-f4af8b20fa80","promo_types":["universesbeyond","boosterfun"],"set":"ltr","variation":false}
- **cardtrader_evidence:** No relevant CardTrader Blueprint/image provenance.
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products?idProduct=717763&referrer=scryfall&utm_campaign=card_prices&utm_medium=text&utm_source=scryfall
- **provenance_gap:** false
- **lost_fields:** NULL
- **original_value:** NULL
- **current_value:** Not detected
- **confidence_reason:** Unique Scryfall printing id=142c3004-fe39-4ca3-bf14-f4af8b20fa80; raw set=ltr + collector_number=316 + cardmarket_id=717763; finish=foil is present; treatment=Showcase is compatible because frame_effects contains showcase; scalar raw cardmarket_id is the unique recovered product.
- **remaining_blocker:** None for identity recovery; this report does not authorize pricing/apply/approval.
- **next_action:** Retain idProduct 717763 as audit evidence; do not modify the review CSV or approve this row.

#### Item `42` — Aragorn, the Uniter

- **collection_item_id:** 42
- **game:** Magic
- **card:** Aragorn, the Uniter
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 716022
- **candidate_cardmarket_ids:** 716022
- **original_import_evidence:** coleccion-a-cargar.numbers exists as historical source; no matching row-level record is present in the derived review CSV.
- **legacy_evidence:** cards.id=12898; collection_items.card_id=12898; printing_variant=normal; variant_label=Showcase; finish=foil; treatment=Showcase; source_variant=e287844c-a829-4f7f-8c4c-ab856e6815f6:foil; release_kind=original; art_kind=alternate_art; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=716022; status=mapped
- **scryfall_evidence:** scryfall_id=e287844c-a829-4f7f-8c4c-ab856e6815f6; scryfall_raw={"booster":false,"border_color":"borderless","cardmarket_id":716022,"collector_number":"317","finishes":["nonfoil","foil"],"frame_effects":["legendary","showcase"],"full_art":false,"id":"e287844c-a829-4f7f-8c4c-ab856e6815f6","promo_types":["universesbeyond","boosterfun"],"set":"ltr","variation":false}
- **cardtrader_evidence:** No relevant CardTrader Blueprint/image provenance.
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products?idProduct=716022&referrer=scryfall&utm_campaign=card_prices&utm_medium=text&utm_source=scryfall
- **provenance_gap:** false
- **lost_fields:** NULL
- **original_value:** NULL
- **current_value:** Not detected
- **confidence_reason:** Unique Scryfall printing id=e287844c-a829-4f7f-8c4c-ab856e6815f6; raw set=ltr + collector_number=317 + cardmarket_id=716022; finish=foil is present; treatment=Showcase is compatible because frame_effects contains showcase; scalar raw cardmarket_id is the unique recovered product.
- **remaining_blocker:** None for identity recovery; this report does not authorize pricing/apply/approval.
- **next_action:** Retain idProduct 716022 as audit evidence; do not modify the review CSV or approve this row.

#### Item `46` — Gimli, Mournful Avenger

- **collection_item_id:** 46
- **game:** Magic
- **card:** Gimli, Mournful Avenger
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 737034
- **candidate_cardmarket_ids:** 737034
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=42; variant=borderless; set_hint=LTR; card_number=NULL; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Gimli-Mournful-Avenger-V2 || collection-ambiguous-review.done.csv source_row=42; variant=borderless; set_hint=LTR; card_number=NULL; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Gimli-Mournful-Avenger-V2 || collection-ambiguous-review.done.csv source_row=42; variant=borderless; set_hint=LTR; card_number=NULL; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Gimli-Mournful-Avenger-V2 || collection-ambiguous-review.done.csv source_row=42; variant=borderless; set_hint=LTR; card_number=NULL; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Gimli-Mournful-Avenger-V2
- **legacy_evidence:** cards.id=13804; collection_items.card_id=13804; printing_variant=normal; variant_label=Surge Foil; finish=foil; treatment=Surge Foil; source_variant=44f74a7c-9bf1-4bd9-ac56-8a186ac140f0:foil; release_kind=original; art_kind=base; catalog_status=active collection notes=sin candidatas en cards (producto fuera del catalogo importado) | Version Surge Foil | link: https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Holiday-Release/Gimli-Mournful-Avenger-V3
- **external_id_evidence:** cardmarket_product_mappings current=737034; status=mapped
- **scryfall_evidence:** scryfall_id=44f74a7c-9bf1-4bd9-ac56-8a186ac140f0; scryfall_raw={"booster":false,"border_color":"borderless","cardmarket_id":737034,"collector_number":"815","finishes":["foil"],"frame_effects":["showcase","legendary"],"full_art":false,"id":"44f74a7c-9bf1-4bd9-ac56-8a186ac140f0","promo_types":["surgefoil","universesbeyond","boosterfun"],"set":"ltr","variation":false}
- **cardtrader_evidence:** No relevant CardTrader Blueprint/image provenance.
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Gimli-Mournful-Avenger-V2 || https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Holiday-Release/Gimli-Mournful-Avenger-V3 || https://www.cardmarket.com/en/Magic/Products?idProduct=737034&referrer=scryfall&utm_campaign=card_prices&utm_medium=text&utm_source=scryfall
- **provenance_gap:** false
- **lost_fields:** NULL
- **original_value:** NULL
- **current_value:** Not detected
- **confidence_reason:** Unique Scryfall printing id=44f74a7c-9bf1-4bd9-ac56-8a186ac140f0; raw set=ltr + collector_number=815 + cardmarket_id=737034; finish=foil is present; treatment=Surge Foil is compatible because promo_types contains surgefoil; scalar raw cardmarket_id is the unique recovered product.
- **remaining_blocker:** None for identity recovery; this report does not authorize pricing/apply/approval.
- **next_action:** Retain idProduct 737034 as audit evidence; do not modify the review CSV or approve this row.

#### Item `47` — Boromir, Warden of the Tower

- **collection_item_id:** 47
- **game:** Magic
- **card:** Boromir, Warden of the Tower
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 716042
- **candidate_cardmarket_ids:** 716042
- **original_import_evidence:** coleccion-a-cargar.numbers exists as historical source; no matching row-level record is present in the derived review CSV.
- **legacy_evidence:** cards.id=12868; collection_items.card_id=12868; printing_variant=normal; variant_label=Showcase; finish=foil; treatment=Showcase; source_variant=e186ef93-f369-4b4d-a683-36f338b6ce3f:foil; release_kind=original; art_kind=alternate_art; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=716042; status=mapped
- **scryfall_evidence:** scryfall_id=e186ef93-f369-4b4d-a683-36f338b6ce3f; scryfall_raw={"booster":false,"border_color":"borderless","cardmarket_id":716042,"collector_number":"302","finishes":["nonfoil","foil"],"frame_effects":["legendary","showcase"],"full_art":false,"id":"e186ef93-f369-4b4d-a683-36f338b6ce3f","promo_types":["universesbeyond","boosterfun"],"set":"ltr","variation":false}
- **cardtrader_evidence:** No relevant CardTrader Blueprint/image provenance.
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products?idProduct=716042&referrer=scryfall&utm_campaign=card_prices&utm_medium=text&utm_source=scryfall
- **provenance_gap:** false
- **lost_fields:** NULL
- **original_value:** NULL
- **current_value:** Not detected
- **confidence_reason:** Unique Scryfall printing id=e186ef93-f369-4b4d-a683-36f338b6ce3f; raw set=ltr + collector_number=302 + cardmarket_id=716042; finish=foil is present; treatment=Showcase is compatible because frame_effects contains showcase; scalar raw cardmarket_id is the unique recovered product.
- **remaining_blocker:** None for identity recovery; this report does not authorize pricing/apply/approval.
- **next_action:** Retain idProduct 716042 as audit evidence; do not modify the review CSV or approve this row.

#### Item `65` — Shortcut to Mushrooms

- **collection_item_id:** 65
- **game:** Magic
- **card:** Shortcut to Mushrooms
- **current_status:** MISMATCH
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 738134
- **candidate_cardmarket_ids:** 717004|738134
- **original_import_evidence:** coleccion-a-cargar.numbers exists as historical source; no matching row-level record is present in the derived review CSV.
- **legacy_evidence:** cards.id=13505; collection_items.card_id=13505; printing_variant=normal; variant_label=Showcase; finish=foil; treatment=Showcase; source_variant=aab671b7-afb3-4d99-8f6d-3240f31508d7:foil; release_kind=original; art_kind=alternate_art; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=717004; status=mapped
- **scryfall_evidence:** scryfall_id=aab671b7-afb3-4d99-8f6d-3240f31508d7; scryfall_raw={"booster":false,"border_color":"black","cardmarket_id":738134,"collector_number":"638","finishes":["nonfoil","foil"],"frame_effects":["showcase"],"full_art":false,"id":"aab671b7-afb3-4d99-8f6d-3240f31508d7","promo_types":["silverfoil","scroll","universesbeyond","boosterfun"],"set":"ltr","variation":false}
- **cardtrader_evidence:** No relevant CardTrader Blueprint/image provenance.
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products?idProduct=738134&referrer=scryfall&utm_campaign=card_prices&utm_medium=text&utm_source=scryfall
- **provenance_gap:** false
- **lost_fields:** NULL
- **original_value:** NULL
- **current_value:** Not detected
- **confidence_reason:** Unique Scryfall printing id=aab671b7-afb3-4d99-8f6d-3240f31508d7; raw set=ltr + collector_number=638 + cardmarket_id=738134; finish=foil is present; treatment=Showcase is compatible because frame_effects contains showcase; scalar raw cardmarket_id is the unique recovered product.
- **remaining_blocker:** None for identity recovery; this report does not authorize pricing/apply/approval.
- **next_action:** Retain idProduct 738134 as audit evidence; do not modify the review CSV or approve this row.

#### Item `70` — The Bath Song

- **collection_item_id:** 70
- **game:** Magic
- **card:** The Bath Song
- **current_status:** MISMATCH
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 737571
- **candidate_cardmarket_ids:** 716138|737570|737571
- **original_import_evidence:** No row-level match in derived review CSV; preserved manual-entry provenance: sin candidatas en cards (producto fuera del catalogo importado) | link: https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Holiday-Release/The-Bath-Song-V1
- **legacy_evidence:** cards.id=13211; collection_items.card_id=13211; printing_variant=normal; variant_label=Showcase; finish=foil; treatment=Showcase; source_variant=9dc2521f-d9a5-4ae7-b5dc-bf0504e66345:foil; release_kind=original; art_kind=alternate_art; catalog_status=active collection notes=sin candidatas en cards (producto fuera del catalogo importado) | link: https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Holiday-Release/The-Bath-Song-V1
- **external_id_evidence:** cardmarket_product_mappings current=716138; status=mapped || cardmarket_product_mappings current=737570; status=mapped
- **scryfall_evidence:** scryfall_id=9dc2521f-d9a5-4ae7-b5dc-bf0504e66345; scryfall_raw={"booster":false,"border_color":"black","cardmarket_id":737571,"collector_number":"491","finishes":["nonfoil","foil"],"frame_effects":["showcase"],"full_art":false,"id":"9dc2521f-d9a5-4ae7-b5dc-bf0504e66345","promo_types":["silverfoil","scroll","universesbeyond","boosterfun"],"set":"ltr","variation":false}
- **cardtrader_evidence:** No relevant CardTrader Blueprint/image provenance.
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Holiday-Release/The-Bath-Song-V1 || https://www.cardmarket.com/en/Magic/Products?idProduct=737571&referrer=scryfall&utm_campaign=card_prices&utm_medium=text&utm_source=scryfall
- **provenance_gap:** false
- **lost_fields:** NULL
- **original_value:** NULL
- **current_value:** Not detected
- **confidence_reason:** Unique Scryfall printing id=9dc2521f-d9a5-4ae7-b5dc-bf0504e66345; raw set=ltr + collector_number=491 + cardmarket_id=737571; finish=foil is present; treatment=Showcase is compatible because frame_effects contains showcase; scalar raw cardmarket_id is the unique recovered product.
- **remaining_blocker:** None for identity recovery; this report does not authorize pricing/apply/approval.
- **next_action:** Retain idProduct 737571 as audit evidence; do not modify the review CSV or approve this row.

#### Item `82` — Gimli, Mournful Avenger

- **collection_item_id:** 82
- **game:** Magic
- **card:** Gimli, Mournful Avenger
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 716059
- **candidate_cardmarket_ids:** 716059
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=42; variant=borderless; set_hint=LTR; card_number=NULL; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Gimli-Mournful-Avenger-V2 || collection-ambiguous-review.done.csv source_row=42; variant=borderless; set_hint=LTR; card_number=NULL; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Gimli-Mournful-Avenger-V2 || collection-ambiguous-review.done.csv source_row=42; variant=borderless; set_hint=LTR; card_number=NULL; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Gimli-Mournful-Avenger-V2 || collection-ambiguous-review.done.csv source_row=42; variant=borderless; set_hint=LTR; card_number=NULL; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Gimli-Mournful-Avenger-V2
- **legacy_evidence:** cards.id=13101; collection_items.card_id=13101; printing_variant=normal; variant_label=Scene; finish=foil; treatment=Scene; source_variant=3a8bd920-5e70-4c3d-bd15-ccb8d1c87e2e:foil; release_kind=original; art_kind=base; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=716059; status=mapped
- **scryfall_evidence:** scryfall_id=3a8bd920-5e70-4c3d-bd15-ccb8d1c87e2e; scryfall_raw={"booster":true,"border_color":"borderless","cardmarket_id":716059,"collector_number":"436","finishes":["nonfoil","foil"],"frame_effects":["legendary","inverted"],"full_art":true,"id":"3a8bd920-5e70-4c3d-bd15-ccb8d1c87e2e","promo_types":["boosterfun","universesbeyond"],"set":"ltr","variation":false}
- **cardtrader_evidence:** No relevant CardTrader Blueprint/image provenance.
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Gimli-Mournful-Avenger-V2 || https://www.cardmarket.com/en/Magic/Products?idProduct=716059&referrer=scryfall&utm_campaign=card_prices&utm_medium=text&utm_source=scryfall
- **provenance_gap:** false
- **lost_fields:** NULL
- **original_value:** NULL
- **current_value:** Not detected
- **confidence_reason:** Unique Scryfall printing id=3a8bd920-5e70-4c3d-bd15-ccb8d1c87e2e; raw set=ltr + collector_number=436 + cardmarket_id=716059; finish=foil is present; treatment=Scene is compatible because full_art=true and frame_effects contains inverted; scalar raw cardmarket_id is the unique recovered product.
- **remaining_blocker:** None for identity recovery; this report does not authorize pricing/apply/approval.
- **next_action:** Retain idProduct 716059 as audit evidence; do not modify the review CSV or approve this row.

#### Item `84` — Art Series: Fog on the Barrow-Downs

- **collection_item_id:** 84
- **game:** Magic
- **card:** Art Series: Fog on the Barrow-Downs
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718546
- **candidate_cardmarket_ids:** 718545|718546
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=45; variant=gold_stamp; set_hint=LTR; card_number=2.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Fog-on-the-Barrow-Downs-V2 || collection-ambiguous-review.done.csv source_row=45; variant=gold_stamp; set_hint=LTR; card_number=2.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Fog-on-the-Barrow-Downs-V2 || collection-ambiguous-review.done.csv source_row=45; variant=gold_stamp; set_hint=LTR; card_number=2.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Fog-on-the-Barrow-Downs-V2
- **legacy_evidence:** cards.id=545; collection_items.card_id=545; printing_variant=normal; variant_label=Art Series; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718546; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250713; source_variant=NULL; source_collector_number=A02; image_language_scope=en; fallback=0 || CONFLICT: CardTrader image collector=A02 vs collection=ART-2
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Fog-on-the-Barrow-Downs-V2
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Fog-on-the-Barrow-Downs-V2
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Cardmarket V2, original gold_stamp + ART-A2 + EN + LTR, and local catalog identify one compatible Gold-Stamped product idProduct=718546; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718546 as final audit evidence; do not modify mappings or approve the review CSV.

#### Item `86` — Art Series: Goldberry, River-Daughter

- **collection_item_id:** 86
- **game:** Magic
- **card:** Art Series: Goldberry, River-Daughter
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718554
- **candidate_cardmarket_ids:** 718553|718554
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=47; variant=gold_stamp; set_hint=LTR; card_number=6.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Goldberry-River-Daughter-V2 || collection-ambiguous-review.done.csv source_row=47; variant=gold_stamp; set_hint=LTR; card_number=6.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Goldberry-River-Daughter-V2 || collection-ambiguous-review.done.csv source_row=47; variant=gold_stamp; set_hint=LTR; card_number=6.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Goldberry-River-Daughter-V2 || collection-ambiguous-review.done.csv source_row=47; variant=gold_stamp; set_hint=LTR; card_number=6.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Goldberry-River-Daughter-V2 || collection-ambiguous-review.done.csv source_row=47; variant=gold_stamp; set_hint=LTR; card_number=6.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Goldberry-River-Daughter-V2
- **legacy_evidence:** cards.id=553; collection_items.card_id=553; printing_variant=normal; variant_label=Art Series; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718554; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250762; source_variant=NULL; source_collector_number=A06; image_language_scope=en; fallback=0 || CONFLICT: CardTrader image collector=A06 vs collection=ART-6
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Goldberry-River-Daughter-V2
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Goldberry-River-Daughter-V2
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Cardmarket V2, original gold_stamp + ART-A6 + EN + LTR, and local catalog identify one compatible Gold-Stamped product idProduct=718554; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718554 as final audit evidence; do not modify mappings or approve the review CSV.

#### Item `87` — Art Series: The Watcher in the Water

- **collection_item_id:** 87
- **game:** Magic
- **card:** Art Series: The Watcher in the Water
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718555
- **candidate_cardmarket_ids:** 718555|718556
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=48; variant=gold_stamp; set_hint=LTR; card_number=7.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-The-Watcher-in-the-Water-V2 || collection-ambiguous-review.done.csv source_row=48; variant=gold_stamp; set_hint=LTR; card_number=7.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-The-Watcher-in-the-Water-V2 || collection-ambiguous-review.done.csv source_row=48; variant=gold_stamp; set_hint=LTR; card_number=7.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-The-Watcher-in-the-Water-V2 || collection-ambiguous-review.done.csv source_row=48; variant=gold_stamp; set_hint=LTR; card_number=7.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-The-Watcher-in-the-Water-V2 || collection-ambiguous-review.done.csv source_row=48; variant=gold_stamp; set_hint=LTR; card_number=7.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-The-Watcher-in-the-Water-V2
- **legacy_evidence:** cards.id=554; collection_items.card_id=554; printing_variant=normal; variant_label=Art Series; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718555; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250777; source_variant=NULL; source_collector_number=A07; image_language_scope=en; fallback=0 || CONFLICT: CardTrader image collector=A07 vs collection=ART-7
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-The-Watcher-in-the-Water-V2
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-The-Watcher-in-the-Water-V2
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Cardmarket V2, original gold_stamp + ART-A7 + EN + LTR, and local catalog identify one compatible Gold-Stamped product idProduct=718555; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718555 as final audit evidence; do not modify mappings or approve the review CSV.

#### Item `88` — Art Series: Éomer of the Riddermark

- **collection_item_id:** 88
- **game:** Magic
- **card:** Art Series: Éomer of the Riddermark
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718559
- **candidate_cardmarket_ids:** 718559|718560
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=49; variant=gold_stamp; set_hint=LTR; card_number=9.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Eomer-of-the-Riddermark-V2 || collection-ambiguous-review.done.csv source_row=49; variant=gold_stamp; set_hint=LTR; card_number=9.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Eomer-of-the-Riddermark-V2 || collection-ambiguous-review.done.csv source_row=49; variant=gold_stamp; set_hint=LTR; card_number=9.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Eomer-of-the-Riddermark-V2
- **legacy_evidence:** cards.id=558; collection_items.card_id=558; printing_variant=normal; variant_label=Art Series; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718559; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250707; source_variant=NULL; source_collector_number=A09; image_language_scope=en; fallback=0 || CONFLICT: CardTrader image collector=A09 vs collection=ART-9
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Eomer-of-the-Riddermark-V2
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Eomer-of-the-Riddermark-V2
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Cardmarket V2, original gold_stamp + ART-A9 + EN + LTR, and local catalog identify one compatible Gold-Stamped product idProduct=718559; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718559 as final audit evidence; do not modify mappings or approve the review CSV.

#### Item `89` — Art Series: Gimli, Counter of Kills

- **collection_item_id:** 89
- **game:** Magic
- **card:** Art Series: Gimli, Counter of Kills
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718561
- **candidate_cardmarket_ids:** 718561|718562|718654|718655
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=50; variant=gold_stamp; set_hint=LTR; card_number=10.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Gimli-Counter-of-Kills-V2 || collection-ambiguous-review.done.csv source_row=50; variant=gold_stamp; set_hint=LTR; card_number=10.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Gimli-Counter-of-Kills-V2 || collection-ambiguous-review.done.csv source_row=50; variant=gold_stamp; set_hint=LTR; card_number=10.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Gimli-Counter-of-Kills-V2 || collection-ambiguous-review.done.csv source_row=50; variant=gold_stamp; set_hint=LTR; card_number=10.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Gimli-Counter-of-Kills-V2 || collection-ambiguous-review.done.csv source_row=50; variant=gold_stamp; set_hint=LTR; card_number=10.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Gimli-Counter-of-Kills-V2 || collection-ambiguous-review.done.csv source_row=50; variant=gold_stamp; set_hint=LTR; card_number=10.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Gimli-Counter-of-Kills-V2
- **legacy_evidence:** cards.id=560; collection_items.card_id=560; printing_variant=other; variant_label=Gold-Stamped; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718561; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250688; source_variant=Gold-Stamped; source_collector_number=A10g; image_language_scope=en; fallback=0
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Gimli-Counter-of-Kills-V2
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Gimli-Counter-of-Kills-V2
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Cardmarket V2, original gold_stamp + ART-A10 + EN + LTR, and local catalog identify one compatible Gold-Stamped product idProduct=718561; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718561 as final audit evidence; do not modify mappings or approve the review CSV.

#### Item `90` — Art Series: Generous Ent

- **collection_item_id:** 90
- **game:** Magic
- **card:** Art Series: Generous Ent
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718563
- **candidate_cardmarket_ids:** 718563|718564
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=51; variant=gold_stamp; set_hint=LTR; card_number=11.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Generous-Ent-V2 || collection-ambiguous-review.done.csv source_row=51; variant=gold_stamp; set_hint=LTR; card_number=11.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Generous-Ent-V2 || collection-ambiguous-review.done.csv source_row=51; variant=gold_stamp; set_hint=LTR; card_number=11.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Generous-Ent-V2
- **legacy_evidence:** cards.id=562; collection_items.card_id=562; printing_variant=normal; variant_label=Art Series; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718563; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250706; source_variant=NULL; source_collector_number=A11; image_language_scope=en; fallback=0
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Generous-Ent-V2
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Generous-Ent-V2
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Cardmarket V2, original gold_stamp + ART-A11 + EN + LTR, and local catalog identify one compatible Gold-Stamped product idProduct=718563; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718563 as final audit evidence; do not modify mappings or approve the review CSV.

#### Item `91` — Art Series: Mirrormere Guardian

- **collection_item_id:** 91
- **game:** Magic
- **card:** Art Series: Mirrormere Guardian
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718565
- **candidate_cardmarket_ids:** 718565|718566
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=52; variant=gold_stamp; set_hint=LTR; card_number=12.0; language=en; notes=NULL; cardmarket_link=https://product-images.s3.cardmarket.com/1/XLTR/718565/718565.jpg || collection-ambiguous-review.done.csv source_row=52; variant=gold_stamp; set_hint=LTR; card_number=12.0; language=en; notes=NULL; cardmarket_link=https://product-images.s3.cardmarket.com/1/XLTR/718565/718565.jpg || collection-ambiguous-review.done.csv source_row=52; variant=gold_stamp; set_hint=LTR; card_number=12.0; language=en; notes=NULL; cardmarket_link=https://product-images.s3.cardmarket.com/1/XLTR/718565/718565.jpg
- **legacy_evidence:** cards.id=565; collection_items.card_id=565; printing_variant=normal; variant_label=Art Series; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718566; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250745; source_variant=NULL; source_collector_number=A12; image_language_scope=en; fallback=0
- **historical_url_evidence:** https://product-images.s3.cardmarket.com/1/XLTR/718565/718565.jpg
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://product-images.s3.cardmarket.com/1/XLTR/718565/718565.jpg
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Unique local Cardmarket idProduct=718565 embedded in historical Cardmarket image URL; original import proves gold_stamp + ART-12 + name + EN + LTR; URL selects one product among 718565|718566. Current mapping is evidence only.
- **remaining_blocker:** None for identity recovery; this report does not authorize pricing/apply/approval.
- **next_action:** Retain idProduct 718565 as audit evidence; do not modify the review CSV or approve this row.

#### Item `92` — Art Series: Bilbo, Retired Burglar

- **collection_item_id:** 92
- **game:** Magic
- **card:** Art Series: Bilbo, Retired Burglar
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718575
- **candidate_cardmarket_ids:** 718573|718575
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=53; variant=gold_stamp; set_hint=LTR; card_number=14.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Bilbo-Retired-Burglar-V2 || collection-ambiguous-review.done.csv source_row=53; variant=gold_stamp; set_hint=LTR; card_number=14.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Bilbo-Retired-Burglar-V2 || collection-ambiguous-review.done.csv source_row=53; variant=gold_stamp; set_hint=LTR; card_number=14.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Bilbo-Retired-Burglar-V2 || collection-ambiguous-review.done.csv source_row=53; variant=gold_stamp; set_hint=LTR; card_number=14.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Bilbo-Retired-Burglar-V2 || collection-ambiguous-review.done.csv source_row=53; variant=gold_stamp; set_hint=LTR; card_number=14.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Bilbo-Retired-Burglar-V2
- **legacy_evidence:** cards.id=569; collection_items.card_id=569; printing_variant=normal; variant_label=Art Series; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718575; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250727; source_variant=NULL; source_collector_number=A14; image_language_scope=en; fallback=0
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Bilbo-Retired-Burglar-V2
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Bilbo-Retired-Burglar-V2
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Cardmarket V2, original gold_stamp + ART-A14 + EN + LTR, and local catalog identify one compatible Gold-Stamped product idProduct=718575; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718575 as final audit evidence; do not modify mappings or approve the review CSV.

#### Item `93` — Art Series: Legolas, Counter of Kills

- **collection_item_id:** 93
- **game:** Magic
- **card:** Art Series: Legolas, Counter of Kills
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718582
- **candidate_cardmarket_ids:** 718582|718583
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=54; variant=gold_stamp; set_hint=LTR; card_number=17.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Legolas-Counter-of-Kills-V2 || collection-ambiguous-review.done.csv source_row=54; variant=gold_stamp; set_hint=LTR; card_number=17.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Legolas-Counter-of-Kills-V2 || collection-ambiguous-review.done.csv source_row=54; variant=gold_stamp; set_hint=LTR; card_number=17.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Legolas-Counter-of-Kills-V2 || collection-ambiguous-review.done.csv source_row=54; variant=gold_stamp; set_hint=LTR; card_number=17.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Legolas-Counter-of-Kills-V2
- **legacy_evidence:** cards.id=574; collection_items.card_id=574; printing_variant=normal; variant_label=Art Series; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718582; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250753; source_variant=NULL; source_collector_number=A17; image_language_scope=en; fallback=0
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Legolas-Counter-of-Kills-V2
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Legolas-Counter-of-Kills-V2
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Cardmarket V2, original gold_stamp + ART-A17 + EN + LTR, and local catalog identify one compatible Gold-Stamped product idProduct=718582; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718582 as final audit evidence; do not modify mappings or approve the review CSV.

#### Item `94` — Art Series: Saruman of Many Colors

- **collection_item_id:** 94
- **game:** Magic
- **card:** Art Series: Saruman of Many Colors
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718601
- **candidate_cardmarket_ids:** 718600|718601
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=55; variant=gold_stamp; set_hint=LTR; card_number=20.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Saruman-of-Many-Colors-V2 || collection-ambiguous-review.done.csv source_row=55; variant=gold_stamp; set_hint=LTR; card_number=20.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Saruman-of-Many-Colors-V2 || collection-ambiguous-review.done.csv source_row=55; variant=gold_stamp; set_hint=LTR; card_number=20.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Saruman-of-Many-Colors-V2 || collection-ambiguous-review.done.csv source_row=55; variant=gold_stamp; set_hint=LTR; card_number=20.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Saruman-of-Many-Colors-V2 || collection-ambiguous-review.done.csv source_row=55; variant=gold_stamp; set_hint=LTR; card_number=20.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Saruman-of-Many-Colors-V2 || collection-ambiguous-review.done.csv source_row=55; variant=gold_stamp; set_hint=LTR; card_number=20.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Saruman-of-Many-Colors-V2
- **legacy_evidence:** cards.id=581; collection_items.card_id=581; printing_variant=normal; variant_label=Art Series; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718601; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250735; source_variant=NULL; source_collector_number=A20; image_language_scope=en; fallback=0
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Saruman-of-Many-Colors-V2
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Saruman-of-Many-Colors-V2
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Cardmarket V2, original gold_stamp + ART-A20 + EN + LTR, and local catalog identify one compatible Gold-Stamped product idProduct=718601; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718601 as final audit evidence; do not modify mappings or approve the review CSV.

#### Item `95` — Art Series: Sharkey, Tyrant of the Shire

- **collection_item_id:** 95
- **game:** Magic
- **card:** Art Series: Sharkey, Tyrant of the Shire
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718605
- **candidate_cardmarket_ids:** 718604|718605
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=56; variant=gold_stamp; set_hint=LTR; card_number=22.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Sharkey-Tyrant-of-the-Shire-V2 || collection-ambiguous-review.done.csv source_row=56; variant=gold_stamp; set_hint=LTR; card_number=22.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Sharkey-Tyrant-of-the-Shire-V2 || collection-ambiguous-review.done.csv source_row=56; variant=gold_stamp; set_hint=LTR; card_number=22.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Sharkey-Tyrant-of-the-Shire-V2 || collection-ambiguous-review.done.csv source_row=56; variant=gold_stamp; set_hint=LTR; card_number=22.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Sharkey-Tyrant-of-the-Shire-V2 || collection-ambiguous-review.done.csv source_row=56; variant=gold_stamp; set_hint=LTR; card_number=22.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Sharkey-Tyrant-of-the-Shire-V2
- **legacy_evidence:** cards.id=585; collection_items.card_id=585; printing_variant=normal; variant_label=Art Series; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718605; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250767; source_variant=NULL; source_collector_number=A22; image_language_scope=en; fallback=0
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Sharkey-Tyrant-of-the-Shire-V2
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Sharkey-Tyrant-of-the-Shire-V2
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Cardmarket V2, original gold_stamp + ART-A22 + EN + LTR, and local catalog identify one compatible Gold-Stamped product idProduct=718605; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718605 as final audit evidence; do not modify mappings or approve the review CSV.

#### Item `96` — Art Series: Shelob, Child of Ungoliant

- **collection_item_id:** 96
- **game:** Magic
- **card:** Art Series: Shelob, Child of Ungoliant
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718606
- **candidate_cardmarket_ids:** 718606|718607
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=57; variant=gold_stamp; set_hint=LTR; card_number=23.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Shelob-Child-of-Ungoliant-V2 || collection-ambiguous-review.done.csv source_row=57; variant=gold_stamp; set_hint=LTR; card_number=23.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Shelob-Child-of-Ungoliant-V2 || collection-ambiguous-review.done.csv source_row=57; variant=gold_stamp; set_hint=LTR; card_number=23.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Shelob-Child-of-Ungoliant-V2 || collection-ambiguous-review.done.csv source_row=57; variant=gold_stamp; set_hint=LTR; card_number=23.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Shelob-Child-of-Ungoliant-V2 || collection-ambiguous-review.done.csv source_row=57; variant=gold_stamp; set_hint=LTR; card_number=23.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Shelob-Child-of-Ungoliant-V2
- **legacy_evidence:** cards.id=586; collection_items.card_id=586; printing_variant=normal; variant_label=Art Series; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718606; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250770; source_variant=NULL; source_collector_number=A23; image_language_scope=en; fallback=0
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Shelob-Child-of-Ungoliant-V2
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Shelob-Child-of-Ungoliant-V2
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Cardmarket V2, original gold_stamp + ART-A23 + EN + LTR, and local catalog identify one compatible Gold-Stamped product idProduct=718606; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718606 as final audit evidence; do not modify mappings or approve the review CSV.

#### Item `97` — Art Series: Théoden, King of Rohan

- **collection_item_id:** 97
- **game:** Magic
- **card:** Art Series: Théoden, King of Rohan
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718610
- **candidate_cardmarket_ids:** 718610|718611
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=58; variant=gold_stamp; set_hint=LTR; card_number=25.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Theoden-King-of-Rohan-V2 || collection-ambiguous-review.done.csv source_row=58; variant=gold_stamp; set_hint=LTR; card_number=25.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Theoden-King-of-Rohan-V2 || collection-ambiguous-review.done.csv source_row=58; variant=gold_stamp; set_hint=LTR; card_number=25.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Theoden-King-of-Rohan-V2
- **legacy_evidence:** cards.id=590; collection_items.card_id=590; printing_variant=normal; variant_label=Art Series; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718610; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250768; source_variant=NULL; source_collector_number=A25; image_language_scope=en; fallback=0
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Theoden-King-of-Rohan-V2
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Theoden-King-of-Rohan-V2
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Cardmarket V2, original gold_stamp + ART-A25 + EN + LTR, and local catalog identify one compatible Gold-Stamped product idProduct=718610; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718610 as final audit evidence; do not modify mappings or approve the review CSV.

#### Item `98` — Art Series: Tom Bombadil

- **collection_item_id:** 98
- **game:** Magic
- **card:** Art Series: Tom Bombadil
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718613
- **candidate_cardmarket_ids:** 718612|718613
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=59; variant=gold_stamp; set_hint=LTR; card_number=26.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Tom-Bombadil-V2 || collection-ambiguous-review.done.csv source_row=59; variant=gold_stamp; set_hint=LTR; card_number=26.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Tom-Bombadil-V2 || collection-ambiguous-review.done.csv source_row=59; variant=gold_stamp; set_hint=LTR; card_number=26.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Tom-Bombadil-V2 || collection-ambiguous-review.done.csv source_row=59; variant=gold_stamp; set_hint=LTR; card_number=26.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Tom-Bombadil-V2 || collection-ambiguous-review.done.csv source_row=59; variant=gold_stamp; set_hint=LTR; card_number=26.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Tom-Bombadil-V2
- **legacy_evidence:** cards.id=593; collection_items.card_id=593; printing_variant=normal; variant_label=Art Series; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718613; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250778; source_variant=NULL; source_collector_number=A26; image_language_scope=en; fallback=0
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Tom-Bombadil-V2
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Tom-Bombadil-V2
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Cardmarket V2, original gold_stamp + ART-A26 + EN + LTR, and local catalog identify one compatible Gold-Stamped product idProduct=718613; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718613 as final audit evidence; do not modify mappings or approve the review CSV.

#### Item `99` — Art Series: Uglúk of the White Hand

- **collection_item_id:** 99
- **game:** Magic
- **card:** Art Series: Uglúk of the White Hand
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718614
- **candidate_cardmarket_ids:** 718614|718615
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=60; variant=gold_stamp; set_hint=LTR; card_number=27.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Ugluk-of-the-White-Hand-V2 || collection-ambiguous-review.done.csv source_row=60; variant=gold_stamp; set_hint=LTR; card_number=27.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Ugluk-of-the-White-Hand-V2 || collection-ambiguous-review.done.csv source_row=60; variant=gold_stamp; set_hint=LTR; card_number=27.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Ugluk-of-the-White-Hand-V2
- **legacy_evidence:** cards.id=594; collection_items.card_id=594; printing_variant=normal; variant_label=Art Series; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718614; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250782; source_variant=NULL; source_collector_number=A27; image_language_scope=en; fallback=0
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Ugluk-of-the-White-Hand-V2
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Ugluk-of-the-White-Hand-V2
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Cardmarket V2, original gold_stamp + ART-A27 + EN + LTR, and local catalog identify one compatible Gold-Stamped product idProduct=718614; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718614 as final audit evidence; do not modify mappings or approve the review CSV.

#### Item `100` — Art Series: Plains

- **collection_item_id:** 100
- **game:** Magic
- **card:** Art Series: Plains
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718621
- **candidate_cardmarket_ids:** 718620|718621
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=61; variant=gold_stamp; set_hint=LTR; card_number=30.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Plains-V2 || collection-ambiguous-review.done.csv source_row=61; variant=gold_stamp; set_hint=LTR; card_number=30.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Plains-V2 || collection-ambiguous-review.done.csv source_row=61; variant=gold_stamp; set_hint=LTR; card_number=30.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Plains-V2 || collection-ambiguous-review.done.csv source_row=61; variant=gold_stamp; set_hint=LTR; card_number=30.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Plains-V2 || collection-ambiguous-review.done.csv source_row=61; variant=gold_stamp; set_hint=LTR; card_number=30.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Plains-V2 || collection-ambiguous-review.done.csv source_row=61; variant=gold_stamp; set_hint=LTR; card_number=30.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Plains-V2
- **legacy_evidence:** cards.id=601; collection_items.card_id=601; printing_variant=normal; variant_label=Art Series; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718621; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250740; source_variant=NULL; source_collector_number=A30; image_language_scope=en; fallback=0
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Plains-V2
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Plains-V2
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Cardmarket V2, original gold_stamp + ART-A30 + EN + LTR, and local catalog identify one compatible Gold-Stamped product idProduct=718621; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718621 as final audit evidence; do not modify mappings or approve the review CSV.

#### Item `101` — Art Series: Mountain

- **collection_item_id:** 101
- **game:** Magic
- **card:** Art Series: Mountain
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718622
- **candidate_cardmarket_ids:** 718622|718623
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=62; variant=gold_stamp; set_hint=LTR; card_number=31.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Mountain-V2 || collection-ambiguous-review.done.csv source_row=62; variant=gold_stamp; set_hint=LTR; card_number=31.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Mountain-V2 || collection-ambiguous-review.done.csv source_row=62; variant=gold_stamp; set_hint=LTR; card_number=31.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Mountain-V2 || collection-ambiguous-review.done.csv source_row=62; variant=gold_stamp; set_hint=LTR; card_number=31.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Mountain-V2 || collection-ambiguous-review.done.csv source_row=62; variant=gold_stamp; set_hint=LTR; card_number=31.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Mountain-V2 || collection-ambiguous-review.done.csv source_row=62; variant=gold_stamp; set_hint=LTR; card_number=31.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Mountain-V2
- **legacy_evidence:** cards.id=602; collection_items.card_id=602; printing_variant=normal; variant_label=Art Series; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718622; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250744; source_variant=NULL; source_collector_number=A31; image_language_scope=en; fallback=0
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Mountain-V2
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Mountain-V2
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Cardmarket V2, original gold_stamp + ART-A31 + EN + LTR, and local catalog identify one compatible Gold-Stamped product idProduct=718622; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718622 as final audit evidence; do not modify mappings or approve the review CSV.

#### Item `102` — Art Series: Elanor Gardner

- **collection_item_id:** 102
- **game:** Magic
- **card:** Art Series: Elanor Gardner
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718625
- **candidate_cardmarket_ids:** 718624|718625
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=63; variant=gold_stamp; set_hint=LTR; card_number=32.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Elanor-Gardner-V2 || collection-ambiguous-review.done.csv source_row=63; variant=gold_stamp; set_hint=LTR; card_number=32.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Elanor-Gardner-V2 || collection-ambiguous-review.done.csv source_row=63; variant=gold_stamp; set_hint=LTR; card_number=32.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Elanor-Gardner-V2 || collection-ambiguous-review.done.csv source_row=63; variant=gold_stamp; set_hint=LTR; card_number=32.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Elanor-Gardner-V2
- **legacy_evidence:** cards.id=605; collection_items.card_id=605; printing_variant=normal; variant_label=Art Series; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718625; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250715; source_variant=NULL; source_collector_number=A32; image_language_scope=en; fallback=0
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Elanor-Gardner-V2
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Elanor-Gardner-V2
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Cardmarket V2, original gold_stamp + ART-A32 + EN + LTR, and local catalog identify one compatible Gold-Stamped product idProduct=718625; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718625 as final audit evidence; do not modify mappings or approve the review CSV.

#### Item `103` — Art Series: Aragorn and Arwen, Wed

- **collection_item_id:** 103
- **game:** Magic
- **card:** Art Series: Aragorn and Arwen, Wed
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718626
- **candidate_cardmarket_ids:** 718626|718627
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=64; variant=gold_stamp; set_hint=LTR; card_number=33.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Aragorn-and-Arwen-Wed-V2 || collection-ambiguous-review.done.csv source_row=64; variant=gold_stamp; set_hint=LTR; card_number=33.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Aragorn-and-Arwen-Wed-V2 || collection-ambiguous-review.done.csv source_row=64; variant=gold_stamp; set_hint=LTR; card_number=33.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Aragorn-and-Arwen-Wed-V2 || collection-ambiguous-review.done.csv source_row=64; variant=gold_stamp; set_hint=LTR; card_number=33.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Aragorn-and-Arwen-Wed-V2
- **legacy_evidence:** cards.id=606; collection_items.card_id=606; printing_variant=normal; variant_label=Art Series; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718626; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250732; source_variant=NULL; source_collector_number=A33; image_language_scope=en; fallback=0
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Aragorn-and-Arwen-Wed-V2
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Aragorn-and-Arwen-Wed-V2
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Cardmarket V2, original gold_stamp + ART-A33 + EN + LTR, and local catalog identify one compatible Gold-Stamped product idProduct=718626; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718626 as final audit evidence; do not modify mappings or approve the review CSV.

#### Item `104` — Art Series: Bilbo's Ring

- **collection_item_id:** 104
- **game:** Magic
- **card:** Art Series: Bilbo's Ring
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718640
- **candidate_cardmarket_ids:** 718640|718641
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=65; variant=gold_stamp; set_hint=LTR; card_number=37.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Bilbos-Ring-V2 || collection-ambiguous-review.done.csv source_row=65; variant=gold_stamp; set_hint=LTR; card_number=37.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Bilbos-Ring-V2 || collection-ambiguous-review.done.csv source_row=65; variant=gold_stamp; set_hint=LTR; card_number=37.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Bilbos-Ring-V2 || collection-ambiguous-review.done.csv source_row=65; variant=gold_stamp; set_hint=LTR; card_number=37.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Bilbos-Ring-V2
- **legacy_evidence:** cards.id=614; collection_items.card_id=614; printing_variant=normal; variant_label=Art Series; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718640; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250725; source_variant=NULL; source_collector_number=A37; image_language_scope=en; fallback=0
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Bilbos-Ring-V2
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Bilbos-Ring-V2
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Cardmarket V2, original gold_stamp + ART-A37 + EN + LTR, and local catalog identify one compatible Gold-Stamped product idProduct=718640; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718640 as final audit evidence; do not modify mappings or approve the review CSV.

#### Item `105` — Art Series: Faramir, Field Commander

- **collection_item_id:** 105
- **game:** Magic
- **card:** Art Series: Faramir, Field Commander
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718643
- **candidate_cardmarket_ids:** 718642|718643
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=66; variant=gold_stamp; set_hint=LTR; card_number=38.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Faramir-Field-Commander-V2 || collection-ambiguous-review.done.csv source_row=66; variant=gold_stamp; set_hint=LTR; card_number=38.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Faramir-Field-Commander-V2 || collection-ambiguous-review.done.csv source_row=66; variant=gold_stamp; set_hint=LTR; card_number=38.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Faramir-Field-Commander-V2 || collection-ambiguous-review.done.csv source_row=66; variant=gold_stamp; set_hint=LTR; card_number=38.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Faramir-Field-Commander-V2
- **legacy_evidence:** cards.id=617; collection_items.card_id=617; printing_variant=normal; variant_label=Art Series; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718643; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250714; source_variant=NULL; source_collector_number=A38; image_language_scope=en; fallback=0
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Faramir-Field-Commander-V2
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Faramir-Field-Commander-V2
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Cardmarket V2, original gold_stamp + ART-A38 + EN + LTR, and local catalog identify one compatible Gold-Stamped product idProduct=718643; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718643 as final audit evidence; do not modify mappings or approve the review CSV.

#### Item `106` — Art Series: Elrond, Lord of Rivendell

- **collection_item_id:** 106
- **game:** Magic
- **card:** Art Series: Elrond, Lord of Rivendell
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718646
- **candidate_cardmarket_ids:** 718646|718647
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=67; variant=gold_stamp; set_hint=LTR; card_number=40.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Elrond-Lord-of-Rivendell-V2 || collection-ambiguous-review.done.csv source_row=67; variant=gold_stamp; set_hint=LTR; card_number=40.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Elrond-Lord-of-Rivendell-V2 || collection-ambiguous-review.done.csv source_row=67; variant=gold_stamp; set_hint=LTR; card_number=40.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Elrond-Lord-of-Rivendell-V2 || collection-ambiguous-review.done.csv source_row=67; variant=gold_stamp; set_hint=LTR; card_number=40.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Elrond-Lord-of-Rivendell-V2
- **legacy_evidence:** cards.id=620; collection_items.card_id=620; printing_variant=normal; variant_label=Art Series; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718646; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250709; source_variant=NULL; source_collector_number=A40; image_language_scope=en; fallback=0
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Elrond-Lord-of-Rivendell-V2
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Elrond-Lord-of-Rivendell-V2
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Cardmarket V2, original gold_stamp + ART-A40 + EN + LTR, and local catalog identify one compatible Gold-Stamped product idProduct=718646; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718646 as final audit evidence; do not modify mappings or approve the review CSV.

#### Item `107` — Art Series: Witch-king of Angmar

- **collection_item_id:** 107
- **game:** Magic
- **card:** Art Series: Witch-king of Angmar
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718652
- **candidate_cardmarket_ids:** 718652|718653
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=68; variant=gold_stamp; set_hint=LTR; card_number=43.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Witch-king-of-Angmar-V2 || collection-ambiguous-review.done.csv source_row=68; variant=gold_stamp; set_hint=LTR; card_number=43.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Witch-king-of-Angmar-V2 || collection-ambiguous-review.done.csv source_row=68; variant=gold_stamp; set_hint=LTR; card_number=43.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Witch-king-of-Angmar-V2 || collection-ambiguous-review.done.csv source_row=68; variant=gold_stamp; set_hint=LTR; card_number=43.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Witch-king-of-Angmar-V2 || collection-ambiguous-review.done.csv source_row=68; variant=gold_stamp; set_hint=LTR; card_number=43.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Witch-king-of-Angmar-V2 || collection-ambiguous-review.done.csv source_row=68; variant=gold_stamp; set_hint=LTR; card_number=43.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Witch-king-of-Angmar-V2
- **legacy_evidence:** cards.id=626; collection_items.card_id=626; printing_variant=other; variant_label=Gold-Stamped; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718652; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250661; source_variant=Gold-Stamped; source_collector_number=A43g; image_language_scope=en; fallback=0
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Witch-king-of-Angmar-V2
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Witch-king-of-Angmar-V2
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Cardmarket V2, original gold_stamp + ART-A43 + EN + LTR, and local catalog identify one compatible Gold-Stamped product idProduct=718652; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718652 as final audit evidence; do not modify mappings or approve the review CSV.

#### Item `108` — Art Series: Frodo Baggins

- **collection_item_id:** 108
- **game:** Magic
- **card:** Art Series: Frodo Baggins
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718580
- **candidate_cardmarket_ids:** 718580|718581|718660|718661
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=69; variant=gold_stamp; set_hint=LTR; card_number=47.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Frodo-Baggins-V4 || collection-ambiguous-review.done.csv source_row=69; variant=gold_stamp; set_hint=LTR; card_number=47.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Frodo-Baggins-V4 || collection-ambiguous-review.done.csv source_row=69; variant=gold_stamp; set_hint=LTR; card_number=47.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Frodo-Baggins-V4 || collection-ambiguous-review.done.csv source_row=69; variant=gold_stamp; set_hint=LTR; card_number=47.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Frodo-Baggins-V4 || collection-ambiguous-review.done.csv source_row=69; variant=gold_stamp; set_hint=LTR; card_number=47.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Frodo-Baggins-V4 || collection-ambiguous-review.done.csv source_row=69; variant=gold_stamp; set_hint=LTR; card_number=47.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Frodo-Baggins-V4 || collection-ambiguous-review.done.csv source_row=69; variant=gold_stamp; set_hint=LTR; card_number=47.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Frodo-Baggins-V4 || collection-ambiguous-review.done.csv source_row=69; variant=gold_stamp; set_hint=LTR; card_number=47.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Frodo-Baggins-V4
- **legacy_evidence:** cards.id=572; collection_items.card_id=572; printing_variant=other; variant_label=Gold-Stamped; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718580; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250693; source_variant=Gold-Stamped; source_collector_number=A16g; image_language_scope=en; fallback=0 || CONFLICT: CardTrader image collector=A16g vs collection=ART-47
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Frodo-Baggins-V4
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Frodo-Baggins-V4
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Decisión humana explícita confirma Art Series: Frodo Baggins A47/47 of 81, Gold-Stamped y Cardmarket V.4; catálogo local único idProduct=718580. La provenance CardTrader A16g era incorrecta para este Collection item; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718580 as final audit evidence; do not modify mappings or approve the review CSV.

#### Item `109` — Art Series: Galadriel of Lothlórien

- **collection_item_id:** 109
- **game:** Magic
- **card:** Art Series: Galadriel of Lothlórien
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718662
- **candidate_cardmarket_ids:** 718662|718663
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=70; variant=gold_stamp; set_hint=LTR; card_number=48.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Galadriel-of-Lothlorien-V2 || collection-ambiguous-review.done.csv source_row=70; variant=gold_stamp; set_hint=LTR; card_number=48.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Galadriel-of-Lothlorien-V2 || collection-ambiguous-review.done.csv source_row=70; variant=gold_stamp; set_hint=LTR; card_number=48.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Galadriel-of-Lothlorien-V2 || collection-ambiguous-review.done.csv source_row=70; variant=gold_stamp; set_hint=LTR; card_number=48.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Galadriel-of-Lothlorien-V2 || collection-ambiguous-review.done.csv source_row=70; variant=gold_stamp; set_hint=LTR; card_number=48.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Galadriel-of-Lothlorien-V2 || collection-ambiguous-review.done.csv source_row=70; variant=gold_stamp; set_hint=LTR; card_number=48.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Galadriel-of-Lothlorien-V2
- **legacy_evidence:** cards.id=636; collection_items.card_id=636; printing_variant=normal; variant_label=Art Series; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718662; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250719; source_variant=NULL; source_collector_number=A48; image_language_scope=en; fallback=0
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Galadriel-of-Lothlorien-V2
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Galadriel-of-Lothlorien-V2
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Cardmarket V2, original gold_stamp + ART-A48 + EN + LTR, and local catalog identify one compatible Gold-Stamped product idProduct=718662; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718662 as final audit evidence; do not modify mappings or approve the review CSV.

#### Item `110` — Art Series: Merry, Esquire of Rohan

- **collection_item_id:** 110
- **game:** Magic
- **card:** Art Series: Merry, Esquire of Rohan
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718666
- **candidate_cardmarket_ids:** 718666|718667
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=71; variant=gold_stamp; set_hint=LTR; card_number=50.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Merry-Esquire-of-Rohan-V2 || collection-ambiguous-review.done.csv source_row=71; variant=gold_stamp; set_hint=LTR; card_number=50.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Merry-Esquire-of-Rohan-V2 || collection-ambiguous-review.done.csv source_row=71; variant=gold_stamp; set_hint=LTR; card_number=50.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Merry-Esquire-of-Rohan-V2 || collection-ambiguous-review.done.csv source_row=71; variant=gold_stamp; set_hint=LTR; card_number=50.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Merry-Esquire-of-Rohan-V2 || collection-ambiguous-review.done.csv source_row=71; variant=gold_stamp; set_hint=LTR; card_number=50.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Merry-Esquire-of-Rohan-V2 || collection-ambiguous-review.done.csv source_row=71; variant=gold_stamp; set_hint=LTR; card_number=50.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Merry-Esquire-of-Rohan-V2
- **legacy_evidence:** cards.id=640; collection_items.card_id=640; printing_variant=normal; variant_label=Art Series; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718666; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250749; source_variant=NULL; source_collector_number=A50; image_language_scope=en; fallback=0
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Merry-Esquire-of-Rohan-V2
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Merry-Esquire-of-Rohan-V2
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Cardmarket V2, original gold_stamp + ART-A50 + EN + LTR, and local catalog identify one compatible Gold-Stamped product idProduct=718666; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718666 as final audit evidence; do not modify mappings or approve the review CSV.

#### Item `111` — Art Series: Pippin, Guard of the Citadel

- **collection_item_id:** 111
- **game:** Magic
- **card:** Art Series: Pippin, Guard of the Citadel
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718669
- **candidate_cardmarket_ids:** 718668|718669
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=72; variant=gold_stamp; set_hint=LTR; card_number=51.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Pippin-Guard-of-the-Citadel-V2 || collection-ambiguous-review.done.csv source_row=72; variant=gold_stamp; set_hint=LTR; card_number=51.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Pippin-Guard-of-the-Citadel-V2 || collection-ambiguous-review.done.csv source_row=72; variant=gold_stamp; set_hint=LTR; card_number=51.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Pippin-Guard-of-the-Citadel-V2 || collection-ambiguous-review.done.csv source_row=72; variant=gold_stamp; set_hint=LTR; card_number=51.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Pippin-Guard-of-the-Citadel-V2 || collection-ambiguous-review.done.csv source_row=72; variant=gold_stamp; set_hint=LTR; card_number=51.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Pippin-Guard-of-the-Citadel-V2 || collection-ambiguous-review.done.csv source_row=72; variant=gold_stamp; set_hint=LTR; card_number=51.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Pippin-Guard-of-the-Citadel-V2
- **legacy_evidence:** cards.id=643; collection_items.card_id=643; printing_variant=normal; variant_label=Art Series; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718669; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250743; source_variant=NULL; source_collector_number=A51; image_language_scope=en; fallback=0
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Pippin-Guard-of-the-Citadel-V2
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Pippin-Guard-of-the-Citadel-V2
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Cardmarket V2, original gold_stamp + ART-A51 + EN + LTR, and local catalog identify one compatible Gold-Stamped product idProduct=718669; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718669 as final audit evidence; do not modify mappings or approve the review CSV.

#### Item `112` — Art Series: Mines of Moria

- **collection_item_id:** 112
- **game:** Magic
- **card:** Art Series: Mines of Moria
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718683
- **candidate_cardmarket_ids:** 718682|718683
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=73; variant=gold_stamp; set_hint=LTR; card_number=56.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Mines-of-Moria-V2 || collection-ambiguous-review.done.csv source_row=73; variant=gold_stamp; set_hint=LTR; card_number=56.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Mines-of-Moria-V2 || collection-ambiguous-review.done.csv source_row=73; variant=gold_stamp; set_hint=LTR; card_number=56.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Mines-of-Moria-V2 || collection-ambiguous-review.done.csv source_row=73; variant=gold_stamp; set_hint=LTR; card_number=56.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Mines-of-Moria-V2 || collection-ambiguous-review.done.csv source_row=73; variant=gold_stamp; set_hint=LTR; card_number=56.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Mines-of-Moria-V2
- **legacy_evidence:** cards.id=653; collection_items.card_id=653; printing_variant=normal; variant_label=Art Series; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718683; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250747; source_variant=NULL; source_collector_number=A56; image_language_scope=en; fallback=0
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Mines-of-Moria-V2
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Mines-of-Moria-V2
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Cardmarket V2, original gold_stamp + ART-A56 + EN + LTR, and local catalog identify one compatible Gold-Stamped product idProduct=718683; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718683 as final audit evidence; do not modify mappings or approve the review CSV.

#### Item `113` — Art Series: Aragorn, King of Gondor

- **collection_item_id:** 113
- **game:** Magic
- **card:** Art Series: Aragorn, King of Gondor
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718685
- **candidate_cardmarket_ids:** 718685|718686
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=74; variant=gold_stamp; set_hint=LTR; card_number=57.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Aragorn-King-of-Gondor-V2 || collection-ambiguous-review.done.csv source_row=74; variant=gold_stamp; set_hint=LTR; card_number=57.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Aragorn-King-of-Gondor-V2
- **legacy_evidence:** cards.id=654; collection_items.card_id=654; printing_variant=normal; variant_label=Art Series; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718685; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250731; source_variant=NULL; source_collector_number=A57; image_language_scope=en; fallback=0
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Aragorn-King-of-Gondor-V2
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Aragorn-King-of-Gondor-V2
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Cardmarket V2, original gold_stamp + ART-A57 + EN + LTR, and local catalog identify one compatible Gold-Stamped product idProduct=718685; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718685 as final audit evidence; do not modify mappings or approve the review CSV.

#### Item `114` — Art Series: Gwaihir, Greatest of the Eagles

- **collection_item_id:** 114
- **game:** Magic
- **card:** Art Series: Gwaihir, Greatest of the Eagles
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718693
- **candidate_cardmarket_ids:** 718692|718693
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=75; variant=gold_stamp; set_hint=LTR; card_number=59.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Gwaihir-Greatest-of-the-Eagles-V2 || collection-ambiguous-review.done.csv source_row=75; variant=gold_stamp; set_hint=LTR; card_number=59.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Gwaihir-Greatest-of-the-Eagles-V2
- **legacy_evidence:** cards.id=659; collection_items.card_id=659; printing_variant=normal; variant_label=Art Series; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718693; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250758; source_variant=NULL; source_collector_number=A59; image_language_scope=en; fallback=0
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Gwaihir-Greatest-of-the-Eagles-V2
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Gwaihir-Greatest-of-the-Eagles-V2
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Cardmarket V2, original gold_stamp + ART-A59 + EN + LTR, and local catalog identify one compatible Gold-Stamped product idProduct=718693; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718693 as final audit evidence; do not modify mappings or approve the review CSV.

#### Item `115` — Art Series: Call for Aid

- **collection_item_id:** 115
- **game:** Magic
- **card:** Art Series: Call for Aid
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718694
- **candidate_cardmarket_ids:** 718694|718697
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=76; variant=gold_stamp; set_hint=LTR; card_number=60.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Call-for-Aid-V2 || collection-ambiguous-review.done.csv source_row=76; variant=gold_stamp; set_hint=LTR; card_number=60.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Call-for-Aid-V2
- **legacy_evidence:** cards.id=660; collection_items.card_id=660; printing_variant=normal; variant_label=Art Series; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718694; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250723; source_variant=NULL; source_collector_number=A60; image_language_scope=en; fallback=0
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Call-for-Aid-V2
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Call-for-Aid-V2
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Cardmarket V2, original gold_stamp + ART-A60 + EN + LTR, and local catalog identify one compatible Gold-Stamped product idProduct=718694; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718694 as final audit evidence; do not modify mappings or approve the review CSV.

#### Item `116` — Art Series: Cavern-Hoard Dragon

- **collection_item_id:** 116
- **game:** Magic
- **card:** Art Series: Cavern-Hoard Dragon
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718700
- **candidate_cardmarket_ids:** 718699|718700
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=77; variant=gold_stamp; set_hint=LTR; card_number=61.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Cavern-Hoard-Dragon-V2 || collection-ambiguous-review.done.csv source_row=77; variant=gold_stamp; set_hint=LTR; card_number=61.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Cavern-Hoard-Dragon-V2
- **legacy_evidence:** cards.id=663; collection_items.card_id=663; printing_variant=normal; variant_label=Art Series; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718700; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250721; source_variant=NULL; source_collector_number=A61; image_language_scope=en; fallback=0
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Cavern-Hoard-Dragon-V2
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Cavern-Hoard-Dragon-V2
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Cardmarket V2, original gold_stamp + ART-A61 + EN + LTR, and local catalog identify one compatible Gold-Stamped product idProduct=718700; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718700 as final audit evidence; do not modify mappings or approve the review CSV.

#### Item `117` — Art Series: Gríma, Saruman's Footman

- **collection_item_id:** 117
- **game:** Magic
- **card:** Art Series: Gríma, Saruman's Footman
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718708
- **candidate_cardmarket_ids:** 718707|718708
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=78; variant=gold_stamp; set_hint=LTR; card_number=63.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Grima-Sarumans-Footman-V2 || collection-ambiguous-review.done.csv source_row=78; variant=gold_stamp; set_hint=LTR; card_number=63.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Grima-Sarumans-Footman-V2
- **legacy_evidence:** cards.id=667; collection_items.card_id=667; printing_variant=normal; variant_label=Art Series; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718708; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250759; source_variant=NULL; source_collector_number=A63; image_language_scope=en; fallback=0
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Grima-Sarumans-Footman-V2
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Grima-Sarumans-Footman-V2
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Cardmarket V2, original gold_stamp + ART-A63 + EN + LTR, and local catalog identify one compatible Gold-Stamped product idProduct=718708; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718708 as final audit evidence; do not modify mappings or approve the review CSV.

#### Item `118` — Art Series: Merry, Warden of Isengard

- **collection_item_id:** 118
- **game:** Magic
- **card:** Art Series: Merry, Warden of Isengard
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718715
- **candidate_cardmarket_ids:** 718714|718715
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=79; variant=gold_stamp; set_hint=LTR; card_number=65.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Merry-Warden-of-Isengard-V2 || collection-ambiguous-review.done.csv source_row=79; variant=gold_stamp; set_hint=LTR; card_number=65.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Merry-Warden-of-Isengard-V2
- **legacy_evidence:** cards.id=671; collection_items.card_id=671; printing_variant=normal; variant_label=Art Series; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718715; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250748; source_variant=NULL; source_collector_number=A65; image_language_scope=en; fallback=0
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Merry-Warden-of-Isengard-V2
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Merry-Warden-of-Isengard-V2
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Cardmarket V2, original gold_stamp + ART-A65 + EN + LTR, and local catalog identify one compatible Gold-Stamped product idProduct=718715; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718715 as final audit evidence; do not modify mappings or approve the review CSV.

#### Item `119` — Art Series: Treebeard, Gracious Host

- **collection_item_id:** 119
- **game:** Magic
- **card:** Art Series: Treebeard, Gracious Host
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718719
- **candidate_cardmarket_ids:** 718719|718722
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=80; variant=gold_stamp; set_hint=LTR; card_number=67.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Treebeard-Gracious-Host-V2 || collection-ambiguous-review.done.csv source_row=80; variant=gold_stamp; set_hint=LTR; card_number=67.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Treebeard-Gracious-Host-V2
- **legacy_evidence:** cards.id=674; collection_items.card_id=674; printing_variant=other; variant_label=Gold-Stamped; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718719; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250801; source_variant=Gold-Stamped; source_collector_number=A67g; image_language_scope=en; fallback=0
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Treebeard-Gracious-Host-V2
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Treebeard-Gracious-Host-V2
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Cardmarket V2, original gold_stamp + ART-A67 + EN + LTR, and local catalog identify one compatible Gold-Stamped product idProduct=718719; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718719 as final audit evidence; do not modify mappings or approve the review CSV.

#### Item `120` — Art Series: Asceticism

- **collection_item_id:** 120
- **game:** Magic
- **card:** Art Series: Asceticism
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718740
- **candidate_cardmarket_ids:** 718740|718741
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=81; variant=gold_stamp; set_hint=LTR; card_number=72.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Asceticism-V2 || collection-ambiguous-review.done.csv source_row=81; variant=gold_stamp; set_hint=LTR; card_number=72.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Asceticism-V2
- **legacy_evidence:** cards.id=684; collection_items.card_id=684; printing_variant=normal; variant_label=Art Series; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718740; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250729; source_variant=NULL; source_collector_number=A72; image_language_scope=en; fallback=0
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Asceticism-V2
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Asceticism-V2
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Cardmarket V2, original gold_stamp + ART-A72 + EN + LTR, and local catalog identify one compatible Gold-Stamped product idProduct=718740; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718740 as final audit evidence; do not modify mappings or approve the review CSV.

#### Item `121` — Art Series: Realm Seekers

- **collection_item_id:** 121
- **game:** Magic
- **card:** Art Series: Realm Seekers
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718747
- **candidate_cardmarket_ids:** 718746|718747
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=82; variant=gold_stamp; set_hint=LTR; card_number=74.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Realm-Seekers-V2 || collection-ambiguous-review.done.csv source_row=82; variant=gold_stamp; set_hint=LTR; card_number=74.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Realm-Seekers-V2
- **legacy_evidence:** cards.id=689; collection_items.card_id=689; printing_variant=other; variant_label=Gold-Stamped; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718747; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250805; source_variant=Gold-Stamped; source_collector_number=A74g; image_language_scope=en; fallback=0
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Realm-Seekers-V2
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Realm-Seekers-V2
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Cardmarket V2, original gold_stamp + ART-A74 + EN + LTR, and local catalog identify one compatible Gold-Stamped product idProduct=718747; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718747 as final audit evidence; do not modify mappings or approve the review CSV.

#### Item `122` — Art Series: Ghost Quarter

- **collection_item_id:** 122
- **game:** Magic
- **card:** Art Series: Ghost Quarter
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718757
- **candidate_cardmarket_ids:** 718757|718758
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=83; variant=gold_stamp; set_hint=LTR; card_number=78.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Ghost-Quarter-V2 || collection-ambiguous-review.done.csv source_row=83; variant=gold_stamp; set_hint=LTR; card_number=78.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Ghost-Quarter-V2
- **legacy_evidence:** cards.id=696; collection_items.card_id=696; printing_variant=normal; variant_label=Art Series; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718757; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250761; source_variant=NULL; source_collector_number=A78; image_language_scope=en; fallback=0
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Ghost-Quarter-V2
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Ghost-Quarter-V2
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Cardmarket V2, original gold_stamp + ART-A78 + EN + LTR, and local catalog identify one compatible Gold-Stamped product idProduct=718757; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718757 as final audit evidence; do not modify mappings or approve the review CSV.

#### Item `123` — Art Series: Valley of Gorgoroth

- **collection_item_id:** 123
- **game:** Magic
- **card:** Art Series: Valley of Gorgoroth
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718763
- **candidate_cardmarket_ids:** 718761|718763
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=84; variant=gold_stamp; set_hint=LTR; card_number=80.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Valley-of-Gorgoroth-V2 || collection-ambiguous-review.done.csv source_row=84; variant=gold_stamp; set_hint=LTR; card_number=80.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Valley-of-Gorgoroth-V2
- **legacy_evidence:** cards.id=701; collection_items.card_id=701; printing_variant=normal; variant_label=Art Series; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718763; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250784; source_variant=NULL; source_collector_number=A80; image_language_scope=en; fallback=0
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Valley-of-Gorgoroth-V2
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Valley-of-Gorgoroth-V2
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Cardmarket V2, original gold_stamp + ART-A80 + EN + LTR, and local catalog identify one compatible Gold-Stamped product idProduct=718763; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718763 as final audit evidence; do not modify mappings or approve the review CSV.

#### Item `124` — Art Series: Faramir, Steward of Gondor

- **collection_item_id:** 124
- **game:** Magic
- **card:** Art Series: Faramir, Steward of Gondor
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718704
- **candidate_cardmarket_ids:** 718704|718705
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=85; variant=gold_stamp; set_hint=LTR; card_number=62.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Faramir-Steward-of-Gondor-V2 || collection-ambiguous-review.done.csv source_row=85; variant=gold_stamp; set_hint=LTR; card_number=62.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Faramir-Steward-of-Gondor-V2
- **legacy_evidence:** cards.id=664; collection_items.card_id=664; printing_variant=normal; variant_label=Art Series; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718704; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250716; source_variant=NULL; source_collector_number=A62; image_language_scope=en; fallback=0
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Faramir-Steward-of-Gondor-V2
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Faramir-Steward-of-Gondor-V2
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Cardmarket V2, original gold_stamp + ART-A62 + EN + LTR, and local catalog identify one compatible Gold-Stamped product idProduct=718704; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718704 as final audit evidence; do not modify mappings or approve the review CSV.

#### Item `125` — Art Series: Nazgûl

- **collection_item_id:** 125
- **game:** Magic
- **card:** Art Series: Nazgûl
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718672
- **candidate_cardmarket_ids:** 718672|718673
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=86; variant=gold_stamp; set_hint=LTR; card_number=53.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Nazgul-V2 || collection-ambiguous-review.done.csv source_row=86; variant=gold_stamp; set_hint=LTR; card_number=53.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Nazgul-V2 || collection-ambiguous-review.done.csv source_row=86; variant=gold_stamp; set_hint=LTR; card_number=53.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Nazgul-V2 || collection-ambiguous-review.done.csv source_row=86; variant=gold_stamp; set_hint=LTR; card_number=53.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Nazgul-V2 || collection-ambiguous-review.done.csv source_row=86; variant=gold_stamp; set_hint=LTR; card_number=53.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Nazgul-V2 || collection-ambiguous-review.done.csv source_row=86; variant=gold_stamp; set_hint=LTR; card_number=53.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Nazgul-V2 || collection-ambiguous-review.done.csv source_row=86; variant=gold_stamp; set_hint=LTR; card_number=53.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Nazgul-V2 || collection-ambiguous-review.done.csv source_row=86; variant=gold_stamp; set_hint=LTR; card_number=53.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Nazgul-V2 || collection-ambiguous-review.done.csv source_row=86; variant=gold_stamp; set_hint=LTR; card_number=53.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Nazgul-V2 || collection-ambiguous-review.done.csv source_row=86; variant=gold_stamp; set_hint=LTR; card_number=53.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Nazgul-V2 || collection-ambiguous-review.done.csv source_row=86; variant=gold_stamp; set_hint=LTR; card_number=53.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Nazgul-V2
- **legacy_evidence:** cards.id=646; collection_items.card_id=646; printing_variant=normal; variant_label=Art Series; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718672; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250742; source_variant=NULL; source_collector_number=A53; image_language_scope=en; fallback=0
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Nazgul-V2
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Nazgul-V2
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Cardmarket V2, original gold_stamp + ART-A53 + EN + LTR, and local catalog identify one compatible Gold-Stamped product idProduct=718672; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718672 as final audit evidence; do not modify mappings or approve the review CSV.

#### Item `126` — Art Series: Sauron, the Dark Lord

- **collection_item_id:** 126
- **game:** Magic
- **card:** Art Series: Sauron, the Dark Lord
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718602
- **candidate_cardmarket_ids:** 718602|718603
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=87; variant=gold_stamp; set_hint=LTR; card_number=21.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Sauron-the-Dark-Lord-V2 || collection-ambiguous-review.done.csv source_row=87; variant=gold_stamp; set_hint=LTR; card_number=21.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Sauron-the-Dark-Lord-V2 || collection-ambiguous-review.done.csv source_row=87; variant=gold_stamp; set_hint=LTR; card_number=21.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Sauron-the-Dark-Lord-V2 || collection-ambiguous-review.done.csv source_row=87; variant=gold_stamp; set_hint=LTR; card_number=21.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Sauron-the-Dark-Lord-V2 || collection-ambiguous-review.done.csv source_row=87; variant=gold_stamp; set_hint=LTR; card_number=21.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Sauron-the-Dark-Lord-V2
- **legacy_evidence:** cards.id=582; collection_items.card_id=582; printing_variant=normal; variant_label=Art Series; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718602; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250765; source_variant=NULL; source_collector_number=A21; image_language_scope=en; fallback=0
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Sauron-the-Dark-Lord-V2
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Sauron-the-Dark-Lord-V2
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Cardmarket V2, original gold_stamp + ART-A21 + EN + LTR, and local catalog identify one compatible Gold-Stamped product idProduct=718602; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718602 as final audit evidence; do not modify mappings or approve the review CSV.

#### Item `127` — Art Series: Éowyn, Fearless Knight

- **collection_item_id:** 127
- **game:** Magic
- **card:** Art Series: Éowyn, Fearless Knight
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718577
- **candidate_cardmarket_ids:** 718577|718578
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=88; variant=gold_stamp; set_hint=LTR; card_number=15.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Eowyn-Fearless-Knight-V2 || collection-ambiguous-review.done.csv source_row=88; variant=gold_stamp; set_hint=LTR; card_number=15.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Eowyn-Fearless-Knight-V2 || collection-ambiguous-review.done.csv source_row=88; variant=gold_stamp; set_hint=LTR; card_number=15.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Eowyn-Fearless-Knight-V2 || collection-ambiguous-review.done.csv source_row=88; variant=gold_stamp; set_hint=LTR; card_number=15.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Eowyn-Fearless-Knight-V2 || collection-ambiguous-review.done.csv source_row=88; variant=gold_stamp; set_hint=LTR; card_number=15.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Eowyn-Fearless-Knight-V2
- **legacy_evidence:** cards.id=570; collection_items.card_id=570; printing_variant=normal; variant_label=Art Series; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718577; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250708; source_variant=NULL; source_collector_number=A15; image_language_scope=en; fallback=0
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Eowyn-Fearless-Knight-V2
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Eowyn-Fearless-Knight-V2
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Cardmarket V2, original gold_stamp + ART-A15 + EN + LTR, and local catalog identify one compatible Gold-Stamped product idProduct=718577; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718577 as final audit evidence; do not modify mappings or approve the review CSV.

#### Item `128` — Art Series: Samwise Gamgee

- **collection_item_id:** 128
- **game:** Magic
- **card:** Art Series: Samwise Gamgee
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718671
- **candidate_cardmarket_ids:** 718598|718599|718670|718671
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=89; variant=gold_stamp; set_hint=LTR; card_number=19.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Samwise-Gamgee-V2 || collection-ambiguous-review.done.csv source_row=89; variant=gold_stamp; set_hint=LTR; card_number=19.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Samwise-Gamgee-V2 || collection-ambiguous-review.done.csv source_row=89; variant=gold_stamp; set_hint=LTR; card_number=19.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Samwise-Gamgee-V2 || collection-ambiguous-review.done.csv source_row=89; variant=gold_stamp; set_hint=LTR; card_number=19.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Samwise-Gamgee-V2 || collection-ambiguous-review.done.csv source_row=89; variant=gold_stamp; set_hint=LTR; card_number=19.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Samwise-Gamgee-V2 || collection-ambiguous-review.done.csv source_row=89; variant=gold_stamp; set_hint=LTR; card_number=19.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Samwise-Gamgee-V2 || collection-ambiguous-review.done.csv source_row=89; variant=gold_stamp; set_hint=LTR; card_number=19.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Samwise-Gamgee-V2
- **legacy_evidence:** cards.id=645; collection_items.card_id=645; printing_variant=other; variant_label=Gold-Stamped; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active
- **external_id_evidence:** cardmarket_product_mappings current=718671; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250811; source_variant=Gold-Stamped; source_collector_number=A52g; image_language_scope=en; fallback=0 || CONFLICT: CardTrader image collector=A52g vs collection=ART-19
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Samwise-Gamgee-V2
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Samwise-Gamgee-V2
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Decisión humana explícita confirma Art Series: Samwise Gamgee A19/19 of 81, Gold-Stamped y Cardmarket V.2; catálogo local único idProduct=718671. La provenance CardTrader A52g era incorrecta para este Collection item; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718671 as final audit evidence; do not modify mappings or approve the review CSV.

#### Item `131` — Art Series: Gandalf the White

- **collection_item_id:** 131
- **game:** Magic
- **card:** Art Series: Gandalf the White
- **current_status:** AMBIGUOUS
- **classification:** EXACT_RECOVERED
- **recovered_cardmarket_id:** 718547
- **candidate_cardmarket_ids:** 718547|718548
- **original_import_evidence:** collection-ambiguous-review.done.csv source_row=46; variant=gold_stamp; set_hint=LTR; card_number=3.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Gandalf-the-White-V2 || collection-ambiguous-review.done.csv source_row=46; variant=gold_stamp; set_hint=LTR; card_number=3.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Gandalf-the-White-V2 || collection-ambiguous-review.done.csv source_row=46; variant=gold_stamp; set_hint=LTR; card_number=3.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Gandalf-the-White-V2 || collection-ambiguous-review.done.csv source_row=46; variant=gold_stamp; set_hint=LTR; card_number=3.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Gandalf-the-White-V2 || collection-ambiguous-review.done.csv source_row=46; variant=gold_stamp; set_hint=LTR; card_number=3.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Gandalf-the-White-V2 || collection-ambiguous-review.done.csv source_row=46; variant=gold_stamp; set_hint=LTR; card_number=3.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Gandalf-the-White-V2 || collection-ambiguous-review.done.csv source_row=46; variant=gold_stamp; set_hint=LTR; card_number=3.0; language=en; notes=NULL; cardmarket_link=https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Gandalf-the-White-V2
- **legacy_evidence:** cards.id=546; collection_items.card_id=546; printing_variant=normal; variant_label=Art Series; finish=nonfoil; treatment=Art Series Gold-Stamped; source_variant=art_series_gold_stamped; release_kind=special; art_kind=special; catalog_status=active collection notes=Agregada manualmente desde lista Art Series; sin purchase_price registrado
- **external_id_evidence:** cardmarket_product_mappings current=718547; status=mapped
- **scryfall_evidence:** No scryfall_raw evidence.
- **cardtrader_evidence:** card_images source_card_id=250705; source_variant=NULL; source_collector_number=A03; image_language_scope=en; fallback=0 || CONFLICT: CardTrader image collector=A03 vs collection=ART-3
- **historical_url_evidence:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Gandalf-the-White-V2
- **provenance_gap:** true
- **lost_fields:** cardmarket_link
- **original_value:** https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Gandalf-the-White-V2
- **current_value:** NULL: no Cardmarket URL/provenance-link field in collection_items/cards
- **confidence_reason:** Cardmarket V2, original gold_stamp + ART-A3 + EN + LTR, and local catalog identify one compatible Gold-Stamped product idProduct=718547; provenance_gap=true.
- **remaining_blocker:** None for identity recovery; provenance_gap=true; no mapping/apply performed.
- **next_action:** Retain idProduct 718547 as final audit evidence; do not modify mappings or approve the review CSV.

## Totals and next actions

- PROVENANCE GAPS: **45** (Art Series historical links absent from normalized DB fields).
- NEXT MANUAL WEB REVIEWS: **67**.
- NEXT PHYSICAL CONFIRMATIONS: **0**.
- Apply remains blocked until the results are reviewed together.
