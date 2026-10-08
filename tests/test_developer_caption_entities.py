"""Developer-owned R1 caption fixtures, distinct from independent checks."""

import io
import json

import pdfplumber
import pytest
from fastapi.testclient import TestClient
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Table

from hld_navigator.app import create_app
from hld_navigator.extraction import extract
from hld_navigator.models import Location, Review, SourceReview
from hld_navigator.prose import parse_prose
from hld_navigator.store import Store


@pytest.mark.parametrize("caption", [
    "Hydraulics component inventory for release 14.6",
    "Bench component catalogue (revision r21)",
    "Actuation interface table: data definitions",
    "Voltage signal list - version 9",
    "Envelope port overview",
    "Recovery flow summary",
    "Coupling dependency index",
    "Thermal component and interface definitions",
])
def test_nominal_caption_labels_are_not_entities(caption):
    entities, issues = parse_prose(caption, Location(section="Own captions", line=2))
    assert not entities
    assert not issues


@pytest.mark.parametrize("caption", [
    "Hydraulics component inventory for release 14.6",
    "Actuation interface table: data definitions",
    "Voltage signal list - version 9",
])
def test_caption_and_real_mentions_in_one_context_are_distinguished(caption):
    text = (
        caption + ": PumpController component provides PressureData interface to Display "
        "and receives CommandData interface from Sequencer."
    )
    entities, issues = parse_prose(text, Location(page=2))
    assert not issues
    assert {(e.kind, e.name) for e in entities} == {
        ("component", "PumpController"), ("component", "Display"),
        ("component", "Sequencer"), ("interface", "PressureData"),
        ("interface", "CommandData"), ("dependency", "PumpController->Display:PressureData"),
        ("dependency", "Sequencer->PumpController:CommandData"),
    }
    assert all(e.evidence == text and e.location.page == 2 for e in entities)


def test_explicit_entity_statement_with_inventory_word_retains_the_named_entity():
    text = "PumpController is a component in the inventory. PressureData is an interface."
    entities, issues = parse_prose(text, Location(line=3))
    assert not issues
    assert {(e.kind, e.name) for e in entities} == {
        ("component", "PumpController"), ("interface", "PressureData")
    }


def test_real_entity_sharing_a_caption_label_is_not_removed_by_name():
    text = (
        "PumpController component inventory: PumpController component provides "
        "PressureData interface to Display."
    )
    entities, issues = parse_prose(text, Location(page=1))
    assert not issues
    assert len([e for e in entities if e.kind == "component" and e.name == "PumpController"]) == 2
    assert any(e.kind == "dependency" for e in entities)


def caption_text_fixture():
    return (
        b"# Hydraulics component inventory for release 14.6\n"
        b"| SWC Name | Responsibility |\n| --- | --- |\n"
        b" | PumpController | Regulates pressure | \n\n"
        b"# Actuation interface catalogue (revision r21)\n"
        b"| Interface Name | Payload |\n| --- | --- |\n"
        b"| PressureData | Pressure |\n\n"
        b"Pressure signal has type uint32 and unit kPa.\n"
    )


def caption_pdf_fixture(statement=None):
    stream = io.BytesIO()
    styles = getSampleStyleSheet()
    story = []
    captions = [
        "Hydraulics component inventory for release 14.6",
        "Bench component catalogue (revision r21)",
    ]
    for page, caption in enumerate(captions, 1):
        if page == 2:
            story.append(PageBreak())
        story.append(Paragraph(caption, styles["Normal"]))
        table = Table(
            [["SWC Name", "Responsibility"], ["PumpController", "Regulates pressure\nin circuit"]],
            colWidths=[145, 235],
        )
        table.setStyle([("GRID", (0, 0), (-1, -1), 1, "black")])
        story.append(table)
        if statement and page == 2:
            story.append(Paragraph(statement, styles["Normal"]))
    SimpleDocTemplate(stream).build(story)
    return stream.getvalue()


@pytest.mark.parametrize("suffix", [".md", ".txt"])
def test_caption_text_has_only_the_supported_architecture_and_keeps_captions(suffix):
    content = caption_text_fixture()
    blocks, entities, issues = extract("own-caption-entities" + suffix, content)
    assert not issues
    assert {(e.kind, e.name) for e in entities} == {
        ("component", "PumpController"), ("interface", "PressureData"), ("signal", "Pressure")
    }
    component = next(e for e in entities if e.kind == "component")
    assert component.attributes == {"description": "Regulates pressure"}
    assert component.evidence == " | PumpController | Regulates pressure | "
    assert component.location == Location(
        section="Hydraulics component inventory for release 14.6", line=4, table=1, row=3
    )
    interface = next(e for e in entities if e.kind == "interface")
    assert interface.attributes == {"payload": "Pressure"}
    signal = next(e for e in entities if e.kind == "signal")
    assert signal.attributes == {"type": "uint32", "unit": "kPa"}
    assert any(b.text == content.decode().splitlines()[0] and b.location.line == 1 for b in blocks)
    assert all(b.text in content.decode().splitlines() for b in blocks)


