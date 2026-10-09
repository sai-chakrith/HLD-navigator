# HLD Navigator remediation report — 9 October 2026

Sai Chakrith Sulluru; CB.AI.U4AID23143; Amrita Viswa Vidyapeetham; guide Dr. D. Palmani. Branch renamed to main. This remains a submission draft: mandatory human actions are unresolved. The external evaluator report and evidence were read only and remain outside the submission.

## Fixed and verified: review granularity

Before: source approval plus approval of Torque returned Engine ASIL D as approved facts from the same line. After: real HTTP returns insufficient evidence for Engine ASIL, while source mode retains the original line as unreviewed context. Approved retrieval text is a projection of reviewed entity names/fields, explicitly identified as structured records rather than literal original quotes. The original text, occurrence location and entity ID remain available separately. Whole-page PDF context is never approved by approving one entity.

Lexical FTS candidates are ranked against eligible approved projections. Embedding fact queries embed the approved projections, never neighboring raw page assertions, after checking the source index exists. Source-mode vectors retain original context. Rejected entities are excluded; approved edited records expose current fields explicitly labeled reviewer_correction, while their unchanged original source stays disputed. Lexical/vector retrieval and exports use the same current-field approval rule; source revocation and workspace isolation apply to both modes. Exported original evidence is explicitly labeled context, while inventory fields are approved. Tests retain exact bytes, locations and persistence checks; assertions moved to source_context for the deliberate response-contract change.

## Fixed and verified: bounded answer controls and token destinations

Named unit/type/owner/direction field questions use deterministic approved records where the narrow question contract fits. Optional free synthesis still requires human review. The literal-Nm / volts claim is rejected. Bounded checks reject detectable field values, reversed parsed directions, wrong explicit recipient roles, and omission of negation, conditions or revision qualifiers from a cited containing assertion. Three separate tests verify that literal substrings cannot crop these qualifiers. These checks are finite patterns, not general semantic entailment or unseen-injection guarantees. Generated claims have no persisted reviewer approval workflow; consequential use remains an operational human responsibility.

The UI accepts loopback API destinations by default. Explicit trusted deployments use HLD_NAVIGATOR_ALLOWED_API_ORIGINS with exact HTTPS origins; malformed URLs/embedded credentials/query fragments are rejected. Redirect forwarding is disabled. Deployed IAM/TLS infrastructure, parser process resource limits and enterprise hardening remain unresolved.

## Improved but limited: extraction

Dominant public misses were multiword linked component labels, named protocol/API declarations and typed dot-separated signal identifiers. Separate invented development examples exercise these grammars. New patterns extract explicit named declarations without inferring dependencies from links; uncertain/conditional relationships continue to require review. No tuning was performed on the frozen six-document set. Labels are agent-authored and not independent architect validation.

Unchanged public set: three documents, 19 expected entity/field facts. Before: 1 TP, 1 FP, 18 FN; precision 50%, recall 5.3%. After: 9 TP, 3 FP, 10 FN; precision 75%, recall 47.4%. Warning counts: before 20 TP, 12 FP, 19 FN; after 20 TP, 11 FP, 19 FN. Per-kind/per-field values, false positives and omissions remain in extraction-public-after.json. Unresolved misses include component roles/headings, implicit dependencies and some protocol names; generic VSS and extra API names remain false positives against these selected non-exhaustive labels.

Frozen synthetic AUTOSAR-style set: six documents covering distinct names, three revision headings, a port table, positive prose, one conditional statement and one negated statement. Frozen before parser changes: 41 expected entity/field facts. Before and after: 41 TP, 0 FP, 0 FN. Warning counts both: 2 TP, 2 FP, 0 FN. The extra no_entities warnings are retained as warning errors. This small familiar grammar set is insufficient for generalized HLD accuracy; no human reviewer or measured correction-time benefit is invented. Existing development fixture remains 22 TP, 0 FP, 0 FN, with two retrieval questions (recall@5 1.0, MRR .625).

Diagram topology, general semantic extraction, mixed text/image OCR coverage and real OEM accuracy remain unresolved. Actual Tesseract integration was previously verified; its availability is now described accurately. No larger models, training or peripheral governance features were added.

## Improved but limited: model experiment and evaluation separation

Pinned existing Qwen2.5-7B Q4_K_M and llama.cpp b11490 CPU artifacts were verified by the launcher. One raw call per unchanged development case, no retries: 29/30 raw contracts, all 30 raw outputs byte-identical to prior v3. Raw failures and the intermediate guard false rejection remain preserved. Final guard is replayed separately against those exact raw outputs; the final submitted source identity is separate from the live-run identity. No source identity was substituted in the original run.

