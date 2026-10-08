"""T7a raw command and handoff/product-byte capture; no acceptance labels."""

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
    supplied = json.loads((HANDOFF / "T7a-candidate-identity.json").read_text())
    actual = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
              for name in supplied["product_files"]}
    manifest = "".join(f"{name}\t{digest}\n" for name, digest in sorted(actual.items()))
    manifest_hash = hashlib.sha256(manifest.encode()).hexdigest()
    return {"snapshot": snapshot(), "product_files": actual,
            "product_manifest_sha256": manifest_hash,
            "product_manifest_bytes": manifest,
            "product_manifest_serialization": "sorted path TAB sha256 LF, trailing LF, UTF-8",
            "expected_manifest_sha256": supplied["product_manifest_sha256"],
            "product_mismatches": {k: v for k, v in actual.items()
                                   if v != supplied["product_files"][k]},
            "handoff_hashes": {name: hashlib.sha256((HANDOFF / name).read_bytes()).hexdigest()
                               for name in ("T7a-developer-spec.md", "T7a-candidate.diff",
                                            "T7a-candidate-identity.json")}}


def main():
    output = ROOT / "tester_acceptance/evidence" / datetime.now(UTC).strftime(
        "t7a-capture-%Y%m%dT%H%M%S")
    output.mkdir(parents=True)
    env = os.environ.copy()
    env["UV_CACHE_DIR"] = str(ROOT / "tester_acceptance/evidence/uv-cache")
    env["PYTEST_DEBUG_TEMPROOT"] = str(output)
    commands = [["uv", "run", "ruff", "check", "."], ["uv", "run", "pytest"],
                ["uv", "run", "python", "-m", "pytest"]]
    records = []
    for i, command in enumerate(commands):
        record = {"command": command, "before": identity(), "exit_code": None}
        records.append(record)
        ledger = {"task": "T7a", "notice": "not independently validated", "runs": records}
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
    artifacts = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                 for path in (ROOT / "tester_acceptance/evidence").glob("t7a-synthetic-*/*")
                 if path.is_file()}
    (output / "synthetic-artifact-hashes.json").write_text(
        json.dumps(artifacts, indent=2), encoding="utf-8")
    print("EVIDENCE:", output)


if __name__ == "__main__":
    main()
