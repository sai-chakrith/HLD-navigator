import os
import sqlite3
from typing import Annotated
from urllib.error import URLError

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile

from .analysis import compare, findings
from .extraction import ALLOWED, REQUIRED, extract
from .models import Question, Review, SourceReview
from .rag import answer
from .store import Store


def create_app(path=None):
    store = Store(path or os.getenv("HLD_NAVIGATOR_DB", ".data/hld_navigator.db"))
    app = FastAPI(title="HLD Navigator — HLD Review Pilot")
    app.state.store = store

    def authorize(workspace, authorization, minimum="viewer"):
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(401, "Individual bearer token required")
        user = store.principal(authorization[7:], workspace)
        ranks = {"viewer": 1, "editor": 2, "reviewer": 3}
        if user is None:
            raise HTTPException(403, "No access to this workspace")
        if ranks.get(user["role"], 0) < ranks[minimum]:
            raise HTTPException(403, f"{minimum} role required")
        return user["id"]

    @app.get("/health")
    def health():
        with store.connection() as db:
            db.execute("SELECT 1")
        return {"status": "ok", "retrieval": "sqlite_fts5", "pilot": True}

    @app.get("/workspaces/{workspace}/documents")
    def documents(workspace: str, authorization: str | None = Header(None)):
        authorize(workspace, authorization)
        return store.documents(workspace)

    @app.post("/workspaces/{workspace}/documents")
    async def upload(
        workspace: str,
        file: Annotated[UploadFile, File()],
        title: str = Form(..., min_length=1, max_length=200),
        version: str = Form(..., min_length=1, max_length=100),
        authorization: str | None = Header(None),
    ):
        actor = authorize(workspace, authorization, "editor")
        if not title.strip() or not version.strip():
            raise HTTPException(422, "Title and version must contain non-whitespace characters")
        content = await file.read(10 * 1024 * 1024 + 1)
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(413, "Maximum upload size is 10 MB")
        try:
            blocks, entities, warnings = extract(file.filename or "", content)
            identifier = store.ingest(
                workspace,
                title.strip(),
                version.strip(),
                file.filename,
                content,
                blocks,
                entities,
                warnings,
                actor,
            )
        except sqlite3.IntegrityError as error:
            raise HTTPException(
                409, "Title/version already exists; upload a new revision"
            ) from error
        except Exception as error:
            raise HTTPException(422, "Extraction failed: " + str(error)) from error
        return {"id": identifier, "proposals": len(entities), "warnings": warnings}

    @app.get("/workspaces/{workspace}/entities")
    def entities(
        workspace: str, document_id: str | None = None, authorization: str | None = Header(None)
    ):
        authorize(workspace, authorization)
        return store.entities(workspace, document_id)

    @app.post("/workspaces/{workspace}/documents/{identifier}/review")
    def source_review(
        workspace: str,
        identifier: str,
        decision: SourceReview,
        authorization: str | None = Header(None),
    ):
        actor = authorize(workspace, authorization, "reviewer")
        try:
            store.review(workspace, identifier, decision, actor, source=True)
        except KeyError as error:
            raise HTTPException(404, "Document not found") from error
        return {"ok": True}

    @app.post("/workspaces/{workspace}/entities/{identifier}/review")
    def entity_review(
        workspace: str, identifier: str, decision: Review, authorization: str | None = Header(None)
    ):
        actor = authorize(workspace, authorization, "reviewer")
        entity = next((e for e in store.entities(workspace) if e["id"] == identifier), None)
        if entity is None:
            raise HTTPException(404, "Entity not found")
        attrs = decision.attributes if decision.attributes is not None else entity["attributes"]
        if (
            set(attrs) - ALLOWED[entity["kind"]]
            or REQUIRED.get(entity["kind"], set()) - attrs.keys()
            or any(not value.strip() for value in attrs.values())
        ):
            raise HTTPException(422, "Unknown, missing or empty architecture attributes")
        if entity["kind"] == "port" and attrs["direction"] not in {"provides", "requires"}:
            raise HTTPException(422, "Invalid port direction")
        store.review(workspace, identifier, decision, actor)
        return {"ok": True}

    @app.post("/workspaces/{workspace}/query")
    def query(workspace: str, question: Question, authorization: str | None = Header(None)):
        authorize(workspace, authorization)
        evidence = store.search(workspace, question.text, question.document_id)
        # Avoid presenting evidence across revisions as a single architecture.
        if not question.document_id and len({(e["title"], e["version"]) for e in evidence}) > 1:
            return {
                "mode": "revision_selection_required",
                "answer": "Select one document revision before asking this question.",
                "evidence": evidence,
            }
        try:
            return answer(question.text, evidence)
        except (URLError, TimeoutError, ValueError, KeyError) as error:
            raise HTTPException(
                503, "Configured local model unavailable or invalid response"
            ) from error

    @app.get("/workspaces/{workspace}/export")
    def export(workspace: str, document_id: str, authorization: str | None = Header(None)):
        authorize(workspace, authorization)
        document = next((d for d in store.documents(workspace) if d["id"] == document_id), None)
        if not document:
            raise HTTPException(404, "Document not found")
        if not document["approved"]:
            raise HTTPException(409, "Approve the source before export")
        proposals = store.entities(workspace, document_id)
        if any(e["status"] == "proposed" for e in proposals):
            raise HTTPException(409, "Review every entity proposal before export")
        approved = store.entities(workspace, document_id, True)
        return {
            "document": document,
            "entities": approved,
            "findings": findings(approved),
            "limitations": (
                "Template-derived approved inventory; unrecognized prose/diagrams may "
                "contain missed requirements. Findings are review candidates, "
                "not confirmed defects."
            ),
        }

    @app.get("/workspaces/{workspace}/compare")
    def revisions(
        workspace: str, before: str, after: str, authorization: str | None = Header(None)
    ):
        first = export(workspace, before, authorization)
        second = export(workspace, after, authorization)
        if first["document"]["title"] != second["document"]["title"]:
            raise HTTPException(422, "Compare revisions of the same document title")
        try:
            return compare(first["entities"], second["entities"])
        except ValueError as error:
            raise HTTPException(409, str(error)) from error

    return app


app = create_app()
