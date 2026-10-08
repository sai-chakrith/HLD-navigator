"""Capture exact commands and shared candidate identity without reading Developer narrative."""

import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "tester_acceptance" / "evidence"


def snapshot():
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=ROOT, stderr=subprocess.DEVNULL)
    diff = git("diff", "--binary", "HEAD")
    files = git("ls-files", "--others", "--exclude-standard").decode().splitlines()
    files += git("diff", "--name-only", "HEAD").decode().splitlines()
    hashes = {}
    for name in files:
        # Evidence and caches are separately hashed; avoid recursive capture identity.
        if name.startswith("tester_acceptance/evidence/"):
            continue
        path = ROOT / name
        if path.is_file():
            hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"head": git("rev-parse", "HEAD").decode().strip(),
            "status": git("status", "--short").decode(),
            "tracked_diff_sha256": hashlib.sha256(diff).hexdigest(),
            "tracked_diff": diff.decode(), "file_hashes": hashes,
            "utc": datetime.now(UTC).isoformat()}


def main():
    EVIDENCE.mkdir(exist_ok=True)
    output = EVIDENCE / datetime.now(UTC).strftime("capture-%Y%m%dT%H%M%S")
    output.mkdir()
    env = os.environ.copy()
    env["UV_CACHE_DIR"] = str(EVIDENCE / "uv-cache")
    env["PYTEST_DEBUG_TEMPROOT"] = str(EVIDENCE)
    commands = [["uv", "run", "ruff", "check", "."], ["uv", "run", "pytest"],
                ["uv", "run", "python", "-m", "pytest"]]
    records = []
    for index, command in enumerate(commands):
        before = snapshot()
        record = {"command": command, "before": before, "exit_code": None,
                  "status": "running"}
        records.append(record)
        ledger = output / "runs.json"
        def save(ledger=ledger):
            ledger.write_text(json.dumps({"task": "T2", "notice": "not independently validated",
                                          "runs": records}, indent=2), encoding="utf-8")
        save()
        stdout_path, stderr_path = (output / f"run-{index}.stdout.txt",
                                    output / f"run-{index}.stderr.txt")
        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            result = subprocess.run(command, cwd=ROOT, env=env, stdout=stdout, stderr=stderr)
        after = snapshot()
        raw_stdout, raw_stderr = stdout_path.read_bytes(), stderr_path.read_bytes()
        record.update({"exit_code": result.returncode, "status": "complete", "after": after,
                        "stdout_sha256": hashlib.sha256(raw_stdout).hexdigest(),
                        "stderr_sha256": hashlib.sha256(raw_stderr).hexdigest(),
                        "environment": {k: env[k] for k in (
                            "UV_CACHE_DIR", "PYTEST_DEBUG_TEMPROOT")}})
        save()
        print("COMMAND:", " ".join(command), "EXIT:", result.returncode, flush=True)
        sys.stdout.buffer.write(raw_stdout)
        sys.stdout.buffer.write(raw_stderr)
        sys.stdout.flush()
    (output / "runs.json").write_text(json.dumps({"task": "T2",
        "notice": "not independently validated", "runs": records}, indent=2), encoding="utf-8")
    print("EVIDENCE:", output)


if __name__ == "__main__":
    main()
