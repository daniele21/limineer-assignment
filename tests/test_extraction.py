import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

import httpx2
from anthropic import Anthropic

from field_notes.extractor import extract_field_note, extract_notes, load_prompt, PROMPT_PATH, validate_evidence
from field_notes.schema import Extraction, Note, Observation, Quantity


class ExtractionTests(unittest.TestCase):
    def setUp(self):
        self.notes = [Note(note_id="S-003:0", text="Owner signed the letter of intent. Wants 12% revenue share.")]
        self.observation = Observation(
            kind="owner_status", value="loi_signed", actor="landowner",
            scope="landowner lease negotiations", statement_status="asserted",
            evidence_basis="unspecified", quantity=None, event_time_text=None,
            note_id="S-003:0", quote="Owner signed the letter of intent.",
        )
        self.extraction = Extraction(opportunity_id="S-003", observations=[self.observation])

    def test_exact_quote_is_accepted(self):
        result = validate_evidence(self.extraction, self.notes)
        self.assertEqual(result.extraction.observations[0].value, "loi_signed")
        self.assertEqual(result.validation_issues, [])

    def test_invented_quote_is_rejected_without_modifying_original(self):
        self.observation.quote = "Owner signed a lease."
        result = validate_evidence(self.extraction, self.notes)
        self.assertEqual(result.extraction.observations, [])
        self.assertTrue(result.validation_issues)
        self.assertEqual(len(self.extraction.observations), 1)

    def test_wrong_note_and_blank_quote_are_rejected(self):
        for note_id, quote in (("missing", self.observation.quote), ("S-003:0", " ")):
            with self.subTest(note_id=note_id, quote=quote):
                self.observation.note_id, self.observation.quote = note_id, quote
                self.assertEqual(validate_evidence(self.extraction, self.notes).extraction.observations, [])

    def test_owner_sentiment_cannot_be_community_sentiment(self):
        self.observation.kind, self.observation.value = "sentiment", "supportive"
        self.assertEqual(validate_evidence(self.extraction, self.notes).extraction.observations, [])

    def test_value_and_event_time_follow_contract(self):
        self.observation.value = "signed_lease"
        self.assertTrue(validate_evidence(self.extraction, self.notes).validation_issues)
        self.observation.value, self.observation.event_time_text = "loi_signed", "last year"
        self.assertTrue(validate_evidence(self.extraction, self.notes).validation_issues)

    def test_invalid_numeric_quantities_are_rejected(self):
        self.observation.kind, self.observation.value = "available_area", "remaining_plot"
        for quantity in (None, Quantity(value=-1, unit="m2", precision="as_stated", subject="plot"),
                         Quantity(value=float("inf"), unit="m2", precision="as_stated", subject="plot"),
                         Quantity(value=700, unit="MW", precision="as_stated", subject="plot")):
            with self.subTest(quantity=quantity):
                self.observation.quantity = quantity
                self.assertTrue(validate_evidence(self.extraction, self.notes).validation_issues)

    def test_qualified_claim_is_preserved_as_qualified(self):
        self.notes[0].text = "Plot might overlap the reserve; needs checking."
        self.observation.kind, self.observation.value = "protected_overlap", "uncertain_overlap"
        self.observation.statement_status = "qualified"
        self.observation.quote = self.notes[0].text
        result = validate_evidence(self.extraction, self.notes)
        self.assertEqual(result.extraction.observations[0].statement_status, "qualified")

    def test_unmeasured_usable_area_is_a_condition_not_a_numeric_area(self):
        self.notes[0].text = "Roughly 700 m² of plot remains. Usable installation area has not been measured."
        remaining = self.observation.model_copy(update={
            "kind": "available_area", "value": "remaining_plot", "actor": "author",
            "scope": "remaining plot area", "quote": "Roughly 700 m² of plot remains.",
            "quantity": Quantity(value=700, unit="m2", precision="approximate", subject="remaining plot area"),
        })
        condition = self.observation.model_copy(update={
            "kind": "site_condition", "value": "Usable installation area has not been measured.",
            "actor": "author", "scope": "usable installation area",
            "quote": "Usable installation area has not been measured.",
        })
        invalid_area = condition.model_copy(update={"kind": "available_area", "value": "usable_installation_area"})
        result = validate_evidence(
            Extraction(opportunity_id="S-003", observations=[remaining, invalid_area, condition]), self.notes,
        )
        self.assertEqual(result.extraction.observations, [remaining, condition])
        self.assertEqual(len(result.validation_issues), 1)
        self.assertIn("numeric observation requires a quantity", result.validation_issues[0])

    def test_empty_notes_skip_api_and_make_no_claims(self):
        client = Mock()
        result = extract_notes([], client=client)
        self.assertEqual(result.extraction.observations, [])
        client.messages.parse.assert_not_called()

    def test_api_receives_stable_ids_and_structured_output(self):
        client = Mock()
        self.extraction.opportunity_id = "field_note"
        self.observation.note_id = "field_note:0"
        client.messages.parse.return_value = SimpleNamespace(stop_reason="end_turn", parsed_output=self.extraction)
        result = extract_field_note(self.notes[0].text, client=client, model="claude-opus-5")
        call = client.messages.parse.call_args.kwargs
        self.assertEqual(call["model"], "claude-opus-5")
        payload = json.loads(call["messages"][0]["content"])
        self.assertEqual(payload["notes"][0]["note_id"], "field_note:0")
        self.assertEqual(result.validation_issues, [])

    def test_separate_system_and_user_prompts_reach_sdk(self):
        client = Mock()
        self.extraction.opportunity_id = "field_note"
        self.observation.note_id = "field_note:0"
        client.messages.parse.return_value = SimpleNamespace(stop_reason="end_turn", parsed_output=self.extraction)
        extract_field_note(
            self.notes[0].text, client=client, system_prompt="Only extract evidence.",
            user_prompt="Source data:\n{{input_json}}", max_tokens=2048,
        )
        request = client.messages.parse.call_args.kwargs
        self.assertEqual(request["system"], "Only extract evidence.")
        self.assertTrue(request["messages"][0]["content"].startswith("Source data:\n"))
        self.assertEqual(request["max_tokens"], 2048)

    def test_incomplete_refused_and_wrong_opportunity_responses_fail(self):
        for stop_reason, output in (("max_tokens", self.extraction), ("refusal", None),
                                    ("end_turn", None), ("end_turn", self.extraction)):
            with self.subTest(stop_reason=stop_reason, output=output):
                client = Mock()
                client.messages.parse.return_value = SimpleNamespace(stop_reason=stop_reason, parsed_output=output)
                with self.assertRaises(RuntimeError):
                    extract_notes(self.notes, client=client, opportunity_id="different")

    def test_duplicate_note_ids_fail_before_api(self):
        client = Mock()
        with self.assertRaises(ValueError):
            extract_notes(self.notes * 2, client=client)
        client.messages.parse.assert_not_called()

    def test_prompt_loader_uses_system_section_only(self):
        prompt = load_prompt(PROMPT_PATH)
        self.assertTrue(prompt.startswith("You extract evidence"))
        self.assertNotIn("## User-message template", prompt)

    def test_actual_sdk_serializes_and_parses_with_an_offline_transport(self):
        self.extraction.opportunity_id = "field_note"
        self.observation.note_id = "field_note:0"
        requests = []

        def respond(request):
            requests.append(json.loads(request.content))
            return httpx2.Response(200, json={
                "id": "offline-message", "type": "message", "role": "assistant",
                "model": "claude-opus-5", "stop_reason": "end_turn", "stop_sequence": None,
                "usage": {"input_tokens": 1, "output_tokens": 1},
                "content": [{"type": "text", "text": self.extraction.model_dump_json()}],
            })

        with Anthropic(api_key="offline-test-key", max_retries=0,
                       http_client=httpx2.Client(transport=httpx2.MockTransport(respond))) as client:
            result = extract_field_note(self.notes[0].text, client=client,
                                        model="claude-opus-5", system_prompt="Use exact evidence.")
        self.assertEqual(result.extraction.observations[0].value, "loi_signed")
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0]["system"], "Use exact evidence.")
        self.assertEqual(requests[0]["output_config"]["format"]["type"], "json_schema")


if __name__ == "__main__":
    unittest.main()
