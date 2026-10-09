"""Isolated live HTTP workflow; leaves no server or user credentials behind."""

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import requests

from hld_navigator.store import Store


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--with-model",
        action="store_true",
        help="Explicitly retain configured local answer-model settings",
    )
    parser.add_argument("--question", default="TorqueInterface")
    args = parser.parse_args()
    if args.with_model and not (
        os.getenv("HLD_NAVIGATOR_CHAT_MODEL") or os.getenv("HLD_NAVIGATOR_OLLAMA_MODEL")
    ):
        parser.error("Configure a local answer model before --with-model")
    report = {}
    with tempfile.TemporaryDirectory() as temporary:
        database = str(Path(temporary) / "smoke.db")
        token = Store(database).provision("smoke-reviewer", "pilot", "reviewer")
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        base = f"http://127.0.0.1:{port}"
        env = os.environ.copy()
        env["HLD_NAVIGATOR_DB"] = database
        for name in (
            "HLD_NAVIGATOR_OLLAMA_MODEL",
            "HLD_NAVIGATOR_CHAT_MODEL",
            "HLD_NAVIGATOR_EMBED_MODEL",
            "HLD_NAVIGATOR_CHAT_BACKEND",
            "HLD_NAVIGATOR_LOCAL_URL",
            "HLD_NAVIGATOR_OLLAMA_URL",
        ):
            if not args.with_model:
                env.pop(name, None)
        with (Path(temporary) / "server.log").open("w") as logs:
            server = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "hld_navigator.app:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                ],
                cwd=root,
                env=env,
                stdout=logs,
                stderr=logs,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            try:
                for _ in range(40):
                    try:
                        health = requests.get(base + "/health", timeout=1)
                        health.raise_for_status()
                        report["health"] = health.json()
                        break
                    except requests.RequestException:
                        if server.poll() is not None:
                            raise RuntimeError("API startup failed") from None
                        time.sleep(0.25)
                if "health" not in report:
                    raise RuntimeError("Startup deadline exceeded")
                url = base + "/workspaces/pilot"
                headers = {"Authorization": "Bearer " + token}
                assert requests.get(url + "/documents", timeout=3).status_code == 401
                upload = requests.post(
                    url + "/documents",
                    headers=headers,
                    data={"title": "Powertrain", "version": "1"},
                    files={
                        "file": (
                            "fixture.md",
                            (root / "data/evaluation/torque-prose.md").read_bytes(),
                        )
                    },
                    timeout=3,
                )
                upload.raise_for_status()
                document = upload.json()["id"]
                response = requests.post(
                    url + f"/documents/{document}/review",
                    headers=headers,
                    json={"approved": True, "reason": "Synthetic smoke"},
                    timeout=3,
                )
                response.raise_for_status()
                proposals = requests.get(
                    url + "/entities", headers=headers, params={"document_id": document}, timeout=3
                ).json()
                for entity in proposals:
                    response = requests.post(
                        url + f"/entities/{entity['id']}/review",
                        headers=headers,
                        json={"status": "approved", "reason": "Synthetic smoke"},
                        timeout=3,
                    )
                    response.raise_for_status()
                response = requests.post(
                    url + "/query",
                    headers=headers,
                    json={"text": args.question, "document_id": document},
                    timeout=200 if args.with_model else 3,
                )
                response.raise_for_status()
                assert response.json()["evidence"]
                exported = requests.get(
                    url + "/export", headers=headers, params={"document_id": document}, timeout=3
                )
                exported.raise_for_status()
                assert len(exported.json()["entities"]) == 8
                report.update(
                    unauthenticated_status=401,
                    approved_entities=8,
                    findings=len(exported.json()["findings"]),
                    retrieval_mode=response.json()["mode"],
                    runtime=sys.version.split()[0],
                    validation=(
                        "Ordinary-prose synthetic live HTTP workflow; "
                        "no real HLD or model benchmark"
                    ),
                    fixture="data/evaluation/torque-prose.md",
                )
                if args.with_model:
                    report.update(
                        validation="Synthetic live API/retrieval/model integration; "
                        "not an independent semantic benchmark",
                        question=args.question,
                        response=response.json(),
                        model=env.get("HLD_NAVIGATOR_CHAT_MODEL")
                        or env.get("HLD_NAVIGATOR_OLLAMA_MODEL"),
                    )
            finally:
                if os.name == "nt":
                    # The Windows venv launcher may spawn a child Python interpreter.
                    subprocess.run(
                        ["taskkill", "/PID", str(server.pid), "/T", "/F"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=False,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                else:
                    server.terminate()
                try:
                    server.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=5)
    name = "live-model-http.json" if args.with_model else "live-http.json"
    (root / "docs/evidence" / name).write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
