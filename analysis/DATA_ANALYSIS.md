# Data Analysis — Five Sites by Thursday

## Purpose

This document summarizes a data audit of the 40 candidate sites provided for the "Five Sites by Thursday" assignment.

The goal is not to rank sites yet, but to understand what the data actually support, where they are incomplete or conflicting, and which records require special treatment before scoring.

---

## 1. Dataset overview

The dataset contains **40 candidate site records** exported on **2026-09-21**.

Each record contains:

- site identity and location;
- official Gridmap data;
- Land Registry data;
- optional vendor headroom estimates;
- business-development field notes.

A separate `fetch_log.csv` records the outcome of source pulls.

### Regional distribution

- Aldmark: 11
- Sveld: 12
- Tarrow: 9
- Nordholm: 8

### Site-type distribution

- depot_yard: 14
- municipal_land: 14
- brownfield: 8
- farm_edge: 4

The data are mostly structured and usable, but a small number of records contain issues that can materially change the shortlist.

---

## 2. Gridmap coverage

Gridmap is the official source for grid headroom and distance to the nearest substation.

Out of 40 sites:

- **30** have numeric official Gridmap values;
- **8** have missing values because of an upstream `503` timeout;
- **2** have missing numeric values because Gridmap successfully returned `no substation within search radius (10 km)`.

This distinction is important.

A technical failure means:

> official data are unknown.

A successful response with no nearby substation means:

> the site is known to be more than 10 km from a substation.

Those two situations should not be treated as equivalent missing values.

### Sites with Gridmap timeout

- S-004
- S-011
- S-015
- S-022
- S-026
- S-029
- S-035
- S-038

### Sites with no substation within 10 km

- S-008
- S-019

For S-008 and S-019, the missing distance is actually informative: the site is beyond the worst distance threshold in the sponsor rubric.

---

## 3. Nordholm unit inconsistency

Grid headroom is not expressed consistently across regions.

The data dictionary states:

- Aldmark, Sveld and Tarrow publish headroom in MW;
- Nordholm publishes it in kW;
- the national feed does not convert it.

Therefore all 8 Nordholm records require normalization before scoring.

Examples:

- `2200` means **2.2 MW**
- `4600` means **4.6 MW**
- `950` means **0.95 MW**

This is deterministic data cleaning and should happen before any scoring logic.

Without this conversion, Nordholm sites would be incorrectly treated as having extremely large grid capacity.

---

## 4. Vendor estimates

Vendor headroom estimates are available for **18 of 40 sites**.

Every estimate carries a stated uncertainty of **±40%**.

The vendor source is explicitly described as modelled rather than official, unvalidated, and only available for some sites.

Among the 10 sites where both official and vendor estimates are available, several fall into different sponsor scoring tiers depending on which source is used.

| Site | Official | Vendor |
|---|---:|---:|
| S-005 | 2.6 MW | 1.8 MW |
| S-007 | 1.6 MW | 5.2 MW |
| S-016 | 3.5 MW | 4.1 MW |
| S-021 | 2.4 MW | 4.9 MW |
| S-025 | 2.0 MW | 1.7 MW |
| S-032 | 4.5 MW | 2.1 MW |

This means vendor fallback is not a neutral technical choice: it can materially change the ranking.

---

## 5. Grid-data freshness

Most successful official Gridmap observations are dated `2026-06-30`.

Two important exceptions use older official data from `2026-03-31`:

- S-007
- S-021

Both also have much newer September vendor estimates that disagree materially with the official values.

This creates a genuine source-precedence question: should older official evidence still take priority over newer but unvalidated evidence?

The dataset itself does not resolve that policy decision.

---

## 6. Land Registry coverage

Land Registry data are available for **38 of 40 sites**.

Missing records:

- S-024
- S-036

This is especially important because Land Registry provides:

- area;
- flood zone;
- protected-area status;
- owner type.

Therefore a missing Land Registry record removes several scoring inputs at once, including the protected-area kill rule.

### S-024 is particularly important

Known:

- 5.0 MW official headroom;
- 0.6 km from substation.

Unknown:

- area;
- flood risk;
- protected-area status;
- owner status;
- community sentiment.

A naive average-imputation approach could make this site appear very attractive despite most of the relevant evidence being missing.

---

## 7. Land Registry freshness and stale records

Most registry records are relatively recent, but there are two very old outliers.

### S-009

Registry record date: `2018-04-20`.

Structured field: `protected_area = false`.

A 2026 field note says that the northern third of the plot may now fall inside a reserve designated in 2024.

This creates a direct conflict with the protected-area kill rule.

