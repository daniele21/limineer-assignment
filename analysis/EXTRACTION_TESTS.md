# Extraction verification — 2026-10-02

## Offline checks: passed

Command: `uv run python -m unittest discover -s tests -v`.

All **31 tests passed**. Coverage includes typed configuration and relative paths,
invalid config fields and API limits, missing credentials, prompt placeholders,
duplicate/unknown site IDs, complete note validation before paid calls, preventing
input overwrite, and a dry-run that creates no API client or output directory.

Extraction checks cover exact quotes, fabricated quotes, invalid note IDs,
quantity validation, owner/community attribution, qualified claims, incomplete
responses and opportunity identity. One test runs the actual Anthropic SDK against
an offline HTTP transport to verify request JSON-schema serialization and typed
response parsing. The response is a fixture: this proves integration wiring,
not Claude's accuracy. A regression verifies that an unmeasured usable-area claim
is rejected as numeric available area, while the explicit 700 m² remaining area
and a separate measurement-status site condition are retained. Checker tests also
verify that rejection details appear in the failed evidence check.

## Local preflight: passed

Both configs were checked with `main.py --config <file> --dry-run`.

- `config.toml`: all assignment sites and notes validate before processing.
- `config.sample.toml`: one artificial site, three notes, one expected API call.
- No API calls or extraction-output writes occur in either dry-run.
- Authentication and model access are intentionally not checked offline.

## Real artificial-sample request: passed

Command: `uv run python scripts/test_live_sample.py --config config.sample.toml`.

The latest real Claude Opus 5 request passed **all 12 checks**, with ten retained
observations and no evidence-validation issues. Its report timestamp is
`2026-10-02T11:35:13.262317+00:00`. The script exited successfully and recorded
`status: passed` in `output/artificial_sample_check.json`.

The user's preceding run failed because an extra `available_area` observation
lacked the required quantity. The valid 700 m² remaining-plot observation and all
other sample checks passed. The original rejected observation is not retained in
the output, so its exact content cannot be reconstructed. The active v1 prompt
and schema description now explicitly require numbers for numeric kinds and
route unmeasured usable area to a site condition. The validator remains strict.
The latest live output preserves this distinction. An earlier authentication
failure has been superseded by these successful API requests.

The artificial notes describe:

- an earlier owner negotiation and a later signed LOI, supplied out of date order;
- explicitly indifferent neighbours;
- approximately 700 m² of remaining plot, without a measured usable area;
- a request for 12% revenue share;
- unknown grid quantities, flood zone and reserve boundaries.

Known expectations are recorded before the request in
`tests/fixtures/artificial_expected.json`. The live checker requires the stated
facts, their source identities and quantities, and verifies that unknown facts
are not promoted to confirmed numeric or legal claims. It also fails if normal
evidence validation rejected anything. Offline tests verify that this checker
catches missing owner history and invented grid data.

## Scope of verification

A passed artificial sample verifies a small working slice; it does not establish
accuracy across the assignment dataset. The latest observations and check report
were inspected. No full-dataset extraction was run as part of this fix.
