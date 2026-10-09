"""New scoped R2 checks for cycle1; prior strict R1/source-granularity checks are untouched."""

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
    / datetime.now(UTC).strftime("t7a-cycle1-synthetic-%Y%m%dT%H%M%S%f")
)
TABLE = "\n| SWC Name | Responsibility |\n|---|---|\n|  Lyrik | Records events |\n"
CAPTIONS = [
    "Fleet component inventory for release 12.7",
    "Subsystem component inventory (release 4)",
    "Runtime component catalogue version 2.5",
    "Integration component table (revision r6)",
    "Build component inventory (for version v8.2)",
    "Package component definitions revision: 9",
    "Operational component inventory for revision 7-2",
    "Lab component inventory",
]
UNKNOWN = [
    "Fleet component inventory for release 12.7 routes telemetry to Mistral.",
    "Fleet component inventory (version v8.2) and arbitrates RateBudget.",
    "Fleet component inventory (release 4) synchronizes Lyrik.",
    "Fleet component inventory for release 12.7; "
    "Lyrik component provides the ILog interface to Mistral and arbitrates RateBudget.",
    "# Runtime component inventory (version 2.5)\nLyrik component arbitrates RateBudget.",
    "# Build component inventory for revision 8\n"
    "Lyrik component provides the ILog interface to Mistral and arbitrates RateBudget.",
]
QUALIFIED = [
    "Lyrik component does not provide the ILog interface to Mistral.",
    "If startup is complete, Lyrik component provides the ILog interface to Mistral.",
    "# Runtime component inventory (version 2.5)\n"
    "Lyrik component may provide the ILog interface to Mistral.",
    "Fleet component inventory for release 12.7 while "
    "Lyrik component provides the ILog interface to Mistral.",
]


def preserve(name, value):
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    path = EVIDENCE / name
    if isinstance(value, bytes):
        path.write_bytes(value)
    else:
        path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def recorded(name, content):
    preserve(name, content)
    blocks, facts, warnings = extract(name, content)
    preserve(
        name + ".outputs.json",
        {
            "notice": "not independently validated",
            "blocks": [b.model_dump() for b in blocks],
            "entities": [e.model_dump() for e in facts],
            "warnings": warnings,
        },
    )
    return facts, warnings


@pytest.mark.parametrize("suffix", ["md", "txt"])
@pytest.mark.parametrize("caption", CAPTIONS, ids=[f"caption-{i}" for i in range(len(CAPTIONS))])
def test_numeric_and_parenthesized_caption_warning_behavior(caption, suffix):
    facts, warnings = recorded(
        f"caption-{CAPTIONS.index(caption)}.{suffix}", (caption + TABLE).encode()
    )
    assert not warnings
    # R1 total-entity assertions remain in the old test file; this check concerns R2.
    table_facts = [f for f in facts if f.name == "Lyrik" and f.kind == "component"]
    assert len(table_facts) == 1
    assert table_facts[0].attributes == {"description": "Records events"}
    assert table_facts[0].evidence == "|  Lyrik | Records events |"


@pytest.mark.parametrize("statement", UNKNOWN, ids=[f"unknown-{i}" for i in range(len(UNKNOWN))])
def test_real_continuations_and_adjacent_unknown_clauses_still_warn(statement):
    facts, warnings = recorded(
        f"unknown-{UNKNOWN.index(statement)}.md", (statement + TABLE).encode()
    )
    original = statement.splitlines()[-1]
    line = len(statement.splitlines())
    assert any(
        w["code"] == "unsupported_relationship"
        and w["severity"] == "blocking"
        and w["text"] == original
        and w["location"]["line"] == line
        for w in warnings
    )
    assert not [f for f in facts if f.kind == "dependency" and "RateBudget" in f.name]
    if "provides the ILog interface" in statement:
        assert any(
            f.kind == "dependency"
            and f.attributes == {"source": "Lyrik", "target": "Mistral", "interface": "ILog"}
            for f in facts
        )


@pytest.mark.parametrize(
    "statement", QUALIFIED, ids=[f"qualified-{i}" for i in range(len(QUALIFIED))]
)
def test_modifier_headings_do_not_remove_qualified_warnings(statement):
    facts, warnings = recorded(
        f"qualified-{QUALIFIED.index(statement)}.txt", (statement + TABLE).encode()
    )
    assert any(
        w["code"] == "ambiguous_prose"
        and w["severity"] == "blocking"
        and w["text"] == statement.splitlines()[-1]
        and w["location"]["line"] == len(statement.splitlines())
        for w in warnings
    )
    assert not [f for f in facts if f.kind in ("dependency", "port", "interface")]


