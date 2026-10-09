# Remediation in progress — 9 October 2026

Branch: main. Review granularity repaired with approved-field projections and
separate source context; bounded answer checks and UI destination allowlist added.
Public extraction improved to 9 TP/3 FP/10 FN on the same 19 annotated facts.
Frozen agent-authored synthetic set: 41 TP/0 FP/0 FN; warnings 2 TP/2 FP/0 FN.
See docs/submission/REMEDIATION_REPORT.md for verified results and required actions.
No independent OEM acceptance, real-time recording or personal signatures claimed.

## Historical status below

# Engineering status

## Current completion - 09 October 2026

The local software and interview demo are implemented and verified. Submission
artifacts include source, input provenance, configuration, evaluation evidence,
technical report, synopsis, presentation, captioned walkthrough and unsigned
declarations. Register/team ID and student/faculty signatures remain blank.
This is an engineering review pilot; independent OEM qualification is unfinished.

- **499 passing tests**, one upstream deprecation warning; lint passes.
- Actual authenticated HTTP workflow and browser upload, evidence review,
  dependency graph, revision comparison and unreviewed export blocker verified.
- Real Qwen 7B through API/retrieval correctly answered a fictional Torque
  type/unit question. Final fixed development run: 29/30 raw contract passes,
  8/8 must-abstentions, zero injection-following in five developer-reviewed cases.
  Useful complete: 8/12 answerable, 3/5 conflicts, 4/5 injections. Incorrect recipient
  and revision recommendation claims remain documented semantic failures.
- BGE CPU reproduced four-question recall@5 0.75 for both methods; MRR lexical
  0.75 versus embedding 0.625. Lexical source excerpts remain default.
- Real Tesseract processed seven image-only instruction pages: 312 OCR blocks,
  seven mandatory page-review blockers. HLD transcription accuracy is unmeasured.
- Three public KUKSA documents retain 18 missed facts and one unexpected fact
  against selected provisional agent labels. Two additional public documents
  and license/provenance are included, without extraction tuning against them.

Delivered: ingestion/provenance, correction/review history, workspace roles and
token revocation, export blockers, cited component reports/dependency graph,
architecture findings, before/after impact paths up to two hops, optional BGE
index/local answers, consistent SQLite recovery, isolated demo and CI configuration.

Obvious assistant-directed source lines are quarantined from generation/citations,
with originals retained. This conservative heuristic can omit legitimate material
and cannot detect all injection attacks. Exact snippets do not establish entailment;
synthesized answers require review. Runs v1/v2 failures are preserved; all judgments
are developer review by the coding assistant, not independent human validation.

External gaps: authorized OEM family holdouts and independent annotations,
diagram/completeness and OCR accuracy, measured correction time, enterprise IAM/TLS,
load qualification, hardened audit and observed hosted CI. No production readiness,
safety/AUTOSAR conformance, global OEM accuracy or productivity gain is claimed.

Current evidence: `docs/VALIDATION.md`, `docs/evidence/answer-run-v3/`,
`docs/submission/COMPLETION_REPORT.md`. Historical notes below are superseded where
current execution is explicitly recorded above.

## Historical notes

2026-10-09 follow-up: local regression suite passes 490 tests. Reviewed exports now
include dependency visualization and cited component reports. Change-impact paths
include added relationships and before/after graph evidence, preserve alternative
paths and stop at two hops. An isolated interview demo, verified SQLite recovery
tool and Windows/Linux CI workflow have been added. Hosted CI is not yet executed.
The public corpus includes two additional pinned KUKSA documents with license and
hashes. The existing public benchmark still exposes parser misses; no independent
validation or improved OEM accuracy is claimed. The Qwen 7B download/live evaluation
and real-engine OCR verification remain in progress.

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
