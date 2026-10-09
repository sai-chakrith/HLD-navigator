"""Explicit developer-only download of pinned official Qwen 7B weights."""

import argparse
import hashlib
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.client import IncompleteRead
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

REVISION = "bb5d59e06d9551d752d08b292a50eb208b07ab1f"
ROOT_URL = f"https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/{REVISION}"
ARTIFACTS = [
    {
        "file": "qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf",
        "size": 3993201344,
        "sha256": "dfce12e3862a5283ccfb88221b48480e58745165de856439950d0f22590580db",
    },
    {
        "file": "qwen2.5-7b-instruct-q4_k_m-00002-of-00002.gguf",
        "size": 689872288,
        "sha256": "539cf93f78e887edea1c04e2d7d8cdaca9d01dae9c9025bcb8accbe29df3d72a",
    },
]
for artifact in ARTIFACTS:
    artifact["url"] = f"{ROOT_URL}/{artifact['file']}?download=true"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def fetch(root, artifact, workers=16, *, allow_unpinned_checksum=False):
    if not artifact.get("sha256") and not allow_unpinned_checksum:
        raise ValueError("A pinned publisher checksum is required for model weights")
    target = root / artifact["file"]
    if (
        target.exists()
        and target.stat().st_size == artifact["size"]
        and (
            digest(target) == artifact["sha256"]
            or allow_unpinned_checksum
            and not artifact["sha256"]
        )
    ):
        print(target.name, "already verified", flush=True)
        return
    partial = target.with_suffix(target.suffix + ".part")
    size = artifact["size"]
    step = 1024**2
    if not partial.exists() or partial.stat().st_size != size:
        with partial.open("wb") as stream:
            stream.truncate(size)
    # Retain existing complete-looking ranges as provisional only. No bytes are
    # accepted for inference until the entire artifact matches official SHA256.
    ranges = []
    with partial.open("rb") as stream:
        for start in range(0, size, step):
            end = min(start + step - 1, size - 1)
            stream.seek(start)
            first = stream.read(32)
            stream.seek(end - 31)
            last = stream.read(32)
            if not (any(first) and any(last)):
                ranges.append((start, end))
    print(target.name, "remaining ranges", len(ranges), flush=True)

    def transfer(bounds):
        start, end = bounds
        # Give each range a distinct URL: intermediary caches may ignore Range.
        req = Request(
            artifact["url"] + f"&range={start}-{end}", headers={"Range": f"bytes={start}-{end}"}
        )
        for attempt in range(5):
            try:
                with urlopen(req, timeout=30) as response:
                    if response.status != 206 or response.headers.get("Content-Range") != (
                        f"bytes {start}-{end}/{size}"
                    ):
                        raise ValueError("Range response mismatch")
                    started = time.monotonic()
                    chunks = []
                    received = 0
                    while received < end - start + 1:
                        if time.monotonic() - started > 180:
                            raise TimeoutError("Range download exceeded its wall-clock budget")
                        chunk = response.read1(min(65536, end - start + 1 - received))
                        if not chunk:
                            raise IncompleteRead(b"".join(chunks), end - start + 1 - received)
                        chunks.append(chunk)
                        received += len(chunk)
                    data = b"".join(chunks)
                break
            except (OSError, URLError, IncompleteRead):
                if attempt == 4:
                    raise
                time.sleep(attempt + 1)
        if len(data) != end - start + 1:
            raise ValueError("Truncated model range")
        with partial.open("r+b") as stream:
            stream.seek(start)
            stream.write(data)

    pool = ThreadPoolExecutor(max_workers=workers)
    try:
        pending = [pool.submit(transfer, bounds) for bounds in ranges]
        errors = []
        for completed, future in enumerate(as_completed(pending), 1):
            try:
                future.result()
            except Exception as error:
                errors.append(str(error))
                print("Range failed after bounded retries:", error, flush=True)
            if completed % 32 == 0 or completed == len(ranges):
                print(target.name, completed, "of", len(ranges), "ranges", flush=True)
        if errors:
            raise RuntimeError(f"{len(errors)} ranges remain incomplete; rerun to resume")
    finally:
        # On failure stop queued work instead of silently waiting through every range.
        pool.shutdown(wait=True, cancel_futures=True)
    if artifact["sha256"] and digest(partial) != artifact["sha256"]:
        raise ValueError("Artifact SHA256 mismatch; refusing to accept partial bytes")
    partial.replace(target)
    print(
        target.name,
        "SHA256 verified" if artifact["sha256"] else "size checked; no publisher checksum supplied",
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-dir", type=Path, default=Path(".data/local-inference"))
    parser.add_argument("--workers", type=int, choices=range(1, 33), default=16)
    args = parser.parse_args()
    args.runtime_dir.mkdir(parents=True, exist_ok=True)
    for artifact in ARTIFACTS:
        fetch(args.runtime_dir, artifact, args.workers)
