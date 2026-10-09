"""Independent T3b2 synthetic provenance, occurrence, atomicity and legacy checks."""

import importlib
import io
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pdfplumber
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from reportlab.pdfgen import canvas

from hld_navigator.extraction import extract
from hld_navigator.models import Block, Entity, EvidenceSource, Location, Review, SourceReview
from hld_navigator.store import ProvenanceError, Store

EVIDENCE = (
    Path(__file__).resolve().parents[1]
    / "tester_acceptance/evidence"
    / datetime.now(UTC).strftime("t3b2-synthetic-%Y%m%dT%H%M%S%f")
)


def preserve(name, data):
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    path = EVIDENCE / name
    if isinstance(data, bytes):
        path.write_bytes(data)
    else:
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def repeated_pdf():
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(612, 792), invariant=1)
    for _ in (1, 2):
        pdf.setFont("Helvetica", 9)
        pdf.drawString(44, 754, "Independent component inventory revision 41")
        for y in (714, 684, 630):
            pdf.line(44, y, 568, y)
        for x in (44, 210, 568):
            pdf.line(x, 630, x, 714)
        pdf.drawString(52, 696, "SWC Name")
        pdf.drawString(218, 696, "Responsibility")
        pdf.drawString(52, 662, "Quartz")
        pdf.drawString(218, 662, "Controls pulses")
        pdf.drawString(218, 648, "within limits")
        pdf.drawString(44, 588, "Quartz component provides PulseBus interface to Nimbus.")
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def extracted(name, content):
    blocks, entities, warnings = extract(name, content)
    preserve(name, content)
    preserve(
        name + ".extracted.json",
        {
            "notice": "not independently validated",
            "blocks": [b.model_dump() for b in blocks],
            "entities": [e.model_dump() for e in entities],
            "warnings": warnings,
        },
    )
    return blocks, entities, warnings


def ingest(store, workspace, title, name, content, actor="tester", version="1"):
    blocks, entities, warnings = extracted(name, content)
    document = store.ingest(
        workspace, title, version, name, content, blocks, entities, warnings, actor
    )
    return document, blocks, entities, warnings


def approve(store, workspace, document):
    store.review(
        workspace,
        document,
        SourceReview(approved=True, reason="Independent synthetic source"),
        "tester",
        source=True,
    )
    for entity in store.entities(workspace, document):
        store.review(
            workspace,
            entity["id"],
            Review(status="approved", reason="Independent synthetic entity"),
            "tester",
        )


def database_state(store):
    with store.connection() as db:
        tables = [
            "documents",
            "blocks",
            "entities",
            "entity_evidence",
            "search",
            "coverage_reviews",
            "audit",
        ]
        return {
            table: [dict(row) for row in db.execute(f"SELECT * FROM {table}").fetchall()]
            for table in tables
        }


@pytest.mark.parametrize(
    "model,payload",
    [
        (Location, {}),
        (Location, {"page": "1"}),
        (Location, {"page": 1, "table": 1}),
        (Location, {"page": 1, "row": 2}),
        (Location, {"page": 1, "line": 2, "table": 1, "row": 2}),
        (Location, {"page": 1, "section": "Foreign", "line": 2}),
        (Location, {"line": 1, "section": "   "}),
        (Location, {"page": 1, "origin": "ocr", "line": 1}),
        (Location, {"page": 1, "unknown": True}),
        (Block, {"text": "  ", "location": {"line": 1}}),
        (EvidenceSource, {"text": "literal", "location": {"line": 1}, "document_id": "foreign"}),
        (
            Entity,
            {
                "kind": "component",
                "name": "Quartz",
                "attributes": {},
                "evidence": "Component: Quartz",
                "location": {"line": 1},
                "sources": "not-a-list",
            },
        ),
    ],
)
def test_strict_provenance_models_reject_malformed_shapes(model, payload):
    with pytest.raises(ValidationError) as rejected:
        model.model_validate(payload, strict=True)
    preserve(
        f"malformed-{model.__name__}-{abs(hash(repr(payload)))}.json",
        {
            "model": model.__name__,
            "payload": payload,
            "rejected": True,
            "reason": str(rejected.value),
        },
    )


