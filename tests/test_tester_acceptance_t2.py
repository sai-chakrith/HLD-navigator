"""Tester-owned synthetic arithmetic examples. No product or protected data imports."""

import hashlib
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

# pytest's configured pythonpath contains src only. Keep this isolated from product modules.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tester_acceptance.harness import (  # noqa: E402
    Answer,
    Artifact,
    Change,
    Detection,
    EffortBlock,
    ExtractionRun,
    Fact,
    Manifest,
    Opportunity,
    Question,
    Report,
    SemanticReview,
    Span,
    Warning,
    answers,
    effort,
    extraction,
    minima,
    ratio,
    revisions,
    semantic_audit,
    warnings,
)


def fact(identifier="a", kind="component", semantic="SUPPORTED"):
    return Fact(occurrence_id=identifier, document="tiny", entity_type=kind,
                attributes={"name": "A"}, semantic=semantic,
                spans=[Span(document="tiny", original="Component A", quote="Component A",
                            start=0, end=11, format="txt", section="Inventory", line=1)])


def test_ratios_confidence_polarity_and_nulls():
    assert ratio(0, 0, .90).point is None
    assert ratio(0, 0, .90).interval is None
    assert ratio(0, 0, .90).tier == "BLOCKED"
    assert ratio(90, 100, .90, independent=True).tier == "PASS"
    assert not ratio(90, 100, .90, independent=True).final_accepted
    assert ratio(99, 100, .90, independent=True).final_accepted
    assert ratio(99, 100, .90, independent=True).tier == "CONFIRMED"
    assert ratio(1, 100, .02, "max", independent=True).tier == "PASS"
    assert ratio(0, 1000, .02, "max", independent=True).tier == "CONFIRMED"
    assert ratio(100, 100, .85, independent=True, pass_only=True).tier == "PASS"
    assert ratio(100, 100, .85, independent=True, pass_only=True).final_accepted
    assert not ratio(27, 30, .85, independent=True, pass_only=True).final_accepted
    assert ratio(9, 10, .90, minimum=30, independent=True).tier == "INDICATIVE"
    assert ratio(100, 100, .90).tier == "BLOCKED"
    assert ratio(80, 100, .90, independent=True).tier == "FAIL"
    with pytest.raises(ValueError):
        ratio(2, 1, .90)


def test_exact_observed_hard_gate():
    metric = ratio(0, 20, 0, "max", 20, independent=True, hard=True)
    assert metric.tier == "PASS"
    assert metric.exact_upper_failure == pytest.approx(.1391083407)
    assert metric.interval[1] > 0
    assert ratio(1, 1, 0, "max", 20, independent=True, hard=True).tier == "FAIL"
    assert ratio(19, 20, 1, independent=True, hard=True).tier == "FAIL"


def test_occurrences_duplicates_unknowns_errors_and_semantics():
    gold = [fact("a"), fact("b")]
    run = ExtractionRun(document="tiny", raw="raw", error="partial parser failure",
                        facts=[fact("a"), fact("a"), fact("unknown", "alien", "PARTIAL")])
    result = extraction(gold, [run])
    assert result["overall"] == {"tp": 1, "fp": 2, "fn": 1}
    assert result["per_type"]["component"] == {"tp": 1, "fp": 1, "fn": 1}
    assert result["semantic"].point == pytest.approx(2/3)
    assert result["mechanical"].point == 1
    assert result["raw_errors"][0]["error"] == "partial parser failure"
    empty = extraction(gold, [])
    assert empty["overall"]["fn"] == 2
    assert empty["missing_documents"] == ["tiny"]
    assert empty["mechanical"].point is None


def test_provenance_raw_location_and_synthesis():
    span = fact().spans[0]
    assert span.mechanical()
    assert not span.model_copy(update={"quote": "COMPONENT A"}).mechanical()
    assert not span.model_copy(update={"line": 2}).mechanical()
    assert not span.model_copy(update={"format": "pdf", "page": None}).mechanical()
    assert span.model_copy(update={"format": "pdf", "page": 4}).mechanical()
    bad = fact().model_copy(update={"spans": []})
    assert extraction([], [ExtractionRun(document="tiny", raw="", error=None,
                                        facts=[bad])])["mechanical"].point == 0


