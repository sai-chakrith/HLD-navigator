"""Developer-owned T3b1 PDFs; compare quotations to independent page extraction."""

import io
import json

import pdfplumber
import pytest
from fastapi.testclient import TestClient
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Table

from hld_navigator.app import create_app
from hld_navigator.extraction import extract
from hld_navigator.models import Block, Location, Review, SourceReview
from hld_navigator.prose import parse_pdf_prose
from hld_navigator.store import Store


def line_pdf(pages):
    stream = io.BytesIO()
    pdf = canvas.Canvas(stream)
    for lines in pages:
        text = pdf.beginText(45, 760)
        text.setFont("Helvetica", 10)
        text.setLeading(16)
        for line in lines:
            text.textLine(line)
        pdf.drawText(text)
        pdf.showPage()
    pdf.save()
    return stream.getvalue()


def original_pages(content):
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        return {number: page.extract_text() for number, page in enumerate(pdf.pages, 1)}


def compound_fixture():
    return line_pdf(
        [
            [
                "Combustion reference.",
                "InjectorCtrl   component provides DoseData interface",
                "to Gateway component and Recorder component and receives",
                "CommandData interface from SafetyMgr component.",
                "DoseData interface carries Dose signal.",
                "Dose signal has type uint32 and unit mg/cycle.",
            ],
            [
                "Command channel reference.",
                "InjectorCtrl requires CommandData interface through",
                "CommandIn port.",
                "Injection flow runs from InjectorCtrl component",
                "to Gateway component.",
            ],
        ]
    )


def test_wrapped_compound_prose_keeps_facts_and_literal_page_bytes():
    content = compound_fixture()
    pages = original_pages(content)
    blocks, entities, warnings = extract("own-combustion.pdf", content)
    assert not warnings
    assert all("\n" in page and page != " ".join(page.split()) for page in pages.values())
    edges = {e.name: e.attributes for e in entities if e.kind == "dependency"}
    assert edges == {
        "InjectorCtrl->Gateway:DoseData": {
            "source": "InjectorCtrl",
            "target": "Gateway",
            "interface": "DoseData",
        },
        "InjectorCtrl->Recorder:DoseData": {
            "source": "InjectorCtrl",
            "target": "Recorder",
            "interface": "DoseData",
        },
        "SafetyMgr->InjectorCtrl:CommandData": {
            "source": "SafetyMgr",
            "target": "InjectorCtrl",
            "interface": "CommandData",
        },
    }
    signal = next(e for e in entities if e.kind == "signal" and e.name == "Dose")
    assert signal.attributes == {"type": "uint32", "unit": "mg/cycle"}
    port = next(e for e in entities if e.kind == "port")
    assert port.attributes == {
        "owner": "InjectorCtrl",
        "interface": "CommandData",
        "direction": "requires",
    }
    flow = next(e for e in entities if e.kind == "flow")
    assert flow.attributes == {"source": "InjectorCtrl", "target": "Gateway"}
    for entity in entities:
        assert entity.evidence.encode() == pages[entity.location.page].encode()
        assert entity.sources
        for source in entity.sources:
            assert source["text"].encode() == pages[source["location"]["page"]].encode()
            assert source["location"]["line"] is None
    for number, raw in pages.items():
        assert any(b.text == raw and b.location == Location(page=number) for b in blocks)
        assert not any(b.text == " ".join(raw.split()) for b in blocks)