Final developer judgments: 8/12 useful complete answerable responses, with four answerable abstentions; 3/5 useful conflict responses, with C02 and C05 rejected; 4/5 useful injection responses, with I03 falsely abstaining; zero instruction-following in these five cases. Missing evidence: 6/6 abstain; irrelevant evidence: 2/2 abstain. These denominators and case IDs are recorded separately. The final guard rejects the provider mislabeled as recipient (A06) and unsupported revision recommendation (C05). No semantic-accuracy percentage is inferred from contract validity. The same assistant assessed its implementation; this is development review, not independent acceptance.

Actual API synthesis returned EngineControl provides TorqueInterface through TorqueOut with a resolved approved-field citation and human_review_required=true. Actual type/unit API query returned uint16/Nm through deterministic reviewed fields, without invoking the model. These different paths are disclosed separately. Excerpt mode remains the default for other questions.

The historical whole-block experiment uses tools/local_benchmark.py --contract legacy and a preserved historical generator from commit 7e90273. Current mode uses the current JSON contract and guard, with no obsolete whole-block scoring. Internal harnesses remain in the repository but are excluded from student submission code; current raw results are labeled developer measurements.

## Fixed and verified: regression and portable package preparation

Repository suite: 520 passed, one upstream Starlette/httpx deprecation warning; Ruff lint and format checks pass. Tests cover mixed assertions, whole-page PDF context, field/qualifier contradictions, edited/rejected entities, source revocation, workspace isolation, token destinations, reports and preserved provenance. Real HTTP smoke returns unauthenticated 401, eight reviewed entities, source export gates, and the corrected mixed-review abstention.

The submission has the required eight folders, real-ID root and versioned deliverable names. Source/prompt/schema hashes match the submitted code. Internal tester reports/capture scripts, live credentials/databases, virtual environments, weights, redundant historical slides and the noncompliant screenshot movie are excluded. Source retains the shared test_pilot fixtures; tests/test_tester_* and tester_acceptance are intentionally excluded together. A separate fresh-environment receipt records the packaged suite count and command outputs. This is a new environment on the same Windows host with dependency caches; not another OS, an offline clean machine or hosted CI. The configured CI now checks formatting but hosted execution remains unobserved.

The fresh package suite passed 286 tests in a new short-path environment. The initial deeply nested environment passed 284 but failed two UI imports because a Streamlit module was absent at a 263-character Windows path. The failed XML is retained. The same packaged source passed in a separate short-path virtual environment, and README documents this deployment constraint.

The archive receipt checks ZIP CRC and every manifest SHA-256. Personal launch paths are replaced by commands run from Code/HLD-navigator. Optional model/OCR provisioning is online; local inference is separate. No Docker/scaling claims were added. Unsigned PDFs identify the real ID but do not fabricate verification or approval.

## Exact verification commands

From the repository root: python -m pytest -q --junitxml=docs/evidence/remediation/pytest-final-eligibility.xml; python -m ruff check src tests tools; python -m ruff format --check src tests tools; python tools/smoke.py --output docs/evidence/remediation/live-http-final.json. Extraction: python tools/evaluate.py --manifest data/evaluation/public/manifest.json --output docs/evidence/remediation/extraction-public-after.json; repeat with data/evaluation/remediation-frozen/manifest.json for the frozen measurement. The files preserve exact manifests, denominators and raw failures.

Optional model: python tools/serve_local_model.py answer; set HLD_NAVIGATOR_CHAT_BACKEND=llama_cpp, HLD_NAVIGATOR_LOCAL_URL=http://127.0.0.1:18883, HLD_NAVIGATOR_CHAT_MODEL=qwen7b. The original run command and runtime/source identities are in answer-run/run-identity.json. Final replay makes no model calls. A fresh packaged-code environment runs uv sync --frozen --extra dev, pytest, Ruff and the real HTTP smoke; outputs are in the adjacent portable verification receipt.

## Requires human action: official eligibility and live demonstration

1. Student personally verifies implementation, data provenance, model limits and AI assistance, and signs integrity/AI-use declarations with a real date.
2. Obtain actual faculty synopsis approval/signatures from Dr. D. Palmani where required. No approval or reviewer identity has been invented.
3. Record continuous actual system behavior for 5–10 minutes using the provided seven-minute live script. Browser snapshot tooling is available here, but an authorized continuous screen-recording API is not. The earlier 301-second still-image sequence does not meet the requirement and is excluded from this package. Video contains a script, not a claimed compliant recording.
4. Practice the code-ownership viva and explain the remaining parser/model failures in your own words. Independent human annotation review and measured correction time remain unavailable; obtain them before claiming independent acceptance or business benefits.

No internship score, employment result, safety certification or completed official eligibility is promised. The mandatory human actions remain open even though the implemented code fixes and package integrity checks pass.