def pdf_source(statement):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(612, 792), invariant=1)
    for caption in [CAPTIONS[0], CAPTIONS[4]]:
        pdf.setFont("Helvetica", 9)
        pdf.drawString(55, 752, caption)
        for y in [710, 680, 626]:
            pdf.line(55, y, 557, y)
        for x in [55, 195, 557]:
            pdf.line(x, 626, x, 710)
        pdf.drawString(63, 695, "SWC Name")
        pdf.drawString(203, 695, "Responsibility")
        pdf.drawString(63, 661, "Lyrik")
        pdf.drawString(203, 661, "Records events")
        pdf.drawString(203, 644, "within limits")
        if statement:
            pdf.drawString(55, 596, statement)
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()


@pytest.mark.parametrize(
    "statement",
    [
        None,
        "Lyrik component arbitrates RateBudget.",
        "Lyrik component may provide the ILog interface to Mistral.",
    ],
    ids=["benign", "unsupported", "qualified"],
)
def test_modifier_pdf_tables_and_real_statements(statement):
    category = "benign" if statement is None else "qualified" if "may" in statement else "unknown"
    content = pdf_source(statement)
    facts, warnings = recorded(f"modifier-{category}.pdf", content)
    targets = [f for f in facts if f.kind == "component" and f.name == "Lyrik"]
    assert len(targets) == 1
    assert targets[0].attributes == {"description": "Records events within limits"}
    rows = []
    with pdfplumber.open(io.BytesIO(content)) as original:
        for page_number, page in enumerate(original.pages, 1):
            raw_span = page.crop((55, 112, 557, 166)).extract_text()
            sources = [
                s
                for s in targets[0].sources
                if s["location"]["page"] == page_number and s["location"]["table"] is not None
            ]
            rows.append(
                {
                    "page": page_number,
                    "original_page_text": page.extract_text(),
                    "original_row_span": raw_span,
                    "complete_target": targets[0].model_dump(),
                }
            )
            preserve(f"modifier-{category}.original-spans.json", rows)
            assert len(sources) == 1
            assert sources[0]["text"] == raw_span == "Lyrik Records events\nwithin limits"
            assert (sources[0]["location"]["table"], sources[0]["location"]["row"]) == (1, 2)
            if statement:
                code = "ambiguous_prose" if category == "qualified" else "unsupported_relationship"
                assert statement in page.extract_text()
                assert any(
                    w["code"] == code
                    and w["severity"] == "blocking"
                    and statement in w["text"]
                    and w["location"]["page"] == page_number
                    for w in warnings
                )
    if statement is None:
        assert not warnings
    if category == "qualified":
        assert not [f for f in facts if f.kind in ("dependency", "port", "interface")]


@pytest.mark.parametrize(
    "caption,statement,expected_status",
    [
        (CAPTIONS[0], None, 200),
        (CAPTIONS[1], None, 200),
        (CAPTIONS[4], "Lyrik component arbitrates RateBudget.", 409),
    ],
)
def test_reviewed_export_after_modifier_caption(
    caption, statement, expected_status, tmp_path, monkeypatch
):
    import hld_navigator.store as store_module

    index = CAPTIONS.index(caption)
    source = caption + ("\n" + statement if statement else "") + TABLE
    preserve(f"api-source-{index}.md", source.encode())
    db_path = tmp_path / "cycle1.sqlite"
    monkeypatch.setattr(store_module, "Store", lambda *a, **kw: Store(str(db_path)))
    module = importlib.import_module("hld_navigator.app")
    monkeypatch.setattr(module, "Store", Store)
    app = module.create_app(str(db_path))
    token = Store(str(db_path)).provision("tester", "tester", "reviewer")
    records = []
    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as client:
        upload = client.post(
            "/workspaces/tester/documents",
            data={"title": "Cycle1 synthetic", "version": "1"},
            files={"file": ("cycle1.md", source.encode(), "text/markdown")},
        )
        records.append({"route": "upload", "status": upload.status_code, "body": upload.json()})
        preserve(f"api-{index}.json", records)
        assert upload.status_code == 200
        doc = upload.json()["id"]
        if statement is None:
            assert not upload.json()["warnings"]
        else:
            assert any(w["code"] == "unsupported_relationship" for w in upload.json()["warnings"])
        approved = client.post(
            f"/workspaces/tester/documents/{doc}/review",
            json={"approved": True, "reason": "synthetic source"},
        )
        records.append(
            {"route": "source-review", "status": approved.status_code, "body": approved.json()}
        )
        assert approved.status_code == 200
        entities = client.get("/workspaces/tester/entities", params={"document_id": doc})
        records.append(
            {"route": "entities", "status": entities.status_code, "body": entities.json()}
        )
        for entity in entities.json():
            reviewed = client.post(
                f"/workspaces/tester/entities/{entity['id']}/review",
                json={"status": "approved", "reason": "synthetic fact"},
            )
            records.append(
                {"route": "entity-review", "status": reviewed.status_code, "body": reviewed.json()}
            )
            assert reviewed.status_code == 200
        exported = client.get("/workspaces/tester/export", params={"document_id": doc})
        records.append({"route": "export", "status": exported.status_code, "body": exported.json()})
        preserve(f"api-{index}.json", records)
        assert exported.status_code == expected_status
