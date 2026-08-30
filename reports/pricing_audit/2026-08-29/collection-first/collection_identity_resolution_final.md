# Collection Identity Resolution — Final Candidate State

Pass consolidado de solo lectura. No modifica DB, mappings, Collection, Wishlist, collection_manual_review.csv ni ejecuta apply.

## Summary

| Scope | Total | EXACT | PHYSICAL_CONFIRMATION_REQUIRED | MANUAL_WEB_REVIEW | MISMATCH | MISSING |
|---|---:|---:|---:|---:|---:|---:|
| Magic | 97 | 97 | 0 | 0 | 0 | 0 |
| One Piece | 23 | 20 | 3 | 0 | 0 | 0 |
| Collection | 120 | 117 | 3 | 0 | 0 | 0 |

Provenance gaps: 45; flags históricos conservados y separados de la identidad final.

## Rules and protections

- Magic: 44 pre-existing EXACT + 53 EXACT_RECOVERED = 97/97 EXACT.
- One Piece: convención de idioma validada 6/6; JP usa Japanese/Non-English según el set.
- EB02 y PRB02 son expansiones distintas. EB02-061A se resolvió a EB02-JP V2 (808172); 823516 era EB02/EN V2 y la pérdida de sufijo/familia produjo el mismatch histórico de aproximadamente EUR 200. No se usó precio.
- Una identidad física no demostrada permanece pendiente.

## Per-item result