def test_pdf_caption_labels_are_absent_and_raw_row_locations_survive():
    content = caption_pdf_fixture()
    blocks, entities, issues = extract("own-caption-entities.pdf", content)
    assert not issues
    assert len(entities) == 1
    component = entities[0]
    assert component.kind == "component" and component.name == "PumpController"
    assert component.attributes == {"description": "Regulates pressure in circuit"}
    assert len(component.sources) == 2
    assert {s["location"]["page"] for s in component.sources} == {1, 2}
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for source in component.sources:
            location = source["location"]
            page = pdf.pages[location["page"] - 1]
            table = page.find_tables()[location["table"] - 1]
            assert source["text"] == page.crop(table.rows[location["row"] - 1].bbox).extract_text()
    assert any(b.text == "Hydraulics component inventory for release 14.6" for b in blocks)
    assert any(b.text == "Bench component catalogue (revision r21)" for b in blocks)


def test_pdf_supported_relationship_keeps_both_prose_and_table_contributing_sources():
    statement = "PumpController component provides PressureData interface to Display."
    _, entities, issues = extract("own-mixed-sources.pdf", caption_pdf_fixture(statement))
    assert not issues
    component = next(e for e in entities if e.kind == "component" and e.name == "PumpController")
    assert component.attributes == {"description": "Regulates pressure in circuit"}
    table_sources = [s for s in component.sources if s["location"]["table"] is not None]
    prose_sources = [s for s in component.sources if s["location"]["table"] is None]
    assert len(table_sources) == 2
    assert {s["location"]["page"] for s in table_sources} == {1, 2}
    # The descriptive and relationship patterns both contribute this source;
    # assert one distinct reference without requiring parser-level deduplication.
    assert len({json.dumps(s, sort_keys=True) for s in prose_sources}) == 1
    assert all(s["location"]["page"] == 2 and statement in s["text"] for s in prose_sources)
    assert any(e.kind == "dependency" for e in entities)
    assert not any(e.name in {"Hydraulics", "Bench"} for e in entities)


@pytest.mark.parametrize("suffix", [".md", ".txt", ".pdf"])
def test_caption_sources_and_entities_survive_review_export_retrieval_and_restart(tmp_path, suffix):
    content = caption_pdf_fixture() if suffix == ".pdf" else caption_text_fixture()
    name = "own-lifecycle" + suffix
    blocks, entities, issues = extract(name, content)
    assert not issues
    path = str(tmp_path / "own-caption-lifecycle.db")
    app = create_app(path)
    store = app.state.store
    token = store.provision("dev", "own", "reviewer")
    document = store.ingest(
        "own", "Own captions", "1", name, content, blocks, entities, issues, "dev"
    )
    store.review("own", document, SourceReview(approved=True, reason="Own source"), "dev", True)
    for entity in store.entities("own", document):
        store.review("own", entity["id"], Review(status="approved", reason="Own source"), "dev")
    with TestClient(app) as client:
        response = client.get(
            "/workspaces/own/export", params={"document_id": document},
            headers={"Authorization": "Bearer " + token},
        )
        assert response.status_code == 200, response.text
        exported = response.json()["entities"]
        assert {(e["kind"], e["name"]) for e in exported} == {(e.kind, e.name) for e in entities}
        for saved in exported:
            expected = next(
                e for e in entities if e.kind == saved["kind"] and e.name == saved["name"]
            )
            assert saved["evidence"] == expected.evidence
            assert saved["location"] == expected.location.model_dump()
            assert saved["attributes"] == expected.attributes
            # Multiple parsing patterns can cite the same source. SQLite keeps
            # one link per exact block, while retaining every distinct location.
            expected_sources = {json.dumps(s, sort_keys=True) for s in expected.sources}
            assert {json.dumps(s, sort_keys=True) for s in saved["sources"]} == expected_sources
            assert len(saved["sources"]) == len(expected_sources)
    stored = store.entities("own", document)
    reopened = Store(path)
    assert reopened.entities("own", document) == stored
    evidence = reopened.search("own", "PumpController", document)
    assert evidence
    assert all(b["location"]["table"] and b["review_state"] == "approved_facts" for b in evidence)
    assert any("component inventory" in b["text"] for b in reopened.eligible_blocks(
        "own", document, "source"
    ))


@pytest.mark.parametrize("statement,code,action", [
    ("PumpController component mediates DiagnosticData with Recorder.",
     "unsupported_relationship", "mediates"),
    ("PumpController component provides PressureData interface to Display "
     "and arbitrates SafetyData.",
     "unsupported_relationship", "arbitrates"),
    ("PumpController component may provide PressureData interface to Display.",
     "ambiguous_prose", None),
    ("PumpController component never provides PressureData interface to Display.",
     "ambiguous_prose", None),
    ("If PumpController component provides PressureData interface to Display, Display sends Alert.",
     "ambiguous_prose", None),
])
def test_caption_entity_exclusion_retains_pdf_relationship_guards(statement, code, action):
    _, entities, issues = extract("own-caption-guards.pdf", caption_pdf_fixture(statement))
    warning = next(w for w in issues if w["code"] == code)
    assert warning["severity"] == "blocking" and warning["location"]["page"] == 2
    assert statement in warning["text"]
    assert not any(e.name in {"Hydraulics", "Bench"} for e in entities)
    if action:
        assert action in warning["unresolved_actions"]
    else:
        assert not any(e.kind == "dependency" for e in entities)
