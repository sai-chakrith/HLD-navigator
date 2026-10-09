"""New independently authored T3b1 PDFs; existing characterization oracles untouched."""

import hashlib
import importlib
import io
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import pdfplumber
import pytest
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas

from hld_navigator.extraction import extract
from hld_navigator.store import Store

EVIDENCE = (
    Path(__file__).resolve().parents[1]
    / "tester_acceptance/evidence"
    / datetime.now(UTC).strftime("t3b1-synthetic-%Y%m%dT%H%M%S%f")
)
PROSE = {
    "valid": [
        "Nacre   is a component.",
        "Solace is a component.",
        "FrameBus is an interface.",
        "FrameBus interface carries Demand signal.",
        "Demand  signal uses data type uint32 with unit Pa.",
        "Nacre component provides the FrameBus interface",
        "to Solace and sends the AuditBus interface to Solace.",
        "Nacre component requires the FrameBus interface",
        "through port Inlet.",
        "Track flow runs from Nacre component to Solace.",
    ],
    "unknown": [
        "Nacre component provides the FrameBus interface to Solace",
        "and arbitrates RetryWindow.",
    ],
    "negated": ["Nacre component does not provide the FrameBus interface", "to Solace."],
    "conditional": [
        "If alignment is complete, Nacre component provides the FrameBus",
        "interface to Solace.",
    ],
    "uncertain": ["Nacre component may provide the FrameBus interface", "to Solace."],
    "caption": [],
}
EXPECTED = {
    ("component", "Nacre"): {"description": "Controls demand within limits"},
    ("component", "Solace"): {"description": "Receives demand"},
    ("interface", "FrameBus"): {"payload": "Demand"},
    ("interface", "AuditBus"): {},
    ("signal", "Demand"): {"type": "uint32", "unit": "Pa"},
    ("dependency", "Nacre->Solace:FrameBus"): {
        "source": "Nacre",
        "target": "Solace",
        "interface": "FrameBus",
    },
    ("dependency", "Nacre->Solace:AuditBus"): {
        "source": "Nacre",
        "target": "Solace",
        "interface": "AuditBus",
    },
    ("port", "Inlet"): {"owner": "Nacre", "direction": "requires", "interface": "FrameBus"},
    ("flow", "Track"): {"source": "Nacre", "target": "Solace"},
}
PROSE_COUNTS = {
    "Nacre": 7,
    "Solace": 3,
    "FrameBus": 7,
    "AuditBus": 2,
    "Demand": 4,
    "Nacre->Solace:FrameBus": 1,
    "Nacre->Solace:AuditBus": 1,
    "Inlet": 1,
    "Track": 1,
}


def preserve(name, data):
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    if isinstance(data, bytes):
        (EVIDENCE / name).write_bytes(data)
    else:
        (EVIDENCE / name).write_text(json.dumps(data, indent=2), encoding="utf-8")


def pdf_source(category, repeated=False):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(612, 792), invariant=1)
    for number in (1, 2):
        pdf.setFont("Courier", 8)
        caption = "Calibration component catalogue (revision 23)"
        if not repeated:
            caption += f" - sheet {number}"
        pdf.drawString(46, 754, caption)
        for y in (714, 684, 638, 592):
            pdf.line(46, y, 566, y)
        for x in (46, 218, 566):
            pdf.line(x, 592, x, 714)
        pdf.drawString(54, 697, "SWC Name")
        pdf.drawString(226, 697, "Responsibility")
        pdf.drawString(54, 665, "Nacre")
        pdf.drawString(226, 665, "Controls demand")
        pdf.drawString(226, 651, "within limits")
        pdf.drawString(54, 618, "Solace")
        pdf.drawString(226, 618, "Receives demand")
        for i, line in enumerate(PROSE[category]):
            pdf.drawString(46, 552 - 17 * i, line)
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def parsed(category, repeated=False):
    name = category + ("-repeated" if repeated else "-distinct")
    content = pdf_source(category, repeated)
    preserve(name + ".pdf", content)
    pages, rows = {}, {}
    with pdfplumber.open(io.BytesIO(content)) as original:
        for number, page in enumerate(original.pages, 1):
            pages[number] = page.extract_text()
            rows[(number, 1, 2)] = page.crop((46, 108, 566, 154)).extract_text()
            rows[(number, 1, 3)] = page.crop((46, 154, 566, 200)).extract_text()
    blocks, entities, warnings = extract(name + ".pdf", content)
    preserve(
        name + ".original-and-outputs.json",
        {
            "notice": "not independently validated",
            "original_pages": pages,
            "pdf_sha256": hashlib.sha256(content).hexdigest(),
            "pdfplumber_version": pdfplumber.__version__,
            "original_rows": [{"identity": key, "text": text} for key, text in rows.items()],
            "blocks": [b.model_dump() for b in blocks],
            "entities": [e.model_dump() for e in entities],
            "warnings": warnings,
        },
    )
    return name, content, pages, rows, blocks, entities, warnings


