"""Independent fix1 checks without changing any earlier Tester assertion."""

import io
import json
from datetime import UTC, datetime
from pathlib import Path

import pdfplumber
import pytest
from reportlab.pdfgen import canvas
from test_tester_t3b1_literal import PROSE, parsed, verify_literal

from hld_navigator.extraction import extract

EVIDENCE = (
    Path(__file__).resolve().parents[1]
    / "tester_acceptance/evidence"
    / datetime.now(UTC).strftime("t3b1-fix1-boundaries-%Y%m%dT%H%M%S%f")
)


def preserve(name, data):
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    if isinstance(data, bytes):
        (EVIDENCE / name).write_bytes(data)
    else:
        (EVIDENCE / name).write_text(json.dumps(data, indent=2), encoding="utf-8")


def boundary_pdf(detected, responsibility, outside=None, qualifier=None):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(612, 792), invariant=1)
    for number in (1, 2):
        pdf.setFont("Helvetica", 9)
        pdf.drawString(38, 762, f"Actuation component inventory - revision {number + 31}")
        if qualifier:
            pdf.drawString(38, 733, qualifier)
        if detected:
            for y in (704, 675, 621):
                pdf.line(38, y, 574, y)
            for x in (38, 193, 574):
                pdf.line(x, 621, x, 704)
        pdf.drawString(46, 688, "SWC Name")
        pdf.drawString(201, 688, "Responsibility")
        pdf.drawString(46, 656, "Mistral")
        pdf.drawString(201, 656, responsibility)
        if outside:
            for i, line in enumerate(outside):
                pdf.drawString(38, 589 - 18 * i, line)
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def recorded(name, content):
    preserve(name + ".pdf", content)
    pages, rows, boundary_counts = {}, {}, {}
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page, original in enumerate(pdf.pages, 1):
            pages[page] = original.extract_text()
            boundary_counts[page] = len(original.find_tables())
            if boundary_counts[page]:
                rows[(page, 1, 2)] = original.crop((38, 117, 574, 171)).extract_text()
    blocks, entities, warnings = extract(name + ".pdf", content)
    preserve(
        name + ".original-outputs.json",
        {
            "notice": "not independently validated",
            "original_pages": pages,
            "independent_detected_table_counts": boundary_counts,
            "independent_row_crops": [{"identity": k, "text": v} for k, v in rows.items()],
            "blocks": [b.model_dump() for b in blocks],
            "entities": [e.model_dump() for e in entities],
            "warnings": warnings,
        },
    )
    return pages, rows, boundary_counts, entities, warnings


@pytest.mark.parametrize(
    "responsibility", ["Receives command", "Sends status", "Routes telemetry", "Transmits samples"]
)
def test_detected_benign_responsibility_verbs(responsibility):
    name = "benign-" + responsibility.split()[0]
    pages, rows, detected, entities, warnings = recorded(name, boundary_pdf(True, responsibility))
    assert detected == {1: 1, 2: 1}
    assert not warnings
    assert len(entities) == 1
    entity = entities[0]
    assert (entity.kind, entity.name, entity.attributes) == (
        "component",
        "Mistral",
        {"description": responsibility},
    )
    assert len(entity.sources) == 2
    assert sorted(
        (s["location"]["page"], s["location"]["table"], s["location"]["row"])
        for s in entity.sources
    ) == [(1, 1, 2), (2, 1, 2)]
    for source in entity.sources:
        verify_literal(source["text"], source["location"], pages, rows)


@pytest.mark.parametrize("detected", [False, True], ids=["undetected", "detected"])
def test_actual_unsupported_outside_table_is_never_hidden(detected):
    statement = "Mistral component routes SafetyBudget."
    name = "unsupported-" + str(detected)
    pages, rows, counts, entities, warnings = recorded(
        name, boundary_pdf(detected, "Receives command", [statement])
    )
    assert counts == {1: int(detected), 2: int(detected)}
    blockers = [w for w in warnings if w["code"] == "unsupported_relationship"]
    assert len(blockers) == 2
    assert sorted(w["location"]["page"] for w in blockers) == [1, 2]
    for warning in blockers:
        assert warning["severity"] == "blocking"
        assert "routes" in [a.lower() for a in warning["unresolved_actions"]]
        assert statement in warning["text"]
        verify_literal(warning["text"], warning["location"], pages, rows)
    assert not [e for e in entities if e.kind == "dependency"]
    for entity in entities:
        verify_literal(entity.evidence, entity.location.model_dump(), pages, rows)
        for source in entity.sources:
            verify_literal(source["text"], source["location"], pages, rows)


