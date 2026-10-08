"""T2c fixture oracles: content correspondence is separate from literal evidence validity."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class PdfLocation(StrictRecord):
    page: int = Field(ge=1)
    section: str | None
    line: int | None
    table: int | None
    row: int | None
    origin: Literal["text"]
    confidence: float | None


class Contributor(StrictRecord):
    text: str = Field(min_length=1)
    location: PdfLocation


class PdfWarning(StrictRecord):
    code: Literal["unsupported_relationship", "ambiguous_prose"]
    severity: Literal["blocking"]
    message: str
    text: str
    location: PdfLocation
    unresolved_actions: list[str] = Field(default_factory=list)


class SourceCharacterization(StrictRecord):
    notice: Literal["not independently validated"] = "not independently validated"
    page: int
    table: int | None
    row: int | None
    text: str
    original_page_text: str
    representation: Literal["literal-table-row", "joined-page-context", "literal-page-context"]
    content_correspondence: bool
    literal_original_substring: bool
    gap_task: Literal["T3b"] | None


def partition_contributors(sources: list[dict], *, require_context: bool):
    table, context = [], []
    for source in sources:
        record = Contributor.model_validate(source)
        location = record.location
        assert location.page in (1, 2), "wrong source page"
        assert location.section is None and location.line is None
        assert location.confidence is None
        if location.table is not None:
            assert (location.table, location.row) == (1, 2), "wrong table/row identity"
            table.append(source)
        else:
            assert location.row is None, "page context must not have a row identity"
            context.append(source)
    assert sorted((s["location"]["page"], s["location"]["table"], s["location"]["row"])
                  for s in table) == [(1, 1, 2), (2, 1, 2)], "missing/duplicate table contributor"
    assert sorted(s["location"]["page"] for s in context) == (
        [1, 2] if require_context else []), "missing/duplicate/unexpected prose contributor"
    return table, context


def verify_contributors(sources: list[dict], *, require_context: bool,
                        originals: dict[int, str], row_spans: dict[int, str],
                        statement: str | None) -> list[SourceCharacterization]:
    table, context = partition_contributors(sources, require_context=require_context)
    assert set(originals) == set(row_spans) == {1, 2}
    results = []
    for source in table:
        page = source["location"]["page"]
        assert source["text"] == row_spans[page], "altered exact table quote"
        assert source["text"] in originals[page], "table quote is not literal original text"
        results.append(SourceCharacterization(
            page=page, table=1, row=2, text=source["text"], original_page_text=originals[page],
            representation="literal-table-row", content_correspondence=True,
            literal_original_substring=True, gap_task=None))
    for source in context:
        page = source["location"]["page"]
        expected = originals[page]
        assert source["text"] == expected, "wrong page or unrelated page-context content"
        assert statement is not None and statement in originals[page]
        assert statement in source["text"], "contributing original statement is missing"
        literal = source["text"] in originals[page]
        # Literal equality is checked independently; normalization cannot satisfy this oracle.
        assert literal, "PDF page context must retain literal original extracted text"
        results.append(SourceCharacterization(
            page=page, table=None, row=None, text=source["text"],
            original_page_text=originals[page],
            representation="literal-page-context", content_correspondence=True,
            literal_original_substring=True, gap_task=None))
    return results


def verify_warnings(warnings: list[dict], *, statement: str, code: str,
                    originals: dict[int, str]) -> list[dict]:
    records = [PdfWarning.model_validate(w) for w in warnings]
    assert len(records) == 2, "missing/duplicate/unexpected warning"
    assert sorted(w.location.page for w in records) == [1, 2], "wrong warning page"
    output = []
    for warning in records:
        location = warning.location
        assert location.section is None and location.line is None
        assert location.table is None and location.row is None and location.confidence is None
        assert warning.code == code, "wrong semantic warning category"
        original = originals[location.page]
        assert statement in original, "expected statement/qualifier absent from original page"
        assert statement in warning.text, "warning lost or altered original statement/qualifier"
        assert warning.text == original, (
            "warning context is altered, unrelated or from the wrong page")
        if code == "unsupported_relationship":
            assert warning.unresolved_actions == ["arbitrates"], "wrong unresolved predicate"
            assert warning.message == (
                "Architecture relationship is not covered by the current extraction patterns")
        else:
            assert warning.unresolved_actions == []
            assert warning.message == (
                "Negated, uncertain or qualified architecture statement needs interpretation")
        output.append({"notice": "not independently validated", "page": location.page,
                       "warning": warning.model_dump(), "original_page_text": original,
                       "complete_original_statement": statement,
                       "statement_start": original.index(statement),
                       "statement_end": original.index(statement)+len(statement),
                       "literal_original_substring": warning.text in original,
                       "full_context_correspondence": True})
    return output