def test_repeated_pdf_page_and_table_occurrences_survive_lifecycle(tmp_path, monkeypatch):
    monkeypatch.delenv("HLD_NAVIGATOR_OLLAMA_MODEL", raising=False)
    content = repeated_pdf()
    path = str(tmp_path / "repeated.db")
    app = importlib.import_module("hld_navigator.app").create_app(path)
    store = app.state.store
    document, _, original_entities, warnings = ingest(
        store, "alpha", "Repeated PDF", "repeated.pdf", content
    )
    assert not warnings
    pages, rows = {}, {}
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page, original in enumerate(pdf.pages, 1):
            pages[page] = original.extract_text()
            rows[page] = original.crop((44, 108, 568, 162)).extract_text()
    assert pages[1] == pages[2]
    assert rows == {
        1: "Quartz Controls pulses\nwithin limits",
        2: "Quartz Controls pulses\nwithin limits",
    }
    saved = store.entities("alpha", document)
    assert {(entity["kind"], entity["name"]) for entity in saved} == {
        ("component", "Quartz"),
        ("component", "Nimbus"),
        ("interface", "PulseBus"),
        ("dependency", "Quartz->Nimbus:PulseBus"),
    }
    audit = []
    for entity in saved:
        for source in entity["sources"]:
            location = source["location"]
            expected = rows[location["page"]] if location["table"] else pages[location["page"]]
            assert source["text"] == expected
            audit.append(
                {
                    "entity": [entity["kind"], entity["name"]],
                    "source": source,
                    "independent_original": expected,
                    "literal_equal": True,
                }
            )
    component = next(e for e in saved if e["kind"] == "component" and e["name"] == "Quartz")
    assert {
        (s["location"]["page"], s["location"]["table"], s["location"]["row"])
        for s in component["sources"]
    } == {(1, None, None), (2, None, None), (1, 1, 2), (2, 1, 2)}
    dependency = next(e for e in saved if e["kind"] == "dependency")
    assert {s["location"]["page"] for s in dependency["sources"]} == {1, 2}
    approve(store, "alpha", document)
    token = store.provision("reader", "alpha", "reviewer")
    headers = {"Authorization": "Bearer " + token}
    with TestClient(app) as client:
        query = client.post(
            "/workspaces/alpha/query",
            headers=headers,
            json={"text": "Quartz PulseBus", "document_id": document},
        )
        exported = client.get(
            "/workspaces/alpha/export", headers=headers, params={"document_id": document}
        )
    assert query.status_code == exported.status_code == 200
    assert {item["location"]["page"] for item in query.json()["evidence"]} == {1, 2}
    reopened = Store(path)
    assert reopened.entities("alpha", document) == store.entities("alpha", document)
    with reopened.connection() as db:
        original = db.execute("SELECT original FROM documents WHERE id=?", (document,)).fetchone()[
            0
        ]
        links = [
            dict(row)
            for row in db.execute(
                "SELECT e.name,b.document_id,b.text,b.location FROM entity_evidence ee "
                "JOIN entities e ON e.id=ee.entity_id JOIN blocks b ON b.id=ee.block_id "
                "WHERE e.document_id=?",
                (document,),
            ).fetchall()
        ]
    assert original == content
    assert {row["document_id"] for row in links} == {document}
    preserve(
        "repeated-lifecycle.json",
        {
            "document": document,
            "original_entity_count": len(original_entities),
            "literal_audit": audit,
            "query": {"status": query.status_code, "body": query.json()},
            "export": {"status": exported.status_code, "body": exported.json()},
            "links": links,
            "reopened": reopened.entities("alpha", document),
        },
    )


