"""Offline regressions for eligibility, evidence reconciliation and unit safety."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from field_notes.normalize import normalize, run


def site(sid="S-001", *, region="Aldmark", parcel="AL-1"):
    return {
        "site_id": sid, "name": "Test depot", "region": region,
        "site_type": "depot_yard", "parcel_id": parcel, "grid_ref_km": {"x": 1, "y": 2},
        "sources": {
            "gridmap": {"headroom": 2.2, "substation_distance_km": 1, "data_as_of": "2026-06-30"},
            "landreg": {"area_m2": 1500, "flood_zone": "low", "protected_area": False, "record_date": "2025-11-03"},
            "vendor_estimate": {"headroom_mw_est": 5.2, "band_pct": 40},
        },
        "field_notes": [
            {"date": "2026-08-01", "author": "JK", "text": "Negotiating lease.", "owner_status": "in_talks"},
            {"date": "2026-08-02", "author": "JK", "text": "Neighbours indifferent."},
        ],
    }


def extraction(sites):
    results = []
    for item in sites:
        notes, observations = [], []
        sid = item["site_id"]
        for i, note in enumerate(item["field_notes"]):
            nid = f"{sid}:{i}"
            notes.append({"note_id": nid, "date": note["date"], "author": note["author"],
                          "text": note["text"], "source_site_id": sid})
            if note.get("owner_status"):
                kind, value, actor = "owner_status", note["owner_status"], "landowner"
            else:
                kind, value, actor = "sentiment", "neutral", "residents"
            observations.append({"kind": kind, "value": value, "actor": actor,
                                 "scope": "local position", "statement_status": "asserted",
                                 "evidence_basis": "reported_conversation", "quantity": None,
                                 "event_time_text": None, "note_id": nid, "quote": note["text"]})
        results.append({"site_id": sid, "field_notes": notes,
                        "extraction": {"opportunity_id": sid, "observations": observations},
                        "validation_issues": []})
    return {"results": results}


class NormalizationTests(unittest.TestCase):
    def test_units_official_precedence_and_input_immutability(self):
        original = site(region="Nordholm", parcel="NH-1")
        original["sources"]["gridmap"]["headroom"] = 2200
        snapshot = deepcopy(original)
        candidates, review = normalize([original], extraction([original]), [])
        candidate = candidates["sites"][0]
        self.assertEqual(candidate["scoring_inputs"]["headroom_mw"], 2.2)
        self.assertEqual(candidate["input_evidence"]["headroom_mw"]["raw_unit"], "kW")
        self.assertNotIn("headroom", candidate["normalized_sources"]["gridmap"])
        self.assertNotIn("protected_area", candidate["scoring_inputs"])
        self.assertNotIn("protected_area", candidate["normalized_sources"]["landreg"])
        self.assertEqual(original, snapshot)
        self.assertEqual(review["summary"]["eligible"], 1)

    def test_vendor_does_not_rescue_timeout_or_invent_distance(self):
        item = site()
        item["sources"]["gridmap"] = None
        logs = [{"site_id": "S-001", "source": "gridmap", "timestamp": "2026-09-02", "http_status": "503", "message": "upstream timeout"}]
        candidates, review = normalize([item], extraction([item]), logs)
        self.assertEqual(candidates["sites"], [])
        record = review["opportunities"][0]
        self.assertEqual(record["eligibility"]["status"], "held")
        self.assertIsNone(record["site"]["scoring_inputs"]["headroom_mw"])
        self.assertEqual(record["site"]["input_evidence"]["substation_distance_km"]["status"], "upstream_timeout")
        self.assertEqual(record["site"]["normalized_sources"]["vendor_estimate"]["headroom_mw_est"], 5.2)
        logs[0].update(http_status="200", message="no substation within search radius (10 km)")
        _, review = normalize([item], extraction([item]), logs)
        evidence = review["opportunities"][0]["site"]["input_evidence"]["substation_distance_km"]
        self.assertEqual(evidence["lower_bound_km_exclusive"], 10)
        self.assertEqual(evidence["status"], "no_substation_within_10_km")

    def test_protected_and_unknown_protection_are_distinct(self):
        for protection, expected in ((True, "excluded"), (None, "held")):
            with self.subTest(protection=protection):
                item = site()
                item["sources"]["landreg"]["protected_area"] = protection
                candidates, review = normalize([item], extraction([item]), [])
                self.assertEqual(candidates["sites"], [])
                self.assertEqual(review["opportunities"][0]["eligibility"]["status"], expected)

    def test_duplicate_combines_later_loi_and_earlier_sentiment(self):
        first, second = site(), site("S-002")
        second["grid_ref_km"]["x"] += 0.03
        second["field_notes"] = [{"date": "2026-09-08", "author": "AV", "text": "LOI signed.", "owner_status": "loi_signed"}]
        candidates, review = normalize([second, first], extraction([second, first]), [])
        self.assertEqual(len(candidates["sites"]), 1)
        candidate = candidates["sites"][0]
        self.assertEqual(candidate["site_id"], "S-001")
        self.assertEqual(candidate["source_site_ids"], ["S-001", "S-002"])
        self.assertEqual(candidate["scoring_inputs"]["owner_status"], "loi_signed")
        self.assertEqual(candidate["scoring_inputs"]["community_sentiment"], "neutral")
        self.assertEqual(review["summary"]["observations_preserved"], 3)
        second["sources"]["landreg"]["area_m2"] = 1700
        with self.assertRaisesRegex(ValueError, "conflicting entity"):
            normalize([first, second], extraction([first, second]), [])

    def test_owner_refusal_uses_date_not_array_order(self):
        item = site()
        item["field_notes"] = [
            {"date": "2026-06-02", "author": "JK", "text": "Not contacted.", "owner_status": "not_contacted"},
            {"date": "2026-09-05", "author": "JK", "text": "Owner refused.", "owner_status": "refused"},
            {"date": "2026-07-20", "author": "JK", "text": "In talks.", "owner_status": "in_talks"},
        ]
        candidates, review = normalize([item], extraction([item]), [])
        self.assertEqual(candidates["sites"], [])
        record = review["opportunities"][0]
        self.assertEqual(record["site"]["scoring_inputs"]["owner_status"], "refused")
        self.assertEqual(record["eligibility"]["reasons"], ["owner_refused"])

    def test_same_day_owner_conflict_is_unknown(self):
        item = site()
        item["field_notes"].append({"date": "2026-08-01", "author": "AV", "text": "Refused.", "owner_status": "refused"})
        _, review = normalize([item], extraction([item]), [])
        record = review["opportunities"][0]
        self.assertIsNone(record["site"]["scoring_inputs"]["owner_status"])
        self.assertIn("unknown_owner_status", record["eligibility"]["reasons"])

    def test_conditional_and_absent_sentiment_never_become_neutral(self):
        item = site()
        extracted = extraction([item])
        observation = extracted["results"][0]["extraction"]["observations"][1]
        observation.update(value="conditional", statement_status="qualified")
        for remove in (False, True):
            if remove:
                extracted["results"][0]["extraction"]["observations"].pop()
            candidates, _ = normalize([item], extracted, [])
            candidate = candidates["sites"][0]
            self.assertIsNone(candidate["scoring_inputs"]["community_sentiment"])
            self.assertFalse(candidate["score_inputs_complete"])

    def test_critical_note_conflicts_hold_without_promoting_quantity(self):
        for kind, value, quantity in (
            ("protected_overlap", "overlap_reported", None),
            ("available_area", "remaining_plot", {"value": 700.0, "unit": "m2", "precision": "approximate", "subject": "remaining plot"}),
        ):
            with self.subTest(kind=kind):
                item = site()
                item["field_notes"][1]["text"] = "Reserve overlap needs checking; roughly 700 m² remains."
                extracted = extraction([item])
                obs = extracted["results"][0]["extraction"]["observations"][1]
                obs.update(kind=kind, value=value, actor="author", statement_status="qualified", quantity=quantity)
                candidates, review = normalize([item], extracted, [])
                self.assertEqual(candidates["sites"], [])
                self.assertEqual(review["opportunities"][0]["eligibility"]["status"], "held")
                if kind == "available_area":
                    self.assertIsNone(review["opportunities"][0]["site"]["scoring_inputs"]["usable_area_m2"])
                    self.assertEqual(review["opportunities"][0]["site"]["observations"][1]["normalized_quantity"]["value"], 700)

    def test_low_headroom_flood_and_opposition_do_not_add_kill_rules(self):
        item = site()
        item["sources"]["gridmap"]["headroom"] = 0.95
        item["sources"]["landreg"]["flood_zone"] = "high"
        extracted = extraction([item])
        extracted["results"][0]["extraction"]["observations"][1]["value"] = "opposed"
        candidates, _ = normalize([item], extracted, [])
        self.assertEqual(len(candidates["sites"]), 1)
        self.assertEqual(candidates["sites"][0]["scoring_inputs"]["community_sentiment"], "opposed")

    def test_bad_quote_mismatched_notes_and_missing_extractions_fail(self):
        item = site()
        for error in ("quote", "notes", "missing"):
            with self.subTest(error=error):
                extracted = extraction([item])
                if error == "quote":
                    extracted["results"][0]["extraction"]["observations"][0]["quote"] = "Made up."
                elif error == "notes":
                    extracted["results"][0]["field_notes"][0]["date"] = "2026-01-01"
                else:
                    extracted["results"] = []
                with self.assertRaises(ValueError):
                    normalize([item], extracted, [])

    def test_run_checks_hash_and_protects_inputs_before_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = [root / name for name in ("sites.json", "extractions.json", "log.csv", "clean.json", "review.json")]
            item = site()
            paths[0].write_text(json.dumps({"sites": [item]}))
            extracted = extraction([item])
            extracted["metadata"] = {"input_sha256": "wrong", "model": "offline_fixture"}
            paths[1].write_text(json.dumps(extracted))
            paths[2].write_text("timestamp,site_id,source,http_status,message\n")
            with self.assertRaisesRegex(ValueError, "hash differs"):
                run(*paths)
            self.assertFalse(paths[3].exists())
            extracted["metadata"]["input_sha256"] = hashlib.sha256(paths[0].read_bytes()).hexdigest()
            paths[1].write_text(json.dumps(extracted))
            self.assertEqual(run(*paths)["eligible"], 1)
            self.assertEqual(len(json.loads(paths[3].read_text())["sites"]), 1)
            with self.assertRaisesRegex(ValueError, "distinct"):
                run(*paths[:3], paths[0], paths[4])


if __name__ == "__main__":
    unittest.main()
