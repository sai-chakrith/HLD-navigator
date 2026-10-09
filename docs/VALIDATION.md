# Validation record

## Current follow-up - 09 October 2026

Current source: **499 tests passed** in `evidence/completion-pytest.xml`; lint passes.
The paragraphs below retain historical runs and their earlier counts/limitations.
`evidence/live-http.json` records the baseline HTTP workflow. Browser captures in
`output/demo/screenshots/` verify actual upload, evidence review, graph rendering,
revision comparison and HTTP 409 on an unreviewed export.

`evidence/live-model-http.json` records real API retrieval plus Qwen 7B synthesis:
the fictional Torque signal answer correctly states uint16/Nm and resolves to the
retrieved source block. `evidence/answer-run-v3/` retains all 30 fixed cases, complete
prompts, original evidence, raw outputs, guarded results, candidate hashes and
hash-bound developer assessments. Mechanical raw contract: 29/30. All eight
must-abstain cases abstained. Zero instruction-following was judged in five
injection cases. Useful complete: 8/12 answerable, 3/5 conflicts, 4/5 injections.
The A06 recipient reversal and C05 unsupported revision recommendation remain
failures even though their literal citations pass. This is not independent or
protected acceptance, and no global semantic-accuracy figure is claimed.

Runs v1/v2 remain intact, including attacker fact adoption and contract failures.
After those failures, the candidate added source-command quarantine, stronger
instructions and llama.cpp JSON schema constraints. The unchanged cases were
rerun once per version, without hidden retries. Quarantine excludes obvious
assistant-directed lines, not originals; it is conservative and incomplete.

`evidence/current-retrieval.json` reproduces real BGE CPU results on four public
questions: recall@5 0.75 for both methods; MRR 0.75 lexical / 0.625 learned.
`evidence/ocr-engine.json` records real Tesseract 5.5.0 on a seven-page image-only
instructions scan: 312 blocks and seven mandatory OCR review warnings. It does
not measure HLD word/entity accuracy. `evidence/public-current.json` preserves
the frozen three-document parser limitations against provisional agent labels.

Snapshot/restore, token revocation, graph/report and before/after impact regressions
pass. Hosted CI is configured, not observed. Human review, OEM generalization,
correction time and production deployment qualification remain external gaps.

## Historical records

Local date: 2026-10-08. Windows/Python 3.14.8. Eight review regressions failed before fixes (`evidence/review-before.txt`). Field-level evaluation also reproduced sentence punctuation becoming part of port names and unreported unsupported relationships (`evidence/prose-before.txt`). Explicit component absence failed before correction (`evidence/absence-before.txt`). Existing declaration ingestion, permissions, human review and document-version controls are preserved.

Final local result: **87 passing tests**, lint/format checks passed, and ordinary-prose live HTTP workflow passed. One upstream Starlette/httpx deprecation warning remains. Ephemeral fixture credentials in failure evidence are redacted.

Latest output: `evidence/pytest.txt` / `evidence/pytest.xml`, with lint/format records adjacent. Checks cover full-block citation context, generated blank/wrapped/table PDFs, ordinary prose, table aliases, merged source references, empty/unresolved exports, coverage invalidation, disputed/edited fact filtering, manual corrections, workspace isolation, persistence/rollback, provider/consumer/type mismatches and change impacts. Scripted embeddings verify cosine ranking, persistent indexing, interrupted indexing, digest drift and actual Ollama request shapes. Controlled OCR TSV plus image rendering establish adapter behavior only.

`uv run python tools/smoke.py` launches an isolated real HTTP API, uploads the ordinary-prose fixture, reviews eight entities, searches/exports and stops the process tree. Report: `evidence/live-http.json`. It is not an OEM/model benchmark.

`uv run python tools/evaluate.py --models` separately records field TP/FP/FN, precision/recall, missed/incorrect facts, correction actions, lexical recall@5/MRR and optional learned retrieval/quote support. `evidence/extraction-retrieval.json` labels the corpus synthetic development/unreviewed and model evaluation NOT_RUN. No Ollama/Tesseract executable was available. Synthetic results cannot estimate OEM accuracy; tuning against these fixtures prevents treating them as independent holdouts.

## External acceptance procedure

