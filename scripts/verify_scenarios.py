"""Verify the existing scenario report offline; this does not generate scores."""

import argparse
from bisect import bisect_left, bisect_right
import csv
import hashlib
import json
from pathlib import Path

from field_notes.normalize import normalize

ROOT = Path(__file__).resolve().parents[1]
WEIGHTS = {"headroom_mw": 30, "substation_distance_km": 15, "owner_status": 20,
           "community_sentiment": 10, "flood_zone": 15, "usable_area_m2": 10}


def contribution(field, value):
    """Independent table-based reading of the sponsor's tiers."""
    if value is None:
        return None
    if field == "headroom_mw":
        tier = [0, 1, 3, 5][bisect_right([1, 2, 4], value)]
    elif field == "substation_distance_km":
        tier = [5, 3, 1, 0][bisect_left([1, 3, 6], value)]
    elif field == "usable_area_m2":
        tier = [0, 2, 5][bisect_right([800, 1200], value)]
    else:
        tier = {"owner_status": {"loi_signed": 5, "in_talks": 3, "not_contacted": 1, "refused": 0},
                "community_sentiment": {"supportive": 5, "neutral": 3, "opposed": 0},
                "flood_zone": {"none": 5, "low": 4, "medium": 2, "high": 0}}[field][value]
    return WEIGHTS[field] * tier / 5