### S-013

Registry record date: `2017-02-11`.

Structured area: 2,400 m².

A 2026 field note says roughly 700 m² remains after part of the plot was sold.

Under the sponsor rubric:

- 2,400 m² receives the maximum area score;
- 700 m² receives zero.

This means newer free-text evidence can materially change a structured scoring input.

---

## 8. Parcel area vs usable area

The sponsor rubric refers to **usable area**.

The Land Registry provides **parcel area**.

These are not necessarily the same thing.

S-013 proves that the parcel can be larger than the area actually available for the project.

A reasonable default is therefore to use parcel area as the best available proxy unless newer evidence explicitly indicates otherwise.

This should remain an explicit assumption rather than a hidden transformation.

---

## 9. Field-note coverage

Field notes are present for almost every site.

Approximate distribution:

- 1 site with no notes;
- 11 sites with one note;
- 26 sites with two notes;
- 1 site with three notes;
- 1 site with four notes.

The notes contain three different kinds of useful information:

1. scoring inputs, such as owner status;
2. sentiment evidence;
3. facts that may override structured data or create material risks.

This means the Claude step should not be limited to sentiment extraction.

---

## 10. Owner-status coverage

Taking the most recent dated explicit owner status, the data are approximately:

- in talks: 22
- LOI signed: 12
- not contacted: 3
- refused: 1
- unknown: 2

Owner status is therefore relatively well covered.

The main issue is not missingness, but temporal evolution.

---

## 11. Temporal state: S-020

S-020 contains several owner-status notes:

- June: `not_contacted`
- July: `in_talks`
- September: `refused`

The array itself is not stored in chronological order.

Therefore:

- taking the first value would be wrong;
- taking the last array item would be wrong;
- taking the most positive status would be wrong.

The correct representation is a state transition:

`not_contacted → in_talks → refused`

For stateful facts, the latest dated explicit evidence should be considered the current state.

---

## 12. Community and council sentiment

Sentiment is available only in free text.

A conservative manual review gives approximately:

- supportive: 17
- neutral: 9
- opposed: 2
- unknown: 12

This is the least complete normal scoring criterion.

The key distinction is:

### Neutral

There is evidence indicating neither support nor opposition.

### Unknown

There is no sufficient evidence.

Unknown should not silently become neutral.

---

## 13. Explicit opposition

Two sites contain clear negative sentiment.

### S-030

A residents' association has started a petition against industrial batteries near a school.

### S-040

A councillor raised fire-safety objections and the note says to expect resistance.

These are strong examples where Claude should be able to extract a clear `opposed` signal with exact supporting quotes.

---

## 14. Protected-area kill rule

S-033 is explicitly marked `protected_area = true`.

It otherwise looks technically attractive:

- 4.8 MW headroom;
- 0.6 km distance;
- 2,500 m²;
- no flood risk.

But the sponsor rule is explicit: protected sites are excluded regardless of score.

Therefore S-033 should never enter the shortlist.

This is a useful example of why the final page should explain not only why selected sites are included, but also why apparently attractive sites were excluded.

---

## 15. Likely duplicate: S-017 and S-031

S-017 `Brekke Depot` and S-031 `Brekke Municipal Depot` appear to refer to the same physical opportunity.

They share:

- parcel ID `SV-2291`;
- the same region;
- the same site type;
- the same headroom;
- the same distance;
- the same area;
- the same flood status;
- the same protected status;
- almost identical coordinates.

Their main difference is the note history.

S-017 records the owner as being in talks.

S-031 later records that the owner signed the LOI.

This strongly suggests duplicate tracker records for the same parcel.

If left unresolved, the same physical site could appear twice in the ranking.

The underlying business entity is therefore probably closer to the parcel than to the tracker `site_id`.

---

## 16. Combining duplicate evidence

If S-017 and S-031 are treated as the same opportunity, their evidence becomes more complete.

Combined evidence includes:

- official grid data;
- no flood risk;
- sufficient area;
- latest owner status: LOI signed;
- neutral community evidence.

This is a useful example of why entity resolution should happen before scoring.

---

## 17. Flood-risk distribution

Among the 38 sites with Land Registry data:

- none: 17
- low: 15
- medium: 3
- high: 3
- missing: 2

Flood risk is therefore mostly complete.

The main issue is not missingness, but the large scoring impact for high-risk sites.

---

## 18. Area distribution

Using raw Land Registry values:

- 32 sites have at least 1,200 m²;
- 6 sites fall between 800 and 1,200 m²;
- 2 sites are missing registry area.

