# Validation record

Local date: 2026-10-08. Windows/Python 3.14.8. Eight review regressions failed before fixes (`evidence/review-before.txt`). Field-level evaluation also reproduced sentence punctuation becoming part of port names and unreported unsupported relationships (`evidence/prose-before.txt`). Explicit component absence failed before correction (`evidence/absence-before.txt`). Existing declaration ingestion, permissions, human review and document-version controls are preserved.

Final local result: **53 passing tests**, lint/format checks passed, and ordinary-prose live HTTP workflow passed. One upstream Starlette/httpx deprecation warning remains. Ephemeral fixture credentials in failure evidence are redacted.

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

Readiness: the specific review defects are locally addressed and supported ordinary prose/tables now work. Real-HLD, OCR/model and deployment acceptance remain pending before a finished Case Study 1 submission claim.
