# Scoring-input review — 2026-10-02

The final extraction file contains 40 site results, 70 notes, 18 distinct note
texts, 106 observations and zero validation issues. The normalization step
revalidates every quote against the original note, checks source-note identities
and checks the extraction input hash. The outputs are separate from the originals.

| Outcome | Count |
|---|---:|
| Raw tracker records | 40 |
| Physical opportunities after merging | 39 |
| Admitted to scoring | 23 |
| Held pending verification | 14 |
| Excluded from this candidate pool | 2 |
| Retained sites with six known scoring inputs | 14 |
| Retained sites with unknown/conditional sentiment | 9 |
| Extracted observations preserved across both outputs | 106 |

## Decisions applied before scoring

1. Convert all eight Nordholm official headroom values from kW to MW. Vendor
   estimates are already MW. Do not convert them again. Explicit quantity units
   in observations are also normalized, while preserving the original quantity.
2. Use official Gridmap headroom and distance. Keep vendor estimates and their
   uncertainty as context. For this precision-first pool, vendor fallback cannot
   replace missing official evidence; every timeout site also lacks distance.
   This applies the conservative grid rule in `assumptions.md` for candidate admission.
3. Merge S-017 and S-031 into canonical S-017. They share parcel SV-2291, region,
   site type and identical structured sources; coordinates differ by about 36 m.
   Preserve both names, coordinates and all note/observation references. Use the
   September 8 LOI from S-031 and July 2 neutral neighbour evidence from S-017.
   Do not sum their areas or headroom.
4. Select the latest dated explicit owner state, including structured note status
   as separately attributed evidence. A structured field is not a Claude quote.
   Same-date conflicts remain unknown. S-020's September refusal supersedes its
   July negotiations despite the array order. Refusal is an operational exclusion
   from this candidate pool; the sponsor rubric itself only gives refusal zero.
5. Preserve sentiment actors and scopes. An energy co-op's backing is community
   evidence; a ward councillor speaks for that councillor, not the full council.
   Conditional officer comments stay unknown. Owner enthusiasm never becomes
   community support. Opposition remains a scoring input and a flag.
6. Check protection before admission. S-033 triggers the sponsor kill rule.
   S-009's qualified reserve-overlap report conflicts with its 2018 registry
   record, so hold it rather than assert confirmed protection or clearance.
   Missing registry protection information also holds a site. Omit
   `protected_area` from the scoring inputs and normalized registry fields, while
   retaining the check and raw evidence in the audit.
7. Use registry parcel area as an explicit usable-area proxy for ordinary sites.
   S-013's newer sale and approximate 700 m² remaining plot invalidate the old
   2,400 m² proxy. Preserve both facts and hold the site; 700 m² is not promoted
   to measured usable installation area. Missing area/flood evidence also holds.
8. Keep unknowns as null. Do not add a 2 MW hard minimum, a flood exclusion or a
   sentiment exclusion beyond the agreed rubric. Small headroom, opposition and
   high flood risk remain visible for scoring and later recommendation judgment.

## Opportunities absent from the scoring input

| Site(s) | Outcome | Reason |
|---|---|---|
| S-004, S-011, S-015, S-022, S-026, S-029, S-035, S-038 | Held | Gridmap timeout; official headroom and substation distance unknown. Vendor context cannot establish grid viability. |
| S-008, S-019 | Held | Successful search found no substation within 10 km; distance is strictly greater than 10 km, not a fabricated exact 10 km. Official headroom unknown. |
| S-009 | Held | Unresolved reserve-overlap concern versus stale registry. |
| S-013 | Held | Plot sale and approximate remaining-area evidence contradict the registry proxy. |
| S-024, S-036 | Held | Protection, flood, area and owner state unknown. |
| S-020 | Excluded | Latest owner state is refused. |
| S-033 | Excluded | Confirmed protected nature area in the registry. |
| S-031 | Merged | Evidence retained under S-017; it is not a second physical site. |

S-007 and S-021 retain their March 31 official headroom despite newer vendor
disagreement, with explicit freshness/conflict flags. An unvalidated vendor
estimate does not override the authoritative source. Reconfirm official capacity
before a feasibility commitment.

S-005, S-010, S-012, S-016, S-021, S-023, S-027, S-032 and S-039 remain admitted
with null sentiment. S-010/S-016/S-021/S-027 are explicitly conditional. A later
scoring algorithm can assign an unknown criterion zero contribution to produce a
labelled lower bound; it must not call that neutral sentiment, opposition, or a
complete score. The strongest evidence pool comprises the 14 complete records.

## Extraction review and verification

The agent compared all 18 distinct note wordings with their extracted owner and
sentiment classifications and inspected the critical S-003/S-009/S-013/S-020 and
Brekke cases. No scoring-relevant classification error was identified. This is an
agent-assisted semantic review, not an independent human sign-off. Optional
follow-up extraction varies across identical note wordings; all emitted facts
remain preserved. Some follow-up wording (for example, describing a noise report
as "required") is stronger than the conditional source quote, so follow-ups are
context for review rather than automatic feasibility constraints. The source
quotes and qualifiers remain available to check that interpretation.

S-003 retains the requested 12% revenue share as a commercial observation with
percent units, separately from its LOI and council support. It creates no invented
rubric penalty. Historic follow-up observations, such as sending heads of terms
before Brekke's later LOI, are retained as history rather than current obligations.

All 42 offline tests passed (31 existing, 11 new normalization regressions).
The new checks cover official precedence and unit safety, duplicate evidence
merging, latest owner state, same-day conflicts, conditional/absent sentiment,
protected/unknown protection distinctions, timeout versus negative search,
critical note conflicts, source immutability, provenance failure and safe output
paths. No additional API request was made. Input hashes and output counts are
recorded in both JSON files. Unchanged input files reproduce identical output.

The next scoring step should read `data/sites.normalized.json["sites"]` and its
`scoring_inputs`, preserving completeness and source caveats. The full audit is
`output/normalization_review.json`; it contains all 39 opportunities and the raw
source records needed to explain why attractive-looking sites were held out.
