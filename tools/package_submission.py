"""Assemble an explicit allowlisted submission, excluding credentials/live state."""

import hashlib
import json
import shutil
import zipfile
from pathlib import Path

from hld_navigator import rag
from hld_navigator.models import ModelAnswer

ROOT = Path(__file__).resolve().parents[1]
NAME = "Amrita_Viswa_Vidyapeetham_Sai_Chakrith_Sulluru_ID_PENDING_CS1_AIML"
EXTENSIONS = {".py", ".md", ".json", ".toml", ".lock", ".txt", ".yml", ".yaml", ".xml"}
EXCLUDED = {
    "__pycache__",
    ".venv",
    ".git",
    ".data",
    ".pytest_cache",
    ".ruff_cache",
    "evidence",
}  # Tester-only local captures are not submission source.


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def copy(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def tree(source, destination, exclude_evidence=False):
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        forbidden = EXCLUDED if exclude_evidence else EXCLUDED - {"evidence"}
        if not path.is_file() or any(part in forbidden for part in relative.parts):
            continue
        if path.suffix in EXTENSIONS or path.name in {"LICENSE", "NOTICE"}:
            copy(path, destination / relative)


def main():
    base = ROOT / "output/submission"
    package = base / NAME
    package.mkdir(parents=True, exist_ok=False)
    source_root = package / "Code/HLD-navigator"
    for directory in ("src", "tests", "tools", "examples", "data", "docs", ".github"):
        tree(ROOT / directory, source_root / directory)
    tree(ROOT / "tester_acceptance", source_root / "tester_acceptance", exclude_evidence=True)
    for name in (
        "pyproject.toml",
        "uv.lock",
        "README.md",
        "STATUS.md",
        ".gitignore",
        ".gitattributes",
        ".env.example",
    ):
        copy(ROOT / name, source_root / name)
    tree(ROOT / "data", package / "Input_Data/data")
    tree(ROOT / "examples", package / "Input_Data/examples")
    tree(ROOT / "docs/evidence", package / "Evaluation_Results")
    tree(ROOT / "docs/submission", package / "Documentation/study-notes")
    for name in ("INTERVIEW_DEMO.md", "PORTFOLIO.md", "VALIDATION.md", "s1b-local-answers.md"):
        copy(ROOT / "docs" / name, package / "Documentation" / name)
    copy(
        ROOT / "output/pdf/HLD_Navigator_Technical_Report_v1.1.pdf",
        package / "Documentation/ID_PENDING_Technical_Report_v1.1.pdf",
    )
    copy(
        ROOT / "output/pdf/HLD_Navigator_Synopsis_v1.1.pdf",
        package / "Synopsis/ID_PENDING_Synopsis_UNSIGNED_v1.1.pdf",
    )
    copy(
        ROOT / "output/pdf/HLD_Navigator_Declarations_UNSIGNED_v1.1.pdf",
        package / "Declarations/ID_PENDING_Declarations_UNSIGNED_v1.1.pdf",
    )
    copy(
        ROOT / "docs/submission/AI-assistance-declaration-draft.md",
        package / "Declarations/AI-assistance-declaration-draft.md",
    )
    copy(
        ROOT / "output/presentation/HLD_Navigator_Presentation_v1.2.pptx",
        package / "Presentation/ID_PENDING_Presentation_v1.2.pptx",
    )
    copy(
        ROOT / "output/demo/HLD_Navigator_Walkthrough_v1.1.mp4",
        package / "Video/ID_PENDING_Captioned_Walkthrough_v1.1.mp4",
    )
    copy(ROOT / "output/demo/video-provenance.json", package / "Video/provenance.json")
    tree(ROOT / "output/demo/screenshots", package / "Video/screenshots")
    # Screenshot PNGs are explicit media rather than general source-tree files.
    for path in (ROOT / "output/demo/screenshots").glob("*.png"):
        copy(path, package / "Video/screenshots" / path.name)

    config = package / "Model_Prompts_Config"
    config.mkdir()
    (config / "system-prompt.txt").write_text(rag.SYSTEM_PROMPT, encoding="utf-8")
    (config / "answer-schema.json").write_text(
        json.dumps(ModelAnswer.model_json_schema(), indent=2), encoding="utf-8"
    )
    for name in ("answer-candidate-v3.json", "answer-runtime-v3.json"):
        copy(ROOT / "docs/evidence" / name, config / name)
    copy(ROOT / "docs/s1b-local-answers.md", config / "REPRODUCE.md")
    copy(ROOT / "tools/setup_s1b_model.py", config / "pinned-answer-artifacts.py")
    copy(ROOT / "tools/setup_local_models.py", config / "pinned-runtime-embedding-artifacts.py")
    (config / "source-preprocessing.txt").write_text(
        "Generation/citation quarantine pattern:\n"
        + rag.DIRECTIVE_LINE.pattern
        + "\nObvious assistant-directed lines are excluded; originals remain in evidence. "
        "This conservative heuristic can miss attacks and omit legitimate lines.\n"
        "Raw fixed-case evidence and actual post-preprocessing prompts are both recorded. "
        "The final cases were used in development, not protected holdout evaluation.\n"
    )

    start = """# HLD Navigator submission draft - version 1.2

Student: Sai Chakrith Sulluru
University: Amrita Viswa Vidyapeetham
Faculty guide: Dr. D. Palmani
Register/team ID: NOT SUPPLIED. Replace ID_PENDING before submission.

Read Documentation/study-notes/COMPLETION_REPORT.md first.
Source lives in Code/HLD-navigator. From that directory run:

    uv sync --frozen --extra dev
    uv run python tools/demo.py

Open http://127.0.0.1:8511. Set API port 8011, workspace demo and the private token
printed by the launcher. A new isolated demo database is created; no credentials
or live databases are shipped. Inference weights/runtime are omitted intentionally;
optional model provisioning commands and pinned hashes are included.

499 regressions pass locally. The default uses cited lexical source excerpts.
Optional model synthesis still has semantic mistakes and requires human review.
Evidence is synthetic/public developer validation, not independent OEM acceptance.
The five-minute video is a captioned sequence of actual UI captures, not a
continuous screen/voice recording. Practice and personalize the presentation/demo.

Synopsis and declarations are unsigned. Obtain faculty approval and personally
verify/sign student declarations. No identity, signatures or external acceptance
were invented. Source/AI assistance is disclosed. No external applications sent.

MANIFEST.json records SHA-256 for every packaged file except itself.
"""
    (package / "START_HERE.md").write_text(start, encoding="utf-8")
    files = {
        path.relative_to(package).as_posix(): digest(path)
        for path in sorted(package.rglob("*"))
        if path.is_file()
    }
    (package / "MANIFEST.json").write_text(
        json.dumps(
            {
                "version": "1.2",
                "identity": json.loads((ROOT / "docs/submission/identity.json").read_text()),
                "files": files,
                "excluded": [
                    "tokens",
                    "live databases",
                    "weights",
                    "virtual environments",
                    "private original instruction PDFs",
                    "Git/private render state",
                ],
                "independent_acceptance": False,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    archive = base / "HLD_Navigator_Submission_v1.2.zip"
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(package.rglob("*")):
            if path.is_file():
                bundle.write(path, path.relative_to(base).as_posix())
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.testzip() is None
        for name, expected in files.items():
            assert hashlib.sha256(bundle.read(NAME + "/" + name)).hexdigest() == expected
        assert not any(
            "/.data/" in name or name.endswith((".db", ".secret", ".gguf", ".env"))
            for name in bundle.namelist()
        )
    receipt = {
        "archive": archive.name,
        "sha256": digest(archive),
        "bytes": archive.stat().st_size,
        "packaged_files": len(files) + 1,
        "crc_and_manifest_verification": "PASS",
    }
    (base / "package-receipt.json").write_text(json.dumps(receipt, indent=2))
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
