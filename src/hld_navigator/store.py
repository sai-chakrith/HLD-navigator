import hashlib
import json
import re
import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4


class Store:
    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version > 2:
                raise ValueError("Database schema is newer than this application")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, token_hash TEXT UNIQUE NOT NULL);
                CREATE TABLE IF NOT EXISTS memberships(user_id TEXT, workspace TEXT, role TEXT,
                    PRIMARY KEY(user_id,workspace), FOREIGN KEY(user_id) REFERENCES users(id));
                CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY, workspace TEXT NOT NULL,
                    title TEXT NOT NULL, version TEXT NOT NULL, name TEXT NOT NULL, sha256 TEXT NOT NULL,
                    original BLOB NOT NULL, approved INTEGER NOT NULL DEFAULT 0, warnings TEXT NOT NULL,
                    UNIQUE(workspace,title,version));
                CREATE TABLE IF NOT EXISTS blocks(id TEXT PRIMARY KEY, document_id TEXT NOT NULL,
                    text TEXT NOT NULL, location TEXT NOT NULL,
                    FOREIGN KEY(document_id) REFERENCES documents(id));
                CREATE VIRTUAL TABLE IF NOT EXISTS search USING fts5(id UNINDEXED,text);
                CREATE TABLE IF NOT EXISTS entities(id TEXT PRIMARY KEY, document_id TEXT NOT NULL,
                    kind TEXT NOT NULL, name TEXT NOT NULL, attributes TEXT NOT NULL,
                    original_attributes TEXT NOT NULL, evidence TEXT NOT NULL, location TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'proposed', FOREIGN KEY(document_id) REFERENCES documents(id));
                CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY, actor TEXT NOT NULL,
                    action TEXT NOT NULL, target TEXT NOT NULL, details TEXT NOT NULL,
                    timestamp TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')));
                CREATE TABLE IF NOT EXISTS entity_evidence(entity_id TEXT, block_id TEXT,
                    PRIMARY KEY(entity_id,block_id), FOREIGN KEY(entity_id) REFERENCES entities(id),
                    FOREIGN KEY(block_id) REFERENCES blocks(id));
                INSERT OR IGNORE INTO entity_evidence
                    SELECT e.id,b.id FROM entities e JOIN blocks b
                    ON e.document_id=b.document_id AND e.evidence=b.text;
                CREATE TABLE IF NOT EXISTS coverage_reviews(document_id TEXT PRIMARY KEY,
                    fingerprint TEXT NOT NULL, scope TEXT NOT NULL, reason TEXT NOT NULL, actor TEXT NOT NULL,
                    FOREIGN KEY(document_id) REFERENCES documents(id));
                CREATE TABLE IF NOT EXISTS embeddings(block_id TEXT, model TEXT, fingerprint TEXT,
                    vector TEXT NOT NULL, PRIMARY KEY(block_id,model), FOREIGN KEY(block_id) REFERENCES blocks(id));
                PRAGMA user_version=2;
            """)

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def provision(self, user: str, workspace: str, role: str) -> str:
        if role not in {"viewer", "editor", "reviewer"}:
            raise ValueError("Unknown role")
        token = secrets.token_urlsafe(40)
        with self.connection() as db:
            # Rotation invalidates earlier tokens for every membership of this user.
            db.execute(
                "INSERT INTO users VALUES(?,?) ON CONFLICT(id) DO UPDATE SET token_hash=excluded.token_hash",
                (user, hashlib.sha256(token.encode()).hexdigest()),
            )
            db.execute(
                "INSERT INTO memberships VALUES(?,?,?) ON CONFLICT(user_id,workspace) DO UPDATE SET role=excluded.role",
                (user, workspace, role),
            )
            self.audit(db, "local-admin", "provision", user, {"workspace": workspace, "role": role})
        return token

    def principal(self, token: str, workspace: str):
        with self.connection() as db:
            return db.execute(
                "SELECT u.id,m.role FROM users u JOIN memberships m ON m.user_id=u.id WHERE u.token_hash=? AND m.workspace=?",
                (hashlib.sha256(token.encode()).hexdigest(), workspace),
            ).fetchone()

    @staticmethod
    def audit(db, actor, action, target, details):
        db.execute(
            "INSERT INTO audit(actor,action,target,details) VALUES(?,?,?,?)",
            (actor, action, target, json.dumps(details, sort_keys=True)),
        )

    def ingest(self, workspace, title, version, name, content, blocks, entities, warnings, actor):
        document = str(uuid4())
        with self.connection() as db:
            db.execute(
                "INSERT INTO documents(id,workspace,title,version,name,sha256,original,warnings) VALUES(?,?,?,?,?,?,?,?)",
                (
                    document,
                    workspace,
                    title,
                    version,
                    name,
                    hashlib.sha256(content).hexdigest(),
                    content,
                    json.dumps(warnings),
                ),
            )
            for block in blocks:
                identifier = str(uuid4())
                db.execute(
                    "INSERT INTO blocks VALUES(?,?,?,?)",
                    (identifier, document, block.text, block.location.model_dump_json()),
                )
                db.execute("INSERT INTO search VALUES(?,?)", (identifier, block.text))
            for entity in entities:
                entity_identifier = str(uuid4())
                attrs = json.dumps(entity.attributes, sort_keys=True)
                db.execute(
                    "INSERT INTO entities VALUES(?,?,?,?,?,?,?,?,'proposed')",
                    (
                        entity_identifier,
                        document,
                        entity.kind,
                        entity.name,
                        attrs,
                        attrs,
                        entity.evidence,
                        entity.location.model_dump_json(),
                    ),
                )
                for source in [entity.evidence, *[source["text"] for source in entity.sources]]:
                    db.execute(
                        "INSERT OR IGNORE INTO entity_evidence SELECT ?,id FROM blocks WHERE document_id=? AND text=?",
                        (entity_identifier, document, source),
                    )
            self.audit(
                db, actor, "upload", document, {"sha256": hashlib.sha256(content).hexdigest()}
            )
        return document

    def documents(self, workspace):
        with self.connection() as db:
            rows = db.execute(
                "SELECT id,title,version,name,sha256,approved,warnings FROM documents WHERE workspace=? ORDER BY rowid DESC",
                (workspace,),
            ).fetchall()
        return [{**dict(r), "warnings": json.loads(r["warnings"])} for r in rows]

    def entities(self, workspace, document=None, approved_only=False):
        query = "SELECT e.*,d.title,d.version FROM entities e JOIN documents d ON d.id=e.document_id WHERE d.workspace=?"
        params = [workspace]
        if document:
            query += " AND d.id=?"
            params.append(document)
        if approved_only:
            query += " AND d.approved=1 AND e.status='approved'"
        with self.connection() as db:
            rows = db.execute(query, params).fetchall()
        with self.connection() as db:
            sources = db.execute(
                "SELECT ee.entity_id,b.text,b.location FROM entity_evidence ee JOIN entities e ON e.id=ee.entity_id JOIN blocks b ON b.id=ee.block_id JOIN documents d ON d.id=e.document_id WHERE d.workspace=?",
                (workspace,),
            ).fetchall()
        source_map = {}
        for source in sources:
            source_map.setdefault(source["entity_id"], []).append(
                {"text": source["text"], "location": json.loads(source["location"])}
            )
        return [
            {
                **dict(r),
                "sources": source_map.get(r["id"], []),
                "attributes": json.loads(r["attributes"]),
                "original_attributes": json.loads(r["original_attributes"]),
                "location": json.loads(r["location"]),
            }
            for r in rows
        ]

    def review(self, workspace, identifier, decision, actor, source=False):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            if source:
                row = db.execute(
                    "SELECT id FROM documents WHERE workspace=? AND id=?", (workspace, identifier)
                ).fetchone()
            else:
                row = db.execute(
                    "SELECT e.id FROM entities e JOIN documents d ON d.id=e.document_id WHERE d.workspace=? AND e.id=?",
                    (workspace, identifier),
                ).fetchone()
            if not row:
                raise KeyError(identifier)
            if source:
                db.execute(
                    "UPDATE documents SET approved=? WHERE id=?", (decision.approved, identifier)
                )
            else:
                if decision.attributes is not None:
                    db.execute(
                        "UPDATE entities SET attributes=? WHERE id=?",
                        (json.dumps(decision.attributes, sort_keys=True), identifier),
                    )
                db.execute("UPDATE entities SET status=? WHERE id=?", (decision.status, identifier))
            if source:
                reviewed_document = identifier
            else:
                reviewed_document = db.execute(
                    "SELECT document_id FROM entities WHERE id=?", (identifier,)
                ).fetchone()[0]
            db.execute("DELETE FROM coverage_reviews WHERE document_id=?", (reviewed_document,))
            self.audit(
                db,
                actor,
                "source_review" if source else "entity_review",
                identifier,
                decision.model_dump(),
            )

    def search(self, workspace, question, document=None, scope="facts"):
        stop = {"what", "which", "the", "is", "are", "a", "an", "of", "to", "does", "how", "and"}
        words = list(
            dict.fromkeys(w for w in re.findall(r"[a-z0-9_]+", question.lower()) if w not in stop)
        )
        if not words:
            return []
        query = " OR ".join('"' + w + '"' for w in words[:30])
        sql = "SELECT b.id,b.text,b.location,d.id AS document_id,d.title,d.version,d.name FROM search JOIN blocks b ON b.id=search.id JOIN documents d ON d.id=b.document_id WHERE search MATCH ? AND d.workspace=? AND d.approved=1"
        params = [query, workspace]
        if document:
            sql += " AND d.id=?"
            params.append(document)
        sql += " ORDER BY bm25(search) LIMIT 100"
        with self.connection() as db:
            rows = db.execute(sql, params).fetchall()
        eligible = {
            block["id"]: block for block in self.eligible_blocks(workspace, document, scope)
        }
        return [eligible[r["id"]] for r in rows if r["id"] in eligible][:5]

    def eligible_blocks(self, workspace, document=None, scope="facts", approved=True):
        sql = "SELECT b.*,d.title,d.version,d.name FROM blocks b JOIN documents d ON d.id=b.document_id WHERE d.workspace=?"
        params = [workspace]
        if approved:
            sql += " AND d.approved=1"
        if document:
            sql += " AND d.id=?"
            params.append(document)
        with self.connection() as db:
            rows = db.execute(sql, params).fetchall()
            links = db.execute(
                "SELECT ee.block_id,e.status,e.attributes,e.original_attributes FROM entity_evidence ee JOIN entities e ON e.id=ee.entity_id JOIN documents d ON d.id=e.document_id WHERE d.workspace=?",
                (workspace,),
            ).fetchall()
        states = {}
        for row in links:
            state = (
                "approved_facts"
                if row["status"] == "approved" and row["attributes"] == row["original_attributes"]
                else "disputed_source"
                if row["status"] == "rejected" or row["attributes"] != row["original_attributes"]
                else "unreviewed_source"
            )
            states.setdefault(row["block_id"], []).append(state)
        output = []
        for row in rows:
            linked = states.get(row["id"], [])
            state = (
                "disputed_source"
                if "disputed_source" in linked
                else "approved_facts"
                if linked and all(s == "approved_facts" for s in linked)
                else "unreviewed_source"
            )
            if scope == "facts" and state != "approved_facts":
                continue
            output.append(
                {**dict(row), "location": json.loads(row["location"]), "review_state": state}
            )
        return output

    def snapshot_fingerprint(self, workspace, document):
        source = next((d for d in self.documents(workspace) if d["id"] == document), None)
        if not source:
            raise KeyError(document)
        entities = self.entities(workspace, document)
        snapshot = {
            "source": source["sha256"],
            "warnings": source["warnings"],
            "entities": sorted([(e["id"], e["status"], e["attributes"]) for e in entities]),
        }
        return hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()

    def coverage_review(self, workspace, document, decision, actor):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            fingerprint = self.snapshot_fingerprint(workspace, document)
            db.execute(
                "INSERT OR REPLACE INTO coverage_reviews VALUES(?,?,?,?,?)",
                (document, fingerprint, decision.scope, decision.reason, actor),
            )
            self.audit(db, actor, "coverage_review", document, decision.model_dump())

    def coverage(self, workspace, document):
        fingerprint = self.snapshot_fingerprint(workspace, document)
        with self.connection() as db:
            row = db.execute(
                "SELECT * FROM coverage_reviews WHERE document_id=? AND fingerprint=?",
                (document, fingerprint),
            ).fetchone()
        return dict(row) if row else None

    def index_vectors(self, workspace, document, embedder):
        blocks = self.eligible_blocks(workspace, document, "source", approved=False)
        if not blocks:
            raise KeyError(document)
        vectors = []
        for start in range(0, len(blocks), 16):
            vectors.extend(embedder.embed([b["text"] for b in blocks[start : start + 16]]))
        from .vectors import validate_vectors

        validate_vectors(vectors, len(blocks))
        with self.connection() as db:
            for block, vector in zip(blocks, vectors, strict=True):
                db.execute(
                    "INSERT OR REPLACE INTO embeddings VALUES(?,?,?,?)",
                    (
                        block["id"],
                        embedder.identity,
                        hashlib.sha256(block["text"].encode()).hexdigest(),
                        json.dumps(vector),
                    ),
                )
        return len(blocks)

    def vector_search(self, workspace, question, document, embedder, scope="facts"):
        from .vectors import cosine, validate_vectors

        blocks = self.eligible_blocks(workspace, document, scope)
        if not blocks:
            return []
        query = embedder.embed([question])[0]
        validate_vectors([query], 1)
        with self.connection() as db:
            rows = db.execute(
                "SELECT block_id,fingerprint,vector FROM embeddings WHERE model=?",
                (embedder.identity,),
            ).fetchall()
        vectors = {r["block_id"]: r for r in rows}
        ranked = []
        for block in blocks:
            row = vectors.get(block["id"])
            if not row or row["fingerprint"] != hashlib.sha256(block["text"].encode()).hexdigest():
                raise ValueError(
                    "Index this document with the configured embedding model before querying"
                )
            vector = json.loads(row["vector"])
            score = cosine(query, vector)
            ranked.append({**block, "vector_similarity": score})
        return sorted(ranked, key=lambda b: b["vector_similarity"], reverse=True)[:5]

    def add_manual(self, workspace, document, decision, actor):
        from .extraction import parse_line
        from .models import Location

        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            block = db.execute(
                "SELECT b.* FROM blocks b JOIN documents d ON d.id=b.document_id WHERE d.workspace=? AND d.id=? AND b.id=?",
                (workspace, document, decision.evidence_block_id),
            ).fetchone()
            if not block:
                raise KeyError(decision.evidence_block_id)
            if decision.name.casefold() not in block["text"].casefold():
                raise ValueError("Manual entity name must occur in the selected evidence block")
            declaration = f"{decision.kind.title()}: {decision.name}" + "".join(
                f" | {key}={value}" for key, value in decision.attributes.items()
            )
            entity, error = parse_line(declaration, Location.model_validate_json(block["location"]))
            if error or not entity:
                raise ValueError(error or "Invalid entity")
            identifier = str(uuid4())
            attrs = json.dumps(decision.attributes, sort_keys=True)
            db.execute(
                "INSERT INTO entities VALUES(?,?,?,?,?,?,?,?,'proposed')",
                (
                    identifier,
                    document,
                    decision.kind,
                    decision.name,
                    attrs,
                    attrs,
                    block["text"],
                    block["location"],
                ),
            )
            db.execute("INSERT INTO entity_evidence VALUES(?,?)", (identifier, block["id"]))
            db.execute("DELETE FROM coverage_reviews WHERE document_id=?", (document,))
            self.audit(db, actor, "manual_proposal", identifier, decision.model_dump())
        return identifier
