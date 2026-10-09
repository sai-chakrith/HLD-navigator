"""Build truthful submission PDFs with the bundled ReportLab runtime."""

# ruff: noqa: E501 -- Report prose is kept as whole paragraphs for editorial review.

import json
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/pdf"
INK = colors.HexColor("#193653")
BLUE = colors.HexColor("#276CAE")
STYLES = getSampleStyleSheet()
STYLES.add(
    ParagraphStyle(
        "DocumentTitle",
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=29,
        textColor=INK,
        spaceAfter=18,
    )
)
STYLES.add(
    ParagraphStyle(
        "SectionTitle",
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=19,
        textColor=BLUE,
        spaceBefore=15,
        spaceAfter=8,
    )
)
STYLES["BodyText"].fontSize = 10
STYLES["BodyText"].leading = 15
STYLES["BodyText"].spaceAfter = 8


def paragraph(text, style="BodyText"):
    return Paragraph(escape(text), STYLES[style])


def section(story, title, *texts):
    story.append(paragraph(title, "SectionTitle"))
    story.extend(paragraph(text) for text in texts)


def table(story, rows):
    cells = [[paragraph(str(value)) for value in row] for row in rows]
    grid = Table(cells, colWidths=[55 * mm, 115 * mm], repeatRows=1, hAlign="LEFT")
    grid.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EDF2F7")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D7DFE8")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.extend([grid, Spacer(1, 8)])


def footer(canvas, doc):
    canvas.setStrokeColor(colors.HexColor("#D7DFE8"))
    canvas.line(20 * mm, 17 * mm, 190 * mm, 17 * mm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(INK)
    canvas.drawString(
        20 * mm, 12 * mm, "HLD Navigator | CS1 | Developer validation | 09 October 2026"
    )
    canvas.drawRightString(190 * mm, 12 * mm, str(doc.page))


def build(name, story):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=24 * mm,
        title="HLD Navigator - " + name.replace("_", " "),
        author="Sai Chakrith Sulluru; Codex assistance disclosed",
    ).build(story, onFirstPage=footer, onLaterPages=footer)
    print(path)


def cover(title):
    return [
        paragraph(title, "DocumentTitle"),
        paragraph("HLD Navigator - AUTOSAR HLD Document Analysis Assistant"),
        paragraph("Case Study 1 | TechPulse FY-26 Applied AI/ML"),
        paragraph("Sai Chakrith Sulluru | Amrita Viswa Vidyapeetham"),
        paragraph("Faculty guide: Dr. D. Palmani | Register/team ID: ____________________"),
        paragraph("Version 1.1 | 09 October 2026 | Unsigned submission draft"),
    ]


