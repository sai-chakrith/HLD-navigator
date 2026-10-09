"""Replay a scoped review on real public architecture prose rendered as PDF."""

import hashlib
import json
from pathlib import Path
from xml.sax.saxutils import escape

from fastapi.testclient import TestClient
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from hld_navigator.app import create_app
from hld_navigator.store import Store

ROOT = Path(__file__).resolve().parents[1]


def render(source, destination):
    styles = getSampleStyleSheet()
    story = []
    for paragraph in source.split("\n\n"):
        text = " ".join(paragraph.splitlines())
        if not text.strip():
            continue
        style = styles["Heading2"] if text.startswith("#") else styles["BodyText"]
        story.extend([Paragraph(escape(text.lstrip("# ")), style), Spacer(1, 8)])
    SimpleDocTemplate(str(destination), title="KUKSA public architecture demo").build(story)


def seed_pdf(database, output):
    database = Path(database).resolve()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    database.parent.mkdir(parents=True, exist_ok=True)
    with database.open("xb"):
        pass
    token = Store(str(database)).provision("demo-reviewer", "demo", "reviewer")
    source_path = ROOT / "data/evaluation/public/system-architecture.md"
    source = source_path.read_text(encoding="utf-8")
    report = {
        "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "provenance": json.loads((source_path.parent / "provenance.json").read_text()),
        "input": "Real KUKSA architecture prose, repaginated as PDF; Markdown retained literally",
        "revision": "Illustrative Cloud Adapter to Telemetry Adapter rename; not upstream history",
        "review": "Scripted scoped demonstration, not independent human approval",
        "steps": [],
    }
    reason = "Scripted demo: source-backed component names only; not engineering acceptance"
    ids = []
    with TestClient(create_app(str(database))) as client:
        headers = {"Authorization": "Bearer " + token}
        base = "/workspaces/demo"

        def request(method, path, **kwargs):
            response = client.request(method, base + path, headers=headers, **kwargs)
            response.raise_for_status()
            return response.json()

        for version, text, adapter in (
            ("public-pdf", source, "Cloud Adapter"),
            (
                "illustrative-edit",
                source.replace("Cloud Adapter", "Telemetry Adapter"),
                "Telemetry Adapter",
            ),
        ):
            pdf = output / f"kuksa-{version}.pdf"
            render(text, pdf)
            uploaded = request(
                "POST",
                "/documents",
                data={"title": "KUKSA PDF architecture", "version": version},
                files={"file": (pdf.name, pdf.read_bytes(), "application/pdf")},
            )
            identifier = uploaded["id"]
            ids.append(identifier)
            # Narrow review scope deliberately excludes automatic proposals. No tuning follows.
            automatic = request("GET", "/entities", params={"document_id": identifier})
            for entity in automatic:
                request(
                    "POST",
                    f"/entities/{entity['id']}/review",
                    json={"status": "rejected", "reason": "Outside scripted name-only scope"},
                )
            blocks = request("GET", f"/documents/{identifier}/blocks")
            manual = []
            for name in ("KUKSA databroker", "DBC Feeder", adapter):
                block = next(b for b in blocks if name in b["text"])
                proposal = request(
                    "POST",
                    f"/documents/{identifier}/entities",
                    json={
                        "kind": "component",
                        "name": name,
                        "attributes": {},
                        "evidence_block_id": block["id"],
                    },
                )
                request(
                    "POST",
                    f"/entities/{proposal['id']}/review",
                    json={"status": "approved", "reason": reason},
                )
                manual.append({"name": name, "block": block, "proposal": proposal})
            request(
                "POST", f"/documents/{identifier}/review", json={"approved": True, "reason": reason}
            )
            request(
                "POST",
                f"/documents/{identifier}/coverage-review",
                json={
                    "scope": "Only manually proposed component names; all edges, diagrams, "
                    "protocols "
                    "and other statements excluded. This inventory is deliberately incomplete.",
                    "reason": reason,
                },
            )
            queried = request(
                "POST",
                "/query",
                json={
                    "text": adapter,
                    "document_id": identifier,
                },
            )
            if not queried["evidence"]:
                raise RuntimeError("Approved component search returned no evidence")
            exported = request("GET", "/export", params={"document_id": identifier})
            report["steps"].append(
                {
                    "pdf": pdf.name,
                    "pdf_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
                    "upload": uploaded,
                    "rejected_automatic": automatic,
                    "manual_review": manual,
                    "query": queried,
                    "export": exported,
                }
            )
        report["comparison"] = request(
            "GET", "/compare", params={"before": ids[0], "after": ids[1]}
        )
    report["success"] = True
    (output / "demo.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    # Guard against a misleading comparison that silently showed the same revision.
    if not report["comparison"]["added"] or not report["comparison"]["removed"]:
        raise RuntimeError("Illustrative rename was not visible in comparison")
    return token, {"pdf_revisions": ids, "evidence": str(output / "demo.json")}
