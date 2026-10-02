"""Build offline, evidence-backed scoring inputs. No API calls or scoring."""

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path

from .extractor import validate_evidence
from .schema import Extraction, Note

ROOT = Path(__file__).resolve().parents[2]
POLICY = {
    "name": "precision_first_v1",
    "headroom_unit": "MW",
    "distance_unit": "km",
    "area_unit": "m2",
    "grid_precedence": "official_gridmap; vendor is contextual evidence only",
    "missing_values": "null; no imputation or positive evidence from absence",
    "area": "registry parcel area is an explicit usable-area proxy unless contradicted",
    "owner_status": "latest dated explicit evidence; same-date conflicts remain unknown",
    "sentiment": "latest per actor and scope; opposition wins across actors; conditional stays unknown",
    "duplicates": "same region/parcel/type, identical sources, within 0.1 km; lowest ID is canonical",
    "eligibility": "exclude protected sites and current owner refusal; hold unknown critical inputs or conflicts",
    "unknown_sentiment": "retain for scoring with null sentiment; score must expose incompleteness",
    "reference_size": "no additional 2 MW minimum or new flood/opposition kill rules",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def number(value, label):
    if value is not None and (
        isinstance(value, bool) or not isinstance(value, (int, float))
        or not math.isfinite(value) or value < 0
    ):
        raise ValueError(f"{label}: expected a finite nonnegative number or null")
    return value


def dated(items):
    return sorted(items, key=lambda item: (item.get("date") or "", item.get("note_id", "")))


def current(items):
    """Do not prefer an older clear claim over a newer qualified/unknown claim."""
    if not items or any(not item.get("date") for item in items):
        return None, items
    latest = max(item["date"] for item in items)
    selected = [item for item in items if item["date"] == latest]
    values = {item["value"] for item in selected}
    if len(values) != 1 or any(item["statement_status"] != "asserted" for item in selected):
        return None, selected
    value = selected[0]["value"]
    return (None if value == "unknown" else value), selected


def sentiment(observations):
    groups = defaultdict(list)
    for item in observations:
        if item["kind"] == "sentiment":
            groups[(item["actor"], item["scope"])].append(item)
    positions = [current(items) for items in groups.values()]
    evidence = [item for _, selected in positions for item in selected]
    values = {value for value, _ in positions}
    if "opposed" in values:
        return "opposed", evidence
    if not values or None in values or "conditional" in values:
        return None, evidence
    # Mixed support/neutral evidence does not imply universal support.
    return ("neutral" if "neutral" in values else "supportive"), evidence


def prepare_extractions(sites, extracted):
    results = extracted.get("results", [])
    ids = [site["site_id"] for site in sites]
    result_ids = [result["site_id"] for result in results]
    if len(set(ids)) != len(ids) or len(set(result_ids)) != len(result_ids) or set(ids) != set(result_ids):
        raise ValueError("Site/extraction IDs must be unique and match exactly")
    by_id = {result["site_id"]: result for result in results}
    prepared = {}
    for site in sites:
        sid = site["site_id"]
        result = by_id[sid]
        expected = [Note.model_validate({**note, "note_id": f"{sid}:{i}", "source_site_id": sid})
                    for i, note in enumerate(site["field_notes"])]
        supplied = [Note.model_validate(note) for note in result["field_notes"]]
        if supplied != expected or result["extraction"]["opportunity_id"] != sid:
            raise ValueError(f"{sid}: extraction notes or opportunity differ from raw input")
        extraction = Extraction.model_validate_json(json.dumps(result["extraction"]))
        checked = validate_evidence(extraction, expected)
        if result.get("validation_issues") or checked.validation_issues:
            raise ValueError(f"{sid}: extraction has validation issues; review before normalizing")
        notes = []
        for raw, note in zip(site["field_notes"], expected):
            notes.append({**note.model_dump(mode="json"), "owner_status": raw.get("owner_status")})
        note_lookup = {note["note_id"]: note for note in notes}
        observations = []
        for i, observation in enumerate(checked.extraction.observations):
            item = observation.model_dump(mode="json")
            note = note_lookup[item["note_id"]]
            item.update(observation_id=f"{sid}:observation:{i}", date=note["date"],
                        author=note["author"], source_site_id=sid)
            quantity = item["quantity"]
            if quantity:
                unit = quantity["unit"]
                quantity = deepcopy(quantity)
                if unit in {"kW", "m"}:
                    quantity["value"] /= 1000
                    quantity["unit"] = {"kW": "MW", "m": "km"}[unit]
                item["normalized_quantity"] = quantity
            observations.append(item)
        prepared[sid] = {"field_notes": notes, "observations": observations}
    return prepared


def normalize(sites, extracted, fetch_log):
    """Return candidate records and an audit of every physical opportunity."""
    prepared = prepare_extractions(sites, extracted)
    groups = defaultdict(list)
    for site in sites:
        if not site.get("parcel_id") or not site.get("region"):
            raise ValueError(f"{site['site_id']}: missing entity identity")
        groups[(site["region"], site["parcel_id"])].append(site)
    reviews = []
    merged = []
    for group in sorted(groups.values(), key=lambda group: min(s["site_id"] for s in group)):
        group = sorted(group, key=lambda site: site["site_id"])
        base = group[0]
        sid = base["site_id"]
        for other in group[1:]:
            distance = math.hypot(base["grid_ref_km"]["x"] - other["grid_ref_km"]["x"],
                                  base["grid_ref_km"]["y"] - other["grid_ref_km"]["y"])
            if other["sources"] != base["sources"] or other["site_type"] != base["site_type"] or distance > 0.1:
                raise ValueError(f"{sid}/{other['site_id']}: same parcel with conflicting entity evidence")
        source_ids = [site["site_id"] for site in group]
        if len(group) > 1:
            merged.append({"canonical_site_id": sid, "source_site_ids": source_ids,
                           "parcel_id": base["parcel_id"], "reason": POLICY["duplicates"]})
        notes = dated([note for site in group for note in prepared[site["site_id"]]["field_notes"]])
        observations = dated([obs for site in group for obs in prepared[site["site_id"]]["observations"]])
        owner_history = [obs for obs in observations if obs["kind"] == "owner_status"]
        # Structured status is separate evidence, not a fabricated Claude quote.
        owner_history += [{"kind": "owner_status", "value": note["owner_status"],
                           "date": note["date"], "note_id": note["note_id"],
                           "source_site_id": note["source_site_id"], "source": "structured_note",
                           "statement_status": "asserted", "quote": None}
                          for note in notes if note["owner_status"]]
        owner_history = dated(owner_history)
        for item in owner_history:
            if item["value"] not in {"loi_signed", "in_talks", "not_contacted", "refused", "unknown"}:
                raise ValueError(f"{sid}: invalid structured owner status")
        owner, owner_evidence = current(owner_history)
        local_sentiment, sentiment_evidence = sentiment(observations)
        sources = deepcopy(base["sources"])
        grid = sources.get("gridmap") or {}
        registry = sources.get("landreg") or {}
        vendor = sources.get("vendor_estimate") or {}
        raw_headroom = number(grid.get("headroom"), f"{sid} headroom")
        headroom = raw_headroom / 1000 if raw_headroom is not None and base["region"] == "Nordholm" else raw_headroom
        distance = number(grid.get("substation_distance_km"), f"{sid} distance")
        parcel_area = number(registry.get("area_m2"), f"{sid} area")
        vendor_headroom = number(vendor.get("headroom_mw_est"), f"{sid} vendor headroom")
        flood = registry.get("flood_zone")
        if flood not in {None, "none", "low", "medium", "high"}:
            raise ValueError(f"{sid}: invalid flood category")
        protection = registry.get("protected_area")
        if protection is not None and not isinstance(protection, bool):
            raise ValueError(f"{sid}: protected_area must be boolean or null")
        logs = [row for row in fetch_log if row["site_id"] in source_ids]
        grid_logs = sorted([row for row in logs if row["source"] == "gridmap"], key=lambda row: row["timestamp"])
        latest_log = grid_logs[-1] if grid_logs else None
        no_substation = bool(latest_log and latest_log["http_status"] == "200"
                             and latest_log["message"] == "no substation within search radius (10 km)")
        grid_status = "available" if headroom is not None and distance is not None else (
            "no_substation_within_10_km" if no_substation else
            "upstream_timeout" if latest_log and latest_log["http_status"] == "503" else "unknown")
        reasons, flags = [], []
        if protection is True:
            reasons.append("protected_nature_area")
        elif protection is None:
            reasons.append("unknown_protection_status")
        overlap = [obs for obs in observations if obs["kind"] == "protected_overlap"
                   and obs["value"] != "no_overlap_reported"]
        if overlap:
            reasons.append("unresolved_protection_overlap")
        if headroom is None:
            reasons.append("missing_official_headroom")
        if distance is None:
            reasons.append("no_substation_within_10_km" if no_substation else "unknown_substation_distance")
        if flood is None:
            reasons.append("unknown_flood_zone")
        if any(obs["kind"] in {"grid_headroom", "substation_distance", "flood_observation"} for obs in observations):
            reasons.append("field_note_infrastructure_claim_requires_reconciliation")
        area_observations = [obs for obs in observations if obs["kind"] == "available_area"]
        area = parcel_area
        if area_observations:
            # Keep remaining/available land distinct from measured installation area.
            area = None
            reasons.append("available_area_requires_verification")
        if parcel_area is None:
            reasons.append("unknown_area")
        if owner == "refused":
            reasons.append("owner_refused")
        elif owner is None:
            reasons.append("unknown_owner_status")
        if local_sentiment is None:
            flags.append("unknown_or_conditional_sentiment")
        if local_sentiment == "opposed":
            flags.append("explicit_opposition")
        if area is not None:
            flags.append("parcel_area_used_as_usable_area_proxy")
        if grid.get("data_as_of") and grid["data_as_of"] < "2026-06-30":
            flags.append("official_grid_predates_latest_dataset_quarter")
        if headroom is not None and vendor_headroom is not None and headroom != vendor_headroom:
            flags.append("vendor_differs_from_official_grid; official_retained")
        if headroom is not None and headroom < 2:
            flags.append("confirmed_headroom_below_2_mw_reference")
        if flood == "high":
            flags.append("high_flood_risk")
        status = "excluded" if {"protected_nature_area", "owner_refused"} & set(reasons) else "held" if reasons else "eligible"
        inputs = {"headroom_mw": headroom, "substation_distance_km": distance,
                  "owner_status": owner, "community_sentiment": local_sentiment,
                  "flood_zone": flood, "usable_area_m2": area}
        clean_grid = {key: value for key, value in grid.items() if key != "headroom"}
        clean_grid["headroom_mw"] = headroom
        clean_land = {key: value for key, value in registry.items() if key != "protected_area"}
        record = {
            **{key: base[key] for key in ("site_id", "name", "region", "site_type", "parcel_id", "grid_ref_km")},
            "source_site_ids": source_ids,
            "aliases": [{"site_id": site["site_id"], "name": site["name"], "grid_ref_km": site["grid_ref_km"]} for site in group],
            "scoring_inputs": inputs,
            "score_inputs_complete": all(value is not None for value in inputs.values()),
            "normalized_sources": {"gridmap": clean_grid if grid else None,
                                   "landreg": clean_land if registry else None,
                                   "vendor_estimate": vendor or None},
            "input_evidence": {
                "headroom_mw": {"source": "gridmap" if headroom is not None else None,
                                "raw_value": raw_headroom, "raw_unit": "kW" if base["region"] == "Nordholm" else "MW",
                                "data_as_of": grid.get("data_as_of")},
                "substation_distance_km": {"source": "gridmap" if distance is not None else "fetch_log" if no_substation else None,
                                           "status": grid_status, "lower_bound_km_exclusive": 10 if no_substation else None},
                "owner_status": owner_evidence,
                "community_sentiment": sentiment_evidence,
                "flood_zone": {"source": "landreg" if flood is not None else None, "record_date": registry.get("record_date")},
                "usable_area_m2": {"source": "landreg" if area is not None else None,
                                   "basis": "parcel_area_proxy" if area is not None else "unknown",
                                   "record_date": registry.get("record_date"), "field_note_area_observations": area_observations},
            },
            "field_notes": notes,
            "observations": observations,
            "owner_status_history": owner_history,
            "flags": flags,
        }
        reviews.append({"site": record, "eligibility": {"status": status, "reasons": reasons},
                        "protection_check": {"registry_protected_area": protection,
                                             "record_date": registry.get("record_date"), "overlap_observations": overlap},
                        "source_records": deepcopy(group), "fetch_log": logs})
    candidates = [review["site"] for review in reviews if review["eligibility"]["status"] == "eligible"]
    counts = Counter(review["eligibility"]["status"] for review in reviews)
    summary = {"raw_records": len(sites), "physical_opportunities": len(reviews),
               "duplicate_records_merged": len(sites) - len(reviews),
               "eligible": counts["eligible"], "held": counts["held"], "excluded": counts["excluded"],
               "complete_scoring_inputs": sum(site["score_inputs_complete"] for site in candidates),
               "observations_preserved": sum(len(review["site"]["observations"]) for review in reviews)}
    return {"sites": candidates}, {"summary": summary, "duplicates": merged, "opportunities": reviews}


def run(sites_path, extractions_path, log_path, output_path, review_path):
    import csv

    inputs = {sites_path.resolve(), extractions_path.resolve(), log_path.resolve()}
    outputs = {output_path.resolve(), review_path.resolve()}
    if inputs & outputs or len(outputs) != 2:
        raise ValueError("Output files must be distinct from each other and every input")
    raw = json.loads(sites_path.read_text(encoding="utf-8"))
    extracted = json.loads(extractions_path.read_text(encoding="utf-8"))
    if extracted.get("metadata", {}).get("input_sha256") != digest(sites_path):
        raise ValueError("Extraction input hash differs from sites.json; use the original matching input")
    with log_path.open(newline="", encoding="utf-8") as stream:
        logs = list(csv.DictReader(stream))
    scoring, review = normalize(raw["sites"], extracted, logs)
    metadata = {"schema_version": 1, "exported_at": raw.get("exported_at"), "country": raw.get("country"),
                "policy": POLICY, "inputs": {"sites_sha256": digest(sites_path),
                                             "extractions_sha256": digest(extractions_path),
                                             "fetch_log_sha256": digest(log_path)},
                "extraction_model": extracted["metadata"].get("model"),
                "summary": review["summary"]}
    for path, payload in ((output_path, {"metadata": metadata, **scoring}),
                          (review_path, {"metadata": metadata, **review})):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    return review["summary"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sites", type=Path, default=ROOT / "data/sites.json")
    parser.add_argument("--extractions", type=Path, default=ROOT / "output/extractions.json")
    parser.add_argument("--fetch-log", type=Path, default=ROOT / "data/fetch_log.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "data/sites.normalized.json")
    parser.add_argument("--review", type=Path, default=ROOT / "output/normalization_review.json")
    args = parser.parse_args()
    try:
        summary = run(args.sites, args.extractions, args.fetch_log, args.output, args.review)
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(1, f"Normalization failed: {exc}\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
