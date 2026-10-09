"""Create unsigned submission PDFs from the current remediation report and identity."""

import json
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

ROOT = Path(__file__).resolve().parents[1]


def build(name, title, paragraphs):
    identity = json.loads((ROOT / "docs/submission/identity.json").read_text(encoding="utf-8"))
    out = ROOT / "output/pdf" / f"{identity['register_or_team_id']}_{name}_v1.3.pdf"
    styles = getSampleStyleSheet()
    styles["BodyText"].leading = 15
    styles["BodyText"].spaceAfter = 9
    story = [Paragraph(escape(title), styles["Title"]), Spacer(1, 12)]
    story.append(
        Paragraph(
            escape(
                f"{identity['student']} | {identity['register_or_team_id']} | "
                f"{identity['university']} | Guide: {identity['faculty_guide']}"
            ),
            styles["BodyText"],
        )
    )
    for text in paragraphs:
        if not text.strip():
            continue
        style = styles["Heading2"] if text.startswith("## ") else styles["BodyText"]
        story.append(Paragraph(escape(text.removeprefix("## ")), style))

    def footer(canvas, doc):
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#536273"))
        canvas.drawString(40, 28, "v1.3 | Developer measurements; mandatory human actions pending")
        canvas.drawRightString(A4[0] - 40, 28, str(doc.page))

    SimpleDocTemplate(
        str(out), pagesize=A4, leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=45
    ).build(story, onFirstPage=footer, onLaterPages=footer)
    return out


def main():
    report = (ROOT / "docs/submission/REMEDIATION_REPORT.md").read_text(encoding="utf-8")
    build("Technical_Report", "HLD Navigator — Technical Remediation", report.splitlines()[1:])
    build(
        "Synopsis_UNSIGNED",
        "HLD Navigator — Synopsis (Unsigned)",
        [
            "## Problem and scope",
            "Case Study 1: review supported AUTOSAR-style HLD prose and tables, retain source "
            "provenance, build architecture inventories, answer reviewed-field questions, compare "
            "revisions and export cited relationships. This is an engineering pilot.",
            "## Implementation",
            "FastAPI, Streamlit and SQLite; deterministic extraction and approved-field answering; "
            "optional local Qwen/BGE. Original context remains separate from reviewed facts. "
            "All free synthesis requires human review; no general semantic guarantee is claimed.",
            "## Measured limits",
            "Unchanged public labels: 9 TP, 3 FP, 10 FN across 19 expected facts. Frozen "
            "agent-authored synthetic labels: 41 TP, 0 FP, 0 FN; warnings 2 TP, 2 FP, 0 FN. "
            "These small development measurements do not establish OEM accuracy.",
            "## Approval",
            "Student signature: ____________________ Date: ____________________",
            "Faculty synopsis approval/signature: ____________________ Date: ____________________",
            "A continuous 5–10 minute live recording and personal code-ownership demonstration "
            "remain mandatory actions. This unsigned draft is not administratively eligible.",
        ],
    )
    build(
        "Declarations_UNSIGNED",
        "Integrity and AI Use — Unsigned",
        [
            "## Student verification (to be completed personally)",
            "I must personally verify the submitted implementation, evidence, sources and claims "
            "before signing. No student verification is asserted by this unsigned draft.",
            "## Disclosed assistance",
            "OpenAI Codex assisted implementation, tests, debugging, developer evaluation, "
            "documentation and packaging. Qwen2.5-7B-Instruct Q4_K_M was used for the local "
            "answer experiment; BGE-small-en-v1.5 for retrieval. Historical 0.5B failures remain "
            "in the repository. No model training/fine-tuning or independent OEM acceptance "
            "claimed.",
            "Synthetic evaluation labels and semantic assessments are agent-authored, not "
            "independent engineer review. Public KUKSA inputs retain licenses and provenance.",
            "## Signatures",
            "Personal verification statement: _____________________________________________",
            "Student signature: ____________________ Date: ____________________",
            "Faculty approval/signature where required: ____________________ "
            "Date: ____________________",
            "This declaration has not been signed. Do not submit it as a verified declaration.",
        ],
    )


if __name__ == "__main__":
    main()
