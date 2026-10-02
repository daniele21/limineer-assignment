"""Generate one offline scoring dataset for frontend policy questions."""

import argparse
from bisect import bisect_left, bisect_right
from copy import deepcopy
import csv
from datetime import date
import hashlib
from itertools import product
import json
import math
from pathlib import Path

from .normalize import normalize

ROOT = Path(__file__).resolve().parents[2]
CUTOFF = "2026-06-30"
RUBRIC = [
    {"id": "headroom_mw", "label": "Grid headroom", "unit": "MW", "weight": 30,
     "tiers": [{"min": 4, "min_inclusive": True, "tier": 5}, {"min": 2, "min_inclusive": True, "max": 4, "max_inclusive": False, "tier": 3}, {"min": 1, "min_inclusive": True, "max": 2, "max_inclusive": False, "tier": 1}, {"max": 1, "max_inclusive": False, "tier": 0}]},
    {"id": "substation_distance_km", "label": "Substation distance", "unit": "km", "weight": 15,
     "tiers": [{"max": 1, "max_inclusive": True, "tier": 5}, {"min": 1, "min_inclusive": False, "max": 3, "max_inclusive": True, "tier": 3}, {"min": 3, "min_inclusive": False, "max": 6, "max_inclusive": True, "tier": 1}, {"min": 6, "min_inclusive": False, "tier": 0}]},
    {"id": "owner_status", "label": "Owner status", "unit": None, "weight": 20,
     "tiers": [{"value": value, "tier": tier} for value, tier in [("loi_signed", 5), ("in_talks", 3), ("not_contacted", 1), ("refused", 0)]]},
    {"id": "community_sentiment", "label": "Council / community sentiment", "unit": None, "weight": 10,
     "tiers": [{"value": value, "tier": tier} for value, tier in [("supportive", 5), ("neutral", 3), ("opposed", 0)]]},
    {"id": "flood_zone", "label": "Flood zone", "unit": None, "weight": 15,
     "tiers": [{"value": value, "tier": tier} for value, tier in [("none", 5), ("low", 4), ("medium", 2), ("high", 0)]]},
    {"id": "usable_area_m2", "label": "Usable-area proxy", "unit": "m2", "weight": 10,
     "tiers": [{"min": 1200, "min_inclusive": True, "tier": 5}, {"min": 800, "min_inclusive": True, "max": 1200, "max_inclusive": False, "tier": 2}, {"max": 800, "max_inclusive": False, "tier": 0}]},
]
FIELDS = [criterion["id"] for criterion in RUBRIC]
WEIGHTS = {criterion["id"]: criterion["weight"] for criterion in RUBRIC}
QUESTIONS = [
    {"id": "grid", "prompt": "Which grid figures should we use?", "default_answer": "official",
     "help": "Vendor alternatives apply only where official data is missing or predates June 30, 2026. Keep official data if it earns the same or more points. Estimates need operator confirmation.",
     "options": [{"id": "official", "label": "Official figures", "description": "Use official capacity only."},
                 {"id": "vendor_central", "label": "Include vendor estimates", "description": "Explore the vendor's central estimate when allowed."},
                 {"id": "vendor_upper", "label": "Explore vendor upside", "description": "Explore the upper end of the vendor's unvalidated ±40% band."}]},
    {"id": "sentiment", "prompt": "How should we treat unknown or conditional local support?", "default_answer": "evidence_only",
     "help": "Known neutral or opposed positions stay unchanged. Choosing upside does not confirm support.",
     "options": [{"id": "evidence_only", "label": "Give no extra points", "description": "Keep unknown sentiment unknown."},
                 {"id": "assume_support", "label": "Explore confirmed support", "description": "Show ten points if support is confirmed and any condition is met."}]},
    {"id": "missing", "prompt": "Should we explore sites with missing critical checks?", "default_answer": "hold",
     "help": "This covers missing capacity, distance, owner, flood, area or protection checks. Best-case values are hypotheses.",
     "options": [{"id": "hold", "label": "Keep them on hold", "description": "Keep sites with unresolved critical gaps out of the ranking."},
                 {"id": "best_case", "label": "Show conditional upside", "description": "Assume favourable critical checks and rank those sites separately."}]},
    {"id": "conflicts", "prompt": "Should we explore sites with unresolved land checks?", "default_answer": "hold",
     "help": "Legal clearance and remaining usable area must be checked. Confirmed protected sites are always excluded.",
     "options": [{"id": "hold", "label": "Keep them on hold", "description": "Wait for protection or area conflicts to be resolved."},
                 {"id": "conditional", "label": "Show pending-check scenarios", "description": "Explore a legal footprint and the reported remaining area without restoring sold land."}]},
]
PRESETS = {
    "conservative": {"grid": "official", "sentiment": "evidence_only", "missing": "hold", "conflicts": "hold"},
    "potential": {"grid": "vendor_upper", "sentiment": "assume_support", "missing": "best_case", "conflicts": "conditional"},
}


