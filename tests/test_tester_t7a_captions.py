"""T7a: independent new synthetic caption and relationship probes; no heldout access."""

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
    / datetime.now(UTC).strftime("t7a-synthetic-%Y%m%dT%H%M%S%f")
)
TABLE = "\n| SWC Name | Responsibility |\n|---|---|\n|  Aster | Monitors pressure |\n"
CAPTIONS = [
    "Plant component inventory - revision 7",
    "Deployment component catalogue: release 7",
    "Application component table – revision 8",
    "Integration component overview",
    "Control component and interface summary: edition 2",
    "Platform port inventory - edition 5",
    "Signal interface list: schema 9",
    "Subsystem component inventory for release 4",
    "Platform component inventory (release 4)",
]
UNSUPPORTED = [
    "Aster component arbitrates GateBudget.",
    "Aster component provides the IAct interface to Lumen and arbitrates GateBudget.",
    "Subsystem component inventory routes telemetry to Lumen.",
    "Subsystem component inventory Routes telemetry to Lumen.",
    "Platform component inventory; Aster component arbitrates GateBudget.",
    "Platform component inventory: Aster component exchanges telemetry with Lumen.",
    "# Platform component inventory\nAster component arbitrates GateBudget.",
    "# Platform component inventory\n"
    "Aster component provides the IAct interface to Lumen and arbitrates GateBudget.",
]
QUALIFIED = [
    "Aster component does not provide the IAct interface to Lumen.",
    "If startup is complete, Aster component provides the IAct interface to Lumen.",
    "Aster component may provide the IAct interface to Lumen.",
    "Aster component provides the IAct interface to Lumen unless calibration is pending.",
]


def preserve(name, value):
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    path = EVIDENCE / name
    if isinstance(value, bytes):
        path.write_bytes(value)
    else:
        path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def extract_record(name, content):
    preserve(name, content)
    blocks, entities, warnings = extract(name, content)
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
@pytest.mark.parametrize("caption", CAPTIONS, ids=[f"caption-{i}" for i in range(len(CAPTIONS))])
def test_new_benign_captions_are_not_actions(caption, suffix):
    i = CAPTIONS.index(caption)
    source = (caption + TABLE).encode()
    _, entities, warnings = extract_record(f"benign-{i}.{suffix}", source)
    assert len(entities) == 1
    assert entities[0].name == "Aster"
    assert entities[0].attributes == {"description": "Monitors pressure"}
    assert entities[0].evidence == "|  Aster | Monitors pressure |"
    assert not warnings, f"benign nominal caption warned: {caption!r}"


@pytest.mark.parametrize(
    "statement", UNSUPPORTED, ids=[f"unsupported-{i}" for i in range(len(UNSUPPORTED))]
)
def test_unknown_supported_then_unknown_and_near_caption_continuations(statement):
    i = UNSUPPORTED.index(statement)
    _, entities, warnings = extract_record(f"unsupported-{i}.md", (statement + TABLE).encode())
    blocking = [
        w
        for w in warnings
        if w["severity"] == "blocking" and w["code"] == "unsupported_relationship"
    ]
    assert blocking, f"unsupported relationship disappeared: {statement!r}"
    expected_line = 2 if statement.startswith("#") else 1
    original = statement.splitlines()[-1]
    assert any(w["text"] == original and w["location"]["line"] == expected_line for w in blocking)
    assert not [e for e in entities if e.kind == "dependency" and "GateBudget" in e.name]
    if "provides the IAct interface" in statement:
        assert any(
            e.kind == "dependency"
            and e.attributes == {"source": "Aster", "target": "Lumen", "interface": "IAct"}
            for e in entities
        )


@pytest.mark.parametrize(
    "statement", QUALIFIED, ids=[f"qualified-{i}" for i in range(len(QUALIFIED))]
)
def test_qualified_relationships_do_not_become_unconditional(statement):
    i = QUALIFIED.index(statement)
    _, entities, warnings = extract_record(f"qualified-{i}.txt", (statement + TABLE).encode())
    assert any(
        w["code"] == "ambiguous_prose"
        and w["severity"] == "blocking"
        and w["text"] == statement
        and w["location"]["line"] == 1
        for w in warnings
    )
    assert not [e for e in entities if e.kind in ("dependency", "port", "interface")]


def pdf_source(statement=None):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(612, 792), invariant=1)
    captions = [
        "Plant component inventory - revision 7",
        "Deployment component catalogue: release 7",
    ]
    for caption in captions:
        pdf.setFont("Helvetica", 10)
        pdf.drawString(60, 748, caption)
        for y in [710, 680, 630]:
            pdf.line(60, y, 560, y)
        for x in [60, 200, 560]:
            pdf.line(x, 630, x, 710)
        pdf.drawString(68, 692, "SWC Name")
        pdf.drawString(208, 692, "Responsibility")
        pdf.drawString(68, 660, "Aster")
        pdf.drawString(208, 660, "Monitors pressure")
        pdf.drawString(208, 646, "within limits")
        if statement:
            pdf.drawString(60, 600, statement)
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()


