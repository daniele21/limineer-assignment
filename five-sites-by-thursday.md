# Take-home: "Five sites by Thursday"

*Venture Engineer (Forward Deployed) · Limineer*

Hi,

Thanks for giving this half a day. The situation below is invented, but it's built from a pattern we hit again and again across our ventures. Treat it as your first week on a real one.

**In short:** our venture lead needs 5 sites for community batteries to show a sponsor on Thursday. You get the data our team collected on 40 candidate sites. You (1) write down what you'd want to know before building, and what you'll assume instead; (2) build a small tool that scores and ranks the sites, and shows why; and (3) publish one page she can read on her phone: which sites to bring, how sure we are, and what to check next.

---

## The situation

It's **Tuesday afternoon**. On **Thursday at 9:00**, Maren (our venture lead) meets our first corporate sponsor. She wants to walk in with **five shortlisted sites** and a reason for each.

The venture finds small plots of land where a **community battery** could be built (see the primer below). We're in the validation stage, trying to prove one belief: *good sites can be found from public data plus a bit of legwork, faster than incumbents who do it by hand.* The sponsor is a large energy company that may fund the next step. If they like a site, they pay for a proper feasibility study on it. Picking the wrong site costs the sponsor money and costs us credibility.

Over the summer, our four-person business development team gathered 40 candidate sites. For each one we pulled data from three sources and added their field notes. Everything is in `data/`. The country is fictional (the Republic of Vessmark), and so is everything else in the data.

### New to energy? A 60-second primer

You don't need any energy background for this. This is everything you need:

- **Community battery.** A shipping-container-sized battery (1–5 MW) placed in a neighbourhood. It charges when power is cheap or plentiful (sunny, windy, night) and discharges when it's scarce, which keeps the local grid stable. It needs a small plot of land and a cable to the grid.
- **Substation.** The local node of the electricity grid, where a battery would connect. Every site has a "nearest substation".
- **Grid headroom.** How much spare capacity that substation has for new connections. If headroom is lower than the battery's size, the battery can't connect without expensive upgrades. It's the single most important criterion.
- **Distance to substation.** The cable has to run from the plot to the substation, so further means costlier and slower.
- **MW and kW.** Megawatt and kilowatt, units of power: 1 MW = 1,000 kW.
- **Grid operators.** Each region's grid is run by a regional operator. They publish headroom figures, which a national open-data feed collects.
- **LOI (letter of intent).** A non-binding signed note from the landowner saying they'd lease the plot. "In talks" means they're negotiating ("heads of terms" is the draft deal). "Refused" means they said no.
- **Flood zone.** Official flood-risk category for the plot. Batteries and floods don't mix.
- **Protected nature area.** A legally designated reserve. You can't build there, full stop.

### Who's who

| Person | Role | Reachable before Thursday? |
|---|---|---|
| **You** | Venture engineer, first week on this venture | Yes |
| **Maren** | Venture lead. Owns the sponsor relationship and presents on Thursday. Smart, not technical. | No: in workshops, reads messages Thursday morning |
| **Jonas** | Engineer who set up the data pull. Suggested the plan below. | No: on holiday |
| **Business development team (initials MA, JK, RS, AV)** | Visited sites, talked to owners and councils, wrote the field notes | No: all at the same workshop |
| **The sponsor** | Energy company that may fund feasibility studies on the shortlisted sites | Thursday only |

Maren's message to you, verbatim:

> "Can you give me one score per site, highest first, and the top five? Keep it simple, the sponsor isn't technical. I'm in workshops until Thursday morning, so just use your judgement."

Jonas, one of the other engineers, dropped this in the channel before going on holiday:

> "Easy one. Load sites.json. For each criterion take whatever value the sources have (use the vendor estimate if gridmap is empty). Fill any remaining gaps with the dataset average so every site gets a score. Weighted sum, sort descending, send Maren the top five. Should take an hour."

## The scoring rubric we agreed with the sponsor

