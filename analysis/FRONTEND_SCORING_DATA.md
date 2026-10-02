# Frontend scoring data

The frontend needs one file: `data/scoring.json`. Generate it offline with:

```bash
uv run python -m field_notes.scoring
```

The command uses the saved extraction, normalized sites and audit, validates that
they still match, and produces scores for all 39 physical opportunities. It makes
no API request. The original files are preserved.

## Questions and answers

These are choices about assumptions, not questions that confirm new facts.
The default answers form the conservative preset; the most optimistic answers
form the potential preset. Users can also combine answers.

| Question | Answers | What changes |
|---|---|---|
| Which grid figures should we use? | Official / include vendor central / explore vendor upper band | Capacity points where official data is missing or older than June 30, 2026 and a newer estimate is available. Keep official evidence if it gives the same or more points. |
| How should we treat unknown or conditional local support? | No extra points / explore confirmed support | Unknown sentiment can earn ten hypothetical points. Support and any condition must be confirmed. Known neutral/opposed positions stay unchanged. |
| Should we explore sites with missing critical checks? | Hold / show conditional upside | Missing capacity, distance, owner, flood, area or protection can be explored under explicit favourable hypotheses. Sites remain conditional. |
| Should we explore sites with unresolved land checks? | Hold / show pending-check scenarios | S-009's legal footprint or S-013's reported remaining land can be explored. Confirmed protection stays excluded; sold land is not restored. |

There are **24 combinations**: 3 × 2 × 2 × 2. Every combination is precomputed.
The file also lists the sites affected by each question. Changing a question may
change a site's score, eligibility group or pending conditions.

When official capacity is missing but a vendor estimate exists, a vendor answer
is required to use it. The missing-checks answer cannot invent 4 MW while ignoring
that estimate. If no capacity source exists, the explicit unsupported ≥4 MW
what-if ceiling is available only through the missing-checks answer.

## File structure

| Key | Purpose |
|---|---|
| `schema_version`, `metadata` | Contract version, counts, units/assumption caveats and source hashes. |
| `rubric` | Sponsor weights, tiers and exact inclusive/exclusive boundaries. |
| `questions` | Stable IDs, wording, answer IDs, defaults, help and affected sites. |
| `presets` | Conservative/potential answers and their profile IDs. |
| `profiles` | Every answer combination and its ordered site IDs by eligibility group. |
| `sites` | Identity, immutable observed inputs, evidence, criterion variants and scores for every profile. |
| `ranking_contract` | Labels, tie handling and separation of conditional cases. |

Each site's `scores[profile_id]` contains:

- `score`: the selected scenario total, or null when held/excluded.
- `status`: eligible, conditional, held or excluded.
- `components`: criterion ID → selected variant ID.
- `score_kind`: complete rubric, partial lower, hypothetical, held or excluded.
- `conditions`: what must be confirmed for assumed points or conditional admission.
- `unresolved_criteria`, `reasons`: missing inputs and reasons for holding/exclusion.
- `rank`: position within eligible or conditional sites; equal scores share a rank.
- `known_subtotal`: the baseline contribution subtotal for context, not a ranked score.

Resolve each component using
`site.criterion_variants[criterion_id][variant_id]`. The variant contains its
value, unit, tier, contribution, evidence basis, evidence and conditions. Null
tier/contribution remains unknown and earns no positive points in the total.

## Frontend selection

1. Load the JSON once and show `questions`, initially using their default answers.
2. Find the profile whose `answers` exactly match the selected answer IDs. The
   frontend need not construct profile IDs or implement scoring rules.
3. Read `profile.rankings.eligible` and resolve each ID against `sites`.
4. Display `site.scores[profile.id]` and its selected components. Use the supplied
   score label and conditions: an optimistic answer never marks a check complete.
5. Show `profile.rankings.conditional` separately as opportunities needing checks.
   Held and excluded lists explain why other sites are absent.

An eligible site can have a hypothetical score when the user explores different
capacity or sentiment assumptions. Its admission is based on the original known
critical inputs; the chosen higher score still requires the supplied checks.
“Eligible” means admitted to screening, not confirmed construction feasibility.
Never combine the conditional ranking with today's recommendation by default.

The conservative preset has 23 eligible, 14 held and two excluded sites. The
potential preset has 23 eligible, 14 conditional and the same two exclusions.
S-017/S-031 remains one physical site in every profile. All 106 observations and
their source notes/quotes are included once per site, independently of user answers.

## Verification

The generation checks raw/extraction consistency and rebuilds normalization
before accepting saved inputs. Both presets match the earlier scenario report
for all 39 opportunities. All 936 site/profile results were checked for correct
totals, group membership, descending order and unchanged exclusions.
Regression tests cover boundaries, invalid inputs, independent questions,
central versus upper vendor tiers, fresh-source precedence, unknowns, land
conflicts, irreversible exclusions, unchanged negative facts and tied ranks.
All 56 offline tests passed. Every ranked mixed-answer score lies within its
conservative/potential preset endpoints where those endpoints exist. Repeating
generation with unchanged inputs produces byte-identical output.
