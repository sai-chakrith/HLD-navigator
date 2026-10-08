"""Developer-owned T3b2 occurrence, validation, rollback and legacy checks."""

import io
import sqlite3

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Table

from hld_navigator.app import create_app
from hld_navigator.extraction import extract
from hld_navigator.models import Block, Entity, EvidenceSource, Location, Review, SourceReview
from hld_navigator.store import ProvenanceError, Store


def prose_pdf(text):
    stream = io.BytesIO()
    styles = getSampleStyleSheet()
    SimpleDocTemplate(stream).build(
        [Paragraph(text, styles["Normal"]), PageBreak(), Paragraph(text, styles["Normal"])]
    )
    return stream.getvalue()


def table_pdf():
    stream = io.BytesIO()
    story = []
    for page in (1, 2):
        if page == 2:
            story.append(PageBreak())
        table = Table(
            [["SWC Name", "Responsibility"], ["ValveCtrl", "Regulates pressure"]],
            colWidths=[140, 240],
        )
        table.setStyle([("GRID", (0, 0), (-1, -1), 1, "black")])
        story.append(table)
    SimpleDocTemplate(stream).build(story)
    return stream.getvalue()


def ingest(store, workspace, title, name, content):
    blocks, entities, warnings = extract(name, content)
    return store.ingest(
        workspace, title, "1", name, content, blocks, entities, warnings, "developer"
    )


def approve(store, workspace, document):
    store.review(
        workspace,
        document,
        SourceReview(approved=True, reason="Developer source review"),
        "developer",
        source=True,
    )
    for entity in store.entities(workspace, document):
        store.review(
            workspace,
            entity["id"],
            Review(status="approved", reason="Developer entity review"),
            "developer",
        )


@pytest.mark.parametrize(
    "model,payload",
    [
        (Location, {}),
        (Location, {"page": "1"}),
        (Location, {"page": 1, "section": "Wrong", "line": 2}),
        (Location, {"table": 1, "page": 1}),
        (Location, {"row": 2, "page": 1}),
        (Location, {"page": 1, "confidence": 88.0}),
        (Location, {"page": 1, "origin": "ocr", "confidence": 88.0}),
        (Location, {"page": 1, "unknown": "field"}),
        (Block, {"text": "   ", "location": {"page": 1}}),
        (
            EvidenceSource,
            {"text": "literal", "location": {"page": 1}, "document_id": "invented"},
        ),
        (
            Entity,
            {
                "kind": "component",
                "name": "ValveCtrl",
                "evidence": "Component: ValveCtrl",
                "location": {"line": 1},
                "unexpected": True,
            },
        ),
        (
            Entity,
            {
                "kind": "component",
                "name": "ValveCtrl",
                "evidence": "Component: ValveCtrl",
                "location": {"line": 1},
                "sources": None,
            },
        ),
    ],
)
def test_malformed_provenance_payloads_are_rejected(model, payload):
    with pytest.raises(ValidationError):
        model.model_validate(payload, strict=True)


def test_identical_pdf_prose_occurrences_keep_both_pages_after_reopen(tmp_path):
    path = str(tmp_path / "repeated-pages.db")
    store = Store(path)
    content = prose_pdf("ValveCtrl component provides PressureData interface to Display.")
    document = ingest(store, "alpha", "Repeated prose", "prose.pdf", content)
    entity = next(e for e in store.entities("alpha", document) if e["kind"] == "dependency")
    assert len(entity["sources"]) == 2
    assert {s["location"]["page"] for s in entity["sources"]} == {1, 2}
    with store.connection() as db:
        links = db.execute(
            "SELECT ee.block_id,b.document_id,b.location FROM entity_evidence ee "
            "JOIN blocks b ON b.id=ee.block_id WHERE ee.entity_id=?",
            (entity["id"],),
        ).fetchall()
    assert len(links) == 2
    assert {row["document_id"] for row in links} == {document}
    assert Store(path).entities("alpha", document) == store.entities("alpha", document)


def test_identical_pdf_table_rows_keep_both_row_occurrences(tmp_path):
    store = Store(str(tmp_path / "repeated-tables.db"))
    content = table_pdf()
    document = ingest(store, "alpha", "Repeated rows", "tables.pdf", content)
    entity = store.entities("alpha", document)[0]
    assert entity["attributes"] == {"description": "Regulates pressure"}
    assert {
        (source["location"]["page"], source["location"]["table"], source["location"]["row"])
        for source in entity["sources"]
    } == {(1, 1, 2), (2, 1, 2)}