def tier(field, value):
    if value is None:
        return None
    if field in {"headroom_mw", "substation_distance_km", "usable_area_m2"}:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError(f"Invalid {field}: {value!r}")
    if field == "headroom_mw":
        return [0, 1, 3, 5][bisect_right([1, 2, 4], value)]
    if field == "substation_distance_km":
        return [5, 3, 1, 0][bisect_left([1, 3, 6], value)]
    if field == "usable_area_m2":
        return [0, 2, 5][bisect_right([800, 1200], value)]
    matches = [row["tier"] for row in next(c for c in RUBRIC if c["id"] == field)["tiers"] if row["value"] == value]
    if not matches:
        raise ValueError(f"Invalid {field}: {value!r}")
    return matches[0]


def profile_id(answers):
    if set(answers) != {question["id"] for question in QUESTIONS}:
        raise ValueError("Every question must have exactly one answer")
    for question in QUESTIONS:
        if answers[question["id"]] not in {option["id"] for option in question["options"]}:
            raise ValueError(f"Invalid answer for {question['id']}")
    return "__".join(answers[question["id"]] for question in QUESTIONS)


def build_variants(review):
    site = review["site"]
    values = site["scoring_inputs"]
    variants = {field: {} for field in FIELDS}

    def add(field, key, value, basis, evidence=None, conditions=None, forced_tier=None):
        selected_tier = tier(field, value) if forced_tier is None else forced_tier
        variants[field][key] = {"value": value, "unit": next(c["unit"] for c in RUBRIC if c["id"] == field),
                                "tier": selected_tier, "contribution": None if selected_tier is None else WEIGHTS[field] * selected_tier / 5,
                                "basis": basis, "evidence": deepcopy(evidence), "conditions": conditions or []}

    for field in FIELDS:
        basis = "unknown" if values[field] is None else "parcel_proxy" if field == "usable_area_m2" else "source_evidence"
        add(field, "baseline", values[field], basis, site["input_evidence"][field])
    if site["input_evidence"]["substation_distance_km"]["status"] == "no_substation_within_10_km":
        add("substation_distance_km", "baseline", None, "known_distance_bound", site["input_evidence"]["substation_distance_km"], forced_tier=0)
    grid = site["normalized_sources"].get("gridmap") or {}
    vendor = site["normalized_sources"].get("vendor_estimate") or {}
    if vendor:
        band = vendor["band_pct"]
        if isinstance(band, bool) or not isinstance(band, (int, float)) or not math.isfinite(band) or not 0 <= band <= 100:
            raise ValueError(f"{site['site_id']}: invalid vendor band")
        tier("headroom_mw", vendor["headroom_mw_est"])
        estimated = date.fromisoformat(vendor["estimated_at"])
        official_date = date.fromisoformat(grid["data_as_of"]) if grid.get("data_as_of") else None
        allowed = values["headroom_mw"] is None or (official_date is not None and official_date < date.fromisoformat(CUTOFF) and estimated > official_date)
        if allowed:
            for key, multiplier in (("vendor_central", 1), ("vendor_upper", 1 + band / 100)):
                add("headroom_mw", key, vendor["headroom_mw_est"] * multiplier, "vendor_estimate", vendor,
                    ["The grid operator confirms capacity sufficient for this tier."])
    hypotheses = {
        "headroom_mw": (4, "An official check confirms at least 4 MW; this is currently unsupported."),
        "substation_distance_km": (1, "A successful check confirms a substation within 1 km."),
        "owner_status": ("loi_signed", "Ownership and a signed LOI are confirmed."),
        "community_sentiment": ("supportive", "Support is confirmed and any stated condition is met."),
        "flood_zone": ("none", "An authoritative check confirms no flood zone."),
        "usable_area_m2": (1200, "At least 1,200 m² of usable installation area is verified."),
    }
    for field, (value, condition) in hypotheses.items():
        if variants[field]["baseline"]["tier"] is None:
            # A missing-data answer cannot bypass the explicit grid-source choice.
            if field == "headroom_mw" and vendor:
                continue
            add(field, "best_case", value, "hypothesis", conditions=[condition])
    area_observations = site["input_evidence"]["usable_area_m2"]["field_note_area_observations"]
    if area_observations:
        observation = max(area_observations, key=lambda o: o["date"] or "")
        quantity = observation.get("normalized_quantity") or observation["quantity"]
        if quantity["unit"] != "m2":
            raise ValueError(f"{site['site_id']}: field-note area must have known m2 units")
        add("usable_area_m2", "remaining_plot", quantity["value"], "remaining_plot_proxy", observation,
            ["Remaining usable area is checked; sold land is not restored. The reported area is approximate."])
        variants["usable_area_m2"].pop("best_case", None)
    return variants


