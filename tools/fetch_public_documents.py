"""Fetch additional public architecture examples at an immutable upstream commit."""

import hashlib
import json
from pathlib import Path
from time import sleep
from urllib.error import URLError
from urllib.request import urlopen

REVISION = "7a210d01fd00a8035cf68c05336bd0860777e892"
BASE = f"https://raw.githubusercontent.com/eclipse-kuksa/kuksa-databroker/{REVISION}"
ROOT = Path(__file__).resolve().parents[1] / "data/evaluation/public/additional"


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    metadata_path = ROOT / "provenance.json"
    previous = json.loads(metadata_path.read_text()) if metadata_path.exists() else None
    documents = []
    for remote, local in (
        ("README.md", "overview.md"),
        ("doc/user_guide.md", "user-guide.md"),
        ("LICENSE", "LICENSE"),
    ):
        url = f"{BASE}/{remote}"
        for attempt in range(3):
            try:
                with urlopen(url, timeout=20) as response:
                    content = response.read(10 * 1024 * 1024 + 1)
                break
            except (URLError, TimeoutError):
                if attempt == 2:
                    raise
                sleep(attempt + 1)
        if len(content) > 10 * 1024 * 1024:
            raise ValueError("Public document exceeds ingestion limit")
        digest = hashlib.sha256(content).hexdigest()
        if previous:
            expected = next(d for d in previous["documents"] if d["file"] == local)
            if expected["sha256"] != digest:
                raise ValueError("Pinned public source hash changed")
        (ROOT / local).write_bytes(content)
        documents.append({"file": local, "url": url, "sha256": digest, "bytes": len(content)})
    metadata = {
        "repository": "eclipse-kuksa/kuksa-databroker",
        "revision": REVISION,
        "license": "Apache-2.0",
        "evaluation": "developer_public_examples",
        "limitations": "Not proprietary OEM HLDs or an independent holdout",
        "documents": documents,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print("Fetched and hashed", len(documents) - 1, "additional documents plus LICENSE")


if __name__ == "__main__":
    main()
