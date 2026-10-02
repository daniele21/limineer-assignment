import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from field_notes.__main__ import preflight, run
from field_notes.config import load_config, resolve_model
from field_notes.extractor import render_user_prompt
from field_notes.schema import Extraction, ExtractionResult


class MainTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.config_path = self.folder / "config.toml"
        self.config_path.write_text('''
[model]
name = "claude-opus"
version = "5"
[prompt]
name = "test"
version = "v1"
system_file = "system.md"
user_file = "user.md"
[input]
sites_file = "sites.json"
site_ids = ["S-001"]
[output]
path = "new/output.json"
[api]
max_tokens = 2048
timeout_seconds = 30.0
max_retries = 0
''')
        (self.folder / "system.md").write_text("Only extract explicit evidence.")
        (self.folder / "user.md").write_text("Source data:\n{{input_json}}")
        (self.folder / "sites.json").write_text(json.dumps({"sites": [
            {"site_id": "S-001", "field_notes": [{"text": "Owner not contacted yet."}]},
            {"site_id": "S-002", "field_notes": []},
        ]}))

    def change_config(self, old, new):
        self.config_path.write_text(self.config_path.read_text().replace(old, new))

    def test_model_name_and_version_resolve_without_double_suffix(self):
        self.assertEqual(resolve_model("claude-opus", "5"), "claude-opus-5")
        self.assertEqual(resolve_model("claude-opus-5", "5"), "claude-opus-5")
        self.assertEqual(resolve_model("claude-opus-5", None), "claude-opus-5")
        with self.assertRaises(ValueError):
            resolve_model("claude-opus-5", "5.1")

    def test_user_template_keeps_source_braces_and_quotes_as_data(self):
        payload = {"text": 'Keep {{input_json}} and "quotes" unchanged.'}
        rendered = render_user_prompt("Read this:\n{{input_json}}", payload)
        self.assertEqual(json.loads(rendered.split("\n", 1)[1]), payload)
        for invalid in ("No placeholder", "{{input_json}}{{input_json}}"):
            with self.assertRaises(ValueError):
                render_user_prompt(invalid, payload)

    def test_paths_are_relative_to_config_not_working_directory(self):
        config = load_config(self.config_path)
        self.assertEqual(config.input.sites_file, self.folder.resolve() / "sites.json")
        self.assertEqual(config.prompt.system_file, self.folder.resolve() / "system.md")

    def test_dry_run_makes_no_api_calls_or_file_writes_without_credentials(self):
        with patch.dict(os.environ, {}, clear=True), patch("field_notes.extractor.Anthropic") as client, patch("field_notes.__main__.extract_notes") as extract:
            result = run(self.config_path, dry_run=True)
        self.assertEqual(result["status"], "preflight_passed")
        self.assertEqual(result["expected_api_calls"], 1)
        self.assertFalse(result["api_key_configured"])
        self.assertEqual(result["authentication"], "not_checked")
        self.assertFalse((self.folder / "new").exists())
        extract.assert_not_called()
        client.assert_not_called()

    def test_run_passes_config_and_records_provenance(self):
        extracted = ExtractionResult(extraction=Extraction(opportunity_id="S-001", observations=[]), validation_issues=[])
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "offline-test-key"}), patch("field_notes.__main__.extract_notes", return_value=extracted) as extract:
            output = run(self.config_path)
        extract.assert_called_once()
        options = extract.call_args.kwargs
        self.assertEqual(options["model"], "claude-opus-5")
        self.assertEqual(options["system_prompt"], "Only extract explicit evidence.")
        self.assertEqual(options["user_prompt"], "Source data:\n{{input_json}}")
        self.assertEqual(options["max_tokens"], 2048)
        self.assertEqual(options["timeout_seconds"], 30.0)
        self.assertEqual(options["max_retries"], 0)
        self.assertEqual(extract.call_args.args[0][0].note_id, "S-001:0")
        self.assertEqual(output["metadata"]["selected_site_ids"], ["S-001"])
        self.assertEqual(len(output["metadata"]["config_sha256"]), 64)
        self.assertEqual(json.loads((self.folder / "new/output.json").read_text()), output)

    def test_invalid_template_fails_before_api(self):
        (self.folder / "user.md").write_text("No data placeholder.")
        with patch("field_notes.__main__.extract_notes") as extract:
            with self.assertRaisesRegex(ValueError, "placeholder"):
                run(self.config_path)
            extract.assert_not_called()

    def test_unknown_config_key_and_invalid_limits_fail(self):
        self.change_config('max_tokens = 2048', 'max_tokens = 0')
        with self.assertRaisesRegex(ValueError, "api.max_tokens"):
            load_config(self.config_path)
        self.change_config('max_tokens = 0', 'max_tokens = 2048\nmax_token = 2048')
        with self.assertRaisesRegex(ValueError, "api.max_token"):
            load_config(self.config_path)

    def test_unknown_site_and_duplicate_site_fail(self):
        self.change_config('site_ids = ["S-001"]', 'site_ids = ["missing"]')
        with self.assertRaisesRegex(ValueError, "Unknown site"):
            preflight(self.config_path)
        self.change_config('site_ids = ["missing"]', 'site_ids = []')
        sites = self.folder / "sites.json"
        sites.write_text(sites.read_text().replace("S-002", "S-001"))
        with self.assertRaisesRegex(ValueError, "Duplicate site_id"):
            preflight(self.config_path)

    def test_all_notes_are_validated_before_any_api_call(self):
        sites = self.folder / "sites.json"
        data = json.loads(sites.read_text())
        data["sites"][1]["field_notes"] = [{"text": None}]
        sites.write_text(json.dumps(data))
        with patch("field_notes.__main__.extract_notes") as extract:
            with self.assertRaises(ValueError):
                run(self.config_path)
            extract.assert_not_called()

    def test_output_cannot_overwrite_input(self):
        self.change_config('path = "new/output.json"', 'path = "sites.json"')
        with self.assertRaisesRegex(ValueError, "distinct"):
            preflight(self.config_path)

    def test_missing_credentials_fail_before_extraction(self):
        with patch.dict(os.environ, {}, clear=True), patch("field_notes.__main__.extract_notes") as extract:
            with self.assertRaisesRegex(ValueError, "ANTHROPIC_API_KEY is missing"):
                run(self.config_path)
            extract.assert_not_called()

    def test_empty_site_does_not_need_api_credentials(self):
        self.change_config('site_ids = ["S-001"]', 'site_ids = ["S-002"]')
        with patch.dict(os.environ, {}, clear=True):
            output = run(self.config_path)
        self.assertEqual(output["metadata"]["expected_api_calls"], 0)
        self.assertEqual(output["results"][0]["extraction"]["observations"], [])


if __name__ == "__main__":
    unittest.main()
