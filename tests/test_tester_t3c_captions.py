"""New T3c synthetic R1 checks; all prior test oracles remain untouched."""

import importlib
import io
import json
from datetime import UTC, datetime
from pathlib import Path

import pdfplumber
import pytest
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas

from hld_navigator.extraction import extract
from hld_navigator.store import Store

EVIDENCE = (
    Path(__file__).resolve().parents[1]
    / "tester_acceptance/evidence"
    / datetime.now(UTC).strftime("t3c-synthetic-%Y%m%dT%H%M%S%f")
)
CAPTIONS = [
    "Mission component inventory for release 14.2",
    "Service interface catalogue (revision r6)",
    "Monitoring signal definitions (for version v3.1)",
    "Integration component, interface and signal summary: edition 2",
    "Architecture port overview",
    "Schedule flow and dependency index",
]
TABLE = (
    "\n| SWC Name | Responsibility |\n|---|---|\n"
    "|  Auriga | Processes requests |\n| Boreal | Receives requests |\n"
)
STATEMENTS = (
    "Auriga is a component.\nBoreal is a component.\n"
    "ControlBus is an interface.\nControlBus interface carries TorqueRequest signal.\n"
    "TorqueRequest signal uses data type uint16 with unit Nm.\n"
    "Auriga component provides the ControlBus interface to Boreal.\n"
    "Auriga component requires the ControlBus interface through port ControlIn.\n"
    "TorqueCycle flow runs from Auriga component to Boreal.\n"
)


def preserve(name, data):
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    path = EVIDENCE / name
    if isinstance(data, bytes):
        path.write_bytes(data)
    else:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def recorded(name, content):
    blocks, entities, warnings = extract(name, content)
    preserve(name, content)
    preserve(
        name + ".outputs.json",
        {
            "notice": "not independently validated",
            "blocks": [b.model_dump() for b in blocks],
            "entities": [e.model_dump() for e in entities],
            "warnings": warnings,
        },
    )
    return blocks, entities, warnings


@pytest.mark.parametrize("suffix", ["md", "txt"])
@pytest.mark.parametrize("caption", CAPTIONS)
def test_new_nominal_captions_keep_text_without_entities(caption, suffix):
    name = f"caption-{CAPTIONS.index(caption)}.{suffix}"
    blocks, entities, warnings = recorded(name, (caption + TABLE).encode())
    assert not warnings
    assert {(e.kind, e.name) for e in entities} == {
        ("component", "Auriga"),
        ("component", "Boreal"),
    }
    assert any(b.text == caption and b.location.line == 1 for b in blocks)
    for entity in entities:
        assert entity.location.table == 1
        assert entity.evidence in (caption + TABLE).splitlines()


@pytest.mark.parametrize("suffix", ["md", "txt"])
@pytest.mark.parametrize(
    "prefix",
    [
        "# Mission component inventory (version v7.2)\n",
        "Mission component inventory (version v7.2): ",
        "Mission component inventory (version v7.2). ",
    ],
)
def test_all_entity_types_and_attributes_survive_mixed_context(prefix, suffix):
    i = 0 if prefix.startswith("#") else 1 if prefix.endswith(": ") else 2
    original = prefix + STATEMENTS + TABLE
    _, entities, warnings = recorded(f"mixed-{i}.{suffix}", original.encode())
    assert not warnings
    facts = {(e.kind, e.name): e for e in entities}
    expected = {
        ("component", "Auriga"): {"description": "Processes requests"},
        ("component", "Boreal"): {"description": "Receives requests"},
        ("interface", "ControlBus"): {"payload": "TorqueRequest"},
        ("signal", "TorqueRequest"): {"type": "uint16", "unit": "Nm"},
        ("port", "ControlIn"): {
            "owner": "Auriga",
            "direction": "requires",
            "interface": "ControlBus",
        },
        ("dependency", "Auriga->Boreal:ControlBus"): {
            "source": "Auriga",
            "target": "Boreal",
            "interface": "ControlBus",
        },
        ("flow", "TorqueCycle"): {"source": "Auriga", "target": "Boreal"},
    }
    assert set(facts) == set(expected)
    for key, attributes in expected.items():
        entity = facts[key]
        assert entity.attributes == attributes
        assert entity.sources
        for source in entity.sources:
            line = source["location"]["line"]
            assert line is not None
            assert source["text"] == original.splitlines()[line - 1]
    auriga_sources = [s["text"] for s in facts[("component", "Auriga")].sources]
    assert any("Auriga is a component." in s for s in auriga_sources)
    assert "|  Auriga | Processes requests |" in auriga_sources


PDF_STATEMENTS = [
    None,
    "Auriga component provides the ControlBus interface to Boreal.",
    "Auriga component provides the ControlBus interface to Boreal and arbitrates TimingBudget.",
    "Auriga component may provide the ControlBus interface to Boreal.",
]


def pdf_source(statement):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(612, 792), invariant=1)
    for caption in [CAPTIONS[0], CAPTIONS[1]]:
        pdf.setFont("Helvetica", 8)
        pdf.drawString(42, 750, caption)
        for y in [716, 686, 628]:
            pdf.line(42, y, 566, y)
        for x in [42, 212, 566]:
            pdf.line(x, 628, x, 716)
        pdf.drawString(50, 699, "SWC Name")
        pdf.drawString(220, 699, "Responsibility")
        pdf.drawString(50, 663, "Auriga")
        pdf.drawString(220, 663, "Processes requests")
        pdf.drawString(220, 642, "within limits")
        if statement:
            pdf.drawString(42, 588, statement)
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()


