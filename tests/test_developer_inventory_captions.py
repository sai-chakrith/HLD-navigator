"""Developer-owned T7a fixtures; no independent acceptance data is used."""

import io

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


@pytest.mark.parametrize(
    "caption",
    [
        "Calibration component inventory - sheet 1",
        "Electrical interface catalog: appendix B",
        "Control port overview",
        "component and interface inventory",
        "component, interface and port table: overview",
        "component / interface inventory",
        "component & port summary",
        "module component definitions",
        "module component list | item | purpose |",
        "component inventory SWC Name Responsibility Actuator Sets target",
        "Mechanical component inventory for release 8.12.4",
        "component inventory (release 5.9)",
        "component and interface inventory (version v4.2) - sheet 3",
        "component inventory revision r17: actuation",
        "component inventory for version 6.5 SWC Name Responsibility",
        "component inventory ( release: 19.4 )",
        "component inventory version=3.2",
    ],
)
def test_nominal_caption_is_not_an_architecture_predicate(caption):
    _, issues = parse_prose(caption, Location(page=3))
    assert not issues


@pytest.mark.parametrize("suffix", [".md", ".txt"])
def test_text_inventory_captions_preserve_real_warnings(suffix):
    caption = "# Control component and interface inventory"
    predicate = "Servo component arbitrates FaultData with Monitor."
    content = (
        caption + "\n| SWC Name | Responsibility |\n| --- | --- |\n"
        "| Servo | Sets target |\n\n" + predicate + "\n"
    ).encode()
    _, entities, issues = extract("developer-caption" + suffix, content)
    entity = next(e for e in entities if e.name == "Servo")
    assert entity.name == "Servo"
    table_sources = [s for s in entity.sources if s["location"]["table"]]
    assert len(table_sources) == 1
    assert table_sources[0]["text"] == "| Servo | Sets target |"
    assert (
        table_sources[0]["location"]
        == Location(
            section="Control component and interface inventory", line=4, table=1, row=3
        ).model_dump()
    )
    warnings = [w for w in issues if w["code"] == "unsupported_relationship"]
    assert len(warnings) == 1
    assert warnings[0]["text"] == predicate
    assert warnings[0]["severity"] == "blocking"
    assert warnings[0]["unresolved_actions"] == ["arbitrates"]
    assert warnings[0]["location"]["line"] == 6


@pytest.mark.parametrize(
    "statement,action",
    [
        ("Servo component arbitrates FaultData with Monitor.", "arbitrates"),
        ("Servo component inventories Sensor interfaces.", "inventories"),
        ("Servo component lists Sensor interfaces.", "lists"),
        ("Servo component inventory arbitrates FaultData with Monitor.", "inventory"),
        ("component inventory - Servo transfers FaultData to Monitor.", "transfers"),
        ("component inventory - Servo component negotiates with Monitor.", "negotiates"),
        ("component and interface inventory: Servo forwards FaultData to Monitor.", "forwards"),
    ],
)
def test_nominal_recognition_does_not_hide_actual_unsupported_statements(statement, action):
    location = Location(section="Developer relationships", line=8)
    _, issues = parse_prose(statement, location)
    warning = next(w for w in issues if w["code"] == "unsupported_relationship")
    assert action in warning["unresolved_actions"]
    assert warning["severity"] == "blocking"
    assert warning["text"] == statement
    assert warning["location"] == location.model_dump()


def test_unknown_coordinated_clause_after_supported_edge_stays_blocking():
    statement = (
        "Servo component provides Target interface to Monitor "
        "and reconciles FaultData with Recorder."
    )
    entities, issues = parse_prose(statement, Location(page=2))
    edge = next(e for e in entities if e.kind == "dependency")
    assert edge.attributes == {"source": "Servo", "target": "Monitor", "interface": "Target"}
    warning = next(w for w in issues if w["code"] == "unsupported_relationship")
    assert warning["unresolved_actions"] == ["reconciles"]
    assert warning["severity"] == "blocking"
    assert warning["text"] == statement
    assert warning["location"]["page"] == 2


