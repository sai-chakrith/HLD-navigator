from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

STRICT_MODEL = ConfigDict(extra="forbid", strict=True)


class AnswerCitation(BaseModel):
    model_config = STRICT_MODEL
    source_id: str = Field(pattern=r"^S[1-9][0-9]*$")
    snippet: str = Field(min_length=1)

    @field_validator("snippet")
    @classmethod
    def nonblank_snippet(cls, value):
        if not value.strip():
            raise ValueError("snippet must be nonblank")
        return value


class AnswerClaim(BaseModel):
    model_config = STRICT_MODEL
    text: str = Field(min_length=1, max_length=2000)
    citations: list[AnswerCitation] = Field(min_length=1)

    @field_validator("text")
    @classmethod
    def nonblank_claim(cls, value):
        if not value.strip():
            raise ValueError("claim must be nonblank")
        return value


class ModelAnswer(BaseModel):
    """Mechanical citation validity does not establish semantic entailment."""

    model_config = STRICT_MODEL
    status: Literal["answered", "abstained", "conflict"]
    claims: list[AnswerClaim]
    reason: Literal["", "insufficient_evidence", "contradictory_evidence"]

    @model_validator(mode="after")
    def consistent_status(self):
        if self.status == "abstained":
            if self.claims or self.reason != "insufficient_evidence":
                raise ValueError("abstention requires no claims and insufficient_evidence reason")
        elif not self.claims:
            raise ValueError("non-abstaining response requires cited claims")
        elif self.reason != ("contradictory_evidence" if self.status == "conflict" else ""):
            raise ValueError("reason must agree with response status")
        if self.status == "conflict":
            alternatives = {
                (c.source_id, c.snippet) for claim in self.claims for c in claim.citations
            }
            if len(alternatives) < 2:
                raise ValueError("conflict disclosure requires at least two cited alternatives")
        return self


class ResolvedAnswerCitation(AnswerCitation):
    block_id: str = Field(min_length=1)


class ResolvedAnswerClaim(BaseModel):
    model_config = STRICT_MODEL
    text: str
    citations: list[ResolvedAnswerCitation]


class Location(BaseModel):
    model_config = STRICT_MODEL

    page: int | None = Field(default=None, ge=1)
    section: str | None = None
    line: int | None = Field(default=None, ge=1)
    table: int | None = Field(default=None, ge=1)
    row: int | None = Field(default=None, ge=1)
    origin: Literal["text", "ocr"] = "text"
    confidence: float | None = Field(default=None, ge=0, le=100)

    @field_validator("section")
    @classmethod
    def nonblank_section(cls, value):
        if value is not None and not value.strip():
            raise ValueError("section must contain non-whitespace characters")
        return value

    @model_validator(mode="after")
    def valid_source_shape(self):
        if (self.table is None) != (self.row is None):
            raise ValueError("table and row must be provided together")
        if self.section is not None and self.line is None:
            raise ValueError("section requires a line")
        if self.page is not None and self.section is not None:
            raise ValueError("page and section locations cannot be combined")
        if self.table is not None:
            if (self.page is None) == (self.line is None):
                raise ValueError("table evidence requires exactly one of page or line")
        elif self.page is None and self.line is None:
            raise ValueError("source location requires a page or line")
        if self.origin == "ocr":
            if self.page is None or self.line is None or self.confidence is None:
                raise ValueError("OCR evidence requires page, line and confidence")
            if self.table is not None:
                raise ValueError("OCR evidence cannot claim a detected table occurrence")
        elif self.confidence is not None:
            raise ValueError("confidence is only valid for OCR evidence")
        return self


class EvidenceSource(BaseModel):
    model_config = STRICT_MODEL

    text: str = Field(min_length=1)
    location: Location

    @field_validator("text")
    @classmethod
    def nonblank_text(cls, value):
        if not value.strip():
            raise ValueError("source evidence must contain non-whitespace characters")
        return value


class Block(BaseModel):
    model_config = STRICT_MODEL

    text: str = Field(min_length=1)
    location: Location

    @field_validator("text")
    @classmethod
    def nonblank_text(cls, value):
        if not value.strip():
            raise ValueError("source block must contain non-whitespace characters")
        return value


class TableDeclaration(BaseModel):
    """Parsing input and captured source are distinct; only evidence may be quoted."""

    model_config = STRICT_MODEL

    declaration: str = Field(min_length=1)
    evidence: str = Field(min_length=1)
    location: Location

    @field_validator("declaration", "evidence")
    @classmethod
    def nonblank_text(cls, value):
        if not value.strip():
            raise ValueError("table declaration and evidence must be nonblank")
        return value


class Entity(BaseModel):
    model_config = STRICT_MODEL

    kind: Literal["component", "interface", "signal", "port", "dependency", "flow"]
    name: str = Field(min_length=1)
    attributes: dict[str, str] = Field(default_factory=dict)
    evidence: str = Field(min_length=1)
    location: Location
    sources: list[dict] = Field(default_factory=list)

    @field_validator("name", "evidence")
    @classmethod
    def nonblank_text(cls, value):
        if not value.strip():
            raise ValueError("entity name and evidence must be nonblank")
        return value

    @field_validator("sources", mode="before")
    @classmethod
    def strict_sources(cls, value):
        if not isinstance(value, list):
            raise ValueError("entity sources must be a list")
        return [EvidenceSource.model_validate(source, strict=True).model_dump() for source in value]


class Review(BaseModel):
    model_config = STRICT_MODEL
    status: Literal["approved", "rejected"]
    attributes: dict[str, str] | None = None
    reason: str = Field(min_length=1, max_length=2000)


class SourceReview(BaseModel):
    model_config = STRICT_MODEL
    approved: bool
    reason: str = Field(min_length=1, max_length=2000)


class Question(BaseModel):
    model_config = STRICT_MODEL

    text: str = Field(min_length=1, max_length=2000)
    document_id: str | None = None
    scope: Literal["facts", "source"] = "facts"


class CoverageReview(BaseModel):
    model_config = STRICT_MODEL
    scope: str = Field(min_length=10, max_length=2000)
    reason: str = Field(min_length=10, max_length=2000)


class ManualEntity(BaseModel):
    model_config = STRICT_MODEL
    kind: Literal["component", "interface", "signal", "port", "dependency", "flow"]
    name: str = Field(min_length=1, max_length=200)
    attributes: dict[str, str] = Field(default_factory=dict)
    evidence_block_id: str