def test_repeated_markdown_sections_and_document_workspace_isolation(tmp_path):
    store = Store(str(tmp_path / "scopes.db"))
    repeated = b"# Primary\nComponent: Quartz\n\n# Redundant\nComponent: Quartz\n"
    first, *_ = ingest(store, "alpha", "First", "first.md", repeated)
    second, *_ = ingest(store, "alpha", "Second", "second.md", b"Component: Quartz")
    beta, *_ = ingest(store, "beta", "Beta", "beta.md", b"Component: Quartz")
    sources = store.entities("alpha", first)[0]["sources"]
    assert {(s["location"]["section"], s["location"]["line"]) for s in sources} == {
        ("Primary", 2),
        ("Redundant", 5),
    }
    with store.connection() as db:
        links = [
            dict(row)
            for row in db.execute(
                "SELECT d.workspace,e.document_id AS entity_document,"
                "b.document_id AS block_document "
                "FROM entity_evidence ee JOIN entities e ON e.id=ee.entity_id "
                "JOIN blocks b ON b.id=ee.block_id JOIN documents d ON d.id=e.document_id"
            )
        ]
    assert {row["entity_document"] for row in links} == {first, second, beta}
    assert all(row["entity_document"] == row["block_document"] for row in links)
    preserve(
        "section-document-workspace-isolation.json",
        {"documents": [first, second, beta], "section_sources": sources, "links": links},
    )


@pytest.mark.parametrize(
    "fault", ["wrong-page", "wrong-line", "wrong-row", "altered", "missing-contributor"]
)
def test_wrong_occurrence_batches_quarantine_atomically(tmp_path, fault):
    store = Store(str(tmp_path / f"wrong-{fault}.db"))
    blocks = [
        Block(text="Component: Quartz", location=Location(page=1, line=1)),
        Block(text="Component: Nimbus", location=Location(page=1, line=2)),
    ]
    locations = {
        "wrong-page": Location(page=2, line=1),
        "wrong-line": Location(page=1, line=9),
        "wrong-row": Location(page=1, table=1, row=2),
        "altered": Location(page=1, line=1),
        "missing-contributor": Location(page=1, line=1),
    }
    primary_text = "Component: Other" if fault == "altered" else blocks[0].text
    sources = (
        [{"text": blocks[1].text, "location": {"page": 1, "line": 8}}]
        if fault == "missing-contributor"
        else []
    )
    entity = Entity(
        kind="component",
        name="Quartz",
        evidence=primary_text,
        location=locations[fault],
        sources=sources,
    )
    with pytest.raises(ProvenanceError) as rejected:
        store.ingest(
            "alpha",
            "Rejected " + fault,
            "1",
            "bad.pdf",
            b"original-" + fault.encode(),
            blocks,
            [entity],
            [{"code": "fixture", "severity": "blocking"}],
            "tester",
        )
    state = database_state(store)
    assert len(state["documents"]) == 1
    assert state["documents"][0]["provenance_status"] == "quarantined"
    assert state["documents"][0]["approved"] == 0
    assert state["documents"][0]["original"] == b"original-" + fault.encode()
    assert not state["blocks"] and not state["entities"] and not state["entity_evidence"]
    assert not state["search"] and not state["coverage_reviews"]
    assert [item["action"] for item in state["audit"]] == ["provenance_rejection"]
    preserve(
        "wrong-occurrence-" + fault + ".json",
        {"fault": fault, "error": str(rejected.value), "database": state},
    )


def test_duplicate_occurrence_blocks_quarantine_without_partial_rows(tmp_path):
    store = Store(str(tmp_path / "duplicate.db"))
    block = Block(text="Component: Quartz", location=Location(line=1))
    entity = Entity(kind="component", name="Quartz", evidence=block.text, location=block.location)
    with pytest.raises(ProvenanceError, match="Duplicate source blocks") as rejected:
        store.ingest(
            "alpha",
            "Duplicate",
            "1",
            "duplicate.md",
            block.text.encode(),
            [block, block],
            [entity],
            [],
            "tester",
        )
    state = database_state(store)
    assert len(state["documents"]) == 1
    assert state["documents"][0]["provenance_status"] == "quarantined"
    assert not state["blocks"] and not state["entities"] and not state["entity_evidence"]
    preserve("duplicate-occurrence.json", {"error": str(rejected.value), "database": state})


def test_malformed_batch_quarantines_original_without_partial_rows(tmp_path):
    store = Store(str(tmp_path / "malformed-batch.db"))
    malformed = {"text": "   ", "location": {"line": 1}, "unexpected": True}
    with pytest.raises(ProvenanceError, match="Provenance validation failed") as rejected:
        store.ingest(
            "alpha",
            "Malformed",
            "1",
            "malformed.md",
            b"raw-malformed",
            [malformed],
            [],
            [{"severity": "blocking", "code": "fixture"}],
            "tester",
        )
    state = database_state(store)
    assert len(state["documents"]) == 1
    assert state["documents"][0]["provenance_status"] == "quarantined"
    assert state["documents"][0]["original"] == b"raw-malformed"
    assert not state["blocks"] and not state["entities"] and not state["entity_evidence"]
    preserve("malformed-batch.json", {"error": str(rejected.value), "database": state})


