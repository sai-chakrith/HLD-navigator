"""Audit every retained PDF source against original Tester geometry; never edit test oracles."""

import io
import json
import sys
from pathlib import Path
from typing import Any, Literal

import pdfplumber
from pydantic import BaseModel, ConfigDict


class SourceCheck(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    fixture: str
    entity_kind: str
    entity_name: str
    source: dict[str, Any]
    original_page_text: str
    independently_captured: str
    representation: Literal["table-row", "page-context"]
    content_and_location_verified: bool
    literal_original_text_substring: bool


def main():
    root, output = Path(sys.argv[1]), Path(sys.argv[2])
    cases = []
    for category, statement in [
        ("unknown", "Aster component arbitrates GateBudget."),
        ("qualified", "Aster component may provide the IAct interface to Lumen."),
    ]:
        fixture = f"multipage-{category}.pdf"
        record = json.loads((root / (fixture + ".outputs.json")).read_text(encoding="utf-8"))
        checks = []
        warning_checks = []
        with pdfplumber.open(io.BytesIO((root / fixture).read_bytes())) as original:
            for entity in record["entities"]:
                for source in entity["sources"]:
                    location = source["location"]
                    page_number = location["page"]
                    page = original.pages[page_number-1]
                    text = page.extract_text()
                    if location["table"] is not None:
                        captured = page.crop((60, 112, 560, 162)).extract_text()
                        valid = source["text"] == captured and (
                            location["table"], location["row"]) == (1, 2)
                        representation = "table-row"
                    else:
                        captured = " ".join(text.splitlines())
                        valid = source["text"] == captured and statement in text
                        representation = "page-context"
                    checks.append(SourceCheck(
                        fixture=fixture, entity_kind=entity["kind"], entity_name=entity["name"],
                        source=source, original_page_text=text, independently_captured=captured,
                        representation=representation, content_and_location_verified=valid,
                        literal_original_text_substring=source["text"] in text).model_dump())
            for warning in record["warnings"]:
                page_number = warning["location"]["page"]
                page_text = original.pages[page_number-1].extract_text()
                expected_code = ("ambiguous_prose" if category == "qualified"
                                 else "unsupported_relationship")
                warning_checks.append({"warning": warning, "original_page_text": page_text,
                    "isolated_sentence_equality": warning["text"] == statement,
                    "original_statement_start": page_text.find(statement),
                    "original_statement_end": page_text.find(statement)+len(statement),
                    "original_statement_on_recorded_page": statement in page_text,
                    "warning_retains_original_statement": statement in warning["text"],
                    "correct_blocking_category": warning["code"] == expected_code
                    and warning["severity"] == "blocking"})
        all_locations = [[s["source"]["location"][k] for k in ("page", "table", "row")]
                         for s in checks]
        table_locations = [x for x in all_locations if x[1] is not None]
        sort_error = None
        try:
            sorted(tuple(x) for x in all_locations)
        except TypeError as error:
            sort_error = str(error)
        cases.append({"fixture": fixture, "entities": record["entities"], "sources": checks,
                      "all_source_locations": all_locations, "table_locations": table_locations,
                      "original_sort_error": sort_error, "warning_checks": warning_checks,
                      "all_contributing_source_content_verified": all(
                          c["content_and_location_verified"] for c in checks),
                      "exact_literal_table_spans_verified": all(
                          c["literal_original_text_substring"]
                          and c["content_and_location_verified"]
                          for c in checks if c["representation"] == "table-row")})
    result = {"task": "T3c", "notice": "not independently validated", "cases": cases,
              "interpretation": "Mixed contributing sources are required; page context is allowed. "
              "Line-joined page context is distinguished from exact original table-row quotes."}
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "cases": [{
        "fixture": c["fixture"], "sources": len(c["sources"]),
        "all_locations": c["all_source_locations"], "table_locations": c["table_locations"],
        "sort_error": c["original_sort_error"],
        "all_source_content_verified": c["all_contributing_source_content_verified"],
        "all_table_spans_exact": c["exact_literal_table_spans_verified"],
        "isolated_warning_equal": [w["isolated_sentence_equality"] for w in c["warning_checks"]]
    } for c in cases]}, indent=2))


if __name__ == "__main__":
    main()