def verify(root=ROOT):
    read = lambda path: json.loads((root / path).read_text(encoding="utf-8"))
    report = read("output/scenario_review.json")
    audit = read("output/normalization_review.json")
    raw = read("data/sites.json")
    extraction = read("output/extractions.json")
    normalized = read("data/sites.normalized.json")
    checks = []

    def check(name, condition):
        checks.append({"check": name, "passed": bool(condition)})

    for path, key in (("data/sites.normalized.json", "normalized_input_sha256"),
                      ("output/normalization_review.json", "audit_input_sha256"),
                      ("assumptions.md", "assumptions_sha256")):
        check(f"Current input hash: {path}", hashlib.sha256((root / path).read_bytes()).hexdigest() == report["metadata"][key])
    check("Raw sites match the extraction input hash",
          hashlib.sha256((root / "data/sites.json").read_bytes()).hexdigest() == extraction["metadata"]["input_sha256"])
    with (root / "data/fetch_log.csv").open(newline="", encoding="utf-8") as stream:
        scoring, rebuilt = normalize(raw["sites"], extraction, list(csv.DictReader(stream)))
    check("Rebuilt normalization and evidence audit match saved artifacts",
          scoring["sites"] == normalized["sites"] and rebuilt["opportunities"] == audit["opportunities"])
    sites = {r["site_id"]: r for r in report["sites"]}
    originals = {r["site"]["site_id"]: r for r in audit["opportunities"]}
    check("Every physical opportunity appears once", len(report["sites"]) == len(sites) == 39 and sites.keys() == originals.keys())
    check("Shared parcel is merged, with both histories preserved",
          "S-031" not in sites and originals["S-017"]["site"]["source_site_ids"] == ["S-017", "S-031"]
          and originals["S-017"]["site"]["scoring_inputs"]["owner_status"] == "loi_signed"
          and originals["S-017"]["site"]["scoring_inputs"]["community_sentiment"] == "neutral")
    for sid, row in sites.items():
        original = originals[sid]
        source_site = original["site"]
        values = source_site["scoring_inputs"]
        expected = {field: contribution(field, value) for field, value in values.items()}
        negative_search = source_site["input_evidence"]["substation_distance_km"]["status"] == "no_substation_within_10_km"
        if negative_search:
            expected["substation_distance_km"] = 0
        subtotal = sum(value for value in expected.values() if value is not None)
        eligible = original["eligibility"]["status"] == "eligible"
        excluded = original["eligibility"]["status"] == "excluded"
        check(f"{sid}: conservative rubric arithmetic and admission",
              expected == row["conservative_contributions"]
              and row["conservative_score_lower"] == (subtotal if eligible else None)
              and row["conservative_status"] == original["eligibility"]["status"])
        if excluded:
            check(f"{sid}: exclusion persists in potential scenario",
                  row["potential_status"] == "excluded" and row["potential_score_upper"] is None)
            continue
        criteria = row["criteria"]
        check(f"{sid}: six criteria and correct potential admission",
              criteria.keys() == WEIGHTS.keys()
              and row["potential_status"] == ("current_candidate" if eligible else "conditional_only"))
        check(f"{sid}: potential arithmetic, interval and uplift",
              sum(c["potential_upper_points"] for c in criteria.values()) == row["potential_score_upper"]
              and sum(c["potential_central_points"] for c in criteria.values()) == row["potential_vendor_central_score"]
              and subtotal <= row["potential_vendor_central_score"] <= row["potential_score_upper"] <= 100
              and row["scenario_uplift"] == (row["potential_score_upper"] - subtotal if eligible else None))
        grid = source_site["normalized_sources"].get("gridmap") or {}
        vendor = source_site["normalized_sources"].get("vendor_estimate") or {}
        vendor_allowed = bool(vendor and (values["headroom_mw"] is None or (
            (grid.get("data_as_of") or "9999") < "2026-06-30"
            and (vendor.get("estimated_at") or "") > (grid.get("data_as_of") or ""))))
        for field, criterion in criteria.items():
            check(f"{sid}/{field}: observed value is preserved",
                  criterion["observed_value"] == values[field])
            if expected[field] is None:
                check(f"{sid}/{field}: missing evidence has an explicit hypothesis", bool(criterion["hypotheses"]))
                if field != "headroom_mw":
                    area_obs = source_site["input_evidence"]["usable_area_m2"]["field_note_area_observations"] if field == "usable_area_m2" else []
                    expected_upper = contribution(field, (area_obs[-1].get("normalized_quantity") or area_obs[-1]["quantity"])["value"]) if area_obs else WEIGHTS[field]
                    check(f"{sid}/{field}: favourable completion follows the stated policy",
                          criterion["potential_upper_points"] == expected_upper
                          and criterion["potential_central_points"] == expected_upper)
            if values[field] is not None and field != "headroom_mw":
                check(f"{sid}/{field}: known non-grid facts are unchanged",
                      criterion["potential_upper_points"] == expected[field])
        headroom = criteria["headroom_mw"]
        if vendor_allowed:
            expected_range = vendor["headroom_mw_est"] * (1 + vendor["band_pct"] / 100)
            check(f"{sid}: allowed vendor range derives from the actual estimate",
                  headroom["vendor_range"]["central_mw"] == vendor["headroom_mw_est"]
                  and headroom["vendor_range"]["upper_mw"] == expected_range
                  and headroom["potential_upper_points"] == max(expected["headroom_mw"] or 0, contribution("headroom_mw", expected_range)))
            check(f"{sid}: vendor central case follows the actual estimate",
                  headroom["potential_central_points"] == max(expected["headroom_mw"] or 0, contribution("headroom_mw", vendor["headroom_mw_est"])))
        elif values["headroom_mw"] is not None:
            check(f"{sid}: fresh official grid source remains authoritative",
                  headroom["potential_upper_points"] == expected["headroom_mw"]
                  and all(a["source"] == "official_gridmap" for a in headroom["allowed_headroom_alternatives"]))
        else:
            check(f"{sid}: unsupported capacity is only the explicit best-case ceiling",
                  headroom["potential_upper_points"] == 30 and headroom["potential_central_points"] == 30
                  and headroom["basis"] == "unsupported_completion_ceiling")
        if negative_search:
            check(f"{sid}: known distance >10 km is not improved",
                  criteria["substation_distance_km"]["potential_upper_points"] == 0)
    for sid, lower, upper in (("S-003", 97, 97), ("S-007", 76, 100), ("S-021", 61, 83),
                              ("S-027", 87, 97), ("S-032", 82, 92), ("S-013", None, 82), ("S-024", None, 100)):
        check(f"Hand-calculated example {sid}: {lower} to {upper}",
              sites[sid]["conservative_score_lower"] == lower and sites[sid]["potential_score_upper"] == upper)
    check("S-013: sold area is not restored", sites["S-013"]["criteria"]["usable_area_m2"]["selected_scenario_value"] == 700
          and sites["S-013"]["criteria"]["usable_area_m2"]["potential_upper_points"] == 0)
    check("S-025: exactly 2 MW earns 18 points", sites["S-025"]["conservative_contributions"]["headroom_mw"] == 18)
    check("S-032: exactly 1 km earns 15 points", sites["S-032"]["conservative_contributions"]["substation_distance_km"] == 15)
    check("Only two score endpoints", all("source_fixed_completion_upper" not in row for row in sites.values()))
    conservative = sorted([r for r in sites.values() if r["conservative_status"] == "eligible"],
                          key=lambda r: (-r["conservative_score_lower"], r["site_id"]))
    potential = sorted(conservative, key=lambda r: (-r["potential_score_upper"], r["site_id"]))
    check("Potential ranking matches scores and only current candidates",
          report["potential_ranking_current_candidates"] == [r["site_id"] for r in potential])
    return {"status": "passed" if all(c["passed"] for c in checks) else "failed",
            "passed": sum(c["passed"] for c in checks), "total": len(checks), "checks": checks,
            "conservative_top_five": [r["site_id"] for r in conservative[:5]],
            "potential_top_five_current_pool": [r["site_id"] for r in potential[:5]],
            "limits": ["Checks verify saved data and scenario calculations, not the physical truth of assumptions.",
                       "This verifies the report; the scenario generator is not integrated into the repository entry point."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    result = verify(args.root)
    destination = args.root / "output/scenario_verification.json"
    destination.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"{result['status']}: {result['passed']}/{result['total']} checks; report: {destination}")
    raise SystemExit(0 if result["status"] == "passed" else 1)


if __name__ == "__main__":
    main()
