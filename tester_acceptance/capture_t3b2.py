"""Independent T3b2 candidate identity and raw command capture."""

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

EXPECTED = "8aa59125ab3a99cae2ff06ab48cfb63fb0c12f339b431a736e4a46bf9d4ba2f0"
PRODUCT_FILES = [str(path.relative_to(ROOT)).replace("\\", "/")
                 for path in sorted((ROOT / "src/hld_navigator").glob("*.py"))]


def identity():
    hashes = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
              for name in PRODUCT_FILES}
    manifest = "".join(f"{name}\t{digest}\n" for name, digest in sorted(hashes.items()))
    value = hashlib.sha256(manifest.encode()).hexdigest()
    return {"snapshot": snapshot(), "base_commit": subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True,
        check=True).stdout.strip(), "product_files": hashes,
        "product_manifest_bytes": manifest, "product_manifest_sha256": value,
        "expected_product_manifest_sha256": EXPECTED,
        "manifest_matches": value == EXPECTED}


def main():
    phase = sys.argv[1] if len(sys.argv) > 1 else "baseline"
    output = ROOT / "tester_acceptance/evidence" / datetime.now(UTC).strftime(
        f"t3b2-{phase}-%Y%m%dT%H%M%S")
    output.mkdir(parents=True)
    env = os.environ.copy()
    env["UV_CACHE_DIR"] = str(ROOT / "tester_acceptance/evidence/uv-cache")
    env["PYTEST_DEBUG_TEMPROOT"] = str(output)
    commands = [["uv", "run", "ruff", "check", "."], ["uv", "run", "pytest"]]
    if phase == "baseline":
        commands.append(["uv", "run", "python", "-m", "pytest"])
    else:
        commands.extend([
            ["uv", "run", "python", "-m", "pytest",
             "tests/test_tester_t3b2_integrity.py", "-q"],
            ["uv", "run", "python", "-m", "pytest",
             "tests/test_developer_provenance_integrity.py",
             "tests/test_tester_t3a_provenance.py", "tests/test_tester_t2c_oracles.py",
             "tests/test_tester_t3b1_literal.py", "tests/test_tester_t3b1_fix1_boundaries.py",
             "tests/test_tester_t3c_captions.py", "tests/test_tester_t7a_captions.py",
             "tests/test_tester_t7a_cycle1.py", "-q"],
            ["uv", "run", "python", "-m", "pytest"],
        ])
    ledger = {"task": "T3b2", "phase": phase, "notice": "not independently validated",
              "runs": []}
    for index, command in enumerate(commands):
        before = identity()
        assert before["manifest_matches"]
        record = {"command": command, "before": before, "exit_code": None}
        ledger["runs"].append(record)
        (output / "runs.json").write_text(json.dumps(ledger, indent=2), encoding="utf-8")
        with (output / f"run-{index}.stdout.txt").open("wb") as stdout:
            with (output / f"run-{index}.stderr.txt").open("wb") as stderr:
                result = subprocess.run(command, cwd=ROOT, env=env, stdout=stdout, stderr=stderr)
        after = identity()
        assert after["manifest_matches"]
        record.update(exit_code=result.returncode, after=after)
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