Area therefore does not strongly differentiate most candidates.

The important exception is where recent notes contradict the registry, especially S-013.

---

## 19. Non-scoring but material information

Some field notes contain business-relevant information that does not belong to any sponsor scoring criterion.

Example: S-003 has a signed LOI, but the owner wants a 12% revenue share.

The LOI affects the sponsor score.

The commercial term does not.

It should not be converted into an invented penalty, but it should probably remain visible as a commercial follow-up item.

This suggests separating LLM output into:

- scoring signals;
- scoring overrides;
- material non-scoring flags;
- supporting quotes.

---

## 20. Rubric boundary ambiguity

The scoring rubric contains overlapping threshold wording.

### Headroom

- ≥4 MW → 5
- 2–4 MW → 3
- 1–2 MW → 1

A value of exactly 2.0 MW appears in both written ranges.

S-025 has exactly 2.0 MW.

The natural implementation is likely:

- `>= 4` → 5
- `>= 2` → 3
- `>= 1` → 1
- otherwise → 0

The same type of overlap appears at 1,200 m² in the area rule.

This should be resolved explicitly in code rather than left accidental.

---

## 21. Score is not the same as feasibility

The brief says:

- batteries range from 1–5 MW;
- insufficient headroom prevents connection without upgrades;
- 2 MW is used as the reference system size for area.

However, the sponsor rubric still gives some positive headroom score to sites below 2 MW.

Therefore the 0–100 score should be treated as a **sponsor-agreed screening score**, not as a probability of technical feasibility.

That distinction should remain clear in the final recommendation.

---

## 22. Data-quality categories

The observed issues can be grouped into four useful categories.

### A. Deterministic cleaning

Can be resolved without stakeholder judgment.

Examples:

- Nordholm kW → MW;
- date parsing;
- chronological ordering;
- distinguishing timeout from successful no-result.

### B. Entity resolution

Concerns what the record represents.

Example:

- S-017 and S-031 likely refer to the same parcel.

### C. Evidence reconciliation

Multiple observations describe the same underlying fact.

Examples:

- official vs vendor headroom;
- registry vs newer field note;
- several owner-status observations over time.

### D. Genuine unknowns

The evidence simply does not contain the answer.

Examples:

- unknown sentiment;
- Gridmap distance after timeout;
- missing protected/flood/area data for S-024 and S-036.

These should remain visible as unknowns rather than being imputed into false certainty.

---

## 23. Why average imputation is risky

Missing values arise for very different reasons:

1. technical failure;
2. successful negative result;
3. no evidence collected;
4. source record not found.

Replacing all of these with the dataset average removes meaningful information about the underlying uncertainty.

In a precision-first shortlist, this is especially risky because it can promote weakly evidenced sites over well-supported ones.

---

## 24. Sites requiring special attention

| Site(s) | Main issue |
|---|---|
| S-002, S-006, S-012, S-018, S-023, S-030, S-034, S-039 | Nordholm headroom requires kW → MW conversion |
| S-004, S-011, S-015, S-022, S-026, S-029, S-035, S-038 | Official Gridmap timeout |
| S-008, S-019 | No substation within 10 km |
| S-007, S-021 | Stale official headroom conflicts with newer vendor estimate |
| S-009 | Possible protected-area conflict with stale registry |
| S-013 | Usable area conflicts with stale registry |
| S-017, S-031 | Likely duplicate physical site |
| S-020 | Owner status evolves to refused |
| S-024 | Strong grid evidence but most other criteria unknown |
| S-036 | Good grid evidence but no registry and owner unknown |
| S-033 | Explicit protected-area exclusion |
| S-030, S-040 | Explicit opposition |
| S-003 | Material commercial flag outside the rubric |

---

## 25. Main conclusion

The dataset is not broadly low quality. Most records are straightforward.

The real challenge is concentrated in a relatively small number of cases where:

- units are inconsistent;
- missing values mean different things;
- sources disagree;
- structured records are stale;
- field notes materially change structured facts;
- duplicate tracker rows may represent the same physical opportunity.

The safest approach is therefore not to build a large data-quality framework, but to use a small and explicit evidence pipeline:

1. normalize known issues;
2. resolve duplicate entities;
3. preserve source provenance;
4. apply clear source-precedence rules;
5. keep genuine unknowns as unknowns;
6. avoid allowing uncertainty to create positive evidence;
7. score only after the evidence layer is coherent.

For the Thursday shortlist, the dataset supports a precision-first approach: prefer sites with strong, consistent and authoritative evidence rather than promoting sites that might be attractive only after imputation or optimistic interpretation.