def evaluate(review, variants, answers):
    profile_id(answers)
    components = {field: "baseline" for field in FIELDS}
    site = review["site"]
    excluded = review["eligibility"]["status"] == "excluded"
    if excluded:
        return {"status": "excluded", "score": None, "known_subtotal": None, "components": components,
                "score_kind": "excluded", "unresolved_criteria": [], "conditions": [],
                "reasons": review["eligibility"]["reasons"]}
    grid_choice = answers["grid"]
    if grid_choice in variants["headroom_mw"]:
        candidate = variants["headroom_mw"][grid_choice]["contribution"]
        baseline = variants["headroom_mw"]["baseline"]["contribution"]
        if baseline is None or candidate > baseline:
            components["headroom_mw"] = grid_choice
    for field in FIELDS:
        if variants[field][components[field]]["tier"] is not None:
            continue
        if field == "community_sentiment":
            if answers["sentiment"] == "assume_support":
                components[field] = "best_case"
        elif field == "usable_area_m2" and "remaining_plot" in variants[field]:
            if answers["conflicts"] == "conditional":
                components[field] = "remaining_plot"
        elif answers["missing"] == "best_case" and "best_case" in variants[field]:
            components[field] = "best_case"
    selected = {field: variants[field][key] for field, key in components.items()}
    unresolved = [field for field, value in selected.items() if value["tier"] is None]
    conditions = list(dict.fromkeys(condition for value in selected.values() for condition in value["conditions"]))
    reasons = ["missing_" + field for field in unresolved if field != "community_sentiment"]
    protection = review["protection_check"]
    if protection["registry_protected_area"] is None:
        if answers["missing"] == "hold":
            reasons.append("unknown_protection_status")
        else:
            conditions.append("The installation footprint is verified outside protected nature areas.")
    if protection["overlap_observations"]:
        if answers["conflicts"] == "hold":
            reasons.append("unresolved_protection_overlap")
        else:
            conditions.append("A legally buildable unprotected footprint with sufficient usable area is verified.")
    if "field_note_infrastructure_claim_requires_reconciliation" in review["eligibility"]["reasons"]:
        reasons.append("field_note_infrastructure_claim_requires_reconciliation")
    # Sites held for critical evidence stay conditional after optimistic completion.
    status = "held" if reasons else "conditional" if review["eligibility"]["status"] == "held" else "eligible"
    subtotal = sum(value["contribution"] or 0 for value in selected.values())
    observed_subtotal = sum(value["baseline"]["contribution"] or 0 for value in variants.values())
    return {"status": status, "score": None if status == "held" else subtotal,
            "known_subtotal": observed_subtotal, "components": components,
            "score_kind": "held" if status == "held" else "hypothetical" if conditions else "partial_lower" if unresolved else "complete_rubric",
            "unresolved_criteria": unresolved, "conditions": list(dict.fromkeys(conditions)), "reasons": reasons}