| ID | Game | Card | Number | Lang. | Set | Version | Promo | Status | idProduct | Cardmarket URL | Rule | Gap | Physical |
|---:|---|---|---|---|---|---|---|---|---:|---|---|---|---|
| 33 | Magic | Frodo Baggins | 812 | en | LTR | Showcase Borderless Foil Booster Fun Surge Foil |  | EXACT | 737031 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=737031) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 34 | Magic | Frodo, Sauron's Bane | 304 | en | LTR |  |  | EXACT | 701765 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=701765&referrer=scryfall&utm_campaign=card_prices&utm_medium=text&utm_source=scryfall) | MAGIC_PRIOR_EXACT_RECOVERY | false | false |
| 35 | Magic | Samwise Gamgee | 327 | en | LTR | Showcase Borderless Foil Booster Fun |  | EXACT | 716026 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=716026) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 36 | Magic | Samwise the Stouthearted | 798 | en | LTR | Showcase Borderless Foil Booster Fun Surge Foil |  | EXACT | 736847 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=736847) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 37 | Magic | Merry, Esquire of Rohan | 325 | en | LTR | Showcase Borderless Foil Booster Fun |  | EXACT | 716061 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=716061) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 38 | Magic | Meriadoc Brandybuck | 806 | en | LTR | Showcase Borderless Foil Booster Fun Surge Foil |  | EXACT | 737025 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=737025) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 39 | Magic | Peregrin Took | 315 | en | LTR | Showcase Borderless Foil Booster Fun |  | EXACT | 716070 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=716070) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 40 | Magic | Pippin, Guard of the Citadel | 818 | en | LTR | Showcase Borderless Foil Surge Foil Booster Fun |  | EXACT | 737037 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=737037) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 41 | Magic | Aragorn, Company Leader | 316 | en | LTR |  |  | EXACT | 717763 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=717763&referrer=scryfall&utm_campaign=card_prices&utm_medium=text&utm_source=scryfall) | MAGIC_PRIOR_EXACT_RECOVERY | false | false |
| 42 | Magic | Aragorn, the Uniter | 317 | en | LTR |  |  | EXACT | 716022 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=716022&referrer=scryfall&utm_campaign=card_prices&utm_medium=text&utm_source=scryfall) | MAGIC_PRIOR_EXACT_RECOVERY | false | false |
| 43 | Magic | Legolas, Counter of Kills | 816 | en | LTR | Showcase Borderless Foil Booster Fun Surge Foil |  | EXACT | 737035 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=737035) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 44 | Magic | Legolas, Master Archer | 313 | en | LTR | Showcase Borderless Foil Booster Fun |  | EXACT | 716051 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=716051) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 45 | Magic | Gimli, Counter of Kills | 804 | en | LTR | Showcase Borderless Foil Booster Fun Surge Foil |  | EXACT | 737023 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=737023) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 46 | Magic | Gimli, Mournful Avenger | 815 | en | LTR |  |  | EXACT | 737034 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=737034&referrer=scryfall&utm_campaign=card_prices&utm_medium=text&utm_source=scryfall) | MAGIC_PRIOR_EXACT_RECOVERY | false | false |
| 47 | Magic | Boromir, Warden of the Tower | 302 | en | LTR |  |  | EXACT | 716042 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=716042&referrer=scryfall&utm_campaign=card_prices&utm_medium=text&utm_source=scryfall) | MAGIC_PRIOR_EXACT_RECOVERY | false | false |
| 48 | Magic | Gandalf the Grey | 814 | en | LTR | Showcase Borderless Foil Surge Foil Booster Fun |  | EXACT | 737033 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=737033) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 49 | Magic | Gandalf the White | 305 | en | LTR | Showcase Borderless Foil Booster Fun |  | EXACT | 716023 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=716023) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 50 | Magic | Gandalf, Friend of the Shire | 800 | en | LTR | Showcase Borderless Foil Booster Fun Surge Foil |  | EXACT | 736849 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=736849) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 51 | Magic | Elrond, Lord of Rivendell | 307 | en | LTR | Showcase Borderless Foil Booster Fun |  | EXACT | 717750 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=717750) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 52 | Magic | Elrond, Master of Healing | 810 | en | LTR | Showcase Borderless Foil Surge Foil Booster Fun |  | EXACT | 737029 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=737029) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 53 | Magic | Faramir, Field Commander | 795 | en | LTR | Showcase Borderless Foil Booster Fun Surge Foil |  | EXACT | 736844 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=736844) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 54 | Magic | Faramir, Prince of Ithilien | 319 | en | LTR | Showcase Borderless Foil Booster Fun |  | EXACT | 717727 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=717727) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 55 | Magic | Galadriel of Lothlórien | 321 | en | LTR | Showcase Borderless Foil Booster Fun |  | EXACT | 717753 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=717753) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 56 | Magic | Gollum, Patient Plotter | 801 | en | LTR | Showcase Borderless Foil Booster Fun Surge Foil |  | EXACT | 736850 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=736850) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 57 | Magic | Saruman of Many Colors | 328 | en | LTR | Showcase Borderless Foil Booster Fun |  | EXACT | 716077 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=716077) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 58 | Magic | Sauron, the Dark Lord | 329 | en | LTR | Showcase Borderless Foil Booster Fun |  | EXACT | 716072 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=716072) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 59 | Magic | Sauron, the Necromancer | 310 | en | LTR | Showcase Borderless Foil Booster Fun |  | EXACT | 716069 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=716069) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 60 | Magic | Sméagol, Helpful Guide | 330 | en | LTR | Showcase Borderless Foil Booster Fun |  | EXACT | 717775 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=717775) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 61 | Magic | Tom Bombadil | 331 | en | LTR | Showcase Borderless Foil Booster Fun |  | EXACT | 701768 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=701768) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 62 | Magic | Rohirrim Chargers | 496 | en | LTR | Borderless Full Art Foil Booster Fun |  | EXACT | 736524 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=736524) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 63 | Magic | Sword of the Animist | 385 | en | LTC | Borderless Full Art Foil Surge Foil Booster Fun |  | EXACT | 717998 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=717998) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 64 | Magic | Gandalf of the Secret Fire | 507 | en | LTR | Borderless Full Art Foil Booster Fun |  | EXACT | 736555 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=736555) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 65 | Magic | Shortcut to Mushrooms | 638 | en | LTR |  |  | EXACT | 738134 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=738134&referrer=scryfall&utm_campaign=card_prices&utm_medium=text&utm_source=scryfall) | MAGIC_PRIOR_EXACT_RECOVERY | false | false |
| 66 | Magic | Shadowfax, Lord of Horses | 227 | en | LTR | Foil |  | EXACT | 716135 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=716135) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 67 | Magic | Fall of Gil-galad | 165 | en | LTR | fbaab2c0-ea18-4b2f-b75b-506cbbea97e1:foil |  | EXACT | 716004 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=716004) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 68 | Magic | Book of Mazarbul | 116 | en | LTR | 04dcef75-6f98-4233-ae32-6fe41724c8e0:foil |  | EXACT | 716003 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=716003) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 69 | Magic | Long List of the Ents | 625 | en | LTR | Showcase Foil Silver Foil Scroll Booster Fun |  | EXACT | 738108 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=738108) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 70 | Magic | The Bath Song | 491 | en | LTR |  |  | EXACT | 737571 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=737571&referrer=scryfall&utm_campaign=card_prices&utm_medium=text&utm_source=scryfall) | MAGIC_PRIOR_EXACT_RECOVERY | false | false |
| 71 | Magic | One Ring to Rule Them All | 102 | en | LTR | bb2dc2e0-f393-4442-818b-d3b860bfffd0:foil |  | EXACT | 715916 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=715916) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 73 | Magic | Oath of the Grey Host | 101 | en | LTR | 6a780abd-f276-40d3-b2af-d2e47d858d3d:foil |  | EXACT | 717047 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=717047) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 74 | Magic | Tale of Tinúviel | 34 | en | LTR | 9ae65f96-7bfd-4390-88bf-764c26bf4668:foil |  | EXACT | 716129 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=716129) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 75 | Magic | War of the Last Alliance | 36 | en | LTR | 60ddf2cd-5b33-4c8a-a610-8e6a15404dde:foil |  | EXACT | 716133 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=716133) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 76 | Magic | Frodo, Sauron's Bane | 448 | en | LTR | Borderless Full Art Foil Booster Fun Bundle |  | EXACT | 716081 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=716081) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 77 | Magic | Pippin's Bravery | 414 | en | LTR | Borderless Full Art Foil Booster Fun |  | EXACT | 716056 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=716056) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 78 | Magic | Gandalf the White | 442 | en | LTR | Borderless Full Art Foil Booster Fun |  | EXACT | 716063 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=716063) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 79 | Magic | Gandalf, Friend of the Shire | 401s | en | PLTC | Borderless Full Art Foil Prerelease Datestamped |  | EXACT | 719346 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=719346) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 80 | Magic | Prince Imrahil the Fair | 431 | en | LTR | Borderless Full Art Foil Booster Fun |  | EXACT | 716025 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=716025) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 81 | Magic | Knights of Dol Amroth | 432 | en | LTR | Borderless Full Art Foil Booster Fun |  | EXACT | 716066 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=716066) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 82 | Magic | Gimli, Mournful Avenger | 436 | en | LTR |  |  | EXACT | 716059 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=716059&referrer=scryfall&utm_campaign=card_prices&utm_medium=text&utm_source=scryfall) | MAGIC_PRIOR_EXACT_RECOVERY | false | false |
| 83 | Magic | The One Ring | 451 | en | LTR | Borderless Full Art Foil Booster Fun Bundle |  | EXACT | 716083 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=716083) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 84 | Magic | Art Series: Fog on the Barrow-Downs | ART-2 | en | LTR | V2 |  | EXACT | 718546 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Fog-on-the-Barrow-Downs-V2) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 86 | Magic | Art Series: Goldberry, River-Daughter | ART-6 | en | LTR | V2 |  | EXACT | 718554 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Goldberry-River-Daughter-V2) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 87 | Magic | Art Series: The Watcher in the Water | ART-7 | en | LTR | V2 |  | EXACT | 718555 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-The-Watcher-in-the-Water-V2) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 88 | Magic | Art Series: Éomer of the Riddermark | ART-9 | en | LTR | V2 |  | EXACT | 718559 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Eomer-of-the-Riddermark-V2) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 89 | Magic | Art Series: Gimli, Counter of Kills | ART-10 | en | LTR | V2 |  | EXACT | 718561 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Gimli-Counter-of-Kills-V2) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 90 | Magic | Art Series: Generous Ent | ART-11 | en | LTR | V2 |  | EXACT | 718563 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Generous-Ent-V2) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 91 | Magic | Art Series: Mirrormere Guardian | ART-12 | en | LTR |  |  | EXACT | 718565 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=718565) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 92 | Magic | Art Series: Bilbo, Retired Burglar | ART-14 | en | LTR | V2 |  | EXACT | 718575 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Bilbo-Retired-Burglar-V2) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 93 | Magic | Art Series: Legolas, Counter of Kills | ART-17 | en | LTR | V2 |  | EXACT | 718582 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Legolas-Counter-of-Kills-V2) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 94 | Magic | Art Series: Saruman of Many Colors | ART-20 | en | LTR | V2 |  | EXACT | 718601 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Saruman-of-Many-Colors-V2) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 95 | Magic | Art Series: Sharkey, Tyrant of the Shire | ART-22 | en | LTR | V2 |  | EXACT | 718605 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Sharkey-Tyrant-of-the-Shire-V2) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 96 | Magic | Art Series: Shelob, Child of Ungoliant | ART-23 | en | LTR | V2 |  | EXACT | 718606 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Shelob-Child-of-Ungoliant-V2) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 97 | Magic | Art Series: Théoden, King of Rohan | ART-25 | en | LTR | V2 |  | EXACT | 718610 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Theoden-King-of-Rohan-V2) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 98 | Magic | Art Series: Tom Bombadil | ART-26 | en | LTR | V2 |  | EXACT | 718613 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Tom-Bombadil-V2) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 99 | Magic | Art Series: Uglúk of the White Hand | ART-27 | en | LTR | V2 |  | EXACT | 718614 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Ugluk-of-the-White-Hand-V2) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 100 | Magic | Art Series: Plains | ART-30 | en | LTR | V2 |  | EXACT | 718621 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Plains-V2) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 101 | Magic | Art Series: Mountain | ART-31 | en | LTR | V2 |  | EXACT | 718622 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Mountain-V2) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 102 | Magic | Art Series: Elanor Gardner | ART-32 | en | LTR | V2 |  | EXACT | 718625 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Elanor-Gardner-V2) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 103 | Magic | Art Series: Aragorn and Arwen, Wed | ART-33 | en | LTR | V2 |  | EXACT | 718626 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Aragorn-and-Arwen-Wed-V2) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 104 | Magic | Art Series: Bilbo's Ring | ART-37 | en | LTR | V2 |  | EXACT | 718640 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Bilbos-Ring-V2) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 105 | Magic | Art Series: Faramir, Field Commander | ART-38 | en | LTR | V2 |  | EXACT | 718643 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Faramir-Field-Commander-V2) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 106 | Magic | Art Series: Elrond, Lord of Rivendell | ART-40 | en | LTR | V2 |  | EXACT | 718646 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Elrond-Lord-of-Rivendell-V2) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 107 | Magic | Art Series: Witch-king of Angmar | ART-43 | en | LTR | V2 |  | EXACT | 718652 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Witch-king-of-Angmar-V2) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 108 | Magic | Art Series: Frodo Baggins | ART-47 | en | LTR | V4 |  | EXACT | 718580 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Frodo-Baggins-V4) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 109 | Magic | Art Series: Galadriel of Lothlórien | ART-48 | en | LTR | V2 |  | EXACT | 718662 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Galadriel-of-Lothlorien-V2) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 110 | Magic | Art Series: Merry, Esquire of Rohan | ART-50 | en | LTR | V2 |  | EXACT | 718666 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Merry-Esquire-of-Rohan-V2) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 111 | Magic | Art Series: Pippin, Guard of the Citadel | ART-51 | en | LTR | V2 |  | EXACT | 718669 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Pippin-Guard-of-the-Citadel-V2) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 112 | Magic | Art Series: Mines of Moria | ART-56 | en | LTR | V2 |  | EXACT | 718683 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Mines-of-Moria-V2) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 113 | Magic | Art Series: Aragorn, King of Gondor | ART-57 | en | LTR | V2 |  | EXACT | 718685 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Aragorn-King-of-Gondor-V2) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 114 | Magic | Art Series: Gwaihir, Greatest of the Eagles | ART-59 | en | LTR | V2 |  | EXACT | 718693 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Gwaihir-Greatest-of-the-Eagles-V2) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 115 | Magic | Art Series: Call for Aid | ART-60 | en | LTR | V2 |  | EXACT | 718694 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Call-for-Aid-V2) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 116 | Magic | Art Series: Cavern-Hoard Dragon | ART-61 | en | LTR | V2 |  | EXACT | 718700 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Cavern-Hoard-Dragon-V2) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 117 | Magic | Art Series: Gríma, Saruman's Footman | ART-63 | en | LTR | V2 |  | EXACT | 718708 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Grima-Sarumans-Footman-V2) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 118 | Magic | Art Series: Merry, Warden of Isengard | ART-65 | en | LTR | V2 |  | EXACT | 718715 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Merry-Warden-of-Isengard-V2) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 119 | Magic | Art Series: Treebeard, Gracious Host | ART-67 | en | LTR | V2 |  | EXACT | 718719 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Treebeard-Gracious-Host-V2) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 120 | Magic | Art Series: Asceticism | ART-72 | en | LTR | V2 |  | EXACT | 718740 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Asceticism-V2) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 121 | Magic | Art Series: Realm Seekers | ART-74 | en | LTR | V2 |  | EXACT | 718747 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Realm-Seekers-V2) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 122 | Magic | Art Series: Ghost Quarter | ART-78 | en | LTR | V2 |  | EXACT | 718757 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Ghost-Quarter-V2) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 123 | Magic | Art Series: Valley of Gorgoroth | ART-80 | en | LTR | V2 |  | EXACT | 718763 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Valley-of-Gorgoroth-V2) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 124 | Magic | Art Series: Faramir, Steward of Gondor | ART-62 | en | LTR | V2 |  | EXACT | 718704 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Faramir-Steward-of-Gondor-V2) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 125 | Magic | Art Series: Nazgûl | ART-53 | en | LTR | V2 |  | EXACT | 718672 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Nazgul-V2) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 126 | Magic | Art Series: Sauron, the Dark Lord | ART-21 | en | LTR | V2 |  | EXACT | 718602 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Sauron-the-Dark-Lord-V2) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 127 | Magic | Art Series: Éowyn, Fearless Knight | ART-15 | en | LTR | V2 |  | EXACT | 718577 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Eowyn-Fearless-Knight-V2) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 128 | Magic | Art Series: Samwise Gamgee | ART-19 | en | LTR | V2 |  | EXACT | 718671 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Samwise-Gamgee-V2) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 129 | Magic | King of the Oathbreakers | 780 | en | LTR | Extended Art Foil Surge Foil Booster Fun |  | EXACT | 738025 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=738025) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 130 | Magic | Radagast the Brown | 776 | en | LTR | Extended Art Foil Surge Foil Booster Fun |  | EXACT | 738021 | [link](https://www.cardmarket.com/en/Magic/Products?idProduct=738021) | MAGIC_PRE_EXISTING_EXACT | false | false |
| 131 | Magic | Art Series: Gandalf the White | ART-3 | en | LTR | V2 |  | EXACT | 718547 | [link](https://www.cardmarket.com/en/Magic/Products/Singles/The-Lord-of-the-Rings-Tales-of-Middle-earth-Extras/Art-Series-Gandalf-the-White-V2) | MAGIC_ART_SERIES_MANUAL_WEB | true | false |
| 133 | One Piece | Borsalino | OP05-051 | jp | OP05 | V1 |  | EXACT | 733344 | [link](https://www.cardmarket.com/en/OnePiece/Products/Singles/Awakening-of-the-New-Era-Japanese/Borsalino-OP05-051-V1) | ONE_PIECE_OPXX_JP_LANGUAGE_FAMILY | false | false |
| 134 | One Piece | Dracule Mihawk | OP01-070 | jp | OP01 | V2 |  | EXACT | 768325 | [link](https://www.cardmarket.com/en/OnePiece/Products/Singles/Romance-Dawn-Japanese/Dracule-Mihawk-OP01-070-V2) | OP01_JP_V2_PARALLEL_FIXED_REPRINT | false | false |
| 135 | One Piece | Dracule Mihawk | OP01-070 | jp | OP01 | PENDING |  | PHYSICAL_CONFIRMATION_REQUIRED |  |  | PENDING_PHYSICAL_CONFIRMATION | false | true |
| 136 | One Piece | Yamato | OP13-054 | jp | OP13 | V1 |  | EXACT | 857251 | [link](https://www.cardmarket.com/en/OnePiece/Products/Singles/Carrying-on-his-Will-Non-English/Yamato-OP13-054-V1) | ONE_PIECE_OPXX_JP_LANGUAGE_FAMILY | false | false |
| 137 | One Piece | Lilith | OP13-113 | jp | OP13 | V2 |  | EXACT | 857331 | [link](https://www.cardmarket.com/en/OnePiece/Products/Singles/Carrying-on-his-Will-Non-English/Lilith-OP13-113-V2) | ONE_PIECE_OPXX_JP_LANGUAGE_FAMILY | false | false |
| 138 | One Piece | Monkey.D.Luffy | EB02-061A | jp | EB02 | V2 |  | EXACT | 808172 | [link](https://www.cardmarket.com/en/OnePiece/Products/Singles/Anime-25th-Collection-Japanese/MonkeyDLuffy-EB02-061-V2) | EB02_061A_EXACT | false | false |
| 139 | One Piece | Rob Lucci | OP05-093 | jp | OP05 | V2 |  | EXACT | 733430 | [link](https://www.cardmarket.com/en/OnePiece/Products/Singles/Awakening-of-the-New-Era-Japanese/Rob-Lucci-OP05-093-V2) | ONE_PIECE_OPXX_JP_LANGUAGE_FAMILY | false | false |
| 140 | One Piece | X.Drake | OP05-055 | jp | OP05 | V2 |  | EXACT | 733352 | [link](https://www.cardmarket.com/en/OnePiece/Products/Singles/Awakening-of-the-New-Era-Japanese/X-Drake-OP05-055-V2) | ONE_PIECE_OPXX_JP_LANGUAGE_FAMILY | false | false |
| 141 | One Piece | Cavendish | OP01-008 | jp | OP01 | PENDING |  | PHYSICAL_CONFIRMATION_REQUIRED |  |  | PENDING_PHYSICAL_CONFIRMATION | false | true |
| 142 | One Piece | Gol.D.Roger | OP13-064 | jp | OP13 | V1 |  | EXACT | 857262 | [link](https://www.cardmarket.com/en/OnePiece/Products/Singles/Carrying-on-his-Will-Non-English/GolDRoger-OP13-064-V1) | ONE_PIECE_OPXX_JP_LANGUAGE_FAMILY | false | false |
| 143 | One Piece | Nefeltari Vivi | EB02-026 | jp | EB02 | V1 |  | EXACT | 808127 | [link](https://www.cardmarket.com/en/OnePiece/Products/Singles/Anime-25th-Collection-Japanese/Nefeltari-Vivi-EB02-026-V1) | ONE_PIECE_OPXX_JP_LANGUAGE_FAMILY | false | false |
| 144 | One Piece | S-Snake | OP08-112 | jp | OP08 | V1 |  | EXACT | 771756 | [link](https://www.cardmarket.com/en/OnePiece/Products/Singles/Two-Legends-Non-English/S-Snake-OP08-112-V1) | ONE_PIECE_OPXX_JP_LANGUAGE_FAMILY | false | false |
| 145 | One Piece | Koala | OP05-006 | jp | OP05 | V1 |  | EXACT | 733281 | [link](https://www.cardmarket.com/en/OnePiece/Products/Singles/Awakening-of-the-New-Era-Japanese/Koala-OP05-006-V1) | ONE_PIECE_OPXX_JP_LANGUAGE_FAMILY | false | false |
| 146 | One Piece | Monkey.D.Luffy | OP01-024 | jp | OP01 | V1 |  | EXACT | 768265 | [link](https://www.cardmarket.com/en/OnePiece/Products/Singles/Romance-Dawn-Japanese/MonkeyDLuffy-OP01-024-V1) | ONE_PIECE_OPXX_JP_LANGUAGE_FAMILY | false | false |
| 147 | One Piece | Yamato | EB02-006 | jp | EB02 | V1 |  | EXACT | 808101 | [link](https://www.cardmarket.com/en/OnePiece/Products/Singles/Anime-25th-Collection-Japanese/Yamato-EB02-006-V1) | ONE_PIECE_OPXX_JP_LANGUAGE_FAMILY | false | false |
| 148 | One Piece | Pica | OP05-032 | jp | OP05 | V1 |  | EXACT | 733317 | [link](https://www.cardmarket.com/en/OnePiece/Products/Singles/Awakening-of-the-New-Era-Japanese/Pica-OP05-032-V1) | ONE_PIECE_OPXX_JP_LANGUAGE_FAMILY | false | false |
| 149 | One Piece | Kin'emon | OP01-040 | jp | OP01 | V1 |  | EXACT | 768285 | [link](https://www.cardmarket.com/en/OnePiece/Products/Singles/Romance-Dawn-Japanese/Kinemon-OP01-040-V1) | ONE_PIECE_OPXX_JP_LANGUAGE_FAMILY | false | false |
| 150 | One Piece | Trafalgar Law | EB02-045 | jp | EB02 | V1 |  | EXACT | 808150 | [link](https://www.cardmarket.com/en/OnePiece/Products/Singles/Anime-25th-Collection-Japanese/Trafalgar-Law-EB02-045-V1) | ONE_PIECE_OPXX_JP_LANGUAGE_FAMILY | false | false |
| 151 | One Piece | Uta | OP13-023 | jp | OP13 | V1 |  | EXACT | 857215 | [link](https://www.cardmarket.com/en/OnePiece/Products/Singles/Carrying-on-his-Will-Non-English/Uta-OP13-023-V1) | ONE_PIECE_OPXX_JP_LANGUAGE_FAMILY | false | false |
| 152 | One Piece | Trafalgar Law | P-038 | jp | PROMO |  | Promos-Japanese | EXACT | 722798 | [link](https://www.cardmarket.com/en/OnePiece/Products/Singles/Promos-Japanese/Trafalgar-Law-P-038) | PROMO_P038_JP_FAMILY | false | false |
| 153 | One Piece | Stussy | OP13-110 | jp | OP13 | V1 |  | EXACT | 857326 | [link](https://www.cardmarket.com/en/OnePiece/Products/Singles/Carrying-on-his-Will-Non-English/Stussy-OP13-110-V1) | ONE_PIECE_OPXX_JP_LANGUAGE_FAMILY | false | false |
| 154 | One Piece | King | OP01-096 | jp | OP01 | PENDING |  | PHYSICAL_CONFIRMATION_REQUIRED |  |  | PENDING_PHYSICAL_CONFIRMATION | false | true |
| 155 | One Piece | Rebecca | OP05-091 | jp | OP05 | V1 |  | EXACT | 733426 | [link](https://www.cardmarket.com/en/OnePiece/Products/Singles/Awakening-of-the-New-Era-Japanese/Rebecca-OP05-091-V1) | ONE_PIECE_OPXX_JP_LANGUAGE_FAMILY | false | false |

## Physical confirmations needed

These items intentionally have no final idProduct until physical confirmation.

### Item 135 — Dracule Mihawk (OP01-070)

Mirar frente y dorso: confirmar Fixed Reprint, leer marcador de errata/copyright y decir si corresponde V1 o V2. No decidir por precio.

JP: 768324 OP01-JP V1 https://www.cardmarket.com/en/OnePiece/Products/Singles/Romance-Dawn-Japanese/Dracule-Mihawk-OP01-070-V1; 768359 OP01-JP V2 https://www.cardmarket.com/en/OnePiece/Products/Singles/Romance-Dawn-Japanese/Dracule-Mihawk-OP01-070-V2. EN: 690896 V1, 690930 V2.

### Item 141 — Cavendish (OP01-008)

Mirar el tratamiento y origen: confirmar Box Topper, no Demo Decks, y distinguir V1 o V2 por texto/copyright. Responder: Item 141: Box Topper V2.

JP: 768246 OP01-JP V1 https://www.cardmarket.com/en/OnePiece/Products/Singles/Romance-Dawn-Japanese/Cavendish-OP01-008-V1; 768247 OP01-JP V2 https://www.cardmarket.com/en/OnePiece/Products/Singles/Romance-Dawn-Japanese/Cavendish-OP01-008-V2; Demo: 874414 https://www.cardmarket.com/en/OnePiece/Products/Singles/Demo-Decks/Cavendish-OP01-008. EN: 690802 V1, 690804 V2.

### Item 154 — King (OP01-096)

Mirar frente y dorso: confirmar Fixed Reprint y el texto/copyright de errata, distinguir V1 o V2 y descartar OP01E Pre-Errata. Responder: Item 154: Fixed Reprint V2.

JP: 768358 OP01-JP V1 https://www.cardmarket.com/en/OnePiece/Products/Singles/Romance-Dawn-Japanese/King-OP01-096-V1; 768359 OP01-JP V2 https://www.cardmarket.com/en/OnePiece/Products/Singles/Romance-Dawn-Japanese/King-OP01-096-V2. EN: 690929 V1, 690930 V2.

## Evidence and safety

The CSV is authoritative row-level output. Evidence records identity basis without price/seller-listing selection.