@pytest.mark.parametrize(
    "statement", PDF_STATEMENTS, ids=["caption-only", "real", "real-plus-unknown", "qualified"]
)
def test_pdf_captions_and_every_contributing_source(statement):
    category = PDF_STATEMENTS.index(statement)
    content = pdf_source(statement)
    _, entities, warnings = recorded(f"mixed-{category}.pdf", content)
    expected_names = {("component", "Auriga")}
    if statement is not None and "may" not in statement:
        expected_names |= {
            ("component", "Boreal"),
            ("interface", "ControlBus"),
            ("dependency", "Auriga->Boreal:ControlBus"),
        }
    assert {(e.kind, e.name) for e in entities} == expected_names
    target = next(e for e in entities if e.name == "Auriga" and e.kind == "component")
    assert target.attributes == {"description": "Processes requests within limits"}
    audits = []
    with pdfplumber.open(io.BytesIO(content)) as original:
        pages = {i: page.extract_text() for i, page in enumerate(original.pages, 1)}
        for entity in entities:
            for source in entity.sources:
                location = source["location"]
                page = location["page"]
                assert page in pages
                if location["table"] is not None:
                    assert (location["table"], location["row"]) == (1, 2)
                    independently_captured = (
                        original.pages[page - 1].crop((42, 106, 566, 164)).extract_text()
                    )
                    assert source["text"] == independently_captured
                    representation = "exact original table-row span"
                else:
                    independently_captured = pages[page]
                    assert source["text"] == independently_captured
                    assert statement is not None and statement in pages[page]
                    representation = "literal complete original extracted page context"
                audits.append(
                    {
                        "entity": [entity.kind, entity.name],
                        "source": source,
                        "original_page_text": pages[page],
                        "independently_captured": independently_captured,
                        "representation": representation,
                        "literal_substring_of_original_page_text": source["text"] in pages[page],
                    }
                )
        for warning in warnings:
            page = warning["location"]["page"]
            assert page in pages and statement is not None
            assert statement in warning["text"] and statement in pages[page]
    preserve(f"mixed-{category}.source-audit.json", audits)
    table_refs = [s for s in target.sources if s["location"]["table"] is not None]
    assert sorted(
        (s["location"]["page"], s["location"]["table"], s["location"]["row"]) for s in table_refs
    ) == [(1, 1, 2), (2, 1, 2)]
    if statement is None or statement == PDF_STATEMENTS[1]:
        assert not warnings
    else:
        code = "ambiguous_prose" if "may" in statement else "unsupported_relationship"
        assert all(
            any(
                w["code"] == code and w["severity"] == "blocking" and w["location"]["page"] == page
                for w in warnings
            )
            for page in [1, 2]
        )


@pytest.mark.parametrize(
    "statement,expected_export",
    [
        (None, 200),
        ("Auriga component arbitrates TimingBudget.", 409),
        ("Auriga component may provide the ControlBus interface to Boreal.", 409),
    ],
)
def test_api_review_export_and_reopen_with_caption(
    statement, expected_export, tmp_path, monkeypatch
):
    import hld_navigator.store as store_module

    category = "benign" if statement is None else "qualified" if "may" in statement else "unknown"
    source = CAPTIONS[0] + ("\n" + statement if statement else "") + TABLE
    preserve(f"api-{category}.md", source.encode())
    db_path = tmp_path / "t3c.sqlite"
    monkeypatch.setattr(store_module, "Store", lambda *a, **kw: Store(str(db_path)))
    module = importlib.import_module("hld_navigator.app")
    monkeypatch.setattr(module, "Store", Store)
    app = module.create_app(str(db_path))
    token = Store(str(db_path)).provision("tester", "tester", "reviewer")
    records = []
    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as client:
        upload = client.post(
            "/workspaces/tester/documents",
            data={"title": "T3c synthetic", "version": "1"},
            files={"file": ("t3c.md", source.encode(), "text/markdown")},
        )
        records.append({"route": "upload", "status": upload.status_code, "body": upload.json()})
        preserve(f"api-{category}.json", records)
        assert upload.status_code == 200
        doc = upload.json()["id"]
        if statement is None:
            assert not upload.json()["warnings"]
        source_review = client.post(
            f"/workspaces/tester/documents/{doc}/review",
            json={"approved": True, "reason": "synthetic"},
        )
        records.append(
            {
                "route": "source-review",
                "status": source_review.status_code,
                "body": source_review.json(),
            }
        )
        assert source_review.status_code == 200
        response = client.get("/workspaces/tester/entities", params={"document_id": doc})
        items = response.json()
        records.append({"route": "entities", "status": response.status_code, "body": items})
        assert {(e["kind"], e["name"]) for e in items} == {
            ("component", "Auriga"),
            ("component", "Boreal"),
        }
        for item in items:
            decision = client.post(
                f"/workspaces/tester/entities/{item['id']}/review",
                json={"status": "approved", "reason": "synthetic"},
            )
            records.append(
                {"route": "entity-review", "status": decision.status_code, "body": decision.json()}
            )
            assert decision.status_code == 200
        exported = client.get("/workspaces/tester/export", params={"document_id": doc})
        records.append({"route": "export", "status": exported.status_code, "body": exported.json()})
        preserve(f"api-{category}.json", records)
        assert exported.status_code == expected_export
    reopened = Store(str(db_path))
    found = reopened.entities("tester", doc, approved_only=True)
    retrieved = reopened.eligible_blocks("tester", doc)
    preserve(f"api-{category}.reopened.json", {"entities": found, "retrieval": retrieved})
    assert [(e["name"], e["attributes"], e["sources"]) for e in found] == [
        (e["name"], e["attributes"], e["sources"]) for e in items
    ]
    for block in retrieved:
        assert block["source_context"]["text"] == source.splitlines()[block["location"]["line"] - 1]
