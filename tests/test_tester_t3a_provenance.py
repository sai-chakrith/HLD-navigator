"""Independent T3a reproductions, using only new synthetic source documents."""

import importlib
import io
import json
from datetime import UTC, datetime
from pathlib import Path

import pdfplumber
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas

from hld_navigator.extraction import extract
from hld_navigator.models import Review, SourceReview
from hld_navigator.store import Store

EVIDENCE = (
    Path(__file__).resolve().parents[1]
    / "tester_acceptance/evidence"
    / datetime.now(UTC).strftime("t3a-synthetic-%Y%m%dT%H%M%S%f")
)
RAW_ROW = "|  Brake  |  Stops safely  |"
MARKDOWN = (
    "# Inventory\n| SWC Name | Responsibility |\n|---|---|\n"
    f"{RAW_ROW}\n{RAW_ROW}\n\n# Repeat\n"
    "| SWC Name | Responsibility |\n|---|---|\n" + RAW_ROW + "\n"
)


def preserve(name, data):
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    path = EVIDENCE / name
    if isinstance(data, bytes):
        path.write_bytes(data)
    else:
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def parsed(name, content):
    blocks, entities, issues = extract(name, content)
    preserve(name, content)
    preserve(
        name + ".extracted.json",
        {
            "notice": "not independently validated",
            "blocks": [b.model_dump() for b in blocks],
            "entities": [e.model_dump() for e in entities],
            "warnings": issues,
        },
    )
    return blocks, entities, issues


def pdf_fixture():
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(612, 792), invariant=1)
    for page, row_count in [(1, 2), (2, 1)]:
        pdf.setFont("Helvetica", 11)
        pdf.drawString(50, 755, f"Tester synthetic component inventory - page {page}")
        edges = [720, 690] + [690 - 48 * i for i in range(1, row_count + 1)]
        for y in edges:
            pdf.line(50, y, 550, y)
        for x in [50, 210, 550]:
            pdf.line(x, edges[-1], x, 720)
        pdf.drawString(58, 703, "SWC Name")
        pdf.drawString(218, 703, "Responsibility")
        for i in range(row_count):
            y = 674 - 48 * i
            pdf.drawString(58, y, "Brake")
            pdf.drawString(218, y, "Stops safely")
            pdf.drawString(218, y - 14, "under command")
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def test_markdown_exact_spacing_locations_multiplicity():
    blocks, entities, issues = parsed("independent.md", MARKDOWN.encode())
    assert not issues
    assert len(entities) == 1
    entity = entities[0]
    assert entity.kind == "component" and entity.name == "Brake"
    assert entity.attributes == {"description": "Stops safely"}
    assert entity.evidence == RAW_ROW
    expected = [(1, 3, 4, "Inventory"), (1, 4, 5, "Inventory"), (2, 3, 10, "Repeat")]
    actual = [
        (
            s["location"]["table"],
            s["location"]["row"],
            s["location"]["line"],
            s["location"]["section"],
        )
        for s in entity.sources
    ]
    assert sorted(actual) == expected
    for source in entity.sources:
        assert source["text"] == MARKDOWN.splitlines()[source["location"]["line"] - 1]
    assert all(b.text != "COMPONENT Brake description=Stops safely" for b in blocks)


def test_pdf_multiline_original_spans_across_pages():
    content = pdf_fixture()
    _, entities, issues = parsed("independent.pdf", content)
    assert not issues
    assert_pdf_spans(content, entities)


def test_pdf_core_spans_retaining_incidental_warnings():
    content = pdf_fixture()
    _, entities, _ = parsed("independent.pdf", content)
    # Separate core provenance from the unchanged failing no-warning requirement above.
    assert_pdf_spans(content, entities)