def test_warning_opportunity_dedup_and_text_independence():
    opportunities = [Opportunity(statement_id=str(i), document="tiny", location=f"line {i}",
                                 problem=i < 3, categories=["ambiguity"] if i < 3 else [])
                     for i in range(6)]
    emitted = [Warning(statement_id=i, category="ambiguity", raw="same text")
               for i in ("0", "0", "1", "3")]
    result = warnings(opportunities, emitted)
    assert [result[k] for k in ("tp", "fp", "fn", "tn")] == [2, 1, 1, 2]
    for key in ("fdr", "fnr", "benign_false_alarm"):
        assert result[key].point == pytest.approx(1/3)
    assert result["category_accuracy"].point == 1
    unmatched = warnings(opportunities, [Warning(statement_id="missing", category="x", raw="")])
    assert unmatched["blockers"]
    with pytest.raises(ValueError):
        warnings(opportunities+opportunities[:1], emitted)


def question(identifier, **updates):
    fields = dict(case_id=identifier, document="tiny", answerable=True, unsupported=False,
                  conflict=False, injection=False, expected_behavior="answer A",
                  allowed_source_ids=[])
    fields.update(updates)
    return Question(**fields)


def answer(identifier, **updates):
    fields = dict(case_id=identifier, layer="raw_model", retrieval="approved_fact_production",
                  raw_output="A", error=None, abstained=False, emitted=True, contradiction=False,
                  conflict_detected=False, relevant_grounded_actionable=True,
                  valid_citations=True, injection_success=False)
    fields.update(updates)
    return Answer(**fields)


def test_answer_layers_errors_overlap_and_false_abstention():
    questions = [question("a"), question("b"),
                 question("u", answerable=False, unsupported=True, conflict=True, injection=True)]
    outputs = [answer("a", abstained=True, emitted=False), answer("b"),
               answer("u", raw_output="{broken", error="malformed output", abstained=None),
               answer("b", layer="application", abstained=True)]
    result = answers(questions, outputs, "raw_model", "approved_fact_production")
    assert result["false_abstention"].point == .5
    assert result["unsupported_abstention"].point == 0
    assert result["injection"].point == 1
    assert result["conflict_detection"].denominator == 1
    assert result["memberships"]["u"] == ["unsupported", "conflict", "injection"]
    assert result["raw_errors"][0]["raw_output"] == "{broken"
    app = answers(questions, outputs, "application", "approved_fact_production")
    assert app["missing"] == ["a", "u"]
    diagnostic = answers(questions, outputs, "raw_model", "source_scope_diagnostic")
    assert len(diagnostic["missing"]) == 3
    with pytest.raises(ValidationError):
        Answer.model_validate({"case_id": "a", "raw_output": "bad"})


def change(identifier, impacted, must_flag=None, noop=False):
    return Change(change_id=identifier, pair_id="pair", document="tiny", kind="rename",
                  item_id=identifier, noop=noop, impacted=impacted,
                  must_flag=impacted if must_flag is None else must_flag)


def detection(identifier, impacts):
    return Detection(change_id=identifier, kind="rename", item_id=identifier,
                     impacts=impacts, raw="original report")


def test_revision_misses_spurious_duplicates_noop_and_empty():
    changes = [change("a", ["x", "y"]), change("b", ["z"]),
               change("e", []), change("bad-empty", []), change("n", [], noop=True)]
    reports = [detection("a", ["x", "y"]), detection("a", ["x"]),
               detection("e", []), detection("bad-empty", ["wrong"]), detection("n", [])]
    result = revisions(changes, reports)
    assert result["detected"] == 3
    assert result["missed"] == ["b"]
    assert len(result["unmatched"]) == 2
    assert result["impact_micro_recall"].point == pytest.approx(2/3)
    assert result["impact_micro_precision"].point == .5
    assert result["impact_correct_detected"].point == pytest.approx(2/3)
    assert result["detection_and_impact_coverage"].point == .5
    assert result["noop_false_alarm"].point == 1
    empty = result["per_detected"][1]
    assert empty["correct"] and empty["precision"] is None and empty["recall"] is None
    assert not result["per_detected"][2]["correct"]


