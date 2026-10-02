# Sponsor rubric review — 2026-10-02

This review applies the sponsor rubric to the 23 candidates in
`data/sites.normalized.json`. It is an exploratory calculation, not the final
scoring implementation or a construction-feasibility assessment. The per-site
tiers and contributions are saved in `output/rubric_review.json`. The input files
were not changed.

This is the conservative-source baseline. The subsequent
`analysis/SCENARIO_ASSUMPTIONS.md` defines the separate potential/risky policy,
including allowed vendor alternatives and conditional admission. The top-five
stability claim below varies missing sentiment only; it does not apply across
these different source policies.

The completion ranges below document the earlier missing-sentiment analysis.
In the current two-scenario contract, favourable completions are included in the
potential upper where allowed; they are not a separate source-fixed score endpoint.

## Exact tier and point definitions

Each criterion contributes `weight × tier / 5`. The six weights total 100.
The table below makes overlapping boundaries unambiguous. Headroom and area are
tested from highest threshold down; distance from lowest threshold up.

| Criterion | Weight / maximum points | Value → tier → contribution |
|---|---:|---|
| C1 Official headroom | 30 | ≥4 MW → 5 → 30; 2≤x<4 → 3 → 18; 1≤x<2 → 1 → 6; <1 → 0 → 0 |
| C2 Official distance | 15 | ≤1 km → 5 → 15; 1<x≤3 → 3 → 9; 3<x≤6 → 1 → 3; >6 → 0 → 0 |
| C3 Owner status | 20 | LOI signed → 5 → 20; in talks → 3 → 12; not contacted → 1 → 4; refused → 0 → 0 |
| C4 Local sentiment | 10 | supportive → 5 → 10; neutral → 3 → 6; opposed → 0 → 0; unknown/conditional → no tier |
| C5 Flood | 15 | none → 5 → 15; low → 4 → 12; medium → 2 → 6; high → 0 → 0 |
| C6 Usable-area proxy | 10 | ≥1,200 m² → 5 → 10; 800≤x<1,200 → 2 → 4; <800 → 0 → 0 |

In tier notation the total is `6C1 + 3C2 + 4C3 + 2C4 + 3C5 + 2C6`.
S-025's exact 2.0 MW receives tier 3 and 18 points. Exactly 4 MW gets 30 points;
exactly 1,200 m² gets 10 points. Exactly 1/3/6 km gets 15/9/3 points respectively.
Numeric zero is a valid known value and must not be mistaken for missing data.

These are discrete tiers. Do not interpolate, smooth, round values into another
tier or give extra points above the maximum. A 4.1 MW site and a 5.5 MW site
receive identical headroom contributions.

## What the weights imply

Grid headroom and distance contribute up to 45 points; owner and sentiment up to
30; flood and area up to 25. One tier unit adds 6, 3, 4, 2, 3 and 2 points
respectively. The actual tiers skip values, producing meaningful jumps:

- Crossing 2 MW or 4 MW adds 12 points each.
- Moving from just above 1 km to 1 km adds 6 points.
- Moving from in talks to LOI signed adds 8 points.
- Moving from neutral to supportive adds 4 points.
- Moving from medium to low flood adds 6 points; low to none adds 3.
- Crossing 1,200 m² adds 6 points; crossing 800 m² adds 4.

A change from 3.9 to 4.0 MW therefore adds more points than gaining a signed LOI
from an in-talks owner. This is a consequence of the agreed rubric, not a claim
that the physical project changes sharply at that threshold. Near-boundary
values need verification before interpreting a small ranking gap as decisive.
The sponsor rubric should remain unchanged; sensitivities should be explained
separately rather than silently changing the weights.

## Missing values and evidence quality

All retained sites have known grid, owner, flood and proxy-area inputs. Nine lack
a scorable sentiment value. For them:

`lower_bound = sum of contributions from known criteria`

`upper_bound = lower_bound + 10`

Keep the sentiment tier and contribution null. The lower-bound total earns zero
additional points from the missing criterion without asserting opposition.
Never reweight the other criteria: dividing an 87-point total by the known
90% weight would create a 96.67 score and reward missing evidence.

These ranges describe possible rubric completion only. They are not statistical
confidence intervals and do not include source-age, measurement or parcel-proxy
uncertainty. Possible sentiment contributions are specifically 0, 6 or 10 points.
Conditional sentiment has the same scoring treatment as unknown, while its
condition and exact quote remain visible.

`score_inputs_complete` and known-weight coverage describe completeness, not
confidence. Fourteen sites have 100% rubric coverage; nine have 90%. Even a
complete site can have an old grid publication, a councillor's individual
support, a non-binding LOI or area known only through a parcel proxy. Every
retained site uses the parcel-area proxy; none has measured usable area in this
dataset. Evidence caveats should remain categorical and source-backed rather
than becoming an invented numerical confidence percentage or hidden discount.

## Exploratory ranking

Rows are ordered by lower-bound score. Site ID only orders equal-score rows for
display; it does not imply a superior site. Equal lower bounds can also differ
in completeness and upside.

