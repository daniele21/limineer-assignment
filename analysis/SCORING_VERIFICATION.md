# Scoring verification — 2026-10-02

The two-scenario calculations are current in `output/scenario_review.json`.
Their input and assumptions hashes match the current files. The numbers are
exploratory: the generator is `/tmp/limineer_scenario_review.py`, and `main.py`
still runs extraction only. There is no repository-integrated scenario scorer.

**Subsequent update:** `src/field_notes/scoring.py` now generates
`data/scoring.json` with the four frontend questions and all 24 answer profiles.
The earlier findings below describe the exploratory report. Generator integration
and regression coverage are now provided by the new module and
`tests/test_scoring.py`; see `analysis/FRONTEND_SCORING_DATA.md` for the current
contract. The Git-history limitation below still applies.

## Evidence checked

Run `uv run python scripts/verify_scenarios.py` to verify the saved report offline.
Results are in `output/scenario_verification.json`. The checker reads the original
sites and extraction, rebuilds normalization, and independently applies the
sponsor tiers using lookup tables rather than the exploratory generator's helpers.

All **627 artifact checks** passed. This count includes repetitive per-site and
per-criterion assertions; it is not 627 independent regression tests. The checks
cover current hashes, exact normalized records and evidence, all conservative
contributions, potential totals, source precedence, actual vendor ranges,
exclusion persistence, duplicate merging, named hand-calculated examples and
the actual 2 MW / 1 km boundary cases in this dataset.

The checker also rejected five deliberately corrupted copies: an inflated
conservative score, an invented vendor range, admission of a protected site,
missing sentiment hypothesis and a duplicate ranking entry. Those corruptions
were created in a temporary directory; the real report was not changed.
All **42 existing offline regression tests** passed again. They test extraction
and normalization; they do not establish full coverage of the scenario generator.
No API request was made.

## Hand calculations

Contributions below are ordered as headroom, distance, owner, sentiment, flood,
area. Unknown contributions earn no points in the conservative subtotal while
their evidence values remain null.

| Site | Conservative calculation | Potential calculation | Required evidence or assumption |
|---|---|---|---|
| S-003 | 30+15+20+10+12+10 = 97 | Same = 97 | 4.6 MW, 0.8 km, LOI, council support, low flood, 2,100 m² parcel proxy. |
| S-007 | 6+15+20+10+15+10 = 76 | 30+15+20+10+15+10 = 100 | March official 1.6 MW is replaced by a hypothetical vendor-supported ≥4 MW tier. September vendor central 5.2 MW already reaches that tier; the 7.28 MW upper band adds no further points. |
| S-021 | 18+9+12+0 earned+12+10 = 61 | 30+9+12+10+12+10 = 83 | Vendor-supported ≥4 MW capacity plus confirmed support after the noise condition is addressed. Neither is a confirmed improvement. |
| S-027 | 30+15+20+0 earned+12+10 = 87 | 30+15+20+10+12+10 = 97 | Confirmed support after the noise condition is addressed. Current official 5.5 MW is retained. |
| S-032 | 30+15+12+0 earned+15+10 = 82 | 30+15+12+10+15+10 = 92 | Support is hypothetical: its only note concerns owner negotiations. Current official 4.5 MW is retained. |

S-021's note says: "Council has no formal position yet; officer said 'depends on
the noise report'." Its unknown sentiment is therefore reasonable; confirmed
support is an upper-scenario hypothesis, not an extracted fact. The assumptions
now explicitly require support **and** any stated condition to be confirmed.
Satisfying a noise-report condition alone does not establish support.

S-025 has exactly 2.0 MW and receives 18 headroom points. S-032 has exactly 1.0 km
and receives 15 distance points. These agree with the chosen inclusive boundaries.

## Important constraints

- S-020's latest September 5 note says the owner declined to lease. It stays
  excluded, despite earlier July negotiations. Refusal exclusion is our stated
  operational policy; the sponsor rubric itself assigns zero owner points.
- S-033 has registry protection true and stays excluded under the sponsor kill rule.
- S-017/S-031 is one parcel and one opportunity, with the September LOI and earlier
  neutral-neighbour evidence both retained.
- S-013's note reports a sale and roughly 700 m² remaining. Its conditional
  82-point calculation earns zero area points. The stale 2,400 m² is not restored.
- S-008/S-019's successful searches found no substation within 10 km. Their distance
  remains zero points even in the potential scenario.
- S-030 retains opposed sentiment and zero sentiment points. S-010 retains high
  flood and zero flood points. Fresh official/vendor disagreements are not
  used to inflate capacity.

## Reasonableness and assignment fit

The conservative calculation follows the sponsor weights and tiers, uses Claude's
evidence-backed extraction without putting scoring in the prompt, merges the
duplicate and avoids average imputation. Its provisional top five are
S-003, S-018, S-017, S-027 and S-014; equal-score leaders remain tied. All five
have at least 4 MW official headroom, so the preference for ≥2 MW does not change
this particular shortlist. S-027 still has a visible sentiment condition.

The potential policy is useful for deciding what to investigate. It is deliberately
risky and should not replace the sponsor recommendation. Its top five within the
same current pool are S-007, S-003, S-018, S-027 and S-017. S-007 leads only if the
vendor-derived capacity tier is confirmed. The stale cutoff is a stated policy
based on the latest quarter in this dataset, not proof that March figures are wrong.

S-024's possible 100 consists of 45 official grid/distance points and 55 points
from favourable unknown owner, sentiment, flood and area outcomes. Protection
clearance is also missing. That ceiling is mathematical opportunity under
hypotheses, not positive evidence. S-024 stays held and outside both current-pool
rankings. S-036 has the same issue.

Neither endpoint is a guaranteed physical bound or a statistical confidence
interval. The vendor band is unvalidated; all ordinary usable-area inputs are
parcel proxies; approximate 700 m² has no quantified error range. Checks prove
the report implements the named assumptions on these data, not that those
assumptions will come true.

## Gaps before claiming the scoring slice is complete

1. Put the scenario generator in the repository and connect it to a documented
   command that produces rankings and explanations. The verifier checks the
   current report, not regeneration from a clean checkout.
2. Add regression tests for the actual generator, including all thresholds,
   missing inputs, malformed quantities, source/date alternatives and exclusions.
3. Make the conservative recommendation and conditional upside visibly distinct
   in the final output. The current report contains the potential display order;
   the verifier independently derives both top-five lists.
4. Address the brief's required Git history. The repository currently has no
   commits; questions/assumptions were not committed before the exploratory
   scoring work. A new commit cannot retroactively satisfy that ordering.

This review did not integrate a new scorer, change the scores, publish a page or
create Git history. It added repeatable verification and tightened the sentiment
hypothesis wording.