def test_repeated_sources_at_same_occurrence_deduplicate_exactly(tmp_path):
    store = Store(str(tmp_path / "deduplicate.db"))
    source = {"text": "Component: Quartz", "location": {"line": 1}}
    block = Block.model_validate(source, strict=True)
    entity = Entity(
        kind="component",
        name="Quartz",
        evidence=source["text"],
        location=Location(line=1),
        sources=[source, source],
    )
    document = store.ingest(
        "alpha",
        "Deduplicate",
        "1",
        "same.md",
        source["text"].encode(),
        [block],
        [entity],
        [],
        "tester",
    )
    saved = store.entities("alpha", document)[0]
    assert saved["sources"] == [{"text": source["text"], "location": Location(line=1).model_dump()}]
    with store.connection() as db:
        links = db.execute("SELECT count(*) FROM entity_evidence").fetchone()[0]
    assert links == 1
    preserve("same-occurrence-dedup.json", {"entity": saved, "link_count": links})


def test_persistence_fault_rolls_back_then_quarantines_original(tmp_path):
    store = Store(str(tmp_path / "persistence.db"))
    with store.connection() as db:
        db.execute(
            "CREATE TRIGGER tester_entity_failure BEFORE INSERT ON entities "
            "BEGIN SELECT RAISE(ABORT,'tester persistence fault'); END"
        )
    blocks, entities, warnings = extract("fault.md", b"Component: Quartz")
    with pytest.raises(ProvenanceError, match="original quarantined") as rejected:
        store.ingest(
            "alpha",
            "Persistence",
            "1",
            "fault.md",
            b"Component: Quartz",
            blocks,
            entities,
            warnings,
            "tester",
        )
    state = database_state(store)
    assert len(state["documents"]) == 1
    assert state["documents"][0]["provenance_status"] == "quarantined"
    assert state["documents"][0]["original"] == b"Component: Quartz"
    assert not state["blocks"] and not state["entities"] and not state["entity_evidence"]
    assert not state["search"] and not state["coverage_reviews"]
    assert [item["action"] for item in state["audit"]] == ["provenance_rejection"]
    preserve("persistence-rollback.json", {"error": str(rejected.value), "database": state})


def test_cross_document_and_orphan_links_quarantine_without_new_review(tmp_path):
    path = str(tmp_path / "tamper.db")
    app = importlib.import_module("hld_navigator.app").create_app(path)
    store = app.state.store
    first, *_ = ingest(store, "alpha", "First tamper", "first.md", b"Component: Quartz")
    second, *_ = ingest(store, "alpha", "Second tamper", "second.md", b"Component: Quartz")
    approve(store, "alpha", first)
    entity = store.entities("alpha", first)[0]
    with store.connection() as db:
        foreign = db.execute("SELECT id FROM blocks WHERE document_id=?", (second,)).fetchone()[0]
        db.execute("INSERT INTO entity_evidence VALUES(?,?)", (entity["id"], foreign))
        reviews_before = db.execute(
            "SELECT count(*) FROM audit WHERE action='entity_review'"
        ).fetchone()[0]
    token = store.provision("reviewer", "alpha", "reviewer")
    headers = {"Authorization": "Bearer " + token}
    with TestClient(app) as client:
        response = client.post(
            f"/workspaces/alpha/entities/{entity['id']}/review",
            headers=headers,
            json={"status": "approved", "reason": "must reject cross-link"},
        )
        query = client.post(
            "/workspaces/alpha/query",
            headers=headers,
            json={"text": "Quartz", "document_id": first},
        )
        exported = client.get(
            "/workspaces/alpha/export", headers=headers, params={"document_id": first}
        )
    assert response.status_code == query.status_code == exported.status_code == 409
    reopened = Store(path)
    states = {doc["id"]: doc for doc in reopened.documents("alpha")}
    assert states[first]["provenance_status"] == "quarantined"
    assert states[first]["approved"] == 0
    assert states[second]["provenance_status"] == "verified"
    with reopened.connection() as db:
        reviews_after = db.execute(
            "SELECT count(*) FROM audit WHERE action='entity_review'"
        ).fetchone()[0]
    assert reviews_after == reviews_before
    preserve(
        "cross-document-lifecycle.json",
        {
            "review": {"status": response.status_code, "body": response.json()},
            "query": {"status": query.status_code, "body": query.json()},
            "export": {"status": exported.status_code, "body": exported.json()},
            "documents": states,
            "entity_reviews_before": reviews_before,
            "entity_reviews_after": reviews_after,
        },
    )


