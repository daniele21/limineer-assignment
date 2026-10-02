"""One paid request against a synthetic fixture, with human-defined expectations."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from anthropic import AnthropicError

from field_notes.__main__ import run
from field_notes.config import load_config

ROOT = Path(__file__).resolve().parents[1]


def matches(actual: dict, expected: dict) -> bool:
    for key, value in expected.items():
        candidate = actual.get(key)
        if isinstance(value, dict):
            if not isinstance(candidate, dict) or not matches(candidate, value):
                return False
        elif candidate != value:
            return False
    return True


def check_sample(output: dict, expected: dict) -> list[dict]:
    checks = []

    def check(name: str, passed: bool, *, details: list[str] | None = None) -> None:
        item = {"name": name, "passed": passed}
        if details:
            item["details"] = details
        checks.append(item)

    results = output["results"]
    check("exactly one artificial site", len(results) == 1 and results[0]["site_id"] == "ART-001")
    if not results:
        return checks
    result = results[0]
    observations = result["extraction"]["observations"]
    check("no evidence validation issues", not result["validation_issues"],
          details=result["validation_issues"])
    for required in expected["required_observations"]:
        check(f"required {required['kind']} ({required.get('value', 'quantity')})",
              any(matches(item, required) for item in observations))
    check("no invented grid quantities", not any(item["kind"] in expected["forbidden_kinds"] for item in observations))
    check("remaining plot area is not measured usable area",
          not any(item["kind"] == "available_area" and item["value"] == "usable_installation_area" for item in observations))
    check("commercial request is not silently accepted", any(
        item["kind"] == "commercial_term" and any(word in item["value"].lower() for word in ("want", "request"))
        for item in observations
    ))
    check("no confirmed protected overlap", all(
        item["value"] == "uncertain_overlap" and item["statement_status"] != "asserted"
        for item in observations if item["kind"] == "protected_overlap"
    ))
    check("no confirmed flood zone", all(
        item["value"].lower() == "unknown" or item["statement_status"] != "asserted"
        for item in observations if item["kind"] == "flood_observation"
    ))
    return checks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config.sample.toml")
    args = parser.parse_args()
    config = load_config(args.config)
    # Never accidentally run this diagnostic against the full production dataset.
    fixture = ROOT / "tests" / "fixtures" / "artificial_sites.json"
    if config.input.sites_file != fixture.resolve() or config.input.site_ids:
        parser.error("Live sample config must select the artificial fixture, without a site filter.")
    expected = json.loads((fixture.parent / "artificial_expected.json").read_text())
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "model": config.model.api_id}
    try:
        output = run(args.config)
        checks = check_sample(output, expected)
        report.update(status="passed" if all(item["passed"] for item in checks) else "failed", checks=checks)
    except AnthropicError as exc:
        report.update(status="blocked", error=type(exc).__name__, checks=[],
                      message="Anthropic request failed; no live extraction-quality assertions ran.")
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        report.update(status="failed", error=type(exc).__name__, checks=[], message=str(exc))
    report_path = config.output.path.parent / "artificial_sample_check.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    print(f"Report: {report_path}", file=sys.stderr)
    if report["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
