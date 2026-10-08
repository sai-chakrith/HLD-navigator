"""Developer-owned T3a checks, using only newly authored source fixtures."""

import io

import pdfplumber
import pytest
from fastapi.testclient import TestClient
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Table

from hld_navigator.app import create_app
from hld_navigator.extraction import extract
from hld_navigator.models import Block, Entity, Location, Review, SourceReview
from hld_navigator.store import Store


def markdown_fixture():
    return (
        b"# Components\n"
        b"| SWC Name | Responsibility |\n"
        b"| --- | --- |\n"
        b"  | DemoECU  | Calculate torque  |  \n"
        b"  | DemoECU  | Calculate torque  |  \n"
        b"\n# Ports\n"
        b"| Port Name | Component | Interface | Port Kind |\n"
        b"| --- | --- | --- | --- |\n"
        b"| TorqueOut | DemoECU | TorqueBus | P-Port |\n"
        b"| TorqueIn | DemoECU | TorqueBus | R-Port |\n"
    )


def pdf_fixture():
    # Build an independent two-page source with tables on page two.
    stream = io.BytesIO()
    components = Table(
        [
            ["SWC Name", "Responsibility"],
            ["DemoECU", "Calculate torque\nwithin limit"],
            ["DemoECU", "Calculate torque\nwithin limit"],
        ],
        colWidths=[110, 180],
    )
    ports = Table(
        [
            ["Port Name", "SWC Owner", "Interface", "Port Kind"],
            ["TorqueOut", "DemoECU", "TorqueBus", "P-Port"],
            ["TorqueIn", "DemoECU", "TorqueBus", "R-Port"],
        ],
        colWidths=[100, 100, 100, 100],
    )
    for table in (components, ports):
        table.setStyle([("GRID", (0, 0), (-1, -1), 1, "black")])
    SimpleDocTemplate(stream).build(
        [
            Paragraph("Table provenance fixture", getSampleStyleSheet()["Normal"]),
            PageBreak(), components, ports,
        ]
    )
    return stream.getvalue()


def test_markdown_exact_spacing_aliases_sections_and_repeated_rows():
    content = markdown_fixture()
    blocks, entities, warnings = extract("own-table.md", content)
    assert not warnings
    component = next(e for e in entities if e.kind == "component")
    raw = "  | DemoECU  | Calculate torque  |  "
    assert component.evidence == raw
    assert component.attributes == {"description": "Calculate torque"}
    assert component.location == Location(section="Components", line=4, table=1, row=3)
    assert [(s["location"]["line"], s["location"]["row"]) for s in component.sources] == [
        (4, 3), (5, 4)
    ]
    assert all(s["text"] == raw for s in component.sources)
    ports = {e.name: e for e in entities if e.kind == "port"}
    assert ports["TorqueOut"].attributes["direction"] == "provides"
    assert ports["TorqueIn"].attributes["direction"] == "requires"
    assert ports["TorqueOut"].location.section == "Ports"
    assert "P-Port" in ports["TorqueOut"].evidence
    assert all(b.text in content.decode().splitlines() for b in blocks)
    assert not any(b.text.startswith("Component:") or "direction=" in b.text for b in blocks)


def test_pdf_exact_captured_spans_multiline_aliases_and_repeated_rows():
    content = pdf_fixture()
    blocks, entities, warnings = extract("own-table.pdf", content)
    assert not warnings
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        page = pdf.pages[1]
        tables = page.find_tables()
        for entity in entities:
            assert entity.location.page == 2
            if entity.location.table is None:
                # Existing prose parsing of the PDF header is outside T3a's scope.
                continue
            for source in entity.sources:
                location = source["location"]
                captured = page.crop(
                    tables[location["table"] - 1].rows[location["row"] - 1].bbox
                ).extract_text()
                assert source["text"] == captured
                assert any(
                    b.text == captured and b.location.model_dump() == location for b in blocks
                )
    component = next(e for e in entities if e.kind == "component" and e.location.table)
    assert component.attributes == {"description": "Calculate torque within limit"}
    assert component.evidence == "Calculate torque\nDemoECU within limit"
    assert [s["location"]["row"] for s in component.sources] == [2, 3]
    ports = {e.name: e for e in entities if e.kind == "port"}
    assert ports["TorqueOut"].attributes["direction"] == "provides"
    assert ports["TorqueIn"].attributes["direction"] == "requires"
    assert "P-Port" in ports["TorqueOut"].evidence
    assert all(not b.text.startswith("Component:") and "direction=" not in b.text for b in blocks)