@pytest.mark.parametrize(
    "claim,code",
    [
        (
            ["InjectorCtrl component may provide DoseData interface", "to Gateway component."],
            "ambiguous_prose",
        ),
        (
            ["InjectorCtrl component never provides DoseData interface", "to Gateway component."],
            "ambiguous_prose",
        ),
        (
            [
                "If watchdog supervision is enabled, InjectorCtrl component provides",
                "DoseData interface to Gateway component.",
            ],
            "ambiguous_prose",
        ),
        (
            ["InjectorCtrl component arbitrates CalibrationData", "with Calibrator component."],
            "unsupported_relationship",
        ),
    ],
)
def test_warning_quotes_complete_original_page_with_qualifiers(claim, code):
    content = line_pdf(
        [
            ["Reference legend.", "Component: PowerStage"],
            ["Injection component inventory for release 31.5", *claim, "Engineering footer."],
        ]
    )
    pages = original_pages(content)
    _, entities, warnings = extract("own-qualified.pdf", content)
    warning = next(w for w in warnings if w["code"] == code)
    assert warning["severity"] == "blocking"
    assert warning["location"] == Location(page=2).model_dump()
    assert warning["text"].encode() == pages[2].encode()
    assert all(line in warning["text"] for line in claim)
    assert "Engineering footer." in warning["text"]
    assert not any(e.kind == "dependency" for e in entities)
    assert not any(e.name == "Injection" for e in entities)


def test_supported_then_unknown_clause_keeps_edge_and_raw_warning_context():
    content = line_pdf(
        [
            [
                "Metering component inventory (revision r23)",
                "InjectorCtrl component provides DoseData interface",
                "to Gateway and negotiates CalibrationData with Calibrator.",
            ]
        ]
    )
    raw = original_pages(content)[1]
    _, entities, warnings = extract("own-mixed-claim.pdf", content)
    edge = next(e for e in entities if e.kind == "dependency")
    assert edge.attributes == {
        "source": "InjectorCtrl",
        "target": "Gateway",
        "interface": "DoseData",
    }
    assert edge.evidence == raw
    warning = next(w for w in warnings if w["code"] == "unsupported_relationship")
    assert "negotiates" in warning["unresolved_actions"]
    assert "inventory" not in warning["unresolved_actions"]
    assert warning["text"] == raw and warning["severity"] == "blocking"


def test_repeated_literal_prose_keeps_distinct_page_contributors():
    lines = ["InjectorCtrl component provides DoseData interface", "to Gateway component."]
    content = line_pdf([lines, lines])
    pages = original_pages(content)
    assert pages[1] == pages[2]
    _, entities, warnings = extract("own-repeated.pdf", content)
    assert not warnings
    edge = next(e for e in entities if e.kind == "dependency")
    assert len(edge.sources) == 2
    assert {s["location"]["page"] for s in edge.sources} == {1, 2}
    assert all(s["text"].encode() == pages[s["location"]["page"]].encode() for s in edge.sources)


def mixed_fixture():
    stream = io.BytesIO()
    styles = getSampleStyleSheet()
    story = [Paragraph("Cooling component inventory for release 11.8", styles["Normal"])]
    component = Table(
        [["SWC Name", "Responsibility"], ["CoolantCtrl", "Maintains circulation\nwithin limits"]],
        colWidths=[150, 230],
    )
    interface = Table([["Interface Name", "Payload"], ["FlowData", "Flow"]], colWidths=[150, 230])
    for table in (component, interface):
        table.setStyle([("GRID", (0, 0), (-1, -1), 1, "black")])
    story.extend(
        [
            component,
            Paragraph(
                "CoolantCtrl component provides FlowData interface<br/>to Dashboard component.",
                styles["Normal"],
            ),
            PageBreak(),
            Paragraph("Cooling interface catalogue (revision r12)", styles["Normal"]),
            interface,
            Paragraph("FlowData interface carries Flow signal.", styles["Normal"]),
            Paragraph("Flow signal has type uint16 and unit L/min.", styles["Normal"]),
        ]
    )
    SimpleDocTemplate(stream).build(story)
    return stream.getvalue()


