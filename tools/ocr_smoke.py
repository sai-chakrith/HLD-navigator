"""Real OCR engine integration on an operator-supplied image-only PDF."""

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

import pdfplumber

from hld_navigator.extraction import extract
from hld_navigator.ocr import page_ocr


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("docs/evidence/ocr-engine.json"))
    args = parser.parse_args()
    os.environ["HLD_NAVIGATOR_OCR"] = "1"
    os.environ["HLD_NAVIGATOR_TESSERACT"] = str(args.executable.resolve())
    with pdfplumber.open(args.source) as pdf:
        page = pdf.pages[0]
        if (page.extract_text() or "").strip():
            raise ValueError("This check requires an image-only source page")
        lines = page_ocr(page)
    blocks, entities, warnings = extract(args.source.name, args.source.read_bytes())
    report = {
        "source_file": args.source.name,
        "source_sha256": digest(args.source),
        "engine_sha256": digest(args.executable),
        "engine_version": subprocess.check_output(
            [str(args.executable), "--version"], stderr=subprocess.STDOUT, text=True
        ),
        "first_page_lines": len(lines),
        "first_page_nonempty": any(text.strip() for text, _ in lines),
        "blocks": len(blocks),
        "entity_proposals": len(entities),
        "ocr_source_blocks": sum(b.location.origin == "ocr" for b in blocks),
        "blocking_ocr_warnings": sum(w["code"] == "ocr_review" for w in warnings),
        "warnings": warnings,
        "status": "REAL_ENGINE_INTEGRATION_PASS" if lines and blocks else "FAIL",
        "limitation": "No independent transcription or entity ground truth; "
        "document may be an instruction scan, not an OEM HLD",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "status",
                    "first_page_lines",
                    "blocks",
                    "entity_proposals",
                    "blocking_ocr_warnings",
                )
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
