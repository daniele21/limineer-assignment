# Field-note enrichment

The field notes add information that the structured sources miss: whether the owner is willing, how local people feel, and whether something has changed on the plot.

We reviewed all **70 notes across 40 sites**. The aim is to turn those notes into facts we can use and check before scoring.

## What we should extract

| Information | Example from the notes | How we use it |
|---|---|---|
| **Owner status** | Signed LOI, negotiating, not contacted, or refused | Direct input to the owner-status score. Keep the history and use the latest dated explicit status. |
| **Council and community sentiment** | Council support, indifferent neighbours, a residents' petition | Direct input to the sentiment score. Record who expressed the position. |
| **Changes to available land** | S-013: roughly 700 m² remains after part of the plot was sold | Flag a conflict with the registry area before using it for scoring. |
| **Protected-area concerns** | S-009: an ecologist reports that the northern third overlaps a reserve | Flag a possible exclusion and request verification. |
| **Commercial terms and next checks** | S-003: owner wants 12% revenue share; other sites need a noise report | Explain what needs checking next. These do not add new scoring penalties. |

The current notes contain no headroom figures, substation distances, or official flood categories. Those inputs still need to come from the structured sources.

## The distinctions that matter

**Owner interest and community support are separate.** A keen owner does not prove local support. In S-020, the energy co-op supports the project, but the owner later refuses to lease.

**Record who is speaking.** One councillor's support is different from council committee support. A co-op writing to the council tells us the co-op's position, not the council's.

**Conditional is different from neutral.** “Neighbours were indifferent” is neutral. “Depends on the noise report” is conditional. The notes contain 17 supportive cases, 5 neutral, 4 conditional, 2 opposed, and 12 with no sentiment evidence. The earlier data analysis grouped the conditional cases with neutral; we should keep them separate during extraction. My proposed scoring assumption is to leave conditional sentiment unknown until clarified.

**An estimate or concern needs its qualifier.** S-013's “roughly 700 m²” is approximate remaining land, not confirmed usable installation area. S-009's reserve overlap “needs checking”; it is a reported concern, not verified legal status. Under our existing assumptions, these critical conflicts hold the sites out of the recommendation until verified.

**Silence means unknown.** “Yard looks big” does not give us an area. No mention of protection does not mean unprotected. S-024 has no notes, so there is nothing to extract.

## What each extracted fact needs

Keep the value, the exact supporting quote, the note reference and date, who the statement concerns, and any uncertainty or condition. For numbers, also keep the unit and whether the value is approximate.

Claude should extract all relevant observations. Code should resolve dates, compare sources, and apply the rubric. Combine evidence for the shared S-017/S-031 parcel so it is scored once, with its later LOI and earlier neighbour sentiment both retained.

## How we check it

There are only **18 distinct note texts**, so we can check every wording against Claude's output. Pay particular attention to S-020's changing owner status, S-009's protection concern, S-013's area change, and the shared S-017/S-031 parcel. Check both that every fact has a matching quote and that important facts were not missed.

The [draft extraction prompt](../prompts/extract_field_notes.md) contains the detailed output format. It has not been run through Claude yet.
