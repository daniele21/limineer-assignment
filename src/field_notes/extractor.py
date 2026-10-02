"""One Claude call, followed by deterministic checks of the evidence."""

import json
import math
import os
from pathlib import Path

from anthropic import Anthropic

from .schema import Extraction, ExtractionResult, Note

DEFAULT_MODEL = "claude-opus-5"
PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "field_notes" / "v1" / "system.md"
ALLOWED_VALUES = {
    "owner_status": {"loi_signed", "in_talks", "not_contacted", "refused", "unknown"},
    "sentiment": {"supportive", "neutral", "opposed", "conditional", "unknown"},
    "available_area": {"remaining_plot", "available_plot", "usable_installation_area"},
    "protected_overlap": {"overlap_reported", "no_overlap_reported", "uncertain_overlap"},
    "grid_headroom": {"headroom_reported"},
    "substation_distance": {"distance_reported"},
}
QUANTITY_UNITS = {
    "available_area": {"m2", "unknown"},
    "grid_headroom": {"MW", "kW", "unknown"},
    "substation_distance": {"km", "m", "unknown"},
}


def load_prompt(path: Path) -> str:
    """Use the system message, excluding draft metadata and the input example."""
    document = path.read_text(encoding="utf-8")
    if "## System message" in document:
        return document.split("## System message", 1)[1].split("## User-message template", 1)[0].strip()
    return document.strip()


def render_user_prompt(template: str, payload: dict) -> str:
    """Replace one explicit placeholder; source text is never a format template."""
    if template.count("{{input_json}}") != 1:
        raise ValueError("User prompt must contain exactly one {{input_json}} placeholder.")
    return template.replace("{{input_json}}", json.dumps(payload, ensure_ascii=False))


def validate_evidence(extraction: Extraction, notes: list[Note]) -> ExtractionResult:
    """Reject unsupported provenance. Quote matching cannot prove semantic truth."""
    by_id = {note.note_id: note for note in notes}
    accepted = []
    issues = []
    for index, observation in enumerate(extraction.observations):
        problems = []
        note = by_id.get(observation.note_id)
        if note is None:
            problems.append("unknown note_id")
        elif not observation.quote.strip() or observation.quote not in note.text:
            problems.append("quote is not an exact nonempty substring of the cited note")
        if not observation.value.strip() or not observation.scope.strip():
            problems.append("missing value or scope")
        allowed = ALLOWED_VALUES.get(observation.kind)
        if allowed is not None and observation.value not in allowed:
            problems.append("invalid value for this observation kind")
        if observation.event_time_text is not None:
            if not observation.event_time_text.strip() or observation.event_time_text not in observation.quote:
                problems.append("event_time_text must occur exactly within the quote")
        quantity = observation.quantity
        if quantity is not None:
            if not math.isfinite(quantity.value) or quantity.value < 0 or not quantity.subject.strip():
                problems.append("quantity must be finite, nonnegative and have a subject")
        units = QUANTITY_UNITS.get(observation.kind)
        if units is not None and (quantity is None or quantity.unit not in units):
            problems.append("numeric observation requires a quantity with appropriate units")
        if observation.kind == "sentiment" and observation.actor == "landowner":
            problems.append("landowner sentiment is not council/community sentiment")
        if problems:
            issues.append(f"observations[{index}] ({observation.kind}): rejected; {', '.join(problems)}")
        else:
            accepted.append(observation.model_copy(deep=True))
    return ExtractionResult(
        extraction=Extraction(opportunity_id=extraction.opportunity_id, observations=accepted),
        validation_issues=issues,
    )


def extract_notes(
    notes: list[Note],
    *,
    opportunity_id: str = "field_note",
    client: Anthropic | None = None,
    model: str | None = None,
    prompt_path: Path = PROMPT_PATH,
    system_prompt: str | None = None,
    user_prompt: str = "{{input_json}}",
    max_tokens: int = 8192,
    timeout_seconds: float = 120.0,
    max_retries: int = 2,
) -> ExtractionResult:
    if max_tokens <= 0:
        raise ValueError("max_tokens must be positive.")
    if len({note.note_id for note in notes}) != len(notes) or any(not note.note_id.strip() for note in notes):
        raise ValueError("Each note needs a unique, nonempty note_id.")
    if not notes or all(not note.text.strip() for note in notes):
        return ExtractionResult(
            extraction=Extraction(opportunity_id=opportunity_id, observations=[]),
            validation_issues=[],
        )
    payload = {
        "opportunity_id": opportunity_id,
        "notes": [note.model_dump(mode="json", exclude_none=True) for note in notes],
    }
    system = system_prompt if system_prompt is not None else load_prompt(prompt_path)
    if not system.strip():
        raise ValueError("System prompt must not be empty.")
    user = render_user_prompt(user_prompt, payload)
    owns_client = client is None
    client = client if client is not None else Anthropic(timeout=timeout_seconds, max_retries=max_retries)
    # Opus 5 thinks adaptively by default; no forced tools or disabled thinking.
    try:
        response = client.messages.parse(
            model=model or os.getenv("ANTHROPIC_MODEL") or DEFAULT_MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_format=Extraction,
        )
    finally:
        if owns_client:
            client.close()
    if response.stop_reason != "end_turn" or response.parsed_output is None:
        raise RuntimeError(f"Extraction did not complete (stop_reason={response.stop_reason}).")
    if response.parsed_output.opportunity_id != opportunity_id:
        raise RuntimeError("Response opportunity_id does not match the input.")
    return validate_evidence(response.parsed_output, notes)


def extract_field_note(field_note: str, **kwargs) -> ExtractionResult:
    """Convenience entry point for a single given text."""
    return extract_notes([Note(note_id="field_note:0", text=field_note)], **kwargs)