def test_repeated_markdown_lines_in_sections_keep_section_and_line(tmp_path):
    store = Store(str(tmp_path / "sections.db"))
    content = (
        b"# Primary\nComponent: ValveCtrl\n\n"
        b"# Redundant\nComponent: ValveCtrl\n"
    )
    document = ingest(store, "alpha", "Sections", "sections.md", content)
    entity = store.entities("alpha", document)[0]
    assert {
        (source["location"]["section"], source["location"]["line"])
        for source in entity["sources"]
    } == {("Primary", 2), ("Redundant", 5)}


def test_repeated_proposals_at_one_occurrence_deduplicate_one_link(tmp_path):
    store = Store(str(tmp_path / "same-occurrence.db"))
    source = {"text": "Component: ValveCtrl", "location": {"line": 1}}
    block = Block.model_validate(source, strict=True)
    entity = Entity(
        kind="component",
        name="ValveCtrl",
        evidence=source["text"],
        location=Location(line=1),
        sources=[source, source],
    )
    document = store.ingest(
        "alpha", "Same occurrence", "1", "same.md", source["text"].encode(),
        [block], [entity], [], "developer",
    )
    saved = store.entities("alpha", document)[0]
    assert saved["sources"] == [
        {"text": source["text"], "location": Location(line=1).model_dump()}
    ]
    with store.connection() as db:
        assert db.execute("SELECT count(*) FROM entity_evidence").fetchone()[0] == 1


def test_same_text_in_documents_and_workspaces_never_cross_links(tmp_path):
    store = Store(str(tmp_path / "scopes.db"))
    content = b"Component: ValveCtrl"
    alpha_one = ingest(store, "alpha", "Alpha one", "one.md", content)
    alpha_two = ingest(store, "alpha", "Alpha two", "two.md", content)
    beta = ingest(store, "beta", "Beta", "beta.md", content)
    documents = {alpha_one, alpha_two, beta}
    with store.connection() as db:
        linked = db.execute(
            "SELECT e.document_id AS entity_document,b.document_id AS block_document "
            "FROM entity_evidence ee JOIN entities e ON e.id=ee.entity_id "
            "JOIN blocks b ON b.id=ee.block_id"
        ).fetchall()
    assert {row["entity_document"] for row in linked} == documents
    assert all(row["entity_document"] == row["block_document"] for row in linked)
    assert len(store.entities("alpha")) == 2
    assert len(store.entities("beta")) == 1


@pytest.mark.parametrize("fault", ["wrong-page", "wrong-row", "altered", "missing"])
def test_unresolvable_sources_reject_atomically(tmp_path, fault):
    store = Store(str(tmp_path / f"reject-{fault}.db"))
    block = Block(text="Component: ValveCtrl", location=Location(page=1, line=1))
    location = {
        "wrong-page": Location(page=2, line=1),
        "wrong-row": Location(page=1, table=1, row=2),
        "altered": block.location,
        "missing": Location(page=1, line=2),
    }[fault]
    text = "Component: Other" if fault == "altered" else block.text
    entity = Entity(kind="component", name="ValveCtrl", evidence=text, location=location)
    with pytest.raises(ProvenanceError, match="exact source-block occurrence"):
        store.ingest(
            "alpha", "Rejected", "1", "bad.pdf", b"source", [block], [entity], [], "dev"
        )
    with store.connection() as db:
        rejected = db.execute(
            "SELECT provenance_status,provenance_detail,original FROM documents"
        ).fetchone()
        assert rejected["provenance_status"] == "quarantined"
        assert "exact source-block occurrence" in rejected["provenance_detail"]
        assert rejected["original"] == b"source"
        for table in ("blocks", "entities", "entity_evidence", "search"):
            assert db.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0
        assert db.execute("SELECT action FROM audit").fetchone()[0] == "provenance_rejection"


