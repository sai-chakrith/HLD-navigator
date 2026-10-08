from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Location(BaseModel):
    page: int | None = None
    section: str | None = None
    line: int | None = None
    table: int | None = None
    row: int | None = None
    origin: str = "text"
    confidence: float | None = None


class Block(BaseModel):
    text: str
    location: Location


class Entity(BaseModel):
    kind: Literal["component", "interface", "signal", "port", "dependency", "flow"]
    name: str
    attributes: dict[str, str] = Field(default_factory=dict)
    evidence: str
    location: Location
    sources: list[dict] = Field(default_factory=list)


class Review(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["approved", "rejected"]
    attributes: dict[str, str] | None = None
    reason: str = Field(min_length=1, max_length=2000)


class SourceReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approved: bool
    reason: str = Field(min_length=1, max_length=2000)


class Question(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    document_id: str | None = None
    scope: Literal["facts", "source"] = "facts"


class CoverageReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scope: str = Field(min_length=10, max_length=2000)
    reason: str = Field(min_length=10, max_length=2000)


class ManualEntity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["component", "interface", "signal", "port", "dependency", "flow"]
    name: str = Field(min_length=1, max_length=200)
    attributes: dict[str, str] = Field(default_factory=dict)
    evidence_block_id: str