@pytest.mark.parametrize(
    "statement",
    [
        "Servo component never provides Target interface to Monitor.",
        "If Servo component provides Target interface to Monitor, Recorder sends an alert.",
        "Servo component might provide Target interface to Monitor.",
        "component inventory - Servo component may provide Target interface to Monitor.",
    ],
)
def test_qualified_relationships_remain_blocked_without_unconditional_facts(statement):
    location = Location(section="Developer qualifications", line=9)
    entities, issues = parse_prose(statement, location)
    assert not entities
    assert len(issues) == 1
    assert issues[0]["code"] == "ambiguous_prose"
    assert issues[0]["severity"] == "blocking"
    assert issues[0]["text"] == statement
    assert issues[0]["location"] == location.model_dump()


def inventory_pdf(relationship=None, caption=None):
    stream = io.BytesIO()
    styles = getSampleStyleSheet()
    story = []
    for sheet in (1, 2):
        if sheet == 2:
            story.append(PageBreak())
        story.append(
            Paragraph(
                (caption or "Calibration component inventory") + f" - sheet {sheet}",
                styles["Normal"],
            )
        )
        table = Table(
            [["SWC Name", "Responsibility"], ["Servo", "Sets target\nat startup"]],
            colWidths=[105, 210],
        )
        table.setStyle([("GRID", (0, 0), (-1, -1), 1, "black")])
        story.append(table)
        if relationship and sheet == 2:
            story.append(Paragraph(relationship, styles["Normal"]))
    SimpleDocTemplate(stream).build(story)
    return stream.getvalue()


def test_multi_page_inventory_pdf_has_exact_rows_and_reviewable_evidence(tmp_path):
    content = inventory_pdf()
    blocks, entities, issues = extract("developer-inventory.pdf", content)
    assert not issues
    servo = next(e for e in entities if e.name == "Servo" and e.location.table)
    assert servo.attributes == {"description": "Sets target at startup"}
    assert servo.evidence == "Sets target\nServo at startup"
    assert len(servo.sources) == 2
    assert {s["location"]["page"] for s in servo.sources} == {1, 2}
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for source in servo.sources:
            location = source["location"]
            page = pdf.pages[location["page"] - 1]
            table = page.find_tables()[location["table"] - 1]
            assert source["text"] == page.crop(table.rows[location["row"] - 1].bbox).extract_text()
    store = Store(str(tmp_path / "developer-inventory.db"))
    document = store.ingest(
        "developer",
        "Inventory",
        "1",
        "developer-inventory.pdf",
        content,
        blocks,
        entities,
        issues,
        "dev",
    )
    store.review(
        "developer", document, SourceReview(approved=True, reason="Own source"), "dev", True
    )
    for entity in store.entities("developer", document):
        store.review(
            "developer", entity["id"], Review(status="approved", reason="Own evidence"), "dev"
        )
    evidence = store.search("developer", "Servo", document)
    table_sources = [b for b in evidence if b["location"]["table"]]
    assert {b["location"]["page"] for b in table_sources} == {1, 2}
    assert all(b["source_context"]["text"] == servo.evidence for b in table_sources)
    assert all(b["review_state"] == "approved_facts" for b in table_sources)


@pytest.mark.parametrize(
    "caption",
    [None, "component inventory for release 27.4", "component inventory (version v10.9)"],
)
@pytest.mark.parametrize(
    "relationship,code",
    [
        ("Servo component arbitrates FaultData with Monitor.", "unsupported_relationship"),
        (
            "Servo component provides Target interface to Monitor and negotiates with Recorder.",
            "unsupported_relationship",
        ),
        ("Servo component may provide Target interface to Monitor.", "ambiguous_prose"),
    ],
)
def test_inventory_pdf_does_not_suppress_relationship_warnings(caption, relationship, code):
    _, entities, issues = extract(
        "developer-relationships.pdf", inventory_pdf(relationship, caption=caption)
    )
    warnings = [w for w in issues if w["code"] == code]
    assert warnings
    assert all(w["severity"] == "blocking" and w["location"]["page"] == 2 for w in warnings)
    assert all(relationship in w["text"] for w in warnings)
    if code == "ambiguous_prose":
        assert not any(e.kind == "dependency" for e in entities)