def test_database_failure_rolls_back_document_blocks_entities_links_and_audit(tmp_path):
    store = Store(str(tmp_path / "rollback.db"))
    blocks, entities, warnings = extract("rollback.md", b"Component: ValveCtrl")
    with pytest.raises(ProvenanceError, match="original quarantined"):
        store.ingest(
            "alpha", "Rollback", "1", "rollback.md", b"source",
            blocks, entities, warnings, None,
        )
    with store.connection() as db:
        rejected = db.execute(
            "SELECT provenance_status,original FROM documents"
        ).fetchone()
        assert rejected["provenance_status"] == "quarantined"
        assert rejected["original"] == b"source"
        for table in ("blocks", "entities", "entity_evidence", "search"):
            assert db.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0
        assert db.execute("SELECT action FROM audit").fetchone()[0] == "provenance_rejection"


def test_orphan_manual_block_and_wrong_workspace_are_rejected(tmp_path):
    app = create_app(str(tmp_path / "manual.db"))
    store = app.state.store
    alpha_token = store.provision("alpha-reviewer", "alpha", "reviewer")
    beta_token = store.provision("beta-reviewer", "beta", "reviewer")
    document = ingest(store, "alpha", "Manual", "manual.md", b"Component: ValveCtrl")
    block = store.eligible_blocks("alpha", document, "source", approved=False)[0]
    payload = {
        "kind": "component", "name": "ValveCtrl", "attributes": {},
        "evidence_block_id": "missing-block",
    }
    with TestClient(app) as client:
        response = client.post(
            f"/workspaces/alpha/documents/{document}/entities",
            headers={"Authorization": "Bearer " + alpha_token}, json=payload,
        )
        assert response.status_code == 404
        payload["evidence_block_id"] = block["id"]
        response = client.post(
            f"/workspaces/beta/documents/{document}/entities",
            headers={"Authorization": "Bearer " + beta_token}, json=payload,
        )
        assert response.status_code == 404
    assert len(store.entities("alpha", document)) == 1


def test_tampered_lineage_quarantines_on_reopen_and_denies_lifecycle(tmp_path):
    path = str(tmp_path / "quarantine.db")
    app = create_app(path)
    store = app.state.store
    token = store.provision("reviewer", "alpha", "reviewer")
    document = ingest(store, "alpha", "Tampered", "tampered.md", b"Component: ValveCtrl")
    approve(store, "alpha", document)
    with store.connection() as db:
        block = db.execute(
            "SELECT b.id FROM entity_evidence ee JOIN blocks b ON b.id=ee.block_id "
            "JOIN entities e ON e.id=ee.entity_id WHERE e.document_id=?",
            (document,),
        ).fetchone()
        db.execute(
            "UPDATE blocks SET location=? WHERE id=?",
            (Location(line=9).model_dump_json(), block["id"]),
        )
    restarted = create_app(path)
    restarted_store = restarted.state.store
    headers = {"Authorization": "Bearer " + token}
    with TestClient(restarted) as client:
        entity = restarted_store.entities("alpha", document)[0]
        assert client.post(
            f"/workspaces/alpha/entities/{entity['id']}/review", headers=headers,
            json={"status": "approved", "reason": "Must fail lineage audit"},
        ).status_code == 409
        assert client.post(
            "/workspaces/alpha/query", headers=headers,
            json={"text": "ValveCtrl", "document_id": document},
        ).status_code == 409
        assert client.get(
            "/workspaces/alpha/export", headers=headers, params={"document_id": document}
        ).status_code == 409
    state = restarted_store.documents("alpha")[0]
    assert state["provenance_status"] == "quarantined"
    assert state["approved"] == 0
    assert "primary evidence resolves to 0 occurrences" in state["provenance_detail"]
    with restarted_store.connection() as db:
        assert db.execute(
            "SELECT count(*) FROM audit WHERE action='entity_review'"
        ).fetchone()[0] == 1


def test_cross_document_link_quarantines_only_the_affected_document(tmp_path):
    store = Store(str(tmp_path / "cross-document.db"))
    first = ingest(store, "alpha", "First", "first.md", b"Component: ValveCtrl")
    second = ingest(store, "alpha", "Second", "second.md", b"Component: ValveCtrl")
    with store.connection() as db:
        entity = db.execute(
            "SELECT id FROM entities WHERE document_id=?", (first,)
        ).fetchone()[0]
        foreign_block = db.execute(
            "SELECT id FROM blocks WHERE document_id=?", (second,)
        ).fetchone()[0]
        db.execute("INSERT INTO entity_evidence VALUES(?,?)", (entity, foreign_block))
    with pytest.raises(ProvenanceError, match="another document"):
        store.review(
            "alpha", first, SourceReview(approved=True, reason="Reject cross-link"),
            "developer", source=True,
        )
    states = {row["id"]: row["provenance_status"] for row in store.documents("alpha")}
    assert states == {first: "quarantined", second: "verified"}