def main():
    identity = json.loads((ROOT / "docs/submission/identity.json").read_text())
    assert identity["faculty_guide"] == "Dr. D. Palmani"
    model_file = ROOT / "docs/evidence/answer-run-v3/summary.json"
    model = json.loads(model_file.read_text()) if model_file.exists() else None
    model_result = (
        f"Live 7B experiment: {model['raw_contract_passes']}/30 raw JSON/citation contract passes; "
        f"{model['raw_generation_errors']} generation errors. See separate raw and semantic assessments. "
        "Developer review: 8/12 useful complete answerable cases, 3/5 conflicts and "
        "4/5 safe useful injection cases. All 8 must-abstain cases abstained; no instruction "
        "following was found in 5 injection cases. Semantic mistakes remain. "
        "These fixed synthetic development cases do not establish OEM accuracy."
        if model
        else "The pinned 7B live experiment is in progress. No answer-model acceptance is claimed."
    )

    story = cover("Technical report")
    section(
        story,
        "1. Problem and objective",
        "Architecture reviewers must reconcile components, interfaces, ports, signals, flows and dependencies across long HLDs and revisions. Manual searching can obscure provenance and differences.",
        "This project provides an evidence-linked review workspace with structured proposals, source citations, explicit uncertainty and controlled exports. It supports engineering judgment; it does not certify automotive safety or AUTOSAR conformance.",
    )
    section(
        story,
        "2. Scope and data",
        "Inputs are PDF, Markdown and text. Synthetic powertrain fixtures exercise supported prose and tables. Five public KUKSA documents are pinned to immutable repository revisions, with license files, source URLs and hashes. Three form the unchanged public extraction baseline; two are additional unfamiliar-input material.",
        "Tata supplied no OEM HLDs. The real OCR integration used an authorized image-only project-instructions PDF. It is a genuine scan but is not an HLD accuracy benchmark. Synthetic fixtures and agent-authored annotations are labeled throughout.",
    )
    section(
        story,
        "3. Architecture and implementation",
        "FastAPI exposes authenticated workspace APIs. Streamlit supplies the engineering UI. SQLite stores original file bytes, source blocks and locations, normalized entities, document revisions, review decisions, memberships, audit history, FTS search and optional vector indexes.",
        "The extraction pipeline hashes and validates files, obtains text or explicitly enabled Tesseract OCR, joins supported wrapped prose, recognizes architecture statements and tables, and records warnings for unsupported or ambiguous material. Proposal approval is separate from source and warning review.",
        "The design uses a custom SQLite cosine index rather than the FAISS/Chroma examples in the case-study brief. This keeps local persistence simple and inspectable; it is a declared implementation variance.",
    )
    table(
        story,
        [
            ["Capability", "Behavior"],
            [
                "Governed review",
                "Reviewer decisions retain literal evidence and history. Empty/unresolved documents block export.",
            ],
            [
                "Architecture reports",
                "Approved component attributes and ports, incoming/outgoing declared dependencies, cited component reports and a dependency graph.",
            ],
            [
                "Revision analysis",
                "Added, removed and changed entities, provider/consumer/type findings, and before/after impact paths limited to two declared edges.",
            ],
            [
                "Access and recovery",
                "Workspace roles, token rotation/revocation, additive schema migration, audited actions and integrity-checked SQLite backup/restore to a new path.",
            ],
        ],
    )
    section(
        story,
        "4. AI/ML approach",
        "Extraction uses explicit patterns rather than trained entity prediction. Retrieval defaults to FTS lexical search; optional BGE-small-en-v1.5 f16 embeddings use persistent cosine ranking. No training, fine-tuning, PCA or measured feature importance is claimed.",
            "Optional local llama.cpp answers use a pre-trained Qwen instruct model and retrieved eligible evidence. Schema-constrained generation returns claims, source IDs and literal snippets. Obvious assistant-directed source lines are quarantined from generation and citations, while originals remain available. The guard rejects malformed or unresolvable citations and returns explicit abstention. These controls do not guarantee injection resistance or semantic entailment; a reviewer must check each claim.",
        "Model artifacts and CPU runtime are pinned and hash verified. Local endpoints bind to loopback, bypass inherited proxies and reject external redirects. Generation uses temperature zero, bounded context/output and timeout. No cloud model service is required for the default demo.",
    )
    section(story, "5. Verification and measured results")
    table(
        story,
        [
            ["Check", "Recorded result / boundary"],
            [
                "Regression suite",
                    "499 passed; one upstream Starlette/httpx deprecation warning. Windows/Python 3.14.8.",
            ],
            [
                "Live HTTP",
                "Unauthorized request rejected; eight fictional facts reviewed and exported; lexical search returned traceable evidence.",
            ],
            [
                "Streamlit",
                "AppTest exercised the actual API transport, report rendering and export controls.",
            ],
            [
                "Learned retrieval",
                "Four fixed public-document questions: lexical and BGE recall@5 both 0.75; MRR 0.75 and 0.625 respectively. No learned advantage shown.",
            ],
            [
                "Public extraction",
                "Three frozen documents: 18 missed facts and one unexpected fact against provisional selected agent annotations. Labels are non-exhaustive and not independently reviewed.",
            ],
            [
                "Real OCR",
                "Tesseract 5.5.0 processed seven image-only pages: 312 OCR blocks; all seven pages retained mandatory review blockers. No transcription accuracy measured.",
            ],
            ["Local answers", model_result],
        ],
    )
    section(
        story,
        "6. Failure handling and risks",
        "Unsupported prose, negation, conditional statements, missing references and OCR uncertainty remain visible rather than silently becoming approved architecture facts. Model failures cause guarded abstention. A source containing instructions is untrusted evidence, not authority.",
        "The public baseline exposes substantial parser omissions. Arbitrary OEM layouts, visual diagram topology, engineering completeness and formal AUTOSAR conformance remain unvalidated. The small retrieval experiment and synthetic answer cases cannot support general performance percentages or productivity claims.",
        "Tokens and SQLite audit records are local pilot controls. Filesystem administrators can alter the database. Enterprise IAM, TLS, concurrency/load qualification and tamper-resistant auditing are outside the demonstrated deployment scope. The Windows/Linux CI workflow is configured but hosted execution has not been observed.",
    )
    section(
        story,
        "7. Reproduction and demonstration",
        "Install Python 3.11+ and uv, then run: uv sync --frozen --extra dev. Verify with: uv run python -m pytest -q; uv run python -m ruff check src tests tools; uv run python tools/smoke.py.",
        "Start the isolated interview demo with: uv run python tools/demo.py. The terminal prints the private token; enter it with workspace demo in the UI at http://127.0.0.1:8511. The API is at http://127.0.0.1:8011. Existing demo databases are never overwritten; pass a new --database path for another run.",
        "Follow docs/INTERVIEW_DEMO.md to inspect fictional revisions, compare findings and impact paths, export the reviewed architecture report, then demonstrate blocked export of the unreviewed public document. Fictional fixture auto-approval is clearly labeled.",
        "Model/OCR setup is optional and explicit. See docs/s1b-local-answers.md, README.md and the evidence JSON for pinned artifacts, commands and actual environment. Keep tokens, live databases and downloaded weights outside the submission source bundle.",
    )
    section(
        story,
        "8. Ownership, assistance and next acceptance",
        "Codex assisted implementation, debugging, tests, documentation and packaging. Earlier separate AI development/tester sessions authored development checks. The present reviewer is the same coding assistant, so the final judgments are developer review, not independent human validation. The student must personally inspect and explain the work before signing declarations.",
        "Before real engineering use: obtain authorized family-separated OEM HLDs, independent architect annotations and adjudication; measure extraction/answer/OCR errors, review time and revision completeness; qualify deployment controls. Unknown register/team ID and faculty/student signatures are left blank. No faculty approval is implied.",
    )
    section(
        story,
        "9. Evidence and references",
        "Project implementation: src/hld_navigator/, tests/, pyproject.toml and uv.lock. Current results: docs/evidence/completion-pytest.xml, live-http.json, public-current.json, current-retrieval.json, current-embedding-transport.json and ocr-engine.json. Local answer outputs, frozen identities and assessments are retained separately when executed.",
        "Public source provenance: data/evaluation/public/provenance.json and additional/provenance.json; Eclipse KUKSA repositories with recorded license files. Model/runtime sources: official Qwen Hugging Face repository, ggml-org model conversion and llama.cpp release records in setup scripts. OCR: official Tesseract GitHub release; publisher installer checksum was unavailable, so its observed digest is identified as such.",
    )
    build("HLD_Navigator_Technical_Report_v1.1.pdf", story)

    story = cover("Project synopsis")
    section(
        story,
        "Proposed work and delivered scope",
        "Build a local AUTOSAR HLD review assistant that turns supported document statements into evidence-linked architecture proposals, permits human correction/approval, retrieves cited context, compares revisions and exports reviewed component/dependency reports.",
        "Delivered software includes PDF/Markdown/text ingestion, optional real OCR, governed review, workspace access controls, FTS search, optional learned embeddings/local answers, architecture findings, dependency visualization, revision impact analysis, recovery tools and a reproducible fictional interview demo.",
    )
    section(
        story,
        "Method and evaluation",
        "Use explicit extraction rules, immutable source bytes/locations, separate review states, lexical and optional dense retrieval, and structured answer citation validation. Evaluate with regressions, real HTTP/UI integration, frozen public documents, real OCR and fixed synthetic answer cases.",
            "The final local regression suite passes 499 tests. Retrieval and public extraction results expose remaining limitations, rather than establishing OEM reliability. No independent automotive validation or measured time saving has occurred.",
    )
    section(
        story,
        "Expected deliverables",
        "Source and lockfile, synthetic/public input corpus with provenance, model/prompt configuration, evaluation evidence, technical report, editable presentation, demo instructions and unsigned integrity/AI-use declarations.",
    )
    section(
        story,
        "Faculty approval",
        "This synopsis is a prepared draft. Dr. D. Palmani has not supplied approval or a signature.",
        "Faculty signature: ____________________    Date: ____________________",
        "Student signature: ____________________    Register/team ID: ____________________",
    )
    build("HLD_Navigator_Synopsis_v1.1.pdf", story)

    story = cover("Integrity and AI-use declarations")
    section(
        story,
        "Unsigned draft - personal verification required",
        "This document records known assistance. It does not claim that the student has personally verified every artifact. The student must review, correct and personally sign the final declarations; the assistant cannot supply student or faculty signatures.",
    )
    section(
        story,
        "Academic integrity declaration",
        "I will accurately identify source code, public datasets, pretrained models and assistance used. I will not represent synthetic fixtures, agent annotations or mocked results as independent human validation or live measured model performance. I will explain limitations, ownership and individual contributions truthfully.",
    )
    section(
        story,
        "Known AI/model assistance",
        "OpenAI Codex coding assistant: implementation, tests, debugging, developer review, documentation, presentation and packaging assistance. Separate earlier AI developer/tester chats provided development evidence; this is not independent human architecture review.",
        "BGE-small-en-v1.5 f16: local embedding comparison. Qwen2.5-0.5B-Instruct Q4_K_M: historical failed answer experiment. Qwen2.5-7B-Instruct Q4_K_M: current pinned answer-model experiment, with outcome recorded in the evaluation evidence. No training or fine-tuning was performed.",
        "Personal student verification of implementation, evidence, configuration and artifacts: ____________________ (enter accurately).",
    )
    section(
        story,
        "Signatures",
        "Student: Sai Chakrith Sulluru",
        "Student signature: ____________________    Date: ____________________",
        "Register/team ID: ____________________",
        "Faculty guide: Dr. D. Palmani",
        "Faculty approval/signature, if required: ____________________",
    )
    build("HLD_Navigator_Declarations_UNSIGNED_v1.1.pdf", story)


if __name__ == "__main__":
    main()