@pytest.mark.parametrize(
    "caption",
    [
        "Mechanical component inventory for release 8.12.4",
        "Mechanical component inventory (version v5.9)",
    ],
)
@pytest.mark.parametrize("suffix", [".md", ".txt", ".pdf"])
def test_versioned_inventory_has_raw_table_sources_and_can_be_reviewed_exported(
    tmp_path, caption, suffix
):
    if suffix == ".pdf":
        content = inventory_pdf(caption=caption)
    else:
        content = (
            caption + "\n| SWC Name | Responsibility |\n| --- | --- |\n| Servo | Sets target |\n"
        ).encode()
    name = "developer-versioned" + suffix
    blocks, entities, issues = extract(name, content)
    assert not issues
    servo = next(e for e in entities if e.name == "Servo")
    table_sources = [s for s in servo.sources if s["location"]["table"]]
    assert len(table_sources) == (2 if suffix == ".pdf" else 1)
    assert all(
        s["text"]
        == ("Sets target\nServo at startup" if suffix == ".pdf" else "| Servo | Sets target |")
        for s in table_sources
    )
    app = create_app(str(tmp_path / "own-versioned.db"))
    store = app.state.store
    token = store.provision("dev", "own", "reviewer")
    document = store.ingest(
        "own", "Own inventory", "1", name, content, blocks, entities, issues, "dev"
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
        exported = next(e for e in response.json()["entities"] if e["name"] == "Servo")
        assert exported["evidence"] == servo.evidence
        assert exported["attributes"] == servo.attributes
        assert len(exported["sources"]) == len(servo.sources)


@pytest.mark.parametrize(
    "caption",
    [
        "component inventory for release 7.14",
        "component and interface inventory (revision r9)",
    ],
)
@pytest.mark.parametrize(
    "statement,code,action",
    [
        (
            "Coordinator component adjudicates SafetyData with Auditor.",
            "unsupported_relationship",
            "adjudicates",
        ),
        ("Coordinator routes SafetyData to Auditor.", "unsupported_relationship", "routes"),
        (
            "Coordinator component provides Status interface to Auditor and arbitrates SafetyData.",
            "unsupported_relationship",
            "arbitrates",
        ),
        ("Coordinator component may provide Status interface to Auditor.", "ambiguous_prose", None),
        (
            "If Coordinator component provides Status interface to Auditor, "
            "Auditor sends SafetyData.",
            "ambiguous_prose",
            None,
        ),
        (
            "Coordinator component never provides Status interface to Auditor.",
            "ambiguous_prose",
            None,
        ),
    ],
)
def test_release_metadata_does_not_hide_nearby_relationships(caption, statement, code, action):
    location = Location(page=4)
    text = caption + ": " + statement
    entities, issues = parse_prose(text, location)
    warning = next(w for w in issues if w["code"] == code)
    assert warning["severity"] == "blocking"
    assert warning["text"] == text
    assert warning["location"] == location.model_dump()
    if action:
        assert action in warning["unresolved_actions"]
        assert "inventory" not in warning["unresolved_actions"]
    else:
        assert not entities


@pytest.mark.parametrize(
    "text",
    [
        "component inventory for release 6.2 adjudicates SafetyData with Auditor.",
        "component inventory (release 6.2 adjudicates SafetyData with Auditor).",
        "component inventory for release pending adjudicates SafetyData with Auditor.",
    ],
)
def test_non_metadata_lowercase_continuations_are_still_flagged(text):
    _, issues = parse_prose(text, Location(page=4))
    assert any(
        w["code"] == "unsupported_relationship" and w["severity"] == "blocking" for w in issues
    )
