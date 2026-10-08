"""Read-only audit-baseline comparison for the new synthetic nuisance-warning finding."""

import importlib
import json
import subprocess
import sys
import types
from pathlib import Path

REVISION = "3518d1b0eac2d74bae93ac529a0a105e2a912677"
ROOT = Path(__file__).resolve().parents[1]


def main():
    fixture = ROOT / "tester_acceptance/evidence/t3a-synthetic-v2/independent.pdf"
    package = types.ModuleType("tester_audit_baseline")
    package.__path__ = []
    sys.modules[package.__name__] = package
    for name in ("models", "ocr", "prose", "tables", "extraction"):
        source = subprocess.check_output(
            ["git", "show", f"{REVISION}:src/hld_navigator/{name}.py"], cwd=ROOT)
        module = types.ModuleType(f"{package.__name__}.{name}")
        module.__package__ = package.__name__
        sys.modules[module.__name__] = module
        exec(compile(source, f"audit-baseline:{name}", "exec"), module.__dict__)
    baseline = sys.modules[f"{package.__name__}.extraction"].extract
    current = importlib.import_module("hld_navigator.extraction").extract
    baseline_warnings = baseline("fixture.pdf", fixture.read_bytes())[2]
    candidate_warnings = current("fixture.pdf", fixture.read_bytes())[2]
    baseline_relationships = [w for w in baseline_warnings
                              if w["code"] == "unsupported_relationship"]
    candidate_relationships = [w for w in candidate_warnings
                               if w["code"] == "unsupported_relationship"]
    result = {"notice": "not independently validated", "baseline": REVISION,
              "fixture": str(fixture), "baseline_warnings": baseline_warnings,
              "candidate_warnings": candidate_warnings,
              "same_warnings": baseline_warnings == candidate_warnings,
              "same_relationship_warnings": baseline_relationships == candidate_relationships}
    output = ROOT / "tester_acceptance/evidence/baseline-warning-comparison.json"
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
