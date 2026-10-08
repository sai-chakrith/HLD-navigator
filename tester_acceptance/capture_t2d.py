"""Capture T2d authorized oracle correction runs and immutable product identities."""

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
REVIEW = ROOT / "tester_acceptance/evidence/t3b1-fix1-review"
ARCHIVE = ROOT / "tester_acceptance/evidence/t2d-oracle-correction-20261008T153500"
EXPECTED = "86b4a75690c00f850a5713a00754a25b0e6ac59d8c535dfc58d24a89575bf76e"
TARGETS = ["tester_acceptance/t2c_oracles.py", "tests/test_tester_t2c_oracles.py",
           "tests/test_tester_t3c_captions.py", "tests/test_tester_t7a_captions.py",
           "tests/test_tester_t3b1_literal.py"]


def identity():
    candidate = json.loads((HANDOFF / "T3b1-fix1-candidate-identity.json").read_text())
    supplied = dict(line.split("\t") for line in
                    Path(candidate["product_manifest_path"]).read_text().splitlines())
    actual = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
              for path in supplied}
    manifest = "".join(f"{path}\t{digest}\n" for path, digest in sorted(actual.items()))
    value = hashlib.sha256(manifest.encode()).hexdigest()
    assert value == EXPECTED
    return {"snapshot": snapshot(), "product_files": actual,
            "product_manifest_sha256": value,
            "mismatches": {path: digest for path, digest in actual.items()
                           if supplied[path] != digest},
            "target_hashes": {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
                              for path in TARGETS},
            "archive_audit_sha256": hashlib.sha256(
                (ARCHIVE / "application-audit.json").read_bytes()).hexdigest(),
            "proposal_diff_hashes": {
                path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in [REVIEW / "PROPOSED-legacy-oracle.diff",
                             REVIEW / "PROPOSED-supplemental-characterization.diff"]}}


def main():
    output = ROOT / "tester_acceptance/evidence" / datetime.now(UTC).strftime(
        "t2d-capture-%Y%m%dT%H%M%S")
    output.mkdir(parents=True)
    env = os.environ.copy()
    env["UV_CACHE_DIR"] = str(ROOT / "tester_acceptance/evidence/uv-cache")
    env["PYTEST_DEBUG_TEMPROOT"] = str(output)
    provenance_files = ["tests/test_tester_t3a_provenance.py",
                        "tests/test_tester_t7a_captions.py",
                        "tests/test_tester_t7a_cycle1.py",
                        "tests/test_tester_t3c_captions.py",
                        "tests/test_tester_t3b1_literal.py",
                        "tests/test_tester_t3b1_fix1_boundaries.py",
                        "tests/test_tester_t2c_oracles.py"]
    affected_files = ["tests/test_tester_t2c_oracles.py",
                      "tests/test_tester_t3c_captions.py",
                      "tests/test_tester_t7a_captions.py",
                      "tests/test_tester_t3b1_literal.py"]
    commands = [
        ["uv", "run", "ruff", "check", "."],
        ["uv", "run", "pytest"],
        ["uv", "run", "python", "-m", "pytest", *affected_files, "-q"],
        ["uv", "run", "python", "-m", "pytest", *provenance_files, "-q"],
        ["uv", "run", "python", "-m", "pytest"],
    ]
    runs = []
    ledger = {"task": "T2d", "notice": "not independently validated", "runs": runs}
    for index, command in enumerate(commands):
        record = {"command": command, "before": identity(), "exit_code": None}
        runs.append(record)
        (output / "runs.json").write_text(json.dumps(ledger, indent=2), encoding="utf-8")
        with (output / f"run-{index}.stdout.txt").open("wb") as stdout:
            with (output / f"run-{index}.stderr.txt").open("wb") as stderr:
                result = subprocess.run(command, cwd=ROOT, env=env, stdout=stdout, stderr=stderr)
        record.update(exit_code=result.returncode, after=identity())
        for stream in ("stdout", "stderr"):
            record[stream + "_sha256"] = hashlib.sha256(
                (output / f"run-{index}.{stream}.txt").read_bytes()).hexdigest()
        (output / "runs.json").write_text(json.dumps(ledger, indent=2), encoding="utf-8")
        print("COMMAND:", " ".join(command), "EXIT:", result.returncode, flush=True)
        print((output / f"run-{index}.stdout.txt").read_text(errors="replace"), end="")
        print((output / f"run-{index}.stderr.txt").read_text(errors="replace"), end="", flush=True)
    print("EVIDENCE:", output)


if __name__ == "__main__":
    main()
