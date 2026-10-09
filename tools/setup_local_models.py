"""Download pinned public CPU model artifacts; never execute unverified bytes."""

import argparse
import hashlib
import json
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request, urlopen

ARTIFACTS = [
    {
        "file": "runtime.zip",
        "size": 19482170,
        "url": "https://github.com/ggml-org/llama.cpp/releases/download/b11490/llama-b11490-bin-win-cpu-x64.zip",
        "sha256": "ed69a9e87713b84c63940b2f0e708c8e698e82b3d74dfa1364e94d97e334720c",
    },
    {
        "file": "qwen.gguf",
        "size": 491400032,
        "url": "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/9217f5db79a29953eb74d5343926648285ec7e67/qwen2.5-0.5b-instruct-q4_k_m.gguf?download=true",
        "sha256": "74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db",
    },
    {
        "file": "bge.gguf",
        "size": 67308128,
        "url": "https://huggingface.co/ggml-org/models/resolve/499bc8821c6b12b4e53c5bffcb21ec206f212d81/bert-bge-small/ggml-model-f16.gguf?download=true",
        "sha256": "f0b2fef971e8366438bfd2d9aefea1b0115919389448806d290237f638bae999",
    },
]


def digest(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def fetch(root, item):
    target = root / item["file"]
    if target.exists() and digest(target) == item["sha256"]:
        print(item["file"], "already verified", flush=True)
        return
    partial = target.with_suffix(target.suffix + ".part")
    if item["file"] == "runtime.zip":
        with urlopen(item["url"], timeout=60) as response, partial.open("wb") as file:
            while block := response.read(1024 * 1024):
                file.write(block)
    else:
        with partial.open("wb") as file:
            file.truncate(item["size"])
        ranges = [
            (start, min(start + 8 * 1024**2 - 1, item["size"] - 1))
            for start in range(0, item["size"], 8 * 1024**2)
        ]

        def chunk(bounds):
            start, end = bounds
            for attempt in range(3):
                try:
                    request = Request(item["url"], headers={"Range": f"bytes={start}-{end}"})
                    with urlopen(request, timeout=60) as response:
                        expected = f"bytes {start}-{end}/{item['size']}"
                        if (
                            response.status != 206
                            or response.headers.get("Content-Range") != expected
                        ):
                            raise ValueError("Range response mismatch")
                        data = response.read()
                    if len(data) != end - start + 1:
                        raise ValueError("Truncated model range")
                    with partial.open("r+b") as file:
                        file.seek(start)
                        file.write(data)
                    return
                except (OSError, ValueError):
                    if attempt == 2:
                        raise
                    time.sleep(1)

        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(chunk, ranges))
    if digest(partial) != item["sha256"]:
        raise ValueError(item["file"] + " hash mismatch; refusing execution")
    partial.replace(target)
    print(item["file"], "verified", flush=True)


def run(root):
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    for item in ARTIFACTS:
        fetch(root, item)
    with zipfile.ZipFile(root / "runtime.zip") as archive:
        for entry in archive.infolist():
            if not (root / entry.filename).resolve().is_relative_to(root):
                raise ValueError("Unsafe archive entry")
        archive.extractall(root)
    (root / "artifacts.json").write_text(json.dumps(ARTIFACTS, indent=2), encoding="utf-8")
    print(
        "Pinned CPU artifacts ready. See docs/LOCAL_SETUP.md or tools/serve_local_model.py",
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-dir", type=Path, default=Path(".data/local-inference"))
    run(parser.parse_args().runtime_dir)