def test_orphan_stored_block_link_is_detected_after_restart(tmp_path):
    path = str(tmp_path / "orphan-link.db")
    store = Store(path)
    document = ingest(store, "alpha", "Orphan", "orphan.md", b"Component: ValveCtrl")
    with sqlite3.connect(path) as db:
        entity = db.execute(
            "SELECT id FROM entities WHERE document_id=?", (document,)
        ).fetchone()[0]
        db.execute("PRAGMA foreign_keys=OFF")
        db.execute("INSERT INTO entity_evidence VALUES(?,?)", (entity, "missing-occurrence"))
    restarted = Store(path)
    with pytest.raises(ProvenanceError, match="missing block"):
        restarted.review(
            "alpha", document, SourceReview(approved=True, reason="Reject orphan"),
            "developer", source=True,
        )
    assert restarted.documents("alpha")[0]["provenance_status"] == "quarantined"


def test_valid_review_export_query_and_restart_preserve_occurrences(tmp_path, monkeypatch):
    monkeypatch.delenv("HLD_NAVIGATOR_OLLAMA_MODEL", raising=False)
    path = str(tmp_path / "valid.db")
    app = create_app(path)
    store = app.state.store
    token = store.provision("reviewer", "alpha", "reviewer")
    content = prose_pdf("ValveCtrl component provides PressureData interface to Display.")
    document = ingest(store, "alpha", "Valid", "valid.pdf", content)
    approve(store, "alpha", document)
    headers = {"Authorization": "Bearer " + token}
    with TestClient(app) as client:
        exported = client.get(
            "/workspaces/alpha/export", headers=headers, params={"document_id": document}
        )
        assert exported.status_code == 200, exported.text
        sources = next(
            entity["sources"] for entity in exported.json()["entities"]
            if entity["kind"] == "dependency"
        )
        assert {source["location"]["page"] for source in sources} == {1, 2}
        queried = client.post(
            "/workspaces/alpha/query", headers=headers,
            json={"text": "ValveCtrl", "document_id": document},
        )
        assert queried.status_code == 200, queried.text
        assert {item["location"]["page"] for item in queried.json()["evidence"]} == {1, 2}
    assert Store(path).entities("alpha", document) == store.entities("alpha", document)


def create_legacy_database(path):
    with sqlite3.connect(path) as db:
        db.executescript("""
            CREATE TABLE documents(id TEXT PRIMARY KEY, workspace TEXT NOT NULL,
                title TEXT NOT NULL, version TEXT NOT NULL, name TEXT NOT NULL,
                sha256 TEXT NOT NULL, original BLOB NOT NULL,
                approved INTEGER NOT NULL DEFAULT 0, warnings TEXT NOT NULL,
                UNIQUE(workspace,title,version));
            INSERT INTO documents VALUES(
                'legacy-doc','alpha','Legacy','1','legacy.md','digest',X'00',1,'[]');
            PRAGMA user_version=2;
        """)


def test_legacy_database_is_explicitly_unverified_and_denied(tmp_path):
    path = str(tmp_path / "legacy.db")
    create_legacy_database(path)
    app = create_app(path)
    store = app.state.store
    token = store.provision("reviewer", "alpha", "reviewer")
    legacy = store.documents("alpha")[0]
    assert legacy["provenance_status"] == "legacy_unverified"
    assert "Predates occurrence validation" in legacy["provenance_detail"]
    with pytest.raises(ProvenanceError, match="re-ingestion"):
        store.review(
            "alpha", "legacy-doc", SourceReview(approved=True, reason="Must re-ingest"),
            "reviewer", source=True,
        )
    with pytest.raises(ProvenanceError, match="re-ingestion"):
        store.index_vectors("alpha", "legacy-doc", object())
    headers = {"Authorization": "Bearer " + token}
    with TestClient(app) as client:
        assert client.get(
            "/workspaces/alpha/export", headers=headers, params={"document_id": "legacy-doc"}
        ).status_code == 409
        assert client.post(
            "/workspaces/alpha/query", headers=headers,
            json={"text": "Legacy", "document_id": "legacy-doc"},
        ).status_code == 409
        assert client.get(
            "/workspaces/alpha/documents/legacy-doc/blocks", headers=headers
        ).status_code == 409