| # | Criterion | Weight | Tiers (score 0–5) |
|---|---|---|---|
| C1 | Grid headroom at nearest substation | 30 | ≥ 4 MW → 5 · 2–4 → 3 · 1–2 → 1 · < 1 → 0 |
| C2 | Distance to that substation | 15 | ≤ 1 km → 5 · ≤ 3 → 3 · ≤ 6 → 1 · > 6 → 0 |
| C3 | Landowner status | 20 | LOI signed → 5 · in talks → 3 · not contacted → 1 · refused → 0 |
| C4 | Local council / community sentiment | 10 | supportive → 5 · neutral → 3 · opposed → 0 |
| C5 | Flood zone | 15 | none → 5 · low → 4 · medium → 2 · high → 0 |
| C6 | Usable area (a 2 MW system needs ~1,200 m²) | 10 | ≥ 1,200 m² → 5 · 800–1,200 → 2 · < 800 → 0 |

**Site score** = Σ (weight × tier ÷ 5), which runs from 0 to 100.

**Kill rule:** sites inside a protected nature area are excluded, whatever their score.

`data/DATA_DICTIONARY.md` explains the files and sources.

---

## What we'd like from you

Roughly 3–4 hours in total. Please don't go past 4. We mean it: stopping and telling us what you'd do next is a skill we're hiring for.

### Part 1: Before you build (~30 min)

Read the brief and the data, then create `QUESTIONS.md` in your repo and **commit it (git) before you write any scoring code**. We'll look at the commit order. In it:

- The questions you'd ask Maren (and Jonas, and the business development team) before building this.
- What you think of Jonas's plan: what's right about it, and what worries you.
- Since nobody's reachable until Thursday, the **assumption you're going ahead with** for each open question.

Nobody will answer these questions; that's the point. We want to see what you'd want to know, and how you move forward without it. Keep it short: ten sharp questions beat forty generic ones.

### Part 2: A working slice, with Claude in the loop (~2 h)

Something we can run with one command, in any language you like. It should:

- load the data and produce a ranked result Maren could use on Thursday;
- make it possible to see **why** any site scored the way it did;
- **use Claude to read the field notes.** The business development team's notes are free text, and some of what the rubric needs only lives there. Call the Anthropic API from your script to turn each site's notes into structured signals: at least owner status, community sentiment, and anything in the notes that should change how the site is scored.

A few rules for the Claude step, because this is how we build with LLMs:

- **Every extracted signal must carry the exact quote it came from.** If the notes don't say, the answer is "unknown". Don't let the model guess.
- **Check it.** Show us how you know the extraction is right. Hand-checking a sample of sites against the model's output and reporting what you found is plenty.
- **Claude reads the notes; your code decides the scores.** Keep the rubric in your code, not in a prompt.
- Keep your prompt(s) in the repo. Use any current Claude model; `claude-opus-5` is a good default.

You don't need an agent framework. One well-designed call per site (or per batch) is enough, and choosing the simplest thing that works is part of the test.

Add a short `README.md` explaining how to run it and what decisions you made.

### Part 3: The page Maren opens on Thursday (~1 h)

Maren will open one link on her phone on Thursday morning, just before she walks in. Build that page:

- **One page, publicly viewable, at a URL we can open.** Vercel, Netlify, GitHub Pages, Cloudflare Pages or anything else free is fine. A static page generated from your script's output is perfectly good. No login, no backend needed.
- It carries your **recommendation for Thursday**: what you'd put in front of the sponsor, what you're confident about, what you aren't, and what you'd do next.
- It lets Maren (or us) **see why** each shortlisted site is there, and why the obvious-looking ones aren't.
- It works on a phone.

Also put the written part in `NOTE.md` (one page at most), so we can read it without the page. Maren is smart, not technical and busy, so write for her, not for us.

This isn't a design test, and one clean page beats a dashboard. We care whether the page helps Maren make a good call in the five minutes she has.

---

## Your Anthropic API key

We'll email you a personal API key for this task, with a small spending cap. It stops working a week after we send it, and you won't come close to the cap. Please:

- keep it out of your repo (use an environment variable, e.g. `ANTHROPIC_API_KEY`);
- **never put it in the page.** Call Claude from your script and publish static output. Your public page must not talk to the API.

If you hit a problem with the key, tell us. It won't count against you.

## On AI tools

Use them. We do, every day. We only ask that you:

