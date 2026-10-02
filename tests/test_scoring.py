"""Regression tests for question-driven scoring, without saved live output."""

from copy import deepcopy
import unittest

from field_notes.normalize import normalize
from field_notes.scoring import build_dataset, build_variants, evaluate, PRESETS, profile_id, tier


def raw_site(sid="S-001"):
    return {"site_id": sid, "name": "Test yard", "region": "Aldmark", "site_type": "depot_yard",
            "parcel_id": sid, "grid_ref_km": {"x": 1, "y": 2},
            "sources": {"gridmap": {"headroom": 4.6, "substation_distance_km": 0.8, "data_as_of": "2026-06-30"},
                        "landreg": {"area_m2": 2100, "flood_zone": "low", "protected_area": False, "record_date": "2025-11-03"},
                        "vendor_estimate": None},
            "field_notes": [{"date": "2026-09-01", "author": "JK", "text": "Owner signed LOI.", "owner_status": "loi_signed"},
                            {"date": "2026-09-01", "author": "JK", "text": "Council supports storage."}]}


def inputs(sites, sentiment_value="supportive"):
    results = []
    for site in sites:
        notes, observations = [], []
        for index, note in enumerate(site["field_notes"]):
            nid = f"{site['site_id']}:{index}"
            notes.append({"note_id": nid, "date": note["date"], "author": note["author"], "text": note["text"], "source_site_id": site["site_id"]})
            owner = note.get("owner_status")
            observations.append({"kind": "owner_status" if owner else "sentiment", "value": owner or sentiment_value,
                                 "actor": "landowner" if owner else "council_body", "scope": "this site",
                                 "statement_status": "asserted", "evidence_basis": "reported_conversation", "quantity": None,
                                 "event_time_text": None, "note_id": nid, "quote": note["text"]})
        results.append({"site_id": site["site_id"], "field_notes": notes, "extraction": {"opportunity_id": site["site_id"], "observations": observations}, "validation_issues": []})
    clean, audit = normalize(sites, {"results": results}, [])
    metadata = {"inputs": {"fixture": True}, "country": "Fictional", "exported_at": "2026-09-21"}
    clean["metadata"] = deepcopy(metadata)
    audit["metadata"] = deepcopy(metadata)
    return clean, audit


