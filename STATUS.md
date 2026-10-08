# Engineering status

The first review defects and the second review's reproduced compound/unsupported/conditional prose defects were corrected locally. This is an improved Case Study 1 pilot, not a completed or production-validated submission.

| Area | Implemented | Boundary |
|---|---|---|
| HLD ingestion | Affirmative prose patterns, wrapped PDF text, PDF/Markdown table aliases and existing declarations | Arbitrary OEM layouts/diagrams unvalidated; no benchmarked LLM extraction |
| Evidence | Merged source references, original bytes/hash, OCR origin/confidence | OCR confidence is not reliability |
| Correctness | Blank pages skip, full-block citation guard, explicit ambiguous/negated/unsupported requirements | Block equality preserves context but does not establish semantic relevance |
| Review/export | Empty/unresolved export blockers, scoped warning resolution and direct evidence-backed corrections | Signed scope is not a completeness certificate |
| Retrieval | Approved facts separated from disputed sources; learned embedding adapter and persistent local cosine vector store | Real BGE CPU retrieval run on four public-document questions; lexical baseline remains explicit |
| Architecture | Reference/conflict, provider/consumer and type checks; traceable declared-edge change-impact paths | Potential findings require architects; no formal AUTOSAR conformance claim |
| OCR | Opt-in Tesseract rendering/TSV adapter with mandatory review | Real executable/scans unavailable; topology interpretation absent |
| Evidence | Regression tests, ordinary-prose live HTTP workflow and field/retrieval evaluation harness | Synthetic regressions plus frozen public KUKSA baseline; independent ground truth/pilot pending |

Additive schema version 2 retains original users/documents/history. Legacy documents retain earlier extraction; ingest a new revision to use improved extraction. Enterprise IAM, deployment/load tests, backups/restore acceptance and tamper-resistant auditing remain unfinished.

Latest authoritative counts and acceptance procedures: docs/VALIDATION.md and docs/evidence/. No percentage reliability, grade or measured productivity benefit is claimed.

Second review: compound edges, unmatched clause warnings and qualifier blockers are covered by regressions. Mixed prose/table revisions exercise review, export, mismatches and impact comparison. See docs/REVIEW_ACCEPTANCE.md for failure evidence and pending independent/model/OCR/value acceptance. Semantic answer quality is still unresolved.

Current follow-up: multiple recipient/sender lists and complete compound units are fixed. Warning evaluation now reports one-to-one source matches, unexpected warnings and missed warnings. Three unfamiliar public documents retain substantial misses; provisional annotations are not independent ground truth. Real BGE retrieval matched lexical coverage and had lower MRR on four selected questions. An architecture reviewer packet is prepared; review and correction time remain pending. See docs/LOCAL_MODEL_VALIDATION.md and docs/reviewer-packet/.

Actual answer run: verified Qwen2.5-0.5B-Instruct Q4_K_M ran ten controlled cases. All outputs failed the citation format contract; five of six answerable cases contained the required passage text, which is not a relevance score. All four expected raw abstentions failed. Contradictions and irrelevant passages were echoed. The application rejected all ten outputs; this model configuration is not accepted for pilot answers. Raw output and separate agent assessment are retained; independent semantic review remains pending.
