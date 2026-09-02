# POKEMON-151-002D — Summary

Route: `all`; offline: `True`.

1. Can Cardmarket public listings be used sustainably?
   `NO automated path demonstrated; status BLOCKED.`
2. Can Reverse Holo Low be obtained directly from Cardmarket?
   `NOT DEMONSTRATED; the public sample was blocked.`
3. Does Cardmarket require browser/manual filtering?
   `UNKNOWN from this run; current Help Center confirms Reverse Holo is a listing attribute.`
4. Is automated access blocked?
   `BLOCKED` on the 20-page sample.
5. Does current Pokémon TCG API expose reverseHoloLow for sv3pt5?
   `YES as a present field in 207/207 responses; positive usable value in 149/207.`
6. For how many 151 cards?
   `149 with positive reverseHoloLow; zeros are treated as unavailable, not as prices.`
7. Does Pokémon TCG API provide TCGplayer reverseHolofoil?
   `YES for 146/207 exact identities with a usable value.`
8. For how many physical reverse printings?
   `Local reverse_holo printings: 153; API finish-specific coverage: 146.`
9. Does TCGdex provide equivalent finish-specific TCGplayer pricing?
   `YES by explicit variant keys where present: normal 123, holo 72, reverse 148.`
10. Do Pokémon TCG API and TCGdex agree where both exist?
   `Availability agreement by finish on common exact identities: {'normal': 193, 'holo': 193, 'reverse_holo': 193}; disagreements: {'normal': 0, 'holo': 0, 'reverse_holo': 0}.`
11. Can any source be trusted enough for exact finish pricing?
   `Only as a candidate/reference after exact identity and finish evidence; this sprint does not promote pricing.`
12. Which source should remain primary?
   `Cardmarket direct exact-finish EUR, when demonstrable.`
13. Which source should be secondary?
   `TCGplayer finish-specific USD; Cardmarket-derived external Reverse is separately classified.`
14. Should Reverse Holo Cardmarket current_price remain NULL?
   `YES for the current dashboard until direct or explicitly approved Cardmarket-derived policy is validated.`
15. Is a safe POKEMON-151-003 now possible?
   `Not globally. Only a future, explicitly reviewed subset could qualify.`
16. If yes, for which subset and using which source?
   `No subset is auto-enabled by 002D; candidates are listed in 05_finish_price_coverage.csv.`

Coverage recommendation counts: `{'tcgplayer_secondary_reference': 201, 'cardmarket_derived_external_reverse_low': 142, 'NULL': 19}`.
Pokémon TCG API acquisition: `bulk`; records: `207/207`.
No database writes, price imports, snapshots, resolutions, Collection or Wishlist changes were made.