@pytest.mark.parametrize(
    "statement",
    [None, UNSUPPORTED[0], QUALIFIED[2]],
    ids=["benign", "unknown-on-table-pages", "qualified-on-table-pages"],
)
def test_new_pdf_captions_do_not_hide_real_statements(statement):
    from tester_acceptance.t2c_oracles import (
        partition_contributors,
        verify_contributors,
        verify_warnings,
    )

    category = "benign" if statement is None else "qualified" if "may" in statement else "unknown"
    content = pdf_source(statement)
    _, entities, warnings = extract_record(f"multipage-{category}.pdf", content)
    assert len(entities) == 1
    assert entities[0].kind == "component"
    assert entities[0].name == "Aster"
    assert entities[0].attributes == {"description": "Monitors pressure within limits"}
    table_sources, _ = partition_contributors(
        entities[0].sources, require_context=category == "unknown"
    )
    assert sorted(
        (s["location"]["page"], s["location"]["table"], s["location"]["row"]) for s in table_sources
    ) == [(1, 1, 2), (2, 1, 2)]
    original_spans = []
    original_pages, row_spans = {}, {}
    with pdfplumber.open(io.BytesIO(content)) as original_pdf:
        for page in [1, 2]:
            span = original_pdf.pages[page - 1].crop((60, 112, 560, 162)).extract_text()
            original_pages[page] = original_pdf.pages[page - 1].extract_text()
            row_spans[page] = span
            original_spans.append({"page": page, "row": 2, "text": span})
            source = next(
                s
                for s in table_sources
                if (s["location"]["page"], s["location"]["table"], s["location"]["row"])
                == (page, 1, 2)
            )
            assert source["text"] == span == "Aster Monitors pressure\nwithin limits"
    preserve(f"multipage-{category}.original-spans.json", original_spans)
    characterization = verify_contributors(
        entities[0].sources,
        require_context=category == "unknown",
        originals=original_pages,
        row_spans=row_spans,
        statement=statement,
    )
    preserve(
        f"multipage-{category}.evidence-characterization.json",
        {
            "notice": "not independently validated",
            "contributors": [c.model_dump() for c in characterization],
            "literal_mechanical_gate_met": all(
                c.literal_original_substring for c in characterization
            ),
            "gap_task": next((c.gap_task for c in characterization if c.gap_task), None),
        },
    )
    if statement is None:
        assert not warnings
    else:
        code = "ambiguous_prose" if category == "qualified" else "unsupported_relationship"
        warning_checks = verify_warnings(
            warnings, statement=statement, code=code, originals=original_pages
        )
        preserve(f"multipage-{category}.warning-context-checks.json", warning_checks)


@pytest.mark.parametrize("caption", [CAPTIONS[0], CAPTIONS[7]])
def test_api_warning_and_export_behavior_for_benign_captions(caption, tmp_path, monkeypatch):
    import hld_navigator.store as store_module

    db_path = tmp_path / "isolated-t7a.sqlite"
    monkeypatch.setattr(store_module, "Store", lambda *a, **kw: Store(str(db_path)))
    module = importlib.import_module("hld_navigator.app")
    monkeypatch.setattr(module, "Store", Store)
    app = module.create_app(str(db_path))
    token = Store(str(db_path)).provision("tester", "tester", "reviewer")
    records = []
    i = CAPTIONS.index(caption)
    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as client:
        uploaded = client.post(
            "/workspaces/tester/documents",
            data={"title": "New synthetic caption", "version": "1"},
            files={"file": ("new.md", (caption + TABLE).encode(), "text/markdown")},
        )
        records.append({"route": "upload", "status": uploaded.status_code, "body": uploaded.json()})
        preserve(f"api-{i}.json", records)
        assert uploaded.status_code == 200
        doc = uploaded.json()["id"]
        source = client.post(
            f"/workspaces/tester/documents/{doc}/review",
            json={"approved": True, "reason": "Tester synthetic source"},
        )
        records.append(
            {"route": "source-review", "status": source.status_code, "body": source.json()}
        )
        assert source.status_code == 200
        response = client.get("/workspaces/tester/entities", params={"document_id": doc})
        found = response.json()
        records.append({"route": "entities", "status": response.status_code, "body": found})
        for entity in found:
            reviewed = client.post(
                f"/workspaces/tester/entities/{entity['id']}/review",
                json={"status": "approved", "reason": "Tester synthetic fact"},
            )
            records.append(
                {"route": "entity-review", "status": reviewed.status_code, "body": reviewed.json()}
            )
            assert reviewed.status_code == 200
        exported = client.get("/workspaces/tester/export", params={"document_id": doc})
        records.append({"route": "export", "status": exported.status_code, "body": exported.json()})
        preserve(f"api-{i}.json", records)
        assert exported.status_code == 200, "benign caption blocks reviewed export"
        assert not uploaded.json()["warnings"]
