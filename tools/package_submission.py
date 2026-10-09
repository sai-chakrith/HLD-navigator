"""Assemble an explicit allowlisted submission, excluding credentials/live state."""

import hashlib
import json
import shutil
import zipfile
from pathlib import Path

from hld_navigator import rag
from hld_navigator.models import ModelAnswer

ROOT = Path(__file__).resolve().parents[1]
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
    if "Evaluation_Results" in destination.parts and destination.suffix in {
        ".xml",
        ".json",
        ".txt",
    }:
        # Keep original audit records in the repository; exported copies redact
        # developer-specific workspace locations without changing model answers.
        content = destination.read_text(encoding="utf-8")
        for prefix in (str(ROOT), ROOT.as_posix(), json.dumps(str(ROOT))[1:-1]):
            content = content.replace(prefix, "[DEVELOPER_WORKSPACE]")
        destination.write_text(content, encoding="utf-8")


def tree(source, destination, exclude_evidence=False):
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        forbidden = EXCLUDED if exclude_evidence else EXCLUDED - {"evidence"}
        if not path.is_file() or any(part in forbidden for part in relative.parts):
            continue
        if path.suffix in EXTENSIONS or path.name in {"LICENSE", "NOTICE"}:
            copy(path, destination / relative)


def main():
    identity = json.loads((ROOT / "docs/submission/identity.json").read_text())
    identifier = identity["register_or_team_id"]
    if not identifier:
        raise ValueError("A real register/team ID is required")
    name = f"Amrita_Viswa_Vidyapeetham_Sai_Chakrith_Sulluru_{identifier}_CS1_AIML"
    base = ROOT / "output/submission"
    package = base / name
    package.mkdir(parents=True, exist_ok=False)
    source_root = package / "Code/HLD-navigator"
    for directory in ("src", "examples", "data", ".github"):
        tree(ROOT / directory, source_root / directory)
    for path in sorted((ROOT / "tests").glob("*.py")):
        if not path.name.startswith("test_tester_"):
            copy(path, source_root / "tests" / path.name)
    for name in (
        "demo.py",
        "smoke.py",
        "evaluate.py",
        "fetch_public_documents.py",
        "setup_local_models.py",
        "setup_s1b_model.py",
        "serve_local_model.py",
        "setup_ocr.py",
        "ocr_smoke.py",
    ):
        copy(ROOT / "tools" / name, source_root / "tools" / name)
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
    for name in ("INTERVIEW_DEMO.md", "PORTFOLIO.md", "LOCAL_SETUP.md"):
        copy(ROOT / "docs" / name, source_root / "docs" / name)
    copy(
        ROOT / "docs/submission/REMEDIATION_REPORT.md",
        source_root / "docs/submission/REMEDIATION_REPORT.md",
    )
    tree(ROOT / "data", package / "Input_Data/data")
    tree(ROOT / "examples", package / "Input_Data/examples")
    tree(ROOT / "docs/evidence/remediation", package / "Evaluation_Results/developer-measurements")
    for artifact, folder in (
        ("Technical_Report", "Documentation"),
        ("Synopsis_UNSIGNED", "Synopsis"),
        ("Declarations_UNSIGNED", "Declarations"),
    ):
        filename = f"{identifier}_{artifact}_v1.3.pdf"
        copy(ROOT / "output/pdf" / filename, package / folder / filename)
    copy(
        ROOT / "docs/submission/REMEDIATION_REPORT.md",
        package / "Documentation" / f"{identifier}_Remediation_Report_v1.3.md",
    )
    copy(
        ROOT / "docs/INTERVIEW_DEMO.md",
        package / "Video" / f"{identifier}_Live_Walkthrough_v1.3.md",
    )
    copy(
        ROOT / "docs/submission/AI-assistance-declaration-draft.md",
        package / "Declarations" / f"{identifier}_AI_Assistance_UNSIGNED_v1.3.md",
    )
    config = package / "Model_Prompts_Config"
    config.mkdir()
    (config / f"{identifier}_System_Prompt_v1.3.txt").write_text(
        rag.SYSTEM_PROMPT, encoding="utf-8"
    )
    (config / f"{identifier}_Answer_Schema_v1.3.json").write_text(
        json.dumps(ModelAnswer.model_json_schema(), indent=2), encoding="utf-8"
    )
    (config / f"{identifier}_Generation_Preprocessing_v1.3.txt").write_text(
        "Source instructions are heuristically quarantined; original context stays preserved.\n"
        + rag.DIRECTIVE_LINE.pattern
        + "\nNo general injection or entailment guarantee.\n"
        "Default fact evidence uses approved current entity fields (corrections labeled); "
        "source context "
        "is labeled separately and is not sent as approved synthesis evidence.\n"
    )
    copy(
        ROOT / "docs/evidence/answer-runtime-v3.json",
        config / f"{identifier}_Local_Model_Identity_v1.3.json",
    )
    copy(
        ROOT / "docs/evidence/remediation/submitted-source.json",
        config / f"{identifier}_Source_Identity_v1.3.json",
    )
    for folder in (
        "Synopsis",
        "Input_Data",
        "Code",
        "Model_Prompts_Config",
        "Evaluation_Results",
        "Documentation",
        "Video",
        "Declarations",
    ):
        (package / folder).mkdir(exist_ok=True)
    (package / "START_HERE.md").write_text(
        "# Submission draft v1.3 — not administratively eligible yet\n\n"
        f"Student: {identity['student']}\nID: {identifier}\n"
        "From Code/HLD-navigator: uv sync --frozen --extra dev; uv run python tools/demo.py.\n"
        "Read Documentation/*Remediation_Report* for measured results and limits.\n"
        "Real-time recording, student verification/signatures and faculty approval "
        "remain mandatory.\n"
        "Video contains a reproducible live script, NOT a completed compliant recording.\n"
        "Internal tester captures/scripts and historical slideshow decks are excluded.\n"
        "Run uv run pytest -q for the submission suite; its verified count is in the receipt.\n"
        "Weights/runtime, live databases and bearer tokens are excluded; provisioning is online.\n",
        encoding="utf-8",
    )
    files = {
        path.relative_to(package).as_posix(): digest(path)
        for path in sorted(package.rglob("*"))
        if path.is_file()
    }
    (package / "MANIFEST.json").write_text(
        json.dumps(
            {
                "version": "1.3",
                "identity": identity,
                "files": files,
                "independent_acceptance": False,
                "missing_mandatory_actions": [
                    "continuous live video",
                    "student verification/signatures",
                    "faculty approval/signatures",
                ],
                "test_scope": (
                    "tests excluding internal test_tester_*; no tester_acceptance dependency"
                ),
                "path_redaction": (
                    "Exported XML/JSON logs replace developer workspace paths; "
                    "originals retained in repository"
                ),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    archive = base / f"{identifier}_Submission_v1.3.zip"
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(package.rglob("*")):
            if path.is_file():
                bundle.write(path, path.relative_to(base).as_posix())
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.testzip() is None
        for filename, expected in files.items():
            assert (
                hashlib.sha256(bundle.read(package.name + "/" + filename)).hexdigest() == expected
            )
        assert not any(
            "tester_acceptance" in n
            or "/.data/" in n
            or n.endswith((".db", ".secret", ".gguf", ".env"))
            for n in bundle.namelist()
        )
    receipt = {
        "archive": archive.name,
        "sha256": digest(archive),
        "bytes": archive.stat().st_size,
        "packaged_files": len(files) + 1,
        "crc_and_manifest_verification": "PASS",
        "prompt_matches_source": True,
        "eligible_for_final_evaluation": False,
    }
    (base / f"{identifier}_Package_Receipt_v1.3.json").write_text(json.dumps(receipt, indent=2))
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