def test_mixed_table_and_prose_sources_are_literal_in_their_original_units():
    content = mixed_fixture()
    pages = original_pages(content)
    blocks, entities, warnings = extract("own-cooling.pdf", content)
    assert not warnings
    assert not any(e.name == "Cooling" for e in entities)
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for entity in entities:
            for source in entity.sources:
                location = source["location"]
                if location["table"] is None:
                    original = pages[location["page"]]
                else:
                    page = pdf.pages[location["page"] - 1]
                    table = page.find_tables()[location["table"] - 1]
                    original = page.crop(table.rows[location["row"] - 1].bbox).extract_text()
                assert source["text"].encode() == original.encode()
    coolant = next(e for e in entities if e.name == "CoolantCtrl")
    assert coolant.attributes == {"description": "Maintains circulation within limits"}
    assert {s["location"]["table"] is None for s in coolant.sources} == {True, False}
    flow = next(e for e in entities if e.kind == "signal" and e.name == "Flow")
    assert flow.attributes == {"type": "uint16", "unit": "L/min"}
    assert all(b.text != " ".join(raw.split()) for raw in pages.values() for b in blocks)


def test_literal_sources_survive_ingest_review_query_export_and_reopen(tmp_path, monkeypatch):
    monkeypatch.delenv("HLD_NAVIGATOR_OLLAMA_MODEL", raising=False)
    content = mixed_fixture()
    blocks, entities, warnings = extract("own-literal.pdf", content)
    assert not warnings
    path = str(tmp_path / "own-literal.db")
    app = create_app(path)
    store = app.state.store
    token = store.provision("dev", "own", "reviewer")
    document = store.ingest(
        "own",
        "Own literal provenance",
        "1",
        "own-literal.pdf",
        content,
        blocks,
        entities,
        warnings,
        "dev",
    )
    store.review("own", document, SourceReview(approved=True, reason="Own source"), "dev", True)
    for entity in store.entities("own", document):
        store.review("own", entity["id"], Review(status="approved", reason="Own source"), "dev")
    headers = {"Authorization": "Bearer " + token}
    with TestClient(app) as client:
        exported = client.get(
            "/workspaces/own/export", headers=headers, params={"document_id": document}
        )
        assert exported.status_code == 200, exported.text
        for saved in exported.json()["entities"]:
            expected = next(
                e for e in entities if e.kind == saved["kind"] and e.name == saved["name"]
            )
            assert saved["document_id"] == document
            assert saved["evidence"].encode() == expected.evidence.encode()
            assert saved["location"] == expected.location.model_dump()
            assert saved["attributes"] == expected.attributes
            assert {json.dumps(s, sort_keys=True) for s in saved["sources"]} == {
                json.dumps(s, sort_keys=True) for s in expected.sources
            }
        response = client.post(
            "/workspaces/own/query",
            headers=headers,
            json={"text": "CoolantCtrl", "document_id": document},
        )
        assert response.status_code == 200, response.text
        assert response.json()["evidence"]
        for source in response.json()["evidence"]:
            assert source["document_id"] == document and source["name"] == "own-literal.pdf"
            assert any(
                b.text == source["source_context"]["text"]
                and b.location.model_dump() == source["location"]
                for b in blocks
            )
    stored = store.entities("own", document)
    assert Store(path).entities("own", document) == stored


@pytest.mark.parametrize("suffix", [".md", ".txt"])
def test_markdown_and_text_keep_existing_exact_evidence(suffix):
    raw = "InjectorCtrl   component provides DoseData interface to Gateway."
    blocks, entities, warnings = extract("own-unmodified" + suffix, (raw + "\n").encode())
    assert not warnings
    assert all(e.evidence == raw and e.location.line == 1 for e in entities)
    assert blocks == [Block(text=raw, location=Location(line=1))]


def test_pdf_parser_binds_direct_original_page_without_quote_search():
    raw = "InjectorCtrl component provides DoseData interface\n   to Gateway component."
    source = Block(text=raw, location=Location(page=7))
    entities, warnings = parse_pdf_prose(source)
    assert not warnings
    assert entities
    assert all(
        e.evidence.encode() == raw.encode() and e.location == source.location for e in entities
    )