@pytest.mark.parametrize("detected", [False, True])
def test_undetected_table_is_not_silently_called_complete(detected):
    pages, rows, counts, entities, warnings = recorded(
        "no-outside-" + str(detected), boundary_pdf(detected, "Receives command")
    )
    assert counts == {1: int(detected), 2: int(detected)}
    if detected:
        assert not warnings and len(entities) == 1
    else:
        assert not entities
        assert any(w["severity"] == "blocking" for w in warnings)
        assert any(w["code"] == "no_entities" for w in warnings)
    for entity in entities:
        for source in entity.sources:
            verify_literal(source["text"], source["location"], pages, rows)


@pytest.mark.parametrize("detected", [False, True])
@pytest.mark.parametrize(
    "qualifier", ["If warmup is complete,", "Unless calibration is pending,", "Nacre component may"]
)
def test_qualifier_split_around_table_retained_and_blocks(detected, qualifier):
    subject = (
        "provide the FrameBus interface to Solace."
        if qualifier.endswith("may")
        else "Nacre component provides the FrameBus interface to Solace."
    )
    name = "split-" + qualifier.split()[0] + "-" + str(detected)
    pages, rows, counts, entities, warnings = recorded(
        name, boundary_pdf(detected, "Sends status", [subject], qualifier)
    )
    assert counts == {1: int(detected), 2: int(detected)}
    blockers = [w for w in warnings if w["code"] == "ambiguous_prose"]
    assert len(blockers) == 2
    for warning in blockers:
        assert warning["severity"] == "blocking"
        assert qualifier in warning["text"] and subject in warning["text"]
        verify_literal(warning["text"], warning["location"], pages, rows)
    assert not [e for e in entities if e.kind in ("dependency", "interface", "port")]
    assert not [e for e in entities if e.name in ("Nacre", "Solace")]


@pytest.mark.parametrize("category", list(PROSE))
@pytest.mark.parametrize("repeated", [False, True])
def test_existing_pdf_bytes_all_literal_quotes_and_boundary_disclosure(category, repeated):
    name, content, pages, rows, _, entities, warnings = parsed(category, repeated)
    audit = []
    for entity in entities:
        audit.append(verify_literal(entity.evidence, entity.location.model_dump(), pages, rows))
        for source in entity.sources:
            audit.append(verify_literal(source["text"], source["location"], pages, rows))
    for warning in warnings:
        audit.append(verify_literal(warning["text"], warning["location"], pages, rows))
    with pdfplumber.open(io.BytesIO(content)) as original:
        # Authored multiple spaces may already be collapsed by extract_text. Quotation
        # must match that actual independent original representation, never author guesses.
        authored_spaces = "".join(c["text"] for c in original.pages[0].chars)
        if category == "valid":
            assert "Nacre   is" in authored_spaces and "Demand  signal" in authored_spaces
            assert "interface\nto Solace" in pages[1]
    assert (pages[1] == pages[2]) is repeated
    if category in ("valid", "caption"):
        assert not warnings
    elif category == "unknown":
        assert all(w["unresolved_actions"] == ["arbitrates"] for w in warnings)
    preserve(
        name + ".all-literal.json",
        {
            "notice": "not independently validated",
            "source_audit": audit,
            "original_pdf_char_text": authored_spaces,
            "original_extract_text_pages": pages,
            "literal_source_granularity": "page context or row",
            "T3b2_boundary": "Identical pages match equally by text; "
            "extraction records page identity, "
            "but current non-table persistence joins text and does not uniquely bind "
            "each originating occurrence. Re-ingestion required for legacy quotes.",
            "frozen_acceptance_established": False,
        },
    )
