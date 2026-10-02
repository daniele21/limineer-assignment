# Evidence-backed site shortlist

A mobile-friendly shortlist for Maren, backed by a Python pipeline that extracts
field-note evidence, reconciles sources and applies the sponsor's scoring rubric.

Open [index.html](index.html) in a browser to use the delivered page. It works
offline and needs no installation or credentials. Read [NOTE.md](NOTE.md) for the
recommendation and [QUESTIONS.md](QUESTIONS.md) for the questions raised before building.

## How to run

Run commands from the repository root. The pipeline requires **Python 3.11+** and
**uv**. Only extraction calls the Anthropic API; normalization, scoring and page
building run offline.

### Set up and check

```bash
uv sync
uv run python -m unittest discover -s tests -v
uv run python main.py --config config.toml --dry-run
```

Preflight validates inputs and reports expected requests without calling the API
or writing extraction output. The supplied dataset has 40 records, 70 notes and
39 expected requests before retries. Empty notes need no request.

### Regenerate the data

Set `ANTHROPIC_API_KEY` in the environment or `.env` beside the config; use
[.env.example](.env.example) as the format. Environment credentials take precedence.
Check that the model in `config.toml` is available to your account; preflight
cannot verify authentication or model access.

```bash
# Check one artificial site with a real API request.
uv run python main.py --config config.sample.toml --dry-run
uv run python scripts/test_live_sample.py --config config.sample.toml

# After reviewing output/artificial_sample_check.json, extract the full dataset.
uv run python main.py --config config.toml

# Review extraction accuracy and validation issues, then generate scores.
uv run python -m field_notes.normalize
uv run python -m field_notes.scoring
```

The sample and full extraction make paid API requests. `output/` is gitignored,
so a fresh checkout needs a new extraction or a separately supplied matching
`output/extractions.json`. Normalization produces `data/sites.normalized.json`
and `output/normalization_review.json`; scoring needs both and writes
`data/scoring.json`. Run these steps in order when inputs change. Stale extraction
or normalization is rejected. Offline results are deterministic for unchanged
inputs; live extraction may vary.

### Build and verify the page

```bash
uv run python scripts/build_maren_page.py

# Optional: requires Node.js, Playwright and installed Google Chrome.
node scripts/verify_maren_ui.cjs /path/to/playwright
```

After a UI-only edit, run the build directly: it needs `web/` and the delivered
`data/scoring.json`, with no API key or extraction files. The browser check covers
all 24 answer profiles, ties, admission rules, reset, evidence, tab persistence
and layouts from 320 to 1280 px.

### Configure a run

Edit [config.toml](config.toml) for the full dataset or
[config.sample.toml](config.sample.toml) for the artificial sample.

| Section | Controls |
|---|---|
| `[model]` | Model name and optional version |
| `[prompt]` | Prompt labels and system/user files |
| `[input]` | Sites file and site IDs; an empty list selects all |
| `[output]` | Extraction output path |
| `[api]` | Token limit, timeout and retries |

Paths resolve relative to the config file. Use a complete API model ID without
`version`, or a base name with a numeric version. Invalid settings fail before
requests. Keep credentials in the environment or `.env`, outside TOML.

## Decisions, from high level to implementation

1. **Goal:** recommend five physical opportunities for further checks. Follow the
   sponsor's rubric, without adding a regional quota or a 2 MW minimum. Favor
   evidence we can defend; a high score cannot clear an exclusion or a critical gap.
   [assumptions.md](assumptions.md) records the adopted policy.

2. **Architecture:** `raw data → extraction → normalization → scoring JSON → page`.
   Claude converts notes into typed observations. Python validates evidence,
   reconciles sources and computes rankings. JavaScript selects precomputed results.
   This keeps scoring auditable and lets the delivered page run without a backend.

3. **Evidence:** use official grid figures for the conservative case, convert
   Nordholm kW to MW, and use the latest dated explicit owner status. Merge duplicate
   parcels while retaining their notes. Registry area is a disclosed usable-area
   proxy. Missing facts stay unknown. Exclude confirmed protection and owner refusal;
   hold critical gaps and land conflicts. Unknown sentiment earns no positive points
   but can remain eligible with a partial lower-bound score. Source conflicts and
   site-level resolutions are in
   [NORMALIZATION_REVIEW.md](analysis/NORMALIZATION_REVIEW.md).

4. **Scoring:** sum `weight × tier / 5` across grid headroom (30), substation
   distance (15), owner status (20), sentiment (10), flood risk (15) and area (10).
   Scores are out of 100. Sort descending; ties share ranks (1, 1, 3), with site ID
   determining display order. Four assumption questions produce 24 profiles for
   39 physical opportunities. The conservative profile has 23 eligible, 14 held
   and two excluded sites. Conditional sites stay outside the current five.
   Vendor estimates and favorable outcomes are explicit what-if assumptions.
   See [SCENARIO_ASSUMPTIONS.md](analysis/SCENARIO_ASSUMPTIONS.md) and the
   [data contract](analysis/FRONTEND_SCORING_DATA.md); exact tiers are in
   [scoring.py](src/field_notes/scoring.py).

5. **Interface:** show priority and next action first, then reveal reasons, scores
   and dated evidence. High ≥80, Medium 60–79 and Low <60 summarize fit; they do
   not express confidence or construction readiness. Answers change the selected
   profile; scenario comparison only explains differences. Answers persist in the
   current tab through `sessionStorage`, with a reset control. The rationale is in
   [MAREN_DESIGN.md](analysis/MAREN_DESIGN.md).

6. **Implementation:** keep config, versioned prompts and scoring rules separate.
   Typed schemas, stable note IDs and exact quotes validate provenance; hashes
   record inputs and detect stale artifacts. Quote matching cannot prove semantic
   accuracy, so review the sample before using extracted facts. The build embeds
   data, CSS and JavaScript in one HTML file and escapes `<` in embedded JSON.

## Deploy

Firebase Hosting is configured for `limineer-assignment`. Install the Firebase CLI,
sign in with `firebase login`, then run:

```bash
# Prepare the upload locally.
python3 scripts/prepare_hosting.py

# Publish with an account that has project access.
firebase deploy --only hosting --project limineer-assignment
```

Deployment also runs preparation automatically. It rebuilds and stages only
`index.html` in `dist/`. The page includes source evidence, which becomes public;
project sources, run configuration and API credentials are excluded.
The Hosting URL is [limineer-assignment.web.app](https://limineer-assignment.web.app).

## Where to look

| Location | Purpose |
|---|---|
| `main.py`, `src/field_notes/` | Extraction CLI, validation, normalization and scoring |
| `prompts/field_notes/v1/` | Versioned system prompt and user template |
| `data/` | Raw inputs, source fetch log and generated scoring data |
| `output/` | Extraction and review artifacts; gitignored |
| `web/`, `scripts/build_maren_page.py` | UI sources and single-file page builder |
| `tests/`, `scripts/verify_maren_ui.cjs` | Offline regressions and browser checks |
| `analysis/` | Detailed decisions, data contracts and recorded verification |

[EXTRACTION_TESTS.md](analysis/EXTRACTION_TESTS.md) records extraction verification.
The historical scenario check, `uv run python scripts/verify_scenarios.py`, requires
`output/scenario_review.json`; it is optional and does not generate the frontend data.

## Time spent

Roughly 2 hours of focused work (~3–3.5 hours total elapsed time).

