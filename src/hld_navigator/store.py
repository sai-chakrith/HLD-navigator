import hashlib
import json
import re
import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from .models import Block, Entity, EvidenceSource, Location


class ProvenanceError(ValueError):
    """Raised when source lineage cannot be proven by an exact occurrence."""


class Store:
    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version > 3:
                raise ValueError("Database schema is newer than this application")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, token_hash TEXT UNIQUE NOT NULL);
                CREATE TABLE IF NOT EXISTS memberships(user_id TEXT, workspace TEXT, role TEXT,
                    PRIMARY KEY(user_id,workspace), FOREIGN KEY(user_id) REFERENCES users(id));
                CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY, workspace TEXT NOT NULL,
                    title TEXT NOT NULL, version TEXT NOT NULL, name TEXT NOT NULL, sha256 TEXT NOT NULL,
                    original BLOB NOT NULL, approved INTEGER NOT NULL DEFAULT 0, warnings TEXT NOT NULL,
                    provenance_status TEXT NOT NULL DEFAULT 'legacy_unverified',
                    provenance_detail TEXT NOT NULL DEFAULT 'Predates occurrence validation',
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
                CREATE TABLE IF NOT EXISTS coverage_reviews(document_id TEXT PRIMARY KEY,
                    fingerprint TEXT NOT NULL, scope TEXT NOT NULL, reason TEXT NOT NULL, actor TEXT NOT NULL,
                    FOREIGN KEY(document_id) REFERENCES documents(id));
                CREATE TABLE IF NOT EXISTS embeddings(block_id TEXT, model TEXT, fingerprint TEXT,
                    vector TEXT NOT NULL, PRIMARY KEY(block_id,model), FOREIGN KEY(block_id) REFERENCES blocks(id));
            """)
            columns = {row[1] for row in db.execute("PRAGMA table_info(documents)")}
            if "provenance_status" not in columns:
                db.execute(
                    "ALTER TABLE documents ADD COLUMN provenance_status TEXT NOT NULL DEFAULT 'legacy_unverified'"
                )
            if "provenance_detail" not in columns:
                db.execute(
                    "ALTER TABLE documents ADD COLUMN provenance_detail TEXT NOT NULL DEFAULT 'Predates occurrence validation'"
                )
            db.execute("PRAGMA user_version=3")

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

    def revoke(self, user: str):
        """Invalidate access across all memberships without deleting history."""
        with self.connection() as db:
            updated = db.execute(
                "UPDATE users SET token_hash=? WHERE id=?",
                (hashlib.sha256(secrets.token_bytes(40)).hexdigest(), user),
            )
            if updated.rowcount != 1:
                raise KeyError(user)
            self.audit(db, "local-admin", "revoke_access", user, {"scope": "all_workspaces"})

    @staticmethod
    def audit(db, actor, action, target, details):
        db.execute(
            "INSERT INTO audit(actor,action,target,details) VALUES(?,?,?,?)",
            (actor, action, target, json.dumps(details, sort_keys=True)),
        )

    @staticmethod
    def _location_json(location: Location) -> str:
        return location.model_dump_json()

    @classmethod
    def _source_key(cls, text: str, location: Location) -> tuple[str, str]:
        return text, cls._location_json(location)

    @classmethod
    def _validate_batch(cls, blocks, entities):
        validated_blocks = [Block.model_validate(block, strict=True) for block in blocks]
        validated_entities = [Entity.model_validate(entity, strict=True) for entity in entities]
        occurrences = {}
        for block in validated_blocks:
            key = cls._source_key(block.text, block.location)
            if key in occurrences:
                raise ProvenanceError("Duplicate source blocks claim the same occurrence")
            occurrences[key] = block
        resolved = []
        for entity in validated_entities:
            sources = [
                EvidenceSource(text=entity.evidence, location=entity.location),
                *[EvidenceSource.model_validate(source, strict=True) for source in entity.sources],
            ]
            unique = {}
            for source in sources:
                key = cls._source_key(source.text, source.location)
                if key not in occurrences:
                    raise ProvenanceError(
                        "Entity evidence does not resolve to an exact source-block occurrence"
                    )
                unique[key] = source
            if not unique:
                raise ProvenanceError("Entity has no resolvable source occurrence")
            resolved.append((entity, list(unique.values())))
        return validated_blocks, resolved

    @classmethod
    def _lineage_issues(cls, db, document):
        issues = []
        block_keys = {}
        blocks = db.execute(
            "SELECT id,text,location FROM blocks WHERE document_id=?", (document,)
        ).fetchall()
        for row in blocks:
            try:
                block = Block(
                    text=row["text"],
                    location=Location.model_validate_json(row["location"], strict=True),
                )
            except Exception as error:
                issues.append(f"block {row['id']} has malformed evidence: {error}")
                continue
            key = cls._source_key(block.text, block.location)
            if key in block_keys:
                issues.append(f"blocks {block_keys[key]} and {row['id']} claim the same occurrence")
            block_keys[key] = row["id"]
        broken_links = db.execute(
            "SELECT ee.entity_id,ee.block_id FROM entity_evidence ee "
            "JOIN entities e ON e.id=ee.entity_id LEFT JOIN blocks b ON b.id=ee.block_id "
            "WHERE e.document_id=? AND b.id IS NULL",
            (document,),
        ).fetchall()
        for link in broken_links:
            issues.append(f"entity {link['entity_id']} links missing block {link['block_id']}")
        entities = db.execute(
            "SELECT id,evidence,location FROM entities WHERE document_id=?", (document,)
        ).fetchall()
        for entity in entities:
            try:
                evidence = EvidenceSource(
                    text=entity["evidence"],
                    location=Location.model_validate_json(entity["location"], strict=True),
                )
            except Exception as error:
                issues.append(f"entity {entity['id']} has malformed primary evidence: {error}")
                continue
            links = db.execute(
                "SELECT b.id,b.document_id,b.text,b.location FROM entity_evidence ee "
                "JOIN blocks b ON b.id=ee.block_id WHERE ee.entity_id=?",
                (entity["id"],),
            ).fetchall()
            if not links:
                issues.append(f"entity {entity['id']} has no evidence occurrence")
                continue
            primary = 0
            for link in links:
                if link["document_id"] != document:
                    issues.append(f"entity {entity['id']} links evidence from another document")
                    continue
                try:
                    block = Block(
                        text=link["text"],
                        location=Location.model_validate_json(link["location"], strict=True),
                    )
                except Exception as error:
                    issues.append(f"block {link['id']} has malformed evidence: {error}")
                    continue
                if cls._source_key(block.text, block.location) == cls._source_key(
                    evidence.text, evidence.location
                ):
                    primary += 1
            if primary != 1:
                issues.append(
                    f"entity {entity['id']} primary evidence resolves to {primary} occurrences"
                )
        return issues

    @classmethod
    def _assert_document_verified(cls, db, workspace, document):
        row = db.execute(
            "SELECT id,provenance_status FROM documents WHERE workspace=? AND id=?",
            (workspace, document),
        ).fetchone()
        if not row:
            raise KeyError(document)
        if row["provenance_status"] != "verified":
            raise ProvenanceError(
                "Document provenance is unverified; governed re-ingestion is required"
            )
        issues = cls._lineage_issues(db, document)
        if issues:
            detail = "; ".join(issues)
            db.execute(
                "UPDATE documents SET provenance_status='quarantined',provenance_detail=?,approved=0 WHERE id=?",
                (detail, document),
            )
            db.commit()
            raise ProvenanceError("Document provenance failed integrity audit: " + detail)
        return row

    def _record_quarantined_upload(
        self, workspace, title, version, name, content, warnings, detail, actor
    ):
        document = str(uuid4())
        with self.connection() as db:
            db.execute(
                "INSERT INTO documents(id,workspace,title,version,name,sha256,original,warnings,provenance_status,provenance_detail) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    document,
                    workspace,
                    title,
                    version,
                    name,
                    hashlib.sha256(content).hexdigest(),
                    content,
                    json.dumps(warnings),
                    "quarantined",
                    detail,
                ),
            )
            self.audit(
                db,
                actor or "provenance-validator",
                "provenance_rejection",
                document,
                {"detail": detail, "sha256": hashlib.sha256(content).hexdigest()},
            )
        return document

    def ingest(self, workspace, title, version, name, content, blocks, entities, warnings, actor):
        try:
            validated_blocks, resolved_entities = self._validate_batch(blocks, entities)
        except (ProvenanceError, ValidationError) as error:
            document = self._record_quarantined_upload(
                workspace, title, version, name, content, warnings, str(error), actor
            )
            raise ProvenanceError(
                f"Provenance validation failed; original quarantined as document {document}: {error}"
            ) from error
        document = str(uuid4())
        try:
            with self.connection() as db:
                db.execute(
                    "INSERT INTO documents(id,workspace,title,version,name,sha256,original,warnings,provenance_status,provenance_detail) VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (
                        document,
                        workspace,
                        title,
                        version,
                        name,
                        hashlib.sha256(content).hexdigest(),
                        content,
                        json.dumps(warnings),
                        "verified",
                        "Exact source occurrences validated during ingestion",
                    ),
                )
                occurrence_ids = {}
                for block in validated_blocks:
                    identifier = str(uuid4())
                    db.execute(
                        "INSERT INTO blocks VALUES(?,?,?,?)",
                        (identifier, document, block.text, block.location.model_dump_json()),
                    )
                    db.execute("INSERT INTO search VALUES(?,?)", (identifier, block.text))
                    occurrence_ids[self._source_key(block.text, block.location)] = identifier
                for entity, sources in resolved_entities:
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
                    for source in sources:
                        block_identifier = occurrence_ids[
                            self._source_key(source.text, source.location)
                        ]
                        db.execute(
                            "INSERT OR IGNORE INTO entity_evidence VALUES(?,?)",
                            (entity_identifier, block_identifier),
                        )
                issues = self._lineage_issues(db, document)
                if issues:
                    raise ProvenanceError(
                        "Stored provenance validation failed: " + "; ".join(issues)
                    )
                self.audit(
                    db, actor, "upload", document, {"sha256": hashlib.sha256(content).hexdigest()}
                )
        except sqlite3.IntegrityError as error:
            if "documents.workspace, documents.title, documents.version" in str(error):
                raise
            rejected = self._record_quarantined_upload(
                workspace, title, version, name, content, warnings, str(error), actor
            )
            raise ProvenanceError(
                f"Persistence failed; original quarantined as document {rejected}: {error}"
            ) from error
        except ProvenanceError as error:
            rejected = self._record_quarantined_upload(
                workspace, title, version, name, content, warnings, str(error), actor
            )
            raise ProvenanceError(
                f"Persistence failed; original quarantined as document {rejected}: {error}"
            ) from error
        return document

    def documents(self, workspace):
        with self.connection() as db:
            rows = db.execute(
                "SELECT id,title,version,name,sha256,approved,warnings,provenance_status,provenance_detail FROM documents WHERE workspace=? ORDER BY rowid DESC",
                (workspace,),
            ).fetchall()
        return [{**dict(r), "warnings": json.loads(r["warnings"])} for r in rows]

    def assert_exportable_provenance(self, workspace, document):
        with self.connection() as db:
            self._assert_document_verified(db, workspace, document)

    def entities(self, workspace, document=None, approved_only=False):
        query = "SELECT e.*,d.title,d.version FROM entities e JOIN documents d ON d.id=e.document_id WHERE d.workspace=?"
        params = [workspace]
        if document:
            query += " AND d.id=?"
            params.append(document)
        if approved_only:
            query += " AND d.approved=1 AND d.provenance_status='verified' AND e.status='approved'"
        with self.connection() as db:
            if approved_only:
                documents = (
                    [document]
                    if document
                    else [
                        row["id"]
                        for row in db.execute(
                            "SELECT id FROM documents WHERE workspace=? AND approved=1",
                            (workspace,),
                        ).fetchall()
                    ]
                )
                for identifier in documents:
                    self._assert_document_verified(db, workspace, identifier)
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
            reviewed_document = (
                identifier
                if source
                else db.execute(
                    "SELECT document_id FROM entities WHERE id=?", (identifier,)
                ).fetchone()[0]
            )
            self._assert_document_verified(db, workspace, reviewed_document)
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
            db.execute("DELETE FROM coverage_reviews WHERE document_id=?", (reviewed_document,))
            self.audit(
                db,
                actor,
                "source_review" if source else "entity_review",
                identifier,
                decision.model_dump(),
            )

    def search(self, workspace, question, document=None, scope="facts"):
        from .fact_answers import relevant

        blocks = self.eligible_blocks(workspace, document, scope)
        words = set(re.findall(r"[a-z0-9_]+", question.lower())) - {
            "what",
            "which",
            "the",
            "is",
            "are",
            "a",
            "an",
            "of",
            "to",
            "does",
            "how",
            "and",
            "have",
            "has",
            "its",
            "in",
            "for",
            "with",
        }
        if not words:
            return []
        query = " OR ".join('"' + w + '"' for w in sorted(words)[:30])
        with self.connection() as db:
            matches = db.execute(
                "SELECT id FROM search WHERE search MATCH ? ORDER BY bm25(search)", (query,)
            ).fetchall()
        positions = {r["id"]: i for i, r in enumerate(matches)}
        ranked = []
        for block in blocks:
            if scope == "source" and block["id"] not in positions:
                continue
            if scope == "facts" and not relevant(question, block):
                continue
            score = len(words & set(re.findall(r"[a-z0-9_]+", block["text"].lower())))
            if score:
                ranked.append((score, -positions.get(block["id"], len(positions)), block))
        return [b for _, _, b in sorted(ranked, key=lambda item: item[:2], reverse=True)][:5]

    def eligible_blocks(self, workspace, document=None, scope="facts", approved=True):
        sql = "SELECT b.*,d.title,d.version,d.name FROM blocks b JOIN documents d ON d.id=b.document_id WHERE d.workspace=? AND d.provenance_status='verified'"
        params = [workspace]
        if approved:
            sql += " AND d.approved=1"
        if document:
            sql += " AND d.id=?"
            params.append(document)
        with self.connection() as db:
            if document:
                present = db.execute(
                    "SELECT 1 FROM documents WHERE workspace=? AND id=?", (workspace, document)
                ).fetchone()
                if not present:
                    return []
                self._assert_document_verified(db, workspace, document)
            else:
                verified = db.execute(
                    "SELECT id FROM documents WHERE workspace=? AND provenance_status='verified'",
                    (workspace,),
                ).fetchall()
                for row in verified:
                    self._assert_document_verified(db, workspace, row["id"])
            rows = db.execute(sql, params).fetchall()
            links = db.execute(
                "SELECT ee.block_id,e.id AS entity_id,e.kind,e.name,e.status,e.attributes,e.original_attributes FROM entity_evidence ee JOIN entities e ON e.id=ee.entity_id JOIN documents d ON d.id=e.document_id WHERE d.workspace=?",
                (workspace,),
            ).fetchall()
        from .fact_answers import render_fact

        links_by_block = {}
        for link in links:
            links_by_block.setdefault(link["block_id"], []).append(dict(link))
        output = []
        for row in rows:
            linked = links_by_block.get(row["id"], [])
            facts = [
                {
                    "entity_id": e["entity_id"],
                    "kind": e["kind"],
                    "name": e["name"],
                    "attributes": json.loads(e["attributes"]),
                    "field_basis": (
                        "reviewer_correction"
                        if e["attributes"] != e["original_attributes"]
                        else "reviewed_extraction"
                    ),
                }
                for e in linked
                if e["status"] == "approved"
            ]
            disputed = any(
                e["status"] == "rejected" or e["attributes"] != e["original_attributes"]
                for e in linked
            )
            context_state = "disputed_source" if disputed else "unreviewed_source"
            block = {
                **dict(row),
                "location": json.loads(row["location"]),
                "review_state": context_state,
                "approved_entity_ids": [f["entity_id"] for f in facts],
            }
            if scope == "facts":
                if not facts:
                    continue
                block.update(
                    text="\n".join(render_fact(f) for f in facts),
                    facts=facts,
                    review_state="approved_facts",
                    text_basis="reviewed structured fields, not a literal source quote",
                    source_context={"text": row["text"], "review_state": context_state},
                )
            output.append(block)
        return output

    def snapshot_fingerprint(self, workspace, document):
        with self.connection() as db:
            self._assert_document_verified(db, workspace, document)
        source = next(d for d in self.documents(workspace) if d["id"] == document)
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
            self._assert_document_verified(db, workspace, document)
            fingerprint = self.snapshot_fingerprint(workspace, document)
            db.execute(
                "INSERT OR REPLACE INTO coverage_reviews VALUES(?,?,?,?,?)",
                (document, fingerprint, decision.scope, decision.reason, actor),
            )
            self.audit(db, actor, "coverage_review", document, decision.model_dump())

    def coverage(self, workspace, document):
        with self.connection() as db:
            self._assert_document_verified(db, workspace, document)
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
        from .fact_answers import relevant

        if scope == "facts":
            with self.connection() as db:
                indexed = {
                    r[0]
                    for r in db.execute(
                        "SELECT block_id FROM embeddings WHERE model=?", (embedder.identity,)
                    )
                }
            if any(b["id"] not in indexed for b in blocks):
                raise ValueError("Index this document before querying")
            blocks = [b for b in blocks if relevant(question, b)]
            if not blocks:
                return []
            vectors = embedder.embed([question] + [b["text"] for b in blocks])
            validate_vectors(vectors, len(blocks) + 1)
            return sorted(
                [
                    {**b, "vector_similarity": cosine(vectors[0], v)}
                    for b, v in zip(blocks, vectors[1:], strict=True)
                ],
                key=lambda b: b["vector_similarity"],
                reverse=True,
            )[:5]
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
            self._assert_document_verified(db, workspace, document)
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
