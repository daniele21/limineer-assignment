"""Typed contract for prompts/extract_field_notes.md; no scoring or state selection."""

from datetime import date as Date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Kind = Literal[
    "owner_status", "sentiment", "available_area", "protected_overlap",
    "owner_identity", "commercial_term", "follow_up", "site_condition",
    "grid_headroom", "substation_distance", "flood_observation",
]


class Note(BaseModel):
    note_id: str
    text: str
    date: Date | None = None
    author: str | None = None
    source_site_id: str | None = None


class OutputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Quantity(OutputModel):
    value: float
    unit: Literal["m2", "MW", "kW", "km", "m", "percent", "unknown"]
    precision: Literal["as_stated", "approximate"]
    subject: str


class Observation(OutputModel):
    kind: Kind
    value: str = Field(description="Only the meaning explicitly supported by the quote.")
    actor: Literal[
        "landowner", "council_body", "councillor", "council_officer", "community_group",
        "residents", "ecologist", "author", "unknown",
    ]
    scope: str
    statement_status: Literal["asserted", "qualified", "unclear"]
    evidence_basis: Literal[
        "reported_document", "reported_conversation", "author_observation",
        "author_assessment", "unspecified",
    ]
    quantity: Quantity | None = Field(
        description="Required for available_area, grid_headroom and substation_distance; "
        "use these kinds only with an explicit relevant number. Otherwise null unless "
        "the observation includes an explicit relevant number."
    )
    event_time_text: str | None
    note_id: str
    quote: str = Field(description="Exact contiguous substring of the cited note's text.")


class Extraction(OutputModel):
    opportunity_id: str
    observations: list[Observation]


class ExtractionResult(OutputModel):
    extraction: Extraction
    validation_issues: list[str]
