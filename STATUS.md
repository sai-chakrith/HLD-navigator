# Engineering status

The review's concrete defects were reproduced and corrected. This is an improved Case Study 1 pilot, not a completed or production-validated submission.

| Area | Implemented | Boundary |
|---|---|---|
| HLD ingestion | Affirmative prose patterns, wrapped PDF text, PDF/Markdown table aliases and existing declarations | Arbitrary OEM layouts/diagrams unvalidated; no benchmarked LLM extraction |
| Evidence | Merged source references, original bytes/hash, OCR origin/confidence | OCR confidence is not reliability |
| Correctness | Blank pages skip, full-block citation guard, explicit ambiguous/negated/unsupported requirements | Block equality preserves context but does not establish semantic relevance |
| Review/export | Empty/unresolved export blockers, scoped warning resolution and direct evidence-backed corrections | Signed scope is not a completeness certificate |
| Retrieval | Approved facts separated from disputed sources; learned embedding adapter and persistent local cosine vector store | Real model benchmark NOT_RUN; lexical baseline remains explicit |
| Architecture | Reference/conflict, provider/consumer and type checks; traceable declared-edge change-impact paths | Potential findings require architects; no formal AUTOSAR conformance claim |
| OCR | Opt-in Tesseract rendering/TSV adapter with mandatory review | Real executable/scans unavailable; topology interpretation absent |
| Evidence | Regression tests, ordinary-prose live HTTP workflow and field/retrieval evaluation harness | Synthetic development corpus only; independent ground truth/pilot pending |

Additive schema version 2 retains original users/documents/history. Legacy documents retain earlier extraction; ingest a new revision to use improved extraction. Enterprise IAM, deployment/load tests, backups/restore acceptance and tamper-resistant auditing remain unfinished.

Latest authoritative counts and acceptance procedures: docs/VALIDATION.md and docs/evidence/. No percentage reliability, grade or measured productivity benefit is claimed.