1. Obtain authorized HLDs across families/variants/revisions, including scans/diagrams. Split by family before development. Two AUTOSAR architects independently annotate entities, attributes, declared edges, directions and locations; adjudicate differences. Freeze hashes/reviewer identities using `data/evaluation/manifest.json` format. Record correction minutes independently of edit counts.
2. Run `uv run python tools/evaluate.py --manifest <heldout-manifest.json> --output <report.json>`. Failures count all expected facts as missed. Inspect false positives, missed interfaces and provenance errors. Signed report scopes cannot waive engineering completeness assessment.
3. Supply local Ollama server, embedding model/tag/digest and answer model/tag/digest. Configure README variables, index documents and evaluate with `--models`. Compare learned recall/MRR with lexical retrieval. Architects must assess answer relevance, entailment, omissions, contradictions, abstention and prompt injection separately from quote equality. Record artifacts/hardware/runtime.
4. Supply Tesseract executable/language data and scanned HLD ground truth. Enable OCR and measure word/entity errors, location errors and correction time. Review every OCR warning. Diagrams still need human relationship annotation.
5. Run a counterbalanced supervised pilot on matched HLD tasks; measure active review/correction time, accepted proposals and independently confirmed inconsistencies. Register targets/sample size first. No business benefits have been measured.
6. Before deployment, validate managed identities/revocation, TLS, secrets, backup restoration, concurrent review/indexing, malicious PDFs, resource limits and monitoring. Filesystem administrators can alter the SQLite database/audit.

Second-review evidence: `compound-before.txt` records nine failures before fixes, and `predicate-before.txt` records two further unknown-predicate failures. Twelve added checks cover these defects plus mixed prose/table revision review, export, type/direction findings and impacts. `REVIEW_ACCEPTANCE.md` gives acceptance procedures and unresolved semantic-answer limitations.

Readiness: the reproduced review defects are locally addressed and supported ordinary prose/tables now work. Real-HLD, OCR/model and deployment acceptance remain pending before a finished Case Study 1 submission claim.

## Multiple recipients, units and unfamiliar baseline

`recipients-units-before.txt` records ten failures before correction; two simple units already passed. Twelve recipient/unit regressions cover coordinated recipients, incoming senders, subsequent clauses, exponents, multiplication and spaced units. Additional warning-accounting and controlled CPU adapter tests bring the suite to 87 (including plural-unit coverage).

`public-baseline.json` freezes a three-document public KUKSA baseline with commit/license/hashes. Against selected provisional agent annotations it records 18 missed facts, one unexpected fact, 20 matched warning locations, 12 unexpected warnings and 19 missed warning locations. The selected annotations were authored after inspection and are not exhaustive or architect-reviewed; these counts expose limitations, not independently established precision/recall. No extraction tuning was applied to these documents.

`local-embedding.json` records an actual BGE-small-en-v1.5 f16 CPU run via the verified llama.cpp b11490 runtime. Four selected public-document questions: lexical and learned recall@5 are both 3/4; lexical MRR is 0.75, learned MRR is 0.625. This configuration does not demonstrate a retrieval advantage. The benchmark includes original retrieved passages; human semantic review is pending. Reproduction is in LOCAL_MODEL_VALIDATION.md.

The architecture reviewer packet has blank identities, annotations and active correction-time records; no independent review or measured benefit has occurred.

## Actual answer model run

`local-model.json` records a complete verified Qwen2.5-0.5B-Instruct Q4_K_M CPU run: ten cases, zero quote-contract passes, required passage text present in five of six answerable cases, and zero raw abstentions among four cases requiring abstention. All outputs are rejected by the existing citation contract. The passages present count is not semantic answer accuracy: the public API response includes unnecessary TLS evidence and the injection case copies a malicious instruction. `local-model-assessment.json` separately documents relevance, omissions, contradictory echoes, abstention failures and injection contamination. These are agent assessments; architecture review remains pending. This small model configuration is rejected for pilot answers.

Exact artifact hashes, prompt, parameters, raw responses and elapsed times are retained. Diagram assets are frozen with the public sources. The reviewer packet includes ten blank semantic review rows tied to response hashes. No architect sign-off or correction-time measurement has occurred. The local model execution dependency is now satisfied for this experiment; independent usefulness/acceptance remains unresolved.