def test_orphan_stored_link_quarantines_after_restart(tmp_path):
    path = str(tmp_path / "orphan-stored.db")
    store = Store(path)
    document, *_ = ingest(store, "alpha", "Orphan stored", "orphan.md", b"Component: Quartz")
    approve(store, "alpha", document)
    with sqlite3.connect(path) as db:
        entity = db.execute("SELECT id FROM entities WHERE document_id=?", (document,)).fetchone()[
            0
        ]
        db.execute("PRAGMA foreign_keys=OFF")
        db.execute("INSERT INTO entity_evidence VALUES(?,?)", (entity, "missing-block"))
    reopened = Store(path)
    with reopened.connection() as db:
        source_reviews = db.execute(
            "SELECT count(*) FROM audit WHERE action='source_review'"
        ).fetchone()[0]
    with pytest.raises(ProvenanceError, match="missing block") as rejected:
        reopened.review(
            "alpha",
            document,
            SourceReview(approved=True, reason="must reject orphan"),
            "tester",
            source=True,
        )
    state = reopened.documents("alpha")[0]
    assert state["provenance_status"] == "quarantined" and state["approved"] == 0
    with reopened.connection() as db:
        after = db.execute("SELECT count(*) FROM audit WHERE action='source_review'").fetchone()[0]
    assert after == source_reviews
    preserve(
        "orphan-stored-reopen.json",
        {
            "error": str(rejected.value),
            "document": state,
            "source_review_audits_before": source_reviews,
            "after": after,
        },
    )


def create_legacy(path):
    with sqlite3.connect(path) as db:
        db.executescript("""
            CREATE TABLE documents(id TEXT PRIMARY KEY, workspace TEXT NOT NULL,
                title TEXT NOT NULL, version TEXT NOT NULL, name TEXT NOT NULL,
                sha256 TEXT NOT NULL, original BLOB NOT NULL,
                approved INTEGER NOT NULL DEFAULT 0, warnings TEXT NOT NULL,
                UNIQUE(workspace,title,version));
            CREATE TABLE blocks(id TEXT PRIMARY KEY,document_id TEXT NOT NULL,
                text TEXT NOT NULL,location TEXT NOT NULL);
            CREATE TABLE entities(id TEXT PRIMARY KEY,document_id TEXT NOT NULL,kind TEXT NOT NULL,
                name TEXT NOT NULL,attributes TEXT NOT NULL,original_attributes TEXT NOT NULL,
                evidence TEXT NOT NULL,location TEXT NOT NULL,status TEXT NOT NULL);
            CREATE TABLE entity_evidence(
                entity_id TEXT,block_id TEXT,PRIMARY KEY(entity_id,block_id));
            CREATE TABLE audit(id INTEGER PRIMARY KEY,actor TEXT NOT NULL,action TEXT NOT NULL,
                target TEXT NOT NULL,details TEXT NOT NULL,
                timestamp TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')));
            INSERT INTO documents VALUES('legacy','alpha','Legacy','1','legacy.md','oldhash',
                X'436F6D706F6E656E743A2051756172747A',1,'[]');
            INSERT INTO blocks VALUES('old-block','legacy','Component: Quartz',
                '{"page":null,"section":null,"line":1,"table":null,"row":null,"origin":"text","confidence":null}');
            INSERT INTO entities VALUES('old-entity','legacy','component','Quartz','{}','{}',
                'Component: Quartz',
                '{"page":null,"section":null,"line":1,"table":null,"row":null,"origin":"text","confidence":null}',
                'approved');
            INSERT INTO entity_evidence VALUES('old-entity','old-block');
            INSERT INTO audit VALUES(
                1,'old-reviewer','entity_review','old-entity','{}','2025-01-01');
            PRAGMA user_version=2;
        """)