def verify_literal(text, location, pages, rows):
    page = location["page"]
    assert page in pages
    assert location["origin"] == "text" and location["confidence"] is None
    assert location["section"] is None and location["line"] is None
    if location["table"] is None:
        assert location["row"] is None
        original = pages[page]
        granularity = "complete original extracted page context"
    else:
        key = (page, location["table"], location["row"])
        assert key in rows
        original = rows[key]
        granularity = "original independently cropped row"
    assert text.encode("utf-8") == original.encode("utf-8")
    assert text in pages[page]
    return {
        "page": page,
        "location": location,
        "text": text,
        "original": original,
        "literal_utf8_equal": True,
        "granularity": granularity,
    }


@pytest.mark.parametrize("category", list(PROSE))
@pytest.mark.parametrize("repeated", [False, True], ids=["distinct-pages", "identical-pages"])
def test_all_original_entities_contributors_and_warnings(category, repeated):
    name, _, pages, rows, blocks, entities, warnings = parsed(category, repeated)
    assert (pages[1] == pages[2]) is repeated
    assert rows[(1, 1, 2)] == rows[(2, 1, 2)] == "Nacre Controls demand\nwithin limits"
    assert rows[(1, 1, 3)] == rows[(2, 1, 3)] == "Solace Receives demand"
    expected = dict(EXPECTED)
    if category != "valid":
        expected = {k: v for k, v in EXPECTED.items() if k[0] == "component"}
        if category == "unknown":
            expected.update(
                {
                    ("interface", "FrameBus"): {},
                    ("dependency", "Nacre->Solace:FrameBus"): EXPECTED[
                        ("dependency", "Nacre->Solace:FrameBus")
                    ],
                }
            )
    assert {(e.kind, e.name): e.attributes for e in entities} == expected
    audits = []
    for entity in entities:
        audits.append(
            {
                "entity": [entity.kind, entity.name],
                "primary": True,
                **verify_literal(entity.evidence, entity.location.model_dump(), pages, rows),
            }
        )
        assert entity.sources
        count = Counter()
        for source in entity.sources:
            audits.append(
                {
                    "entity": [entity.kind, entity.name],
                    "primary": False,
                    **verify_literal(source["text"], source["location"], pages, rows),
                }
            )
            location = source["location"]
            count[(location["page"], location["table"], location["row"])] += 1
            assert any(
                b.text == source["text"] and b.location.model_dump() == location for b in blocks
            )
        per_page = (
            PROSE_COUNTS.get(entity.name, 0)
            if category == "valid"
            else (
                {"Nacre": 2, "Solace": 1, "FrameBus": 2, "Nacre->Solace:FrameBus": 1}.get(
                    entity.name, 0
                )
                if category == "unknown"
                else 0
            )
        )
        expected_counts = Counter()
        for page in (1, 2):
            if per_page:
                expected_counts[(page, None, None)] = per_page
            if entity.kind == "component":
                expected_counts[(page, 1, 2 if entity.name == "Nacre" else 3)] = 1
        assert count == expected_counts, (entity.name, count, expected_counts)
    if category in ("valid", "caption"):
        assert not warnings
    else:
        code = "unsupported_relationship" if category == "unknown" else "ambiguous_prose"
        assert len(warnings) == 2
        assert sorted(w["location"]["page"] for w in warnings) == [1, 2]
        for warning in warnings:
            assert warning["code"] == code and warning["severity"] == "blocking"
            audits.append(
                {
                    "warning": code,
                    **verify_literal(warning["text"], warning["location"], pages, rows),
                }
            )
            assert "\n".join(PROSE[category]) in warning["text"]
            if category == "unknown":
                assert warning["unresolved_actions"] == ["arbitrates"]
    if category == "valid":
        assert "Nacre is a component." in pages[1]
        assert "Demand signal uses data type uint32 with unit Pa." in pages[1]
        assert "interface\nto Solace" in pages[1]
    preserve(
        name + ".literal-audit.json",
        {
            "notice": "not independently validated",
            "checks": audits,
            "source_units": "pages or independently cropped rows",
            "frozen_acceptance_established": False,
        },
    )


