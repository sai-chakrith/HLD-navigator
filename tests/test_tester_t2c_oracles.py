"""Synthetic negative controls for the exact T2c oracles used by the repaired test."""

import io
import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import pdfplumber
import pytest
from pydantic import ValidationError
from test_tester_t7a_captions import QUALIFIED, UNSUPPORTED, pdf_source

from hld_navigator.extraction import extract
from tester_acceptance.t2c_oracles import verify_contributors, verify_warnings

EVIDENCE = (Path(__file__).resolve().parents[1] / "tester_acceptance/evidence"
            / datetime.now(UTC).strftime("t2c-synthetic-%Y%m%dT%H%M%S%f"))


def preserve(name, value):
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    if isinstance(value, bytes):
        (EVIDENCE / name).write_bytes(value)
    else:
        (EVIDENCE / name).write_text(json.dumps(value, indent=2), encoding="utf-8")


@pytest.fixture(scope="module", params=["unknown", "qualified"])
def original(request):
    category = request.param
    statement = UNSUPPORTED[0] if category == "unknown" else QUALIFIED[2]
    content = pdf_source(statement)
    preserve(category + ".pdf", content)
    blocks, entities, warnings = extract(category + ".pdf", content)
    assert len(entities) == 1
    assert entities[0].kind == "component" and entities[0].name == "Aster"
    assert entities[0].attributes == {"description": "Monitors pressure within limits"}
    originals, rows = {}, {}
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in (1, 2):
            originals[page] = pdf.pages[page - 1].extract_text()
            rows[page] = pdf.pages[page - 1].crop((60, 112, 560, 162)).extract_text()
            assert rows[page] == "Aster Monitors pressure\nwithin limits"
    result = {"category": category, "statement": statement, "originals": originals,
              "row_spans": rows, "sources": entities[0].sources, "warnings": warnings,
              "code": "unsupported_relationship" if category == "unknown" else "ambiguous_prose"}
    preserve(category + ".original-audit.json", {
        "notice": "not independently validated", **result,
        "blocks": [b.model_dump() for b in blocks],
        "entities": [e.model_dump() for e in entities]})
    return result


def check_sources(original, sources):
    return verify_contributors(
        sources, require_context=original["category"] == "unknown",
        originals=original["originals"], row_spans=original["row_spans"],
        statement=original["statement"])


def check_warnings(original, warnings):
    return verify_warnings(warnings, statement=original["statement"],
                           code=original["code"], originals=original["originals"])


def test_complete_positive_control_and_literal_gap(original):
    characterized = check_sources(original, original["sources"])
    checked = check_warnings(original, original["warnings"])
    literal_gate = all(c.literal_original_substring for c in characterized)
    assert literal_gate is True
    if original["category"] == "unknown":
        assert all(c.gap_task is None for c in characterized)
        joined_sources = deepcopy(original["sources"])
        for source in joined_sources:
            if source["location"]["table"] is None:
                source["text"] = " ".join(source["text"].splitlines())
                assert source["text"] not in original["originals"][source["location"]["page"]]
        with pytest.raises(AssertionError):
            check_sources(original, joined_sources)
    preserve(original["category"] + ".positive-control.json", {
        "notice": "not independently validated",
        "contributors": [c.model_dump() for c in characterized],
        "warnings": checked, "literal_mechanical_gate_met": literal_gate,
        "frozen_acceptance_established": False,
        "gap_task": "T3b" if not literal_gate else None})


@pytest.mark.parametrize("mutation", ["wrong-table-page", "altered-table-quote",
                                     "duplicate-table", "unrelated-contributor"])
def test_rejects_bad_table_or_extra_sources(original, mutation):
    sources = deepcopy(original["sources"])
    table = next(s for s in sources if s["location"]["table"] == 1)
    if mutation == "wrong-table-page":
        table["location"]["page"] = 2
    elif mutation == "altered-table-quote":
        table["text"] = table["text"].replace("pressure", "temperature")
    elif mutation == "duplicate-table":
        sources.append(deepcopy(table))
    else:
        sources.append({"text": "Unrelated statement", "location": {
            **table["location"], "table": None, "row": None}})
    with pytest.raises((AssertionError, ValidationError)) as rejected:
        check_sources(original, sources)
    preserve(original["category"] + ".source-negative-" + mutation + ".json", {
        "notice": "not independently validated", "mutation": mutation, "sources": sources,
        "rejected": True, "reason": str(rejected.value)})


@pytest.mark.parametrize("mutation", ["missing-prose", "wrong-prose-page", "altered-prose"])
def test_rejects_prose_mutations(original, mutation):
    sources = deepcopy(original["sources"])
    if original["category"] == "unknown":
        prose = next(s for s in sources if s["location"]["table"] is None)
        if mutation == "missing-prose":
            sources.remove(prose)
        elif mutation == "wrong-prose-page":
            prose["location"]["page"] = 2
        else:
            prose["text"] = prose["text"].replace("arbitrates", "provides")
    else:
        # Qualified prose must contribute no unconditional entity source.
        sources.append({"text": original["statement"], "location": {
            **sources[0]["location"], "table": None, "row": None}})
    with pytest.raises((AssertionError, ValidationError)) as rejected:
        check_sources(original, sources)
    preserve(original["category"] + ".source-negative-" + mutation + ".json", {
        "notice": "not independently validated", "sources": sources,
        "rejected": True, "reason": str(rejected.value)})


@pytest.mark.parametrize("mutation", ["wrong-page", "wrong-page-context", "missing-statement",
                                     "altered-statement", "wrong-category", "nonblocking",
                                     "missing-warning"])
def test_rejects_warning_mutations(original, mutation):
    warnings = deepcopy(original["warnings"])
    warning = warnings[0]
    if mutation == "wrong-page":
        warning["location"]["page"] = 2
    elif mutation == "wrong-page-context":
        warning["text"] = warnings[1]["text"]
    elif mutation == "missing-statement":
        warning["text"] = warning["text"].replace(original["statement"], "")
    elif mutation == "altered-statement":
        warning["text"] = warning["text"].replace("may", "will").replace("arbitrates", "controls")
    elif mutation == "wrong-category":
        warning["code"] = ("ambiguous_prose" if original["category"] == "unknown"
                           else "unsupported_relationship")
    elif mutation == "nonblocking":
        warning["severity"] = "informational"
    else:
        warnings.pop()
    with pytest.raises((AssertionError, ValidationError)) as rejected:
        check_warnings(original, warnings)
    preserve(original["category"] + ".warning-negative-" + mutation + ".json", {
        "notice": "not independently validated", "warnings": warnings,
        "rejected": True, "reason": str(rejected.value)})


def test_missing_qualifier_rejected(original):
    warnings = deepcopy(original["warnings"])
    if original["category"] == "qualified":
        warnings[0]["text"] = warnings[0]["text"].replace("may ", "")
    else:
        warnings[0]["text"] = warnings[0]["text"].replace("arbitrates ", "")
    with pytest.raises((AssertionError, ValidationError)) as rejected:
        check_warnings(original, warnings)
    preserve(original["category"] + ".missing-qualifier-or-action.json", {
        "notice": "not independently validated", "warnings": warnings,
        "rejected": True, "reason": str(rejected.value)})