def build_dataset(normalized, audit):
    reviews = audit["opportunities"]
    ids = [r["site"]["site_id"] for r in reviews]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate canonical site IDs")
    expected = [r["site"] for r in reviews if r["eligibility"]["status"] == "eligible"]
    if normalized["sites"] != expected:
        raise ValueError("Normalized candidates differ from the audit")
    if normalized["metadata"]["inputs"] != audit["metadata"]["inputs"]:
        raise ValueError("Normalized input and audit provenance differ")
    profiles = []
    for choice in product(*[[o["id"] for o in q["options"]] for q in QUESTIONS]):
        answers = dict(zip([q["id"] for q in QUESTIONS], choice))
        profiles.append({"id": profile_id(answers), "answers": answers, "rankings": {}})
    sites = []
    for review in reviews:
        original = review["site"]
        variants = build_variants(review)
        site = {key: deepcopy(original[key]) for key in ("site_id", "name", "region", "site_type", "parcel_id", "grid_ref_km", "source_site_ids", "aliases", "flags")}
        site.update(observed_inputs=deepcopy(original["scoring_inputs"]),
                    base_status=deepcopy(review["eligibility"]), protection=deepcopy(review["protection_check"]),
                    evidence={key: deepcopy(original[key]) for key in ("normalized_sources", "field_notes", "observations", "input_evidence", "owner_status_history")},
                    criterion_variants=variants,
                    scores={p["id"]: evaluate(review, variants, p["answers"]) for p in profiles})
        sites.append(site)
    for profile in profiles:
        for status in ("eligible", "conditional", "held", "excluded"):
            group = [site for site in sites if site["scores"][profile["id"]]["status"] == status]
            if status in {"eligible", "conditional"}:
                group.sort(key=lambda site: (-site["scores"][profile["id"]]["score"], site["site_id"]))
                last_score, last_rank = None, 0
                for position, site in enumerate(group, 1):
                    score = site["scores"][profile["id"]]
                    if score["score"] != last_score:
                        last_rank, last_score = position, score["score"]
                    score["rank"] = last_rank
            profile["rankings"][status] = [site["site_id"] for site in group]
    questions = deepcopy(QUESTIONS)
    for question in questions:
        other_ids = [q["id"] for q in questions if q["id"] != question["id"]]
        affected = []
        for site in sites:
            groups = {}
            for profile in profiles:
                other_answers = tuple(profile["answers"][qid] for qid in other_ids)
                row = site["scores"][profile["id"]]
                signature = json.dumps({k: row[k] for k in ("status", "score", "components", "conditions")}, sort_keys=True)
                groups.setdefault(other_answers, set()).add(signature)
            if any(len(values) > 1 for values in groups.values()):
                affected.append(site["site_id"])
        question["affected_site_ids"] = affected
    return {
        "schema_version": 1,
        "metadata": {"country": normalized["metadata"].get("country"), "exported_at": normalized["metadata"].get("exported_at"),
                     "official_stale_before": CUTOFF, "site_count": len(sites), "profile_count": len(profiles),
                     "bounds_meaning": "Scores under selected assumptions, not confidence intervals or guaranteed physical bounds.",
                     "area_basis": "Parcel area is a proxy unless contradicted; it is not measured usable area."},
        "rubric": {"formula": "sum(weight * tier / 5)", "maximum_score": 100, "criteria": deepcopy(RUBRIC)},
        "questions": questions,
        "presets": [{"id": key, "label": key.capitalize(), "answers": deepcopy(value), "profile_id": profile_id(value)} for key, value in PRESETS.items()],
        "default_profile_id": profile_id(PRESETS["conservative"]),
        "ranking_contract": {"order": "score descending", "ties": "Equal scores share a competition rank; site ID orders display only.",
                             "groups": "Eligible and conditional sites have separate rankings; held and excluded sites are unranked.",
                             "interaction": "Answers change assumptions, never source evidence or confirmation status.",
                             "score_labels": {"complete_rubric": "Rubric score", "partial_lower": "At least", "hypothetical": "If checks confirm", "held": "Needs checks", "excluded": "Excluded"}},
        "profiles": profiles, "sites": sites,
    }


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(root=ROOT, output=None):
    root = root.resolve()
    output = output or root / "data/scoring.json"
    paths = {"normalized": root / "data/sites.normalized.json", "audit": root / "output/normalization_review.json",
             "raw": root / "data/sites.json", "extractions": root / "output/extractions.json",
             "fetch_log": root / "data/fetch_log.csv", "assumptions": root / "assumptions.md"}
    if output.resolve() in {path.resolve() for path in paths.values()}:
        raise ValueError("Scoring output must not overwrite an input")
    loaded = {key: json.loads(path.read_text(encoding="utf-8")) for key, path in paths.items() if key not in {"fetch_log", "assumptions"}}
    if loaded["extractions"]["metadata"]["input_sha256"] != digest(paths["raw"]):
        raise ValueError("Raw data no longer matches the extraction")
    with paths["fetch_log"].open(newline="", encoding="utf-8") as stream:
        scoring, review = normalize(loaded["raw"]["sites"], loaded["extractions"], list(csv.DictReader(stream)))
    if scoring["sites"] != loaded["normalized"]["sites"] or review["opportunities"] != loaded["audit"]["opportunities"]:
        raise ValueError("Saved normalization is stale; regenerate it first")
    dataset = build_dataset(loaded["normalized"], loaded["audit"])
    dataset["metadata"]["input_hashes"] = {key: digest(path) for key, path in paths.items()}
    dataset["metadata"]["generator_sha256"] = digest(Path(__file__))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(dataset, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    return dataset


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        dataset = run(args.root, args.output)
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(1, f"Scoring generation failed: {exc}\n")
    print(f"Generated {dataset['metadata']['site_count']} sites × {dataset['metadata']['profile_count']} answer combinations")


if __name__ == "__main__":
    main()
