"""Field extraction and separate learned-retrieval evaluation; never a reliability score."""

import argparse
import hashlib
import json
import os
import platform
import tempfile
from collections import defaultdict
from pathlib import Path

from hld_navigator.evaluation import warning_scores
from hld_navigator.extraction import extract
from hld_navigator.models import SourceReview
from hld_navigator.rag import answer, supported
from hld_navigator.store import Store
from hld_navigator.vectors import configured_embedder


def facts(entities):
    result = set()
    for entity in entities:
        result.add((entity["kind"], entity["name"], "entity", "present"))
        for field, value in entity["attributes"].items():
            result.add((entity["kind"], entity["name"], field, value))
    return result


def run(manifest_path, output, models=False):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    metrics = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "missed": [], "incorrect": []})
    embedder = configured_embedder() if models else None
    chat_model = os.getenv("HLD_NAVIGATOR_CHAT_MODEL") or os.getenv("HLD_NAVIGATOR_OLLAMA_MODEL")
    report = {
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "runtime": {"python": platform.python_version(), "platform": platform.platform()},
        "model_artifacts": {
            "embedding_identity": embedder.identity if embedder else None,
            "answer_model_tag": chat_model if models else None,
            "answer_model_digest": None,
            "answer_artifact_verification": "PENDING_OPERATOR_RECORD",
        },
        "corpus_status": manifest["review_status"],
        "reviewers": manifest.get("reviewers", []),
        "measured_correction_minutes": manifest.get("measured_correction_minutes"),
        "model_evaluation": "NOT_RUN" if embedder is None else "RUN_ON_MANIFEST",
        "human_semantic_groundedness": None,
        "answer_model_evaluation": "NOT_RUN"
        if not embedder or not chat_model
        else "RUN_ON_MANIFEST",
        "retrieval": [],
        "cases": [],
    }
    with tempfile.TemporaryDirectory() as temporary:
        store = Store(str(Path(temporary) / "eval.db"))
        for case in manifest["documents"]:
            path = manifest_path.parent / case["file"]
            content = path.read_bytes()
            if hashlib.sha256(content).hexdigest() != case["sha256"]:
                raise ValueError("Evaluation file hash mismatch")
            try:
                blocks, entities, warnings = extract(path.name, content)
                actual = facts([e.model_dump() for e in entities])
                result = {
                    "file": case["file"],
                    "warnings": warnings,
                    "locations": [e.model_dump() for e in entities],
                }
            except Exception as error:
                blocks, entities, warnings = [], [], []
                actual = set()
                result = {"file": case["file"], "extraction_error": str(error)}
            expected = facts(case["entities"])
            for fact in actual | expected:
                group = metrics[f"{fact[0]}.{fact[2]}"]
                if fact in actual and fact in expected:
                    group["tp"] += 1
                elif fact in expected:
                    group["fn"] += 1
                    group["missed"].append({"file": case["file"], "fact": fact})
                else:
                    group["fp"] += 1
                    group["incorrect"].append({"file": case["file"], "fact": fact})
            if "expected_warnings" in case:
                result["warning_accuracy"] = warning_scores(warnings, case["expected_warnings"])
                result["warning_annotation_status"] = case.get(
                    "warning_annotation_status", manifest["review_status"]
                )
            report["cases"].append(result)
            if not blocks:
                continue
            document = store.ingest(
                "eval", path.name, "1", path.name, content, blocks, entities, [], "evaluation"
            )
            store.review(
                "eval",
                document,
                SourceReview(
                    approved=True,
                    reason="Isolated evaluation source access; not engineering approval",
                ),
                "evaluation",
                source=True,
            )
            if embedder:
                store.index_vectors("eval", document, embedder)
            for query in case.get("queries", []):
                lexical = store.search("eval", query["text"], document, "source")
                retrieved = (
                    store.vector_search("eval", query["text"], document, embedder, "source")
                    if embedder
                    else None
                )

                def rank(items, query=query):
                    return next(
                        (i for i, e in enumerate(items, 1) if query["relevant_quote"] == e["text"]),
                        None,
                    )

                item = {
                    "document_sha256": case["sha256"],
                    "question": query["text"],
                    "expected_behavior": query.get("expected_behavior", "answer_from_sources"),
                    "lexical_evidence": lexical,
                    "embedding_evidence": retrieved,
                    "semantic_review": {
                        "reviewer": None,
                        "review_seconds": None,
                        "relevance": None,
                        "entailment": None,
                        "necessary_evidence_complete": None,
                        "contradiction_handling": None,
                        "abstention": None,
                        "prompt_injection_resistance": None,
                        "notes": None,
                    },
                    "lexical_rank": rank(lexical),
                    "embedding_rank": rank(retrieved) if retrieved is not None else None,
                }
                if embedder:
                    response = answer(query["text"], retrieved)
                    item.update(
                        answer=response,
                        response_sha256=hashlib.sha256(
                            json.dumps(response, sort_keys=True).encode()
                        ).hexdigest(),
                        full_block_quote_support=supported(
                            response["answer"], response["evidence"]
                        ),
                        human_relevance_entailment_review="PENDING",
                    )
                report["retrieval"].append(item)
    for group in metrics.values():
        tp, fp, fn = group["tp"], group["fp"], group["fn"]
        group.update(
            precision=tp / (tp + fp) if tp + fp else None,
            recall=tp / (tp + fn) if tp + fn else None,
            correction_actions=fp + fn,
            measured_correction_minutes=None,
        )
    report["fields"] = dict(metrics)
    warning_cases = [c["warning_accuracy"] for c in report["cases"] if "warning_accuracy" in c]
    tp, fp, fn = (sum(c[key] for c in warning_cases) for key in ("tp", "fp", "fn"))
    report["warning_metrics"] = {
        "annotated_documents": len(warning_cases),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
        "annotation_status": manifest["review_status"],
        "annotation_scope": manifest.get("scope", "declared manifest scope"),
        "human_warning_semantics_review": "PENDING"
        if not manifest.get("reviewers")
        else "SEE_REVIEW_RECORD",
    }
    for name, key in [("lexical", "lexical_rank"), ("embedding", "embedding_rank")]:
        ranks = [r[key] for r in report["retrieval"]]
        report[name + "_metrics"] = (
            {
                "recall_at_5": sum(r is not None for r in ranks) / len(ranks),
                "mrr": sum(1 / r if r else 0 for r in ranks) / len(ranks),
            }
            if ranks and (name == "lexical" or embedder)
            else None
        )
    if not embedder:
        report["model_dependency"] = (
            "Available local Ollama endpoint, embedding model and verified artifact digest; "
            "answer model required for model-answer quality measurement"
        )
    report["limitation"] = (
        "Only independently reviewed, frozen holdouts support acceptance conclusions. "
        "Quote support does not establish relevance or semantic entailment. "
        "Correction actions are not measured effort."
    )
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "corpus_status": report["corpus_status"],
                "model_evaluation": report["model_evaluation"],
                "lexical_metrics": report["lexical_metrics"],
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("data/evaluation/manifest.json"))
    parser.add_argument(
        "--output", type=Path, default=Path("docs/evidence/extraction-retrieval.json")
    )
    parser.add_argument("--models", action="store_true")
    args = parser.parse_args()
    run(args.manifest, args.output, args.models)
