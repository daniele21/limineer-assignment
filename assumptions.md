# Assumptions

We use two scenarios to decide which sites to recommend now and which deserve more investigation.

- **Conservative:** build a shortlist we can defend with the evidence we have. Prioritize precision and avoid giving credit to unverified benefits.
- **Potential / risky:** show how attractive a site could become if favourable assumptions are confirmed. Identify the checks that could improve its score or bring it onto the shortlist.

Comparing the two shows how much each site's score depends on assumptions and where further checks could change the decision.

## Rules for both scenarios

- Keep the sponsor's rubric and weights. There is no extra 2 MW minimum or regional quota.
- Use the latest dated owner status. Exclude owners who refused and sites confirmed as protected.
- Merge duplicate parcels and keep their combined evidence.
- Use parcel area as a proxy for usable area unless newer notes contradict it. Sold land stays sold.
- Keep known neutral sentiment, opposition and flood risk as recorded.
- If the search found no substation within 10 km, distance earns zero points.

## Conservative assumptions

- Use official grid figures, even when the vendor estimate is higher. Hold sites with missing official grid data.
- Unknown values earn no points. Unknown sentiment stays unknown, not opposed.
- Hold sites with missing protection, flood, area or owner information, or unresolved protection/area conflicts.
- Prefer sites with at least 2 MW of confirmed headroom when stronger options exist.

## Potential / risky assumptions

- If official grid data is missing or older than June 30, 2026, consider a newer vendor estimate. Use its stated upper band for upside and show the central estimate too. The vendor's ±40% band is unvalidated.
- Unknown or conditional sentiment can earn ten points if support is confirmed and any stated condition is met.
- Unknown distance can earn 15 points if a new check confirms a substation within 1 km.
- Other unknowns can show a best-case ceiling: at least 4 MW, a signed LOI, no flood risk and at least 1,200 m² of usable land. List each assumption; these points are hypothetical.
- A protection concern needs a verified, legally buildable footprint before recommendation. A high potential score does not clear it.
- For S-013, use the reported roughly 700 m² as the potential area proxy. It earns zero area points; do not use the old 2,400 m².

## Comparing the scores

Show two scores: **conservative lower** and **potential upper**. The difference shows how much depends on favourable assumptions. Explain each increase and what must be checked.

Held sites have no conservative ranked score, not a score of zero. Show their potential separately and keep them off the current shortlist until critical checks pass.

Potential scores describe what could happen under these assumptions. They are not promises or confidence intervals.

See `analysis/SCENARIO_ASSUMPTIONS.md` for examples.

The frontend can choose grid evidence, unknown sentiment, missing critical checks
and unresolved land checks independently. The conservative and potential presets
are the endpoints; mixed answers select a score under that combination.
`data/scoring.json` contains the questions, answers and precomputed results.
If official capacity is missing but a vendor estimate exists, using that estimate
requires the vendor answer. Other optimistic answers cannot bypass that choice
by inventing a higher capacity.