def assert_pdf_spans(content, entities):
    assert len(entities) == 1
    entity = entities[0]
    assert entity.attributes == {"description": "Stops safely under command"}
    sources = entity.sources
    assert sorted(
        (s["location"]["page"], s["location"]["table"], s["location"]["row"]) for s in sources
    ) == [(1, 1, 2), (1, 1, 3), (2, 1, 2)]
    independently_captured = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page, rows in [(1, 2), (2, 1)]:
            for i in range(rows):
                # Coordinates come from our authoring geometry, not candidate table boxes.
                original = (
                    pdf.pages[page - 1].crop((50, 102 + 48 * i, 550, 150 + 48 * i)).extract_text()
                )
                independently_captured.append({"page": page, "row": i + 2, "text": original})
                matching = [
                    s
                    for s in sources
                    if s["location"]["page"] == page and s["location"]["row"] == i + 2
                ]
                assert len(matching) == 1
                assert matching[0]["text"] == original == "Brake Stops safely\nunder command"
    preserve("independent-pdf-original-spans.json", independently_captured)


def test_port_aliases_do_not_replace_raw_row():
    content = (
        b"# Port Inventory\n| Component | Port Name | Port Kind | Interface |\n"
        b"|---|---|---|---|\n|  Brake | Cmd | P-Port | ICommand |\n"
        b"| Brake | State | R-Port | IStatus |\n"
    )
    _, entities, issues = parsed("aliases.md", content)
    assert not issues
    assert {e.name: e.attributes for e in entities} == {
        "Cmd": {"owner": "Brake", "direction": "provides", "interface": "ICommand"},
        "State": {"owner": "Brake", "direction": "requires", "interface": "IStatus"},
    }
    for entity in entities:
        assert entity.evidence == content.decode().splitlines()[entity.location.line - 1]


def test_bad_populated_columns_and_invalid_directions_warn():
    fixtures = [
        b"| SWC Name | Mystery |\n|---|---|\n| Brake | unsupported |\n",
        b"| Component | Port | Direction | Interface |\n|---|---|---|---|\n"
        b"| Brake | Cmd | sideways | ICommand |\n",
    ]
    for i, content in enumerate(fixtures):
        _, entities, issues = parsed(f"invalid-{i}.md", content)
        assert issues, "unsupported/invalid populated row silently dropped"
        assert not entities
        assert any(w["severity"] == "blocking" for w in issues)


def test_uncapturable_pdf_row_warns_without_quote(monkeypatch):
    from pdfplumber.page import CroppedPage

    monkeypatch.setattr(CroppedPage, "extract_text", lambda *a, **kw: "")
    _, entities, issues = parsed("uncapturable.pdf", pdf_fixture())
    assert not [e for e in entities if e.location.table]
    assert any(
        w["code"] == "unsupported_table" and w["message"] == "Table row has no captured source text"
        for w in issues
    )


def test_db_lineage_review_retrieval_and_reopen(tmp_path):
    blocks, entities, issues = parsed("stored.md", MARKDOWN.encode())
    path = tmp_path / "lineage.sqlite"
    store = Store(str(path))
    doc = store.ingest(
        "tester",
        "Independent miniature",
        "1",
        "stored.md",
        MARKDOWN.encode(),
        blocks,
        entities,
        issues,
        "tester",
    )
    assert not store.eligible_blocks("tester", doc)
    entity = store.entities("tester", doc)[0]
    store.review(
        "tester", doc, SourceReview(approved=True, reason="synthetic"), "tester", source=True
    )
    store.review("tester", entity["id"], Review(status="approved", reason="synthetic"), "tester")
    with store.connection() as db:
        linked = [
            dict(r)
            for r in db.execute(
                "SELECT b.text,b.location FROM entity_evidence ee "
                "JOIN blocks b ON b.id=ee.block_id "
                "WHERE ee.entity_id=?",
                (entity["id"],),
            )
        ]
    preserve("db-links.json", linked)
    assert len(linked) == 3
    assert {json.loads(r["location"])["line"] for r in linked} == {4, 5, 10}
    assert all(json.loads(r["location"])["table"] is not None for r in linked)
    reopened = Store(str(path))
    retrieved = reopened.eligible_blocks("tester", doc)
    preserve("reopened-retrieval.json", retrieved)
    assert len(retrieved) == 3
    assert all(r["source_context"]["text"] == RAW_ROW for r in retrieved)
    assert reopened.entities("tester", doc)[0]["sources"] == entity["sources"]
    preserve("lineage.sqlite", path.read_bytes())


