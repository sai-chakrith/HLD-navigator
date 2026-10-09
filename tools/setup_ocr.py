"""Explicit download of the official Tesseract Windows release installer."""

import json
from pathlib import Path

from setup_s1b_model import digest, fetch

ARTIFACT = {
    "file": "tesseract-installer.exe",
    "size": 21381872,
    "sha256": None,
    "url": "https://github.com/tesseract-ocr/tesseract/releases/download/5.5.0/"
    "tesseract-ocr-w64-setup-5.5.0.20241111.exe?download=true",
}


def main():
    root = Path(".data")
    root.mkdir(exist_ok=True)
    target = root / ARTIFACT["file"]
    partial = target.with_suffix(target.suffix + ".part")
    if target.exists() and target.stat().st_size < ARTIFACT["size"] and not partial.exists():
        with target.open("rb") as original, partial.open("wb") as output:
            while chunk := original.read(1024**2):
                output.write(chunk)
            output.truncate(ARTIFACT["size"])
    fetch(root, ARTIFACT, workers=8, allow_unpinned_checksum=True)
    metadata = {
        **ARTIFACT,
        "observed_sha256": digest(target),
        "verification": "Official release URL and byte size; publisher checksum unavailable",
        "installed": False,
    }
    (root / "ocr-artifact.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