class ScoringTests(unittest.TestCase):
    def test_exact_and_adjacent_thresholds(self):
        cases = {
            "headroom_mw": [(0, 0), (0.999, 0), (1, 1), (1.999, 1), (2, 3), (3.999, 3), (4, 5), (5.5, 5)],
            "substation_distance_km": [(0, 5), (1, 5), (1.001, 3), (3, 3), (3.001, 1), (6, 1), (6.001, 0)],
            "usable_area_m2": [(799, 0), (800, 2), (1199, 2), (1200, 5)],
        }
        for field, pairs in cases.items():
            for value, expected in pairs:
                with self.subTest(field=field, value=value):
                    self.assertEqual(tier(field, value), expected)
        self.assertIsNone(tier("headroom_mw", None))

    def test_invalid_values_and_answers_fail(self):
        for value in (True, -1, float("nan"), float("inf"), "4"):
            with self.assertRaises(ValueError):
                tier("headroom_mw", value)
        with self.assertRaises(ValueError):
            tier("owner_status", "signed_contract")
        with self.assertRaises(ValueError):
            profile_id({"grid": "official"})
        with self.assertRaises(ValueError):
            profile_id({**PRESETS["conservative"], "grid": "largest_number"})

    def test_twenty_four_complete_profiles_and_unchanged_evidence(self):
        clean, audit = inputs([raw_site()])
        snapshot = deepcopy((clean, audit))
        dataset = build_dataset(clean, audit)
        self.assertEqual(len(dataset["profiles"]), 24)
        self.assertEqual(len({p["id"] for p in dataset["profiles"]}), 24)
        self.assertEqual(len(dataset["sites"][0]["scores"]), 24)
        self.assertEqual((clean, audit), snapshot)
        for result in dataset["sites"][0]["scores"].values():
            self.assertEqual(result["score"], 97)
            self.assertEqual(result["rank"], 1)

    def test_grid_choice_only_uses_allowed_vendor_alternatives(self):
        site = raw_site()
        site["sources"]["gridmap"].update(headroom=1.6, data_as_of="2026-03-31")
        site["sources"]["vendor_estimate"] = {"headroom_mw_est": 5.2, "band_pct": 40, "estimated_at": "2026-09-15"}
        clean, audit = inputs([site])
        dataset = build_dataset(clean, audit)
        scores = dataset["sites"][0]["scores"]
        # Fixture has low flood; all other facts are unchanged.
        self.assertEqual(scores[profile_id(PRESETS["conservative"])]["score"], 73)
        upside = scores[profile_id(PRESETS["potential"])]
        self.assertEqual(upside["score"], 97)
        self.assertEqual(upside["score_kind"], "hypothetical")
        self.assertEqual(upside["components"]["headroom_mw"], "vendor_upper")
        site["sources"]["gridmap"]["data_as_of"] = "2026-06-30"
        clean, audit = inputs([site])
        dataset = build_dataset(clean, audit)
        self.assertNotIn("vendor_upper", dataset["sites"][0]["criterion_variants"]["headroom_mw"])
        self.assertEqual(dataset["sites"][0]["scores"][profile_id(PRESETS["potential"])]["score"], 73)
        site["sources"]["gridmap"]["data_as_of"] = "2026-03-31"
        site["sources"]["vendor_estimate"]["estimated_at"] = "2026-01-01"
        clean, audit = inputs([site])
        self.assertNotIn("vendor_upper", build_dataset(clean, audit)["sites"][0]["criterion_variants"]["headroom_mw"])

    def test_grid_central_and_upper_can_have_different_tiers(self):
        site = raw_site()
        site["sources"]["gridmap"] = None
        site["sources"]["vendor_estimate"] = {"headroom_mw_est": 3.4, "band_pct": 40, "estimated_at": "2026-09-15"}
        clean, audit = inputs([site])
        dataset = build_dataset(clean, audit)
        scores = dataset["sites"][0]["scores"]
        self.assertEqual(scores[profile_id(PRESETS["conservative"])]["status"], "held")
        central = {**PRESETS["potential"], "grid": "vendor_central"}
        self.assertEqual(scores[profile_id(central)]["score"], 85)
        self.assertEqual(scores[profile_id(PRESETS["potential"])]["score"], 97)
        self.assertEqual(scores[profile_id(PRESETS["potential"])]["status"], "conditional")
        official_only = {**PRESETS["potential"], "grid": "official"}
        self.assertEqual(scores[profile_id(official_only)]["status"], "held")
        self.assertIsNone(scores[profile_id(official_only)]["score"])
        self.assertNotIn("best_case", dataset["sites"][0]["criterion_variants"]["headroom_mw"])

    def test_sentiment_choice_does_not_fill_other_gaps(self):
        site = raw_site()
        site["field_notes"] = site["field_notes"][:1]
        clean, audit = inputs([site])
        dataset = build_dataset(clean, audit)
        scores = dataset["sites"][0]["scores"]
        default = scores[profile_id(PRESETS["conservative"])]
        self.assertEqual(default["score"], 87)
        self.assertEqual(default["score_kind"], "partial_lower")
        support = scores[profile_id({**PRESETS["conservative"], "sentiment": "assume_support"})]
        self.assertEqual(support["score"], 97)
        self.assertTrue(support["conditions"])
        self.assertIsNone(dataset["sites"][0]["observed_inputs"]["community_sentiment"])

    def test_exclusions_cannot_be_overridden_by_any_answer(self):
        protected, refused = raw_site(), raw_site("S-002")
        protected["sources"]["landreg"]["protected_area"] = True
        refused["field_notes"][0]["owner_status"] = "refused"
        clean, audit = inputs([protected, refused])
        dataset = build_dataset(clean, audit)
        for site in dataset["sites"]:
            for row in site["scores"].values():
                self.assertEqual(row["status"], "excluded")
                self.assertIsNone(row["score"])
                self.assertNotIn("rank", row)

    def test_unknown_critical_evidence_is_conditional_not_confirmed(self):
        site = raw_site()
        site["sources"]["landreg"] = None
        clean, audit = inputs([site])
        dataset = build_dataset(clean, audit)
        scores = dataset["sites"][0]["scores"]
        self.assertIsNone(scores[profile_id(PRESETS["conservative"])]["score"])
        upside = scores[profile_id(PRESETS["potential"])]
        self.assertEqual(upside["status"], "conditional")
        self.assertEqual(upside["score"], 100)
        self.assertTrue(any("protected" in c for c in upside["conditions"]))

    def test_area_conflict_cannot_be_filled_with_generic_best_case(self):
        clean, audit = inputs([raw_site()])
        review = audit["opportunities"][0]
        review["site"]["scoring_inputs"]["usable_area_m2"] = None
        review["eligibility"] = {"status": "held", "reasons": ["available_area_requires_verification"]}
        review["site"]["input_evidence"]["usable_area_m2"]["field_note_area_observations"] = [{"date": "2026-09-01", "quantity": {"value": 700, "unit": "m2", "precision": "approximate"}}]
        variants = build_variants(review)
        self.assertNotIn("best_case", variants["usable_area_m2"])
        held = evaluate(review, variants, {**PRESETS["potential"], "conflicts": "hold"})
        self.assertIsNone(held["score"])
        upside = evaluate(review, variants, PRESETS["potential"])
        self.assertEqual(upside["status"], "conditional")
        self.assertEqual(upside["score"], 87)
        self.assertEqual(variants["usable_area_m2"]["remaining_plot"]["contribution"], 0)

    def test_protection_conflict_is_an_independent_question(self):
        clean, audit = inputs([raw_site()])
        review = audit["opportunities"][0]
        review["eligibility"] = {"status": "held", "reasons": ["unresolved_protection_overlap"]}
        review["protection_check"]["overlap_observations"] = [{"value": "overlap_reported"}]
        variants = build_variants(review)
        self.assertIsNone(evaluate(review, variants, {**PRESETS["potential"], "conflicts": "hold"})["score"])
        row = evaluate(review, variants, {**PRESETS["conservative"], "conflicts": "conditional"})
        self.assertEqual(row["status"], "conditional")
        self.assertTrue(row["conditions"])

    def test_known_negative_distance_result_cannot_be_improved(self):
        clean, audit = inputs([raw_site()])
        review = audit["opportunities"][0]
        review["site"]["scoring_inputs"]["substation_distance_km"] = None
        review["site"]["input_evidence"]["substation_distance_km"]["status"] = "no_substation_within_10_km"
        row = evaluate(review, build_variants(review), PRESETS["potential"])
        self.assertEqual(row["components"]["substation_distance_km"], "baseline")
        self.assertEqual(row["score"], 82)

    def test_equal_scores_keep_equal_ranks(self):
        clean, audit = inputs([raw_site(), raw_site("S-002")])
        dataset = build_dataset(clean, audit)
        default = dataset["default_profile_id"]
        self.assertEqual([site["scores"][default]["rank"] for site in dataset["sites"]], [1, 1])

    def test_known_opposition_flood_and_owner_negotiations_stay_unchanged(self):
        site = raw_site()
        site["sources"]["gridmap"]["headroom"] = 2
        site["sources"]["landreg"].update(area_m2=900, flood_zone="high")
        site["field_notes"][0].update(text="Owner is negotiating.", owner_status="in_talks")
        site["field_notes"][1]["text"] = "Council opposes storage."
        clean, audit = inputs([site], sentiment_value="opposed")
        dataset = build_dataset(clean, audit)
        for row in dataset["sites"][0]["scores"].values():
            self.assertEqual(row["score"], 49)
            self.assertEqual(row["status"], "eligible")
            self.assertEqual(row["score_kind"], "complete_rubric")

    def test_mismatched_normalized_inputs_fail(self):
        clean, audit = inputs([raw_site()])
        clean["sites"] = []
        with self.assertRaises(ValueError):
            build_dataset(clean, audit)


if __name__ == "__main__":
    unittest.main()