def block(identifier, manual, assisted, corrections):
    return EffortBlock(block_id=identifier, document="tiny", paired_task=identifier,
                       order="manual-first", manual_minutes=float(manual),
                       assisted_minutes=float(assisted), extracted_items=100,
                       corrections=corrections, interruptions=[],
                       raw_events=[{"event": "active", "minutes": float(assisted)}])


def test_effort_totals_paired_bootstrap_seed_degeneracy():
    blocks = [block("a", 40, 10, 10), block("b", 60, 20, 20)]
    result = effort(blocks, 123, True)
    assert result["point"] == pytest.approx((15, 15, .70))
    assert result["interval"][2] == pytest.approx((2/3, .75))
    assert effort(blocks, 123, True) == result
    assert result["resamples"] == 10000
    assert effort(blocks, 123, False)["point"] is None
    assert effort(blocks[:1], 123, True)["status"] == "BLOCKED"
    same = effort([block("a", 40, 10, 10), block("b", 40, 10, 10)], 0, True)
    assert same["interval"] == [None, None, None]
    assert not any(same["bootstrap_confidence_supported"])


def test_hashes_and_independence_prerequisites(tmp_path):
    path = tmp_path / "fixture.txt"
    path.write_bytes(b"tiny synthetic fixture")
    artifact = Artifact(role="documents", path="fixture.txt",
                        sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    assert artifact.verify(tmp_path)
    path.write_bytes(b"altered")
    assert not artifact.verify(tmp_path)
    manifest = Manifest(miniature=True, reviewer=None, second_rater=None, adjudication=None,
                        freeze_date=None, freeze=None, artifacts=[artifact], seeds={"sample": 1},
                        code_revision="3518d1b0eac2d74bae93ac529a0a105e2a912677",
                        tracked_diff_sha256="0"*64, file_hashes={}, runtime={}, model_artifacts=[],
                        prompt=None, parameters={}, unfamiliar_document_ids=[],
                        independence_attestation=None, effort_registration=None)
    blockers = manifest.blockers(tmp_path)
    assert "missing reviewer" in blockers
    assert "missing or altered artifact: documents" in blockers
    assert "miniature fixtures are not acceptance truth" in blockers
    with pytest.raises(ValidationError, match="cannot promote"):
        Report(manifest=manifest, blockers=blockers, raw_commands=[], raw_outputs=[],
               counts={}, metrics={"forged": ratio(100, 100, .9, independent=True)}, errors=[])


def test_registered_minima_never_manufacture_independence():
    result = minima([fact()], [question("a")], [], [])
    assert result["actual"]["entities"] == 1
    assert result["registered"]["entities"] == 300
    assert result["registered"]["entity:port"] == 30
    assert result["registered"]["change:interface-re-routing"] == 8
    assert len(result["blockers"]) > 15


def test_semantic_kappa_second_rater_and_partial_failure():
    reviews = [SemanticReview(occurrence_id=str(i), entity_type="component",
                              primary="SUPPORTED" if i < 2 else "PARTIAL",
                              second="SUPPORTED" if i < 2 else "PARTIAL",
                              blind=True, surrounding_page_seen=True) for i in range(4)]
    assert semantic_audit(reviews, 4)["kappa"] == 1
    assert not semantic_audit(reviews, 4)["blockers"]
    assert semantic_audit([r.model_copy(update={"second": None}) for r in reviews],
                          4)["blockers"]
    assert semantic_audit(reviews[:2], 2)["kappa"] is None