def test_invalid_table_declaration_reports_raw_row_without_invented_quote():
    raw = "| TorqueOut | DemoECU | TorqueBus | sideways |"
    content = (
        "# Ports\n| Port Name | Component | Interface | Port Kind |\n"
        "| --- | --- | --- | --- |\n" + raw + "\n"
    ).encode()
    blocks, entities, warnings = extract("own-invalid.md", content)
    assert not entities
    issue = next(w for w in warnings if w["code"] == "invalid_declaration")
    assert issue["text"] == raw
    assert issue["location"] == Location(section="Ports", line=4, table=1, row=3).model_dump()
    assert all(b.text in content.decode().splitlines() for b in blocks)


@pytest.mark.parametrize("name,fixture", [("own.md", markdown_fixture), ("own.pdf", pdf_fixture)])
def test_raw_evidence_survives_ingest_review_retrieval_export_and_reopen(
    tmp_path, monkeypatch, name, fixture
):
    monkeypatch.delenv("HLD_NAVIGATOR_OLLAMA_MODEL", raising=False)
    content = fixture()
    _, expected, warnings = extract(name, content)
    assert not warnings
    path = str(tmp_path / "developer.db")
    app = create_app(path)
    store = app.state.store
    headers = {"Authorization": "Bearer " + store.provision("dev", "own", "reviewer")}
    with TestClient(app) as client:
        response = client.post(
            "/workspaces/own/documents", headers=headers,
            data={"title": "Own provenance fixture", "version": "1"},
            files={"file": (name, content)},
        )
        assert response.status_code == 200, response.text
        document = response.json()["id"]
        store.review("own", document, SourceReview(approved=True, reason="Own source"), "dev", True)
        for entity in store.entities("own", document):
            store.review("own", entity["id"], Review(status="approved", reason="Own row"), "dev")
        response = client.get(
            "/workspaces/own/export", headers=headers, params={"document_id": document}
        )
        assert response.status_code == 200, response.text
        exported = {e["name"]: e for e in response.json()["entities"]}
        for entity in expected:
            saved = exported[entity.name]
            assert saved["evidence"] == entity.evidence
            assert saved["location"] == entity.location.model_dump()
            assert saved["attributes"] == entity.attributes
            assert sorted(saved["sources"], key=lambda s: str(s["location"])) == sorted(
                entity.sources, key=lambda s: str(s["location"])
            )
        response = client.post(
            "/workspaces/own/query", headers=headers,
            json={"text": "DemoECU", "document_id": document},
        )
        assert response.status_code == 200, response.text
        evidence = response.json()["evidence"]
        assert evidence
        assert all(e["document_id"] == document and e["name"] == name for e in evidence)
        table_evidence = [e for e in evidence if e["location"]["table"]]
        assert table_evidence
        assert all(e["review_state"] == "approved_facts" for e in table_evidence)
        assert all(e["text"] in {s["text"] for v in expected for s in v.sources} for e in evidence)
    reopened = Store(path)
    assert reopened.entities("own", document) == store.entities("own", document)


def test_identical_table_rows_link_only_their_exact_locations(tmp_path):
    store = Store(str(tmp_path / "rows.db"))
    raw = "| DemoECU | Calculate torque |"
    locations = [Location(section="Components", line=n, table=1, row=n) for n in (3, 4)]
    blocks = [Block(text=raw, location=location) for location in locations]
    entities = [
        Entity(kind="component", name="DemoECU", evidence=raw, location=location)
        for location in locations
    ]
    document = store.ingest("own", "Rows", "1", "own.md", raw.encode(), blocks, entities, [], "dev")
    store.review("own", document, SourceReview(approved=True, reason="Own source"), "dev", True)
    rows = store.entities("own", document)
    store.review("own", rows[0]["id"], Review(status="approved", reason="Row three"), "dev")
    store.review("own", rows[1]["id"], Review(status="rejected", reason="Row four"), "dev")
    # Reopening must not create text-only cross-links between repeated rows.
    reopened = Store(store.path)
    for entity in reopened.entities("own", document):
        assert entity["sources"] == [{"text": raw, "location": entity["location"]}]
    evidence = reopened.search("own", "DemoECU", document)
    assert len(evidence) == 1
    assert evidence[0]["location"]["row"] == 3
