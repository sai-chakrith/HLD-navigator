"""Create an isolated interview demo; never modify the operator's existing database."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from hld_navigator.extraction import extract
from hld_navigator.models import Review, SourceReview
from hld_navigator.store import Store

ROOT = Path(__file__).resolve().parents[1]


def seed(database):
    database = Path(database).resolve()
    database.parent.mkdir(parents=True, exist_ok=True)
    with database.open("xb"):
        pass
    store = Store(str(database))
    token = store.provision("demo-reviewer", "demo", "reviewer")
    documents = []
    for version in ("v1", "v2"):
        source = ROOT / f"examples/revision-review/{version}.md"
        content = source.read_bytes()
        blocks, entities, warnings = extract(source.name, content)
        identifier = store.ingest(
            "demo",
            "Synthetic Powertrain",
            version,
            source.name,
            content,
            blocks,
            entities,
            warnings,
            "demo-reviewer",
        )
        reason = "Auto-approved fictional demo fixture; not an engineering acceptance decision"
        store.review(
            "demo",
            identifier,
            SourceReview(approved=True, reason=reason),
            "demo-reviewer",
            source=True,
        )
        for entity in store.entities("demo", identifier):
            store.review(
                "demo", entity["id"], Review(status="approved", reason=reason), "demo-reviewer"
            )
        documents.append(identifier)
    # Public architecture stays proposed so a user can demonstrate actual review.
    source = ROOT / "data/evaluation/public/system-architecture.md"
    content = source.read_bytes()
    blocks, entities, warnings = extract(source.name, content)
    public = store.ingest(
        "demo",
        "Public KUKSA Architecture",
        "pinned-baseline",
        source.name,
        content,
        blocks,
        entities,
        warnings,
        "demo-reviewer",
    )
    return token, {"synthetic_revisions": documents, "unreviewed_public_document": public}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=ROOT / ".data/interview-demo.db")
    parser.add_argument("--api-port", type=int, default=8011)
    parser.add_argument("--ui-port", type=int, default=8511)
    parser.add_argument("--seed-only", action="store_true")
    args = parser.parse_args()
    try:
        token, documents = seed(args.database)
    except FileExistsError:
        parser.exit(1, "Demo database already exists. Choose a new --database path.\n")
    print(json.dumps(documents, indent=2), flush=True)
    print("Workspace: demo. Individual token (keep private):", token, flush=True)
    if args.seed_only:
        return
    env = os.environ.copy()
    env["HLD_NAVIGATOR_DB"] = str(args.database.resolve())
    env["HLD_NAVIGATOR_API_URL"] = f"http://127.0.0.1:{args.api_port}"
    # Default demo is self-contained and needs no model service.
    for key in (
        "HLD_NAVIGATOR_CHAT_MODEL",
        "HLD_NAVIGATOR_OLLAMA_MODEL",
        "HLD_NAVIGATOR_EMBED_MODEL",
    ):
        env.pop(key, None)
    processes = []
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        processes.append(
            subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "hld_navigator.app:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(args.api_port),
                ],
                env=env,
                cwd=ROOT,
                creationflags=flags,
            )
        )
        processes.append(
            subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "streamlit",
                    "run",
                    str(ROOT / "src/hld_navigator/ui.py"),
                    "--server.address",
                    "127.0.0.1",
                    "--server.port",
                    str(args.ui_port),
                    "--server.headless",
                    "true",
                ],
                env=env,
                cwd=ROOT,
                creationflags=flags,
            )
        )
        print(
            f"Open http://127.0.0.1:{args.ui_port}; backend connected automatically.",
            flush=True,
        )
        print("Press Ctrl+C to stop both services. The demo database is retained.", flush=True)
        while all(process.poll() is None for process in processes):
            try:
                processes[0].wait(timeout=1)
            except subprocess.TimeoutExpired:
                pass
    except KeyboardInterrupt:
        pass
    finally:
        for process in processes:
            if process.poll() is None:
                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                        capture_output=True,
                        creationflags=flags,
                        check=False,
                    )
                else:
                    process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


if __name__ == "__main__":
    main()
