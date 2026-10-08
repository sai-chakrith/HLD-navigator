"""Facet assessment of retained synthetic outputs; preserves every strict test failure."""

import io
import json
import sys
from pathlib import Path

import pdfplumber


def main():
    root = Path(sys.argv[1])

    def read(name):
        return json.loads((root / name).read_text(encoding="utf-8"))

    captions = []
    for i in range(9):
        for suffix in ["md", "txt"]:
            record = read(f"benign-{i}.{suffix}.outputs.json")
            source = (root / f"benign-{i}.{suffix}").read_text(encoding="utf-8")
            caption = source.splitlines()[0]
            facts = [e for e in record["entities"] if e["name"] == "Aster"
                     and e["kind"] == "component"]
            captions.append({"fixture": f"benign-{i}.{suffix}", "caption": caption,
                             "caption_warning_count": len(record["warnings"]),
                             "warnings": record["warnings"],
                             "total_entities": len(record["entities"]),
                             "table_fact_correct": len(facts) == 1 and facts[0]["attributes"]
                             == {"description": "Monitors pressure"}})
    unsupported = []
    for i in range(8):
        record = read(f"unsupported-{i}.md.outputs.json")
        statement = (root / f"unsupported-{i}.md").read_text().split("\n|")[0].rstrip()
        line = statement.splitlines()[-1]
        expected_line = len(statement.splitlines())
        unsupported.append({"fixture": f"unsupported-{i}.md", "statement": statement,
                            "blocking_original_warning": any(
                                w["code"] == "unsupported_relationship"
                                and w["severity"] == "blocking" and w["text"] == line
                                and w["location"]["line"] == expected_line
                                for w in record["warnings"])})
    qualified = []
    for i in range(4):
        record = read(f"qualified-{i}.txt.outputs.json")
        statement = (root / f"qualified-{i}.txt").read_text().splitlines()[0]
        qualified.append({"fixture": f"qualified-{i}.txt", "statement": statement,
                          "blocking_original_warning": any(
                              w["code"] == "ambiguous_prose" and w["severity"] == "blocking"
                              and w["text"] == statement and w["location"]["line"] == 1
                              for w in record["warnings"]),
                          "unconditional_relationship_count": sum(
                              e["kind"] in ("dependency", "port", "interface")
                              for e in record["entities"])})
    pdf_checks = []
    for category in ["benign", "unknown", "qualified"]:
        record = read(f"multipage-{category}.pdf.outputs.json")
        content = (root / f"multipage-{category}.pdf").read_bytes()
        facts = [e for e in record["entities"] if e["name"] == "Aster"
                 and e["kind"] == "component"]
        correct_attributes = len(facts) == 1 and facts[0]["attributes"] == {
            "description": "Monitors pressure within limits"}
        rows = []
        with pdfplumber.open(io.BytesIO(content)) as original:
            for page_number, page in enumerate(original.pages, 1):
                original_page_text = page.extract_text()
                original_span = page.crop((60, 112, 560, 162)).extract_text()
                sources = [s for e in facts for s in e["sources"]
                           if s["location"]["page"] == page_number
                           and s["location"]["table"] is not None]
                statement = ("Aster component arbitrates GateBudget." if category == "unknown"
                             else "Aster component may provide the IAct interface to Lumen.")
                code = "unsupported_relationship" if category == "unknown" else "ambiguous_prose"
                mapped = None if category == "benign" else any(
                    w["code"] == code and w["severity"] == "blocking"
                    and w["location"]["page"] == page_number
                    and statement in w["text"] and statement in original_page_text
                    for w in record["warnings"])
                rows.append({"page": page_number, "original_page_text": original_page_text,
                             "warning_contains_original_statement_on_correct_page": mapped,
                             "original_row_span": original_span, "stored_sources": sources,
                             "raw_source_correct": len(sources) == 1
                             and sources[0]["text"] == original_span
                             and sources[0]["location"]["table"] == 1
                             and sources[0]["location"]["row"] == 2})
        pdf_checks.append({"fixture": f"multipage-{category}.pdf",
                           "table_attributes_correct": correct_attributes, "rows": rows,
                           "complete_aster_entities_including_prose_sources": facts,
                           "raw_warnings": record["warnings"]})
    result = {"task": "T7a", "notice": "not independently validated",
              "caption_cases": captions, "unsupported_cases": unsupported,
              "qualified_cases": qualified, "pdf_checks": pdf_checks,
              "warning_caption_cases": sum(bool(c["caption_warning_count"]) for c in captions),
              "caption_opportunities": len(captions),
              "strict_test_failures_are_retained": True,
              "api_benign_caption_export": read("api-0.json")[-1],
              "api_for_release_caption_export": read("api-7.json")[-1]}
    output = root / "facet-assessment.json"
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"output": str(output), "caption_warning_cases": result[
        "warning_caption_cases"], "caption_opportunities": len(captions),
        "unsupported_original_warnings": sum(c["blocking_original_warning"] for c in unsupported),
        "qualified_original_warnings": sum(c["blocking_original_warning"] for c in qualified),
        "all_pdf_table_sources_correct": all(c["table_attributes_correct"] and all(
            r["raw_source_correct"] for r in c["rows"]) for c in pdf_checks)}, indent=2))


if __name__ == "__main__":
    main()
