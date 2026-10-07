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
            if version > 1:
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
                PRAGMA user_version=1;
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
                attrs = json.dumps(entity.attributes, sort_keys=True)
                db.execute(
                    "INSERT INTO entities VALUES(?,?,?,?,?,?,?,?,'proposed')",
                    (
                        str(uuid4()),
                        document,
                        entity.kind,
                        entity.name,
                        attrs,
                        attrs,
                        entity.evidence,
                        entity.location.model_dump_json(),
                    ),
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
        return [
            {
                **dict(r),
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
            self.audit(
                db,
                actor,
                "source_review" if source else "entity_review",
                identifier,
                decision.model_dump(),
            )

    def search(self, workspace, question, document=None):
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
        sql += " ORDER BY bm25(search) LIMIT 5"
        with self.connection() as db:
            rows = db.execute(sql, params).fetchall()
        return [{**dict(r), "location": json.loads(r["location"])} for r in rows]