def test_legacy_quarantine_and_governed_reingestion_do_not_transfer_review(tmp_path, monkeypatch):
    monkeypatch.delenv("HLD_NAVIGATOR_OLLAMA_MODEL", raising=False)
    path = str(tmp_path / "legacy.db")
    create_legacy(path)
    app = importlib.import_module("hld_navigator.app").create_app(path)
    store = app.state.store
    token = store.provision("reviewer", "alpha", "reviewer")
    headers = {"Authorization": "Bearer " + token}
    legacy = next(doc for doc in store.documents("alpha") if doc["id"] == "legacy")
    assert legacy["provenance_status"] == "legacy_unverified" and legacy["approved"] == 1
    with TestClient(app) as client:
        source_review = client.post(
            "/workspaces/alpha/documents/legacy/review",
            headers=headers,
            json={"approved": True, "reason": "must re-ingest"},
        )
        query = client.post(
            "/workspaces/alpha/query",
            headers=headers,
            json={"text": "Quartz", "document_id": "legacy"},
        )
        exported = client.get(
            "/workspaces/alpha/export", headers=headers, params={"document_id": "legacy"}
        )
        blocks = client.get("/workspaces/alpha/documents/legacy/blocks", headers=headers)
    assert {
        source_review.status_code,
        query.status_code,
        exported.status_code,
        blocks.status_code,
    } == {409}
    new_document, *_ = ingest(
        store, "alpha", "Legacy", "replacement.md", b"Component: Quartz", version="2"
    )
    assert new_document != "legacy"
    replacement = store.entities("alpha", new_document)[0]
    assert replacement["id"] != "old-entity" and replacement["status"] == "proposed"
    assert store.documents("alpha")[0]["approved"] == 0
    with store.connection() as db:
        old = db.execute("SELECT status FROM entities WHERE id='old-entity'").fetchone()[0]
        audits = [dict(row) for row in db.execute("SELECT * FROM audit ORDER BY id")]
    assert old == "approved"
    assert not [
        row
        for row in audits
        if row["target"] == replacement["id"] and row["action"] == "entity_review"
    ]
    preserve(
        "legacy-reingestion.json",
        {
            "legacy": legacy,
            "denials": {
                "review": source_review.status_code,
                "query": query.status_code,
                "export": exported.status_code,
                "blocks": blocks.status_code,
            },
            "replacement": replacement,
            "audits": audits,
            "disclosure": "Legacy data retained unverified; replacement requires fresh review.",
        },
    )


def test_orphan_manual_and_wrong_workspace_leave_entity_batch_unchanged(tmp_path):
    app = importlib.import_module("hld_navigator.app").create_app(str(tmp_path / "manual.db"))
    store = app.state.store
    document, *_ = ingest(store, "alpha", "Manual", "manual.md", b"Component: Quartz")
    block = store.eligible_blocks("alpha", document, "source", approved=False)[0]
    alpha = store.provision("alpha-reviewer", "alpha", "reviewer")
    beta = store.provision("beta-reviewer", "beta", "reviewer")
    initial = store.entities("alpha", document)
    payload = {
        "kind": "component",
        "name": "Quartz",
        "attributes": {},
        "evidence_block_id": "missing",
    }
    with TestClient(app) as client:
        missing = client.post(
            f"/workspaces/alpha/documents/{document}/entities",
            headers={"Authorization": "Bearer " + alpha},
            json=payload,
        )
        payload["evidence_block_id"] = block["id"]
        foreign = client.post(
            f"/workspaces/beta/documents/{document}/entities",
            headers={"Authorization": "Bearer " + beta},
            json=payload,
        )
    assert missing.status_code == foreign.status_code == 404
    assert store.entities("alpha", document) == initial
    preserve(
        "manual-orphan-workspace.json",
        {
            "missing": {"status": missing.status_code, "body": missing.json()},
            "foreign": {"status": foreign.status_code, "body": foreign.json()},
            "entities_before_after": initial,
        },
    )