def test_api_export_preserves_sources(tmp_path, monkeypatch):
    import hld_navigator.store as store_module

    db_path = tmp_path / "api.sqlite"
    # Isolate the default app on first import; explicit factory uses the same fresh DB.
    monkeypatch.setattr(store_module, "Store", lambda *a, **kw: Store(str(db_path)))
    module = importlib.import_module("hld_navigator.app")
    monkeypatch.setattr(module, "Store", Store)
    app = module.create_app(str(db_path))
    store = Store(str(db_path))
    token = store.provision("tester", "tester", "reviewer")
    headers = {"Authorization": f"Bearer {token}"}
    records = []
    with TestClient(app, headers=headers) as client:
        uploaded = client.post(
            "/workspaces/tester/documents",
            data={"title": "Miniature", "version": "1"},
            files={"file": ("api.md", MARKDOWN.encode(), "text/markdown")},
        )
        records.append({"upload_status": uploaded.status_code, "upload": uploaded.json()})
        preserve("api-responses.json", records)
        assert uploaded.status_code == 200
        doc = uploaded.json()["id"]
        found = client.get("/workspaces/tester/entities", params={"document_id": doc}).json()
        records.append({"entities": found})
        preserve("api-responses.json", records)
        source_review = client.post(
            f"/workspaces/tester/documents/{doc}/review",
            json={"approved": True, "reason": "synthetic"},
        )
        assert source_review.status_code == 200
        # Response schema is discovered from the API, never Developer test code.
        items = found if isinstance(found, list) else found["entities"]
        for item in items:
            reviewed = client.post(
                f"/workspaces/tester/entities/{item['id']}/review",
                json={"status": "approved", "reason": "synthetic"},
            )
            assert reviewed.status_code == 200
        exported = client.get("/workspaces/tester/export", params={"document_id": doc})
        records.append({"export_status": exported.status_code, "export": exported.json()})
        preserve("api-responses.json", records)
        assert exported.status_code == 200
        output = exported.json()
        export_items = output if isinstance(output, list) else output["entities"]
        assert len(export_items) == 1
        assert export_items[0]["evidence"] == RAW_ROW
        assert len(export_items[0]["sources"]) == 3


def test_pdf_db_reopen_links_only_correct_rows(tmp_path):
    content = pdf_fixture()
    blocks, entities, issues = parsed("pdf-db.pdf", content)
    path = tmp_path / "pdf-lineage.sqlite"
    store = Store(str(path))
    document = store.ingest(
        "tester", "PDF miniature", "1", "pdf-db.pdf", content, blocks, entities, issues, "tester"
    )
    entity = store.entities("tester", document)[0]
    store.review(
        "tester", document, SourceReview(approved=True, reason="synthetic"), "tester", source=True
    )
    store.review("tester", entity["id"], Review(status="approved", reason="synthetic"), "tester")
    reopened = Store(str(path))
    linked = reopened.eligible_blocks("tester", document)
    preserve("pdf-reopened-retrieval.json", linked)
    assert len(linked) == 3
    assert sorted(
        (r["location"]["page"], r["location"]["table"], r["location"]["row"]) for r in linked
    ) == [(1, 1, 2), (1, 1, 3), (2, 1, 2)]
    assert all(r["source_context"]["text"] == "Brake Stops safely\nunder command" for r in linked)
    preserve("pdf-lineage.sqlite", path.read_bytes())