1. **Include your AI conversation(s)**, exported unedited, in `ai-transcripts/`. Any format works: a share link or export from Claude or ChatGPT, a Cursor or Claude Code session export, or a plain copy-paste into a `.md` file. We're not grading your prompts' style. We want to see how you work: what context you gave, where you pushed back, and when you decided something was good enough.
2. Add `AI_LOG.md` with 3–5 bullets on moments where you **disagreed with or corrected** the AI, and why. For example: *"It proposed a SQLite database; I kept a single JSON-in, HTML-out script because 40 records don't need one and Maren's page must be generated from the same code."*

If you didn't use AI, say so. That's fine too.

## What we don't care about

Production polish, full test coverage, a polished UI, CI/CD, or reproducing the rubric in a fancy framework. We'd rather see a small thing you trust than a big thing you don't.

## Submitting

**The public URL of your page**, plus a git repo (zip or private link) containing `QUESTIONS.md`, your code, your Claude prompt(s), the extraction check and `README.md`, `NOTE.md`, `AI_LOG.md`, `ai-transcripts/`, and a line in the README with roughly how long you spent. Please keep the page up for two weeks after you submit. Please keep your commit history; we look at it.

We'll follow up with a 30-minute call. For part of it, one of us will play Maren on Thursday morning with your page open on her phone, and someone else will play the sponsor. Then we'll step out of role and talk it through as engineers. Expect us to ask "why?" a lot, which says nothing about whether we liked your answer.

If something in this brief is unclear, that's probably on purpose. Decide, write down what you decided, and move on.

Good luck, and have fun with it.

— The Limineer venture team


---

# Appendix: Data dictionary

All data is synthetic. Two files:

- `sites.json`: 40 candidate sites, exported from our site tracker on 2026-09-21.
- `fetch_log.csv`: the log from the job that pulled the source data into the tracker.

## `sites.json`

Each site has:

| Field | Meaning |
|---|---|
| `site_id` | Tracker ID (`S-001`…). Created by whoever first logged the site. |
| `name` | Human name as entered by the business development team. |
| `region` | One of Aldmark, Nordholm, Sveld, Tarrow. |
| `site_type` | brownfield, depot_yard, municipal_land, farm_edge. |
| `grid_ref_km` | Position on the national km grid (x east, y north). |
| `parcel_id` | Land registry parcel identifier. |
| `sources` | Data from the three sources below. A source is `null` if it returned nothing. |
| `field_notes` | Free-text notes from the business development team (see below). |

### Source: `gridmap` (national grid open-data feed)

| Field | Meaning |
|---|---|
| `headroom` | Available connection capacity at the nearest substation. |
| `substation_distance_km` | Straight-line distance to that substation. |
| `data_as_of` | When the grid operator last updated the figure (published quarterly). |
| `fetched_at` | When our job pulled it. |

The national feed aggregates the regional distribution operators' publications. It's the official figure and the one the sponsor will trust.

### Source: `landreg` (land registry)

| Field | Meaning |
|---|---|
| `area_m2` | Parcel area. |
| `flood_zone` | none / low / medium / high. |
| `protected_area` | Whether the parcel is inside a designated nature area. |
| `owner_type` | municipal / private. |
| `record_date` | When the registry record was last updated. Some records are old. |

### Source: `vendor_estimate` (third-party data vendor, trial licence)

| Field | Meaning |
|---|---|
| `headroom_mw_est` | The vendor's modelled headroom estimate, in MW. |
| `band_pct` | The vendor's stated uncertainty (± %). |
| `estimated_at` | When the estimate was produced. |

This is a machine-learning estimate from load profiles, not an official figure. It's available for only some sites. We're on a trial and haven't validated it.

### `field_notes`

A list of notes from the business development team. Each note has a `date`, `author` initials and `text`. Some also have a structured `owner_status` (`loi_signed`, `in_talks`, `not_contacted`, `refused`). Community sentiment is only ever in the free text. Notes were appended by hand, sometimes from memory, sometimes later.

## `fetch_log.csv`

One row per source per site: `timestamp, site_id, source, http_status, message`.

## Known quirks

- Headroom figures come through as the regional operators publish them. Aldmark, Sveld and Tarrow publish in MW. Nordholm publishes in kW, and the national feed doesn't convert.
- The land registry doesn't have every parcel.
