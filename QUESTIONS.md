## Questions before building

### 1. Are we screening every site for a 2 MW battery, or should the sponsor rubric be applied independently of the final battery size?
The brief uses 2 MW as the area reference, but the scoring rubric still awards points to sites with less than 2 MW of headroom.

### 2. When the official Gridmap pull fails, is the vendor estimate acceptable as fallback evidence, and can a site with unknown substation distance still reach the shortlist?
Eight sites have Gridmap timeouts, while the available vendor estimates are explicitly unvalidated and carry ±40% uncertainty.

### 3. What evidence-precedence rule should be used when official structured data, newer field notes and vendor estimates disagree?
Some sites contain materially conflicting evidence, such as S-007's 1.6 MW official headroom versus a 5.2 MW vendor estimate, or S-013's 2,400 m² registry area versus a newer note saying only ~700 m² remains.

### 4. For facts that evolve over time, such as landowner status, should the latest dated reliable evidence supersede earlier observations?
S-020 progresses from `not_contacted` to `in_talks` to `refused`, while its notes are not stored in chronological order.

### 5. How should genuinely unknown criteria be handled, particularly when the missing fact could trigger a hard exclusion?
S-024 has strong grid data but no Land Registry record or notes, leaving area, flood risk, protected status, owner status and sentiment unknown.

### 6. Should tracker records that refer to the same parcel be consolidated into a single physical opportunity?
S-017 and S-031 share parcel `SV-2291`, nearly identical locations and the same structured data, but contain different field-note histories.

### 7. Should the Thursday shortlist simply contain the five highest qualifying sites, or should it satisfy any geographic or site-type diversification constraint?
The dataset spans four regions and multiple site types, but the sponsor rubric does not specify whether the final five should be diversified.


## What I think of Jonas's plan

**What's right about it:**
It's pragmatic, simple, and aims for a fast working slice to unblock Maren.

**What worries me:**
- **Filling gaps with dataset averages creates phantom sites:** It fabricates positive evidence for unverified criteria, creating false certainty and risking recommending sites that are fundamentally unviable.
- **Blind trust in vendor estimates:** Vendor numbers are unvalidated trial models with ±40% uncertainty. Swapping them in unconditionally risks our credibility with the sponsor.
- **Unit mismatch:** Nordholm publishes in kW, not MW. Treating all numbers as MW penalizes Nordholm by 1,000x and completely distorts the ranking.
- **Bypassing the kill rule:** A weighted average ignores non-negotiable hard constraints, like legally protected nature areas. A high-scoring site inside a reserve is still unbuildable.
- **Treating duplicates as separate opportunities:** S-017 and S-031 share parcel `SV-2291`. Scoring them separately could waste two of Maren's five shortlist spots on the same physical plot.

*(See `assumptions.md` for the concrete normalization rules and scenarios adopted to resolve these).*