| Site | Name | Lower bound / complete score | Possible completion range | Coverage |
|---|---|---:|---:|---:|
| S-003 | Kessby Old Quarry Yard | 97 | 97 | 100% |
| S-018 | Grelle Harbour Plot | 97 | 97 | 100% |
| S-017 | Brekke Depot | 96 | 96 | 100% |
| S-027 | Varne Farm Edge | 87 | 87–97 | 90% |
| S-014 | Orlund Depot Yard | 86 | 86 | 100% |
| S-032 | Ashcombe Field Corner | 82 | 82–92 | 90% |
| S-006 | Ulven Works Site | 76 | 76 | 100% |
| S-007 | Tallow Cross Brownfield | 76 | 76 | 100% |
| S-001 | Brisk Lane Yard | 68 | 68 | 100% |
| S-037 | Merrow Depot | 68 | 68 | 100% |
| S-002 | Farrow Bridge Yard | 67 | 67 | 100% |
| S-028 | Jessop Common | 64 | 64 | 100% |
| S-030 | Tofte Industrial Estate | 64 | 64 | 100% |
| S-005 | Dalby Works | 61 | 61–71 | 90% |
| S-016 | Glaze Farm Edge | 61 | 61–71 | 90% |
| S-021 | Selby Quay Yard | 61 | 61–71 | 90% |
| S-034 | Vinstra Old Dairy | 61 | 61 | 100% |
| S-025 | Ingle Street Yard | 59 | 59 | 100% |
| S-010 | Eller Road Plot | 57 | 57–67 | 90% |
| S-012 | Nesby Rail Sidings | 43 | 43–53 | 90% |
| S-040 | Otterley Works | 43 | 43 | 100% |
| S-039 | Oddan Car Park | 41 | 41–51 | 90% |
| S-023 | Hask Common | 32 | 32–42 | 90% |

Worked example, S-003: headroom 30 + distance 15 + owner 20 + sentiment 10 +
flood 12 + area 10 = **97**. Its requested 12% revenue share is a commercial
follow-up; it does not alter any criterion. S-018 has the same rubric score even
though its real-world follow-up issues differ.

S-027 contributes 30 + 15 + 20 + unknown + 12 + 10 = **at least 87**. Even if
sentiment resolves to opposed, its rubric score exceeds S-014's complete 86.
This does not establish community acceptance or resolve its noise-report condition.

## Shortlist stability and precision-first judgment

Under the current inputs, varying only the nine missing sentiment values leaves
S-003, S-018, S-017 and S-027 in the top five in every completion scenario. This
is stability within the rubric, not a guarantee against new evidence. S-027 can
tie the 97-point leaders if sentiment becomes supportive; it can fall to fifth
if S-032 gets enough sentiment points while S-027 gets none.

The remaining slot is S-014 versus S-032. S-032 scores 82 if opposed, 88 if
neutral, or 92 if supportive; S-014 scores 86. Resolving S-032's sentiment is
therefore the clearest information-gathering action for the fifth-slot decision.
S-027's condition also needs resolving for recommendation confidence, although
it does not change membership in the top five under sentiment-only scenarios.
All other incomplete sites have maximum scores of 71 or less.

An exhaustive calculation over all 19,683 combinations of the nine missing
sentiment contributions (0, 6 or 10) confirmed these membership conclusions.
These scenarios are not assigned probabilities. All contribution totals and
the actual 2 MW and 1 km boundary cases were also checked.

Completeness-first selection would remove S-027/S-032 and bring S-006 or S-007
into fifth position at 76. Both have less than 2 MW of official headroom, so
complete evidence alone is not sufficient to identify a stronger project fit.
The existing assumption allows smaller batteries under the rubric; it expresses
a preference for at least 2 MW when stronger options exist, not a new kill rule.

Avoid silently mixing this preference into the score. A final recommendation can
explain suitability separately. Likewise, area below 1,200 m² loses only six
points rather than triggering exclusion, and high flood loses at most 15.
Theoretically, a high-flood site could score 85, an opposed site 90, or a site
with less than 1 MW 70 if every other criterion were maximal. The weighted sum
allows strengths to compensate for weaknesses; it does not certify feasibility.

## Recommended scoring contract

Implement the six sponsor tiers exactly. For each criterion output its selected
value, tier (or null), weight, contribution (or null), evidence reference and
assumptions. For each site output the lower and upper bounds, completeness,
known-weight coverage, flags and source provenance. A single displayed score
can be the conservative lower bound, labelled "at least" when incomplete.

Rank admitted sites by lower bound descending, preserving equal-score ties and
using site ID only for deterministic display. Do not apply vendor overrides,
imputation, confidence multipliers, commercial penalties or extra points for
excess land/headroom. Recommendation priority can use explicit judgment and
evidence caveats separately from the sponsor score.

The final interface should distinguish admission status, rubric score and the
recommendation. Held/excluded sites have no place in the active ranking; their
reasons remain visible in `output/normalization_review.json`. A precise
provisional reading is three complete leaders, S-027 with a visible sentiment
condition, S-014 as the conservative fifth site and S-032 as the reserve whose
sentiment could change that fifth-slot choice. Commercial and technical checks
remain necessary even for the complete leaders.
