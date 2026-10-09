"""Developer-owned T3b1 fix-cycle fixtures; table cells are not prose assertions."""

import io

import pdfplumber
import pytest
from fastapi.testclient import TestClient
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Table

from hld_navigator.app import create_app
from hld_navigator.extraction import extract
from hld_navigator.models import Block, Location, Review, SourceReview
from hld_navigator.prose import parse_pdf_prose


def boundary_pdf(responsibility="Receives operator request", before=None, after=None):
    stream = io.BytesIO()
    styles = getSampleStyleSheet()
    story = []
    for sheet in (1, 2):
        if sheet == 2:
            story.append(PageBreak())
        story.append(
            Paragraph(f"Load component inventory version v12.3 - sheet {sheet}", styles["Normal"])
        )
        if before:
            story.append(Paragraph(before, styles["Normal"]))
        table = Table(
            [["SWC Name", "Responsibility"], ["DemandCtrl", responsibility]],
            colWidths=[140, 260],
        )
        table.setStyle([("GRID", (0, 0), (-1, -1), 1, "black")])
        story.append(table)
        if after:
            story.append(Paragraph(after, styles["Normal"]))
    SimpleDocTemplate(stream).build(story)
    return stream.getvalue()


@pytest.mark.parametrize(
    "responsibility",
    [
        "Receives operator request",
        "Sends safety summary",
        "Provides state history",
        "Routes diagnostics",
    ],
)
def test_benign_responsibilities_are_parsed_only_as_table_attributes(responsibility):
    content = boundary_pdf(responsibility)
    _, entities, warnings = extract("own-load-inventory.pdf", content)
    assert not warnings
    assert len(entities) == 1
    entity = entities[0]
    assert entity.kind == "component" and entity.name == "DemandCtrl"
    assert entity.attributes == {"description": responsibility}
    assert len(entity.sources) == 2
    assert {s["location"]["page"] for s in entity.sources} == {1, 2}
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for source in entity.sources:
            location = source["location"]
            page = pdf.pages[location["page"] - 1]
            table = page.find_tables()[location["table"] - 1]
            assert source["text"] == page.crop(table.rows[location["row"] - 1].bbox).extract_text()


def test_real_wrapped_prose_outside_table_retains_literal_page_and_all_contributors():
    content = boundary_pdf(
        after=("DemandCtrl component provides DemandData interface<br/>to LoadMonitor component.")
    )
    _, entities, warnings = extract("own-load-relationship.pdf", content)
    assert not warnings
    edge = next(e for e in entities if e.kind == "dependency")
    assert edge.attributes == {
        "source": "DemandCtrl",
        "target": "LoadMonitor",
        "interface": "DemandData",
    }
    component = next(e for e in entities if e.name == "DemandCtrl")
    assert component.attributes == {"description": "Receives operator request"}
    assert {s["location"]["table"] is None for s in component.sources} == {False, True}
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for source in edge.sources:
            location = source["location"]
            raw_page = pdf.pages[location["page"] - 1].extract_text()
            assert source["text"].encode() == raw_page.encode()
            assert "Receives operator request" in source["text"]
            assert "\n" in source["text"]
    assert {s["location"]["page"] for s in edge.sources} == {1, 2}


@pytest.mark.parametrize(
    "before,after,code,action",
    [
        (
            None,
            "DemandCtrl component adjudicates DemandData with LoadMonitor.",
            "unsupported_relationship",
            "adjudicates",
        ),
        (
            None,
            "DemandCtrl component receives DiagnosticData from Reviewer.",
            "unsupported_relationship",
            "receives",
        ),
        (
            None,
            "DemandCtrl component provides DemandData interface to LoadMonitor "
            "and arbitrates TimingData with Recorder.",
            "unsupported_relationship",
            "arbitrates",
        ),
        (
            None,
            "DemandCtrl component never provides DemandData interface to LoadMonitor.",
            "ambiguous_prose",
            None,
        ),
        (
            None,
            "DemandCtrl component might provide DemandData interface to LoadMonitor.",
            "ambiguous_prose",
            None,
        ),
        (
            "If controller readiness is confirmed,",
            "DemandCtrl component provides DemandData interface to LoadMonitor.",
            "ambiguous_prose",
            None,
        ),
    ],
)
def test_outside_table_claims_keep_blocking_warnings_and_complete_qualifiers(
    before, after, code, action
):
    content = boundary_pdf(before=before, after=after)
    _, entities, warnings = extract("own-load-guards.pdf", content)
    matched = [w for w in warnings if w["code"] == code]
    assert len(matched) == 2
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for warning in matched:
            assert warning["severity"] == "blocking"
            raw_page = pdf.pages[warning["location"]["page"] - 1].extract_text()
            assert warning["text"].encode() == raw_page.encode()
            if before:
                assert before in warning["text"]
            if action:
                assert action in warning["unresolved_actions"]
                assert "Receives" not in warning["unresolved_actions"]
    if code == "ambiguous_prose":
        assert not any(e.kind == "dependency" for e in entities)


def test_reviewed_benign_table_document_exports_without_coverage_override(tmp_path):
    content = boundary_pdf()
    blocks, entities, warnings = extract("own-load-export.pdf", content)
    assert not warnings
    app = create_app(str(tmp_path / "own-load.db"))
    store = app.state.store
    token = store.provision("dev", "own", "reviewer")
    document = store.ingest(
        "own",
        "Own load document",
        "1",
        "own-load-export.pdf",
        content,
        blocks,
        entities,
        warnings,
        "dev",
    )
    store.review("own", document, SourceReview(approved=True, reason="Own source"), "dev", True)
    for entity in store.entities("own", document):
        store.review("own", entity["id"], Review(status="approved", reason="Own proposal"), "dev")
    with TestClient(app) as client:
        response = client.get(
            "/workspaces/own/export",
            params={"document_id": document},
            headers={"Authorization": "Bearer " + token},
        )
        assert response.status_code == 200, response.text
        assert response.json()["coverage_review"] is None
        assert response.json()["entities"][0]["attributes"] == {
            "description": "Receives operator request"
        }


def test_pdf_interpretation_cannot_be_bound_to_a_different_source_page():
    original = Block(text="Original page one", location=Location(page=1))
    interpretation = Block(
        text="DemandCtrl component provides DemandData interface to LoadMonitor.",
        location=Location(page=2),
    )
    with pytest.raises(ValueError, match="same page"):
        parse_pdf_prose(original, interpretation=interpretation)