@pytest.mark.parametrize("category", ["valid", "unknown", "negated", "conditional", "uncertain"])
@pytest.mark.parametrize("repeated", [False, True])
def test_pdf_api_review_export_retrieval_and_reopen(category, repeated, tmp_path, monkeypatch):
    import hld_navigator.store as store_module

    name, content, pages, rows, _, extracted, warnings = parsed(category, repeated)
    db_path = tmp_path / "t3b1.sqlite"
    monkeypatch.setattr(store_module, "Store", lambda *a, **kw: Store(str(db_path)))
    module = importlib.import_module("hld_navigator.app")
    monkeypatch.setattr(module, "Store", Store)
    app = module.create_app(str(db_path))
    token = Store(str(db_path)).provision("tester", "tester", "reviewer")
    records = []
    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as client:
        uploaded = client.post(
            "/workspaces/tester/documents",
            data={"title": name, "version": "1"},
            files={"file": (name + ".pdf", content, "application/pdf")},
        )
        records.append({"route": "upload", "status": uploaded.status_code, "body": uploaded.json()})
        assert uploaded.status_code == 200
        document = uploaded.json()["id"]
        before = client.get("/workspaces/tester/export", params={"document_id": document})
        assert before.status_code == 409
        decision = client.post(
            f"/workspaces/tester/documents/{document}/review",
            json={"approved": True, "reason": "synthetic source"},
        )
        assert decision.status_code == 200
        found = client.get("/workspaces/tester/entities", params={"document_id": document}).json()
        by_name = {(e.kind, e.name): e for e in extracted}
        for entity in found:
            original = by_name[(entity["kind"], entity["name"])]
            assert entity["evidence"] == original.evidence
            assert entity["location"] == original.location.model_dump()
            assert entity["attributes"] == original.attributes
            # Storage stores source blocks, deduplicating multiple proposals at one source unit.
            expected_units = {
                (s["text"], json.dumps(s["location"], sort_keys=True)) for s in original.sources
            }
            actual_units = {
                (s["text"], json.dumps(s["location"], sort_keys=True)) for s in entity["sources"]
            }
            assert actual_units == expected_units
            for source in entity["sources"]:
                verify_literal(source["text"], source["location"], pages, rows)
            reviewed = client.post(
                f"/workspaces/tester/entities/{entity['id']}/review",
                json={"status": "approved", "reason": "synthetic fact"},
            )
            assert reviewed.status_code == 200
        records.append({"route": "entities", "body": found})
        query = client.post(
            "/workspaces/tester/query",
            json={"text": "Nacre FrameBus Demand", "document_id": document, "scope": "facts"},
        )
        records.append({"route": "query", "status": query.status_code, "body": query.json()})
        assert query.status_code == 200 and query.json()["evidence"]
        for block in query.json()["evidence"]:
            page = block["location"]["page"]
            assert block["source_context"]["text"] in pages[page]
        exported = client.get("/workspaces/tester/export", params={"document_id": document})
        records.append({"route": "export", "status": exported.status_code, "body": exported.json()})
        preserve(name + ".lifecycle.json", records)
        if category == "valid":
            for entity in exported.json().get("entities", []):
                for source in entity["sources"]:
                    verify_literal(source["text"], source["location"], pages, rows)
    reopened = Store(str(db_path))
    persisted = reopened.entities("tester", document, True)
    assert [
        (e["name"], e["attributes"], e["evidence"], e["location"], e["sources"]) for e in persisted
    ] == [(e["name"], e["attributes"], e["evidence"], e["location"], e["sources"]) for e in found]
    stored_document = next(d for d in reopened.documents("tester") if d["id"] == document)
    assert stored_document["warnings"] == warnings
    for warning in stored_document["warnings"]:
        verify_literal(warning["text"], warning["location"], pages, rows)
    with reopened.connection() as db:
        saved = db.execute("SELECT original FROM documents WHERE id=?", (document,)).fetchone()[0]
        links = [
            dict(r)
            for r in db.execute(
                "SELECT e.name,e.location AS entity_location,b.location AS block_location,b.text "
                "FROM entity_evidence ee JOIN entities e ON e.id=ee.entity_id "
                "JOIN blocks b ON b.id=ee.block_id WHERE e.document_id=?",
                (document,),
            )
        ]
    assert saved == content
    preserve(
        name + ".reopened.json",
        {
            "entities": persisted,
            "document": stored_document,
            "links": links,
            "repeated_identical_page_text": repeated,
            "T3b2_boundary": "non-table linkage uses text equality, not location identity; "
            "merged extraction references both pages, but storage alone cannot "
            "prove unique occurrence lineage or distinguish omitted contributors",
        },
    )
    assert exported.status_code == (200 if category == "valid" else 409)


