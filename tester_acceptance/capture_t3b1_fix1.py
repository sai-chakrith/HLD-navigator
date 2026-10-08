"""T3b1 fix1 independent capture, including unchanged old-oracle identities."""

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
OLD_FILES = ["tester_acceptance/t2c_oracles.py", "tests/test_tester_t2c_oracles.py",
             "tests/test_tester_t3c_captions.py", "tests/test_tester_t7a_captions.py"]


def identity():
    candidate = json.loads((HANDOFF / "T3b1-fix1-candidate-identity.json").read_text())
    supplied = dict(line.split("\t") for line in
                    Path(candidate["product_manifest_path"]).read_text().splitlines())
    actual = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
              for p in supplied}
    manifest = "".join(f"{p}\t{h}\n" for p, h in sorted(actual.items()))
    return {"snapshot": snapshot(), "product_files": actual,
            "product_manifest_sha256": hashlib.sha256(manifest.encode()).hexdigest(),
            "expected_manifest": candidate["product_manifest_sha256"],
            "mismatches": {p: h for p, h in actual.items() if supplied[p] != h},
            "old_oracle_hashes": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
                                  for p in OLD_FILES},
            "handoff_hashes": {p: hashlib.sha256((HANDOFF / p).read_bytes()).hexdigest()
                               for p in ["T3b1-developer-spec.md", "T3b1-candidate.diff",
                                         "T3b1-fix1-candidate-identity.json"]}}


def main():
    phase = sys.argv[1] if len(sys.argv) > 1 else "baseline"
    output = ROOT / "tester_acceptance/evidence" / datetime.now(UTC).strftime(
        f"t3b1-fix1-{phase}-%Y%m%dT%H%M%S")
    output.mkdir(parents=True)
    env = os.environ.copy()
    env["UV_CACHE_DIR"] = str(ROOT / "tester_acceptance/evidence/uv-cache")
    env["PYTEST_DEBUG_TEMPROOT"] = str(output)
    commands = [["uv", "run", "ruff", "check", "."], ["uv", "run", "pytest"],
                ["uv", "run", "python", "-m", "pytest"]]
    if phase == "scoped":
        commands.append(["uv", "run", "python", "-m", "pytest",
                         "tests/test_tester_t3b1_literal.py",
                         "tests/test_tester_t3b1_fix1_boundaries.py", "-q"])
        commands.append(["uv", "run", "python", "-m", "pytest",
                         "tests/test_tester_t3b1_fix1_boundaries.py", "-q"])
    runs = []
    ledger = {"task": "T3b1", "phase": phase, "notice": "not independently validated",
              "runs": runs}
    for p in OLD_FILES:
        (output / (Path(p).name + ".before.txt")).write_bytes((ROOT / p).read_bytes())
    for i, command in enumerate(commands):
        record = {"command": command, "before": identity(), "exit_code": None}
        runs.append(record)
        (output / "runs.json").write_text(json.dumps(ledger, indent=2), encoding="utf-8")
        with (output / f"run-{i}.stdout.txt").open("wb") as stdout:
            with (output / f"run-{i}.stderr.txt").open("wb") as stderr:
                result = subprocess.run(command, cwd=ROOT, env=env, stdout=stdout, stderr=stderr)
        record.update(exit_code=result.returncode, after=identity())
        for stream in ("stdout", "stderr"):
            record[stream + "_sha256"] = hashlib.sha256(
                (output / f"run-{i}.{stream}.txt").read_bytes()).hexdigest()
        (output / "runs.json").write_text(json.dumps(ledger, indent=2), encoding="utf-8")
        print("COMMAND:", " ".join(command), "EXIT:", result.returncode, flush=True)
        print((output / f"run-{i}.stdout.txt").read_text(errors="replace"), end="")
        print((output / f"run-{i}.stderr.txt").read_text(errors="replace"), end="", flush=True)
    print("EVIDENCE:", output)


if __name__ == "__main__":
    main()
