"""Start a verified local CPU model service; no weights are downloaded implicitly."""

import argparse
import hashlib
import json
import os
import subprocess
import zipfile
from pathlib import Path

from setup_s1b_model import ARTIFACTS


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_runtime(root):
    manifest = json.loads((root / "artifacts.json").read_text())
    runtime = next(artifact for artifact in manifest if artifact["file"] == "runtime.zip")
    archive = root / "runtime.zip"
    if digest(archive) != runtime["sha256"]:
        raise ValueError("Runtime archive hash mismatch")
    with zipfile.ZipFile(archive) as bundle:
        for entry in bundle.infolist():
            if entry.is_dir():
                continue
            relative = Path(entry.filename)
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("Invalid runtime archive path")
            deployed = root / relative
            if digest(deployed) != hashlib.sha256(bundle.read(entry)).hexdigest():
                raise ValueError(f"Runtime file hash mismatch: {relative}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=["answer", "embedding"])
    parser.add_argument("--runtime-dir", type=Path, default=Path(".data/local-inference"))
    parser.add_argument("--port", type=int)
    parser.add_argument("--threads", type=int, choices=range(1, 33), default=4)
    args = parser.parse_args()
    root = args.runtime_dir.resolve()
    try:
        verify_runtime(root)
        manifest = json.loads((root / "artifacts.json").read_text())
        artifacts = (
            ARTIFACTS
            if args.kind == "answer"
            else [next(artifact for artifact in manifest if artifact["file"] == "bge.gguf")]
        )
        for artifact in artifacts:
            if digest(root / artifact["file"]) != artifact["sha256"]:
                raise ValueError("Model hash mismatch: " + artifact["file"])
    except (OSError, ValueError, KeyError, StopIteration) as error:
        parser.exit(1, f"Verification failed: {error}\n")
    port = args.port or (18883 if args.kind == "answer" else 18882)
    if not 1 <= port <= 65535:
        parser.error("Port must be between 1 and 65535")
    alias = "qwen7b" if args.kind == "answer" else "bge"
    command = [
        str(root / "llama-server.exe"),
        "-m",
        str(root / artifacts[0]["file"]),
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "-t",
        str(args.threads),
        "-np",
        "1",
        "-ngl",
        "0",
        "--alias",
        alias,
    ]
    if args.kind == "embedding":
        command += ["--embedding", "--pooling", "mean", "-c", "512", "-b", "512", "-ub", "512"]
        settings = {
            "HLD_NAVIGATOR_EMBED_BACKEND": "llama_cpp",
            "HLD_NAVIGATOR_EMBED_URL": f"http://127.0.0.1:{port}",
            "HLD_NAVIGATOR_EMBED_MODEL": alias,
            "HLD_NAVIGATOR_EMBED_ARTIFACT": str(root / artifacts[0]["file"]),
            "HLD_NAVIGATOR_EMBED_DIGEST": artifacts[0]["sha256"],
        }
    else:
        command += ["-c", "2048", "-b", "128", "-ub", "128"]
        settings = {
            "HLD_NAVIGATOR_CHAT_BACKEND": "llama_cpp",
            "HLD_NAVIGATOR_LOCAL_URL": f"http://127.0.0.1:{port}",
            "HLD_NAVIGATOR_CHAT_MODEL": alias,
        }
    print("Verified artifacts. Set these variables in the API terminal before starting it:")
    print(json.dumps(settings, indent=2), flush=True)
    process = subprocess.Popen(
        command, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    )
    try:
        code = process.wait()
        if code:
            raise SystemExit(code)
    except KeyboardInterrupt:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


if __name__ == "__main__":
    main()