@pytest.mark.parametrize("category", list(PROSE))
@pytest.mark.parametrize("repeated", [False, True])
def test_literal_provenance_independently_of_semantic_warning_failure(category, repeated):
    from hld_navigator.models import Location
    from hld_navigator.prose import parse_prose

    name, _, pages, rows, _, entities, warnings = parsed(category, repeated)
    audit = []
    for entity in entities:
        audit.append(verify_literal(entity.evidence, entity.location.model_dump(), pages, rows))
        for source in entity.sources:
            audit.append(verify_literal(source["text"], source["location"], pages, rows))
    for warning in warnings:
        audit.append(verify_literal(warning["text"], warning["location"], pages, rows))
    legacy_route = {}
    for page, text in pages.items():
        # The pre-T3b1 interpretation route used parse_prose on normalized page text.
        _, old_warnings = parse_prose(" ".join(text.split()), Location(page=page))
        legacy_route[page] = old_warnings
        assert [
            (w["code"], [a for a in w.get("unresolved_actions", []) if a != "Receives"])
            for w in old_warnings
            if w["code"] != "unsupported_relationship"
            or any(a != "Receives" for a in w.get("unresolved_actions", []))
        ] == [
            (w["code"], w.get("unresolved_actions", []))
            for w in warnings
            if w["location"]["page"] == page
        ]
    if category == "valid":
        assert "Nacre is a component." in pages[1]
        assert "Demand signal uses data type uint32 with unit Pa." in pages[1]
    preserve(
        name + ".core-literal-and-prior-route.json",
        {
            "notice": "not independently validated",
            "literal_checks": audit,
            "prior_normalized_interpretation_warnings": legacy_route,
            "candidate_literal_warning_text": warnings,
            "only_detected_table_responsibility_false_warning_removed": True,
            "frozen_acceptance_established": False,
        },
    )


def test_joined_quotes_wrong_page_and_altered_qualifier_rejected():
    name, _, pages, rows, _, _, warnings = parsed("uncertain")
    original = warnings[0]
    variants = {
        "joined": (" ".join(original["text"].split()), original["location"]),
        "lost-qualifier": (original["text"].replace("may ", ""), original["location"]),
        "altered-qualifier": (original["text"].replace("may", "will"), original["location"]),
        "wrong-page": (original["text"], {**original["location"], "page": 2}),
    }
    negatives = []
    for mutation, (text, location) in variants.items():
        with pytest.raises(AssertionError) as rejected:
            verify_literal(text, location, pages, rows)
        negatives.append(
            {
                "mutation": mutation,
                "text": text,
                "location": location,
                "rejected": True,
                "reason": str(rejected.value),
            }
        )
    preserve(
        name + ".literal-negatives.json",
        {"notice": "not independently validated", "negative_controls": negatives},
    )


@pytest.mark.parametrize("suffix", ["md", "txt"])
def test_original_md_txt_spacing_table_and_qualified_controls(suffix):
    original = (
        "# Calibration\nNacre   component provides the FrameBus interface to Solace.\n"
        "Nacre component may provide the AuditBus interface to Solace.\n"
        "| SWC Name | Responsibility |\n|---|---|\n"
        "|  Nacre  | Controls demand |\n"
    )
    blocks, entities, warnings = extract("controls." + suffix, original.encode())
    preserve("controls." + suffix, original.encode())
    preserve(
        "controls." + suffix + ".outputs.json",
        {
            "entities": [e.model_dump() for e in entities],
            "warnings": warnings,
            "blocks": [b.model_dump() for b in blocks],
        },
    )
    assert {(e.kind, e.name) for e in entities} == {
        ("component", "Nacre"),
        ("component", "Solace"),
        ("interface", "FrameBus"),
        ("dependency", "Nacre->Solace:FrameBus"),
    }
    for entity in entities:
        for source in entity.sources:
            assert source["text"] == original.splitlines()[source["location"]["line"] - 1]
    assert len(warnings) == 1
    assert warnings[0]["code"] == "ambiguous_prose" and warnings[0]["severity"] == "blocking"
    assert warnings[0]["text"] == original.splitlines()[2]
