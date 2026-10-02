import copy
import json
from pathlib import Path
import unittest

from scripts.test_live_sample import check_sample


class SampleCheckTests(unittest.TestCase):
    def setUp(self):
        self.expected = json.loads((Path(__file__).parent / "fixtures/artificial_expected.json").read_text())
        observations = copy.deepcopy(self.expected["required_observations"])
        for item in observations:
            item["statement_status"] = "asserted"
            if item["kind"] == "commercial_term":
                item["value"] = "Owner requests 12% revenue share."
        self.output = {"results": [{"site_id": "ART-001", "validation_issues": [], "extraction": {"observations": observations}}]}

    def test_expected_sample_passes_checker(self):
        self.assertTrue(all(item["passed"] for item in check_sample(self.output, self.expected)))

    def test_missing_owner_history_fails_checker(self):
        self.output["results"][0]["extraction"]["observations"].pop(1)
        self.assertFalse(all(item["passed"] for item in check_sample(self.output, self.expected)))

    def test_invented_grid_quantity_fails_checker(self):
        self.output["results"][0]["extraction"]["observations"].append({"kind": "grid_headroom", "value": "headroom_reported"})
        self.assertFalse(all(item["passed"] for item in check_sample(self.output, self.expected)))

    def test_reported_validation_issue_fails_checker(self):
        self.output["results"][0]["validation_issues"] = ["Rejected fabricated quote."]
        checks = check_sample(self.output, self.expected)
        self.assertFalse(all(item["passed"] for item in checks))
        evidence_check = next(item for item in checks if item["name"] == "no evidence validation issues")
        self.assertFalse(evidence_check["passed"])
        self.assertEqual(evidence_check["details"], ["Rejected fabricated quote."])


if __name__ == "__main__":
    unittest.main()
