"""Bundle the offline scoring output and UI into a portable static page."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build():
    dataset = json.loads((ROOT / "data/scoring.json").read_text())
    # The public UI needs score decisions and evidence, never API configuration.
    public = {key: dataset[key] for key in (
        "metadata", "questions", "presets", "default_profile_id", "profiles", "rubric"
    )}
    public["metadata"] = {key: dataset["metadata"][key] for key in (
        "country", "exported_at", "site_count", "bounds_meaning"
    )}
    public["sites"] = [{
        **{key: site[key] for key in (
            "site_id", "name", "region", "site_type", "parcel_id",
            "source_site_ids", "observed_inputs", "base_status", "scores"
        )},
        "criterion_variants": {field: {
            name: {key: variant[key] for key in (
                "value", "unit", "tier", "contribution", "basis", "conditions"
            )} for name, variant in variants.items()
        } for field, variants in site["criterion_variants"].items()},
        "notes": site["evidence"]["field_notes"],
        "sources": site["evidence"]["normalized_sources"],
    } for site in dataset["sites"]]
    template = (ROOT / "web/template.html").read_text()
    replacements = {
        "/* STYLES */": (ROOT / "web/maren.css").read_text(),
        "/* APPLICATION */": (ROOT / "web/maren.js").read_text(),
        "/* DATA */": json.dumps(public, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c"),
    }
    for token, value in replacements.items():
        if template.count(token) != 1:
            raise ValueError(f"Expected exactly one template token: {token}")
        template = template.replace(token, value)
    target = ROOT / "index.html"
    target.write_text(template)
    print(f"Built {target.name}: {len(public['sites'])} sites, {len(public['profiles'])} profiles, {target.stat().st_size:,} bytes")


if __name__ == "__main__":
    build()
