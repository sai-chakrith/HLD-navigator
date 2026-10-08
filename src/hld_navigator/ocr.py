"""Opt-in local Tesseract adapter. No OCR output is auto-approved."""

import csv
import io
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def page_ocr(page):
    executable = os.getenv("HLD_NAVIGATOR_TESSERACT") or shutil.which("tesseract")
    if os.getenv("HLD_NAVIGATOR_OCR") != "1" or not executable:
        raise ValueError("OCR required: enable HLD_NAVIGATOR_OCR=1 and configure local Tesseract")
    if page.width * page.height > 4_000_000:
        raise ValueError("PDF page exceeds the OCR rendering limit")
    with tempfile.TemporaryDirectory() as directory:
        image = Path(directory) / "page.png"
        page.to_image(resolution=180).original.save(image)
        result = subprocess.run(
            [executable, str(image), "stdout", "tsv"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
            check=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    lines = {}
    for row in csv.DictReader(io.StringIO(result.stdout), delimiter="\t"):
        if row["text"].strip() and float(row["conf"]) >= 0:
            key = (row["block_num"], row["par_num"], row["line_num"])
            lines.setdefault(key, []).append(row)
    return [
        (" ".join(r["text"] for r in rows), min(float(r["conf"]) for r in rows))
        for rows in lines.values()
    ]
