"""Cycle1 command evidence and authoritative before/after product hashes."""

import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tester_acceptance.capture import snapshot  # noqa: E402

HANDOFF = Path(
    "C:/Users/peddi/.codex/visualizations/2026/10/08/01a11aaa-24d7-7770-94da-9d4ff8b8876d")


def identity():
    supplied = json.loads((HANDOFF / "T7a-cycle1-candidate-identity.json").read_text())
    actual = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
              for name in supplied["product_files"]}
    manifest = "".join(f"{name}\t{digest}\n" for name, digest in sorted(actual.items()))
    return {"snapshot": snapshot(), "product_files": actual, "product_manifest_bytes": manifest,
            "product_manifest_sha256": hashlib.sha256(manifest.encode()).hexdigest(),
            "expected_product_manifest_sha256": supplied["product_manifest_sha256"],
            "mismatches": {k: v for k, v in actual.items() if v != supplied["product_files"][k]},
            "handoff_hashes": {name: hashlib.sha256((HANDOFF / name).read_bytes()).hexdigest()
                               for name in ["T7a-developer-spec.md", "T7a-cycle1-candidate.diff",
                                            "T7a-cycle1-candidate-identity.json"]}}


def main():
    output = ROOT / "tester_acceptance/evidence" / datetime.now(UTC).strftime(
        "t7a-cycle1-capture-%Y%m%dT%H%M%S")
    output.mkdir(parents=True)
    env = os.environ.copy()
    env["UV_CACHE_DIR"] = str(ROOT / "tester_acceptance/evidence/uv-cache")
    env["PYTEST_DEBUG_TEMPROOT"] = str(output)
    commands = [["uv", "run", "ruff", "check", "."], ["uv", "run", "pytest"],
                ["uv", "run", "python", "-m", "pytest"],
                ["uv", "run", "python", "-m", "pytest", "tests/test_tester_t7a_cycle1.py", "-q"]]
    runs = []
    ledger = {"task": "T7a", "fix_cycle": 1, "notice": "not independently validated", "runs": runs}
    for i, command in enumerate(commands):
        record = {"command": command, "before": identity(), "exit_code": None}
        runs.append(record)
        (output / "runs.json").write_text(json.dumps(ledger, indent=2), encoding="utf-8")
        with (output / f"run-{i}.stdout.txt").open("wb") as stdout:
            with (output / f"run-{i}.stderr.txt").open("wb") as stderr:
                result = subprocess.run(command, cwd=ROOT, env=env, stdout=stdout, stderr=stderr)
        record.update(exit_code=result.returncode, after=identity())
        for stream in ["stdout", "stderr"]:
            record[f"{stream}_sha256"] = hashlib.sha256(
                (output / f"run-{i}.{stream}.txt").read_bytes()).hexdigest()
        (output / "runs.json").write_text(json.dumps(ledger, indent=2), encoding="utf-8")
        print("COMMAND:", " ".join(command), "EXIT:", result.returncode, flush=True)
        print((output / f"run-{i}.stdout.txt").read_text(errors="replace"), end="")
        print((output / f"run-{i}.stderr.txt").read_text(errors="replace"), end="", flush=True)
    paths = [p for directory in (ROOT / "tester_acceptance/evidence").glob(
        "t7a-cycle1-synthetic-*") for p in directory.glob("*") if p.is_file()]
    paths += [p for p in output.glob("*") if p.is_file()]
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    (output / "artifact-hashes.json").write_text(json.dumps(hashes, indent=2), encoding="utf-8")
    print("EVIDENCE:", output)


if __name__ == "__main__":
    main()
