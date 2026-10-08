# Independent Tester handback: T2 and T3a

2026-10-08. **Not independently validated.** No R1–R7 real-holdout acceptance.
Product files and existing/Developer tests were not edited. No holdout was accessed,
no acceptance ground truth was authored, and no messages were sent to other chats.
Only the supplied candidate diff/identity, baseline code snapshot, public API/model
signatures, and new Tester-created synthetic fixtures were used for verification.

## Candidate and target identity

HEAD: `3518d1b0eac2d74bae93ac529a0a105e2a912677`.
Tracked diff SHA-256 before/after final commands:
`05ae4c766282c7f6903d53396dacc2c729df8ff8d734435cd6718378f7754fc3`.
All supplied product/config/lockfile hashes matched the handoff; no product byte drift.
The four existing modified product files are Developer-owned: extraction.py, models.py,
store.py and tables.py. tests/test_developer_table_provenance.py is Developer-owned and
was never read as an oracle. Its execution in the full suite is only a regression result.

Target-record SHA-256 verified:
`c13e2114ad0ee6e061073e7c7d436b1d1810d880b64301b39a9933cd68ef4e93`.
This is the human target record, NOT a corpus freeze. Latest final acceptance requires
the appropriate two-sided 95% confidence bound, including EACH entity type. Numeric
targets remain unchanged. Mechanical provenance/injection/permissions retain observed
hard gates and uncertainty; effort retains paired task-block bootstrap.

Runtime: Windows, Python 3.14.8, Pydantic 2.13.5, pytest 9.1.1, anyio 4.15.1, uv 0.12.23.
Exact pre/post candidate snapshots, file hashes, commands, exit codes, and byte hashes
of stdout/stderr are in evidence/capture-20261008T085652/runs.json.

## T2 acceptance harness/protocol

Files: tester_acceptance/harness.py, __init__.py, PROTOCOL.md, capture.py,
baseline_warning_probe.py, .gitignore; tests/test_tester_acceptance_t2.py.
Evidence is Tester-owned. baseline_warning_probe.py supports T3a only.

| Criterion | Result | Evidence and boundary |
|---|---|---|
| 1 Contracts and annotation/run identity | PASS for miniature scaffold | Strict Pydantic manifest/artifact/report/unit contracts; raw runtime/prompt/model/hash fields; custody and annotation protocol. Actual independent runtime/manifest absent. |
| 2 Extraction/provenance/multiplicity | PASS on own fixtures | Unknown prediction FP, duplicate prediction FP, missing occurrence FN; separate exact-span and SUPPORTED metrics; errors retained. Protected source and sampling adapters absent. |
| 3 Warning opportunities and TNs | PASS on own fixtures | Stable IDs, category sets, duplicates counted once; TP/FP/FN/TN and separate FDR/FNR/benign rate; unknown IDs retained and block. |
| 4 Raw/application answers | PASS on own fixtures | Raw/application and production/diagnostic retrieval separate; abstention/conflict/injection/relevance/citation groups, overlap, raw malformed errors retained. No real model/API acceptance adapter. |
| 5 Revision and impact | PASS on own fixtures | Missed seeds and unmatched/duplicate reports retained; empty ratios null; impact denominator includes missed changes. Independent matching/impact labels absent. |
| 6 Global prerequisites/minima/final gate | BLOCKED | No independent review/custody/freeze; registered minima checker and artifact checks exist, but full protected acceptance orchestrator is not implemented. |
| 7 Hand-calculated examples | PASS | Eleven Tester-only tests pass in final full run; Wilson polarity, null denominators, minima, dedup, hard gates, hashes, failed extraction, malformed output, bootstrap, kappa and report promotion rejection. |
| 8 Required lint/regression commands | FAIL to obtain a clean full run | Ruff passes; exact uv pytest launcher fails; module fallback has one retained T3a synthetic nuisance-warning failure. |

Hand calculations verified: extraction TP=1, FP=2, FN=1 (including unknown type and
duplicate); warnings TP=2, FP=1, FN=1, TN=2 with FDR=FNR=benign rate=1/3 and category
accuracy=1; answerable false abstention=1/2; malformed unsupported output abstention=0/1
and injection unknown/failure=1/1. Revision example impact micro recall=2/3, precision=1/2,
impact-correct/detected=2/3, unconditional detection-and-impact coverage=1/2.
Matched effort example: 15 corrections/100, 15 assisted active minutes/100, reduction=70%;
10,000 paired bootstrap draws with seed 123 give reduction interval [2/3, 3/4].
Twenty zero observed failures have separate exact one-sided 95% upper failure bound
0.1391083407; true zero risk is not asserted. These are arithmetic fixtures, not corpus metrics.

Updated rule enforcement: `Metric.final_accepted` requires independent status, minimum,
point target AND the appropriate bound; observed hard gates are the stated exception.
`tier=PASS` is retained only as a diagnostic and does not qualify for final acceptance.
Tests explicitly reject 90/100 extraction acceptance and 27/30 per-type acceptance when
their lower bounds miss the targets. The Report rejects promoted metrics if reviewer/
freeze evidence is missing. This enforces the rule at metric/report level, not an entire
protected run: no caller may bypass global minima, custody, adjudication, sample identity,
hash integrity, local-only runtime checks or permission coverage. That orchestrator is a gap.

## T3a independent candidate verification

File: tests/test_tester_t3a_provenance.py. Nine synthetic checks: eight pass, one fails.

| Criterion | Result | Evidence |
|---|---|---|
| 1 Raw/normalized separation | PASS on miniature fixtures | Exact Markdown whitespace/section/line/table/row; PDF rows compared with original authoring geometry, independently cropped text and rendered pages; multiline captured quote differs correctly from normalized attributes. |
| 2 Aliases/repeated source identity | PASS on miniature fixtures | SWC Name/Responsibility, Port Name/Port Kind, P-Port/R-Port; three repeated Markdown occurrences across tables; three multiline PDF occurrences across two pages, correct row/page identity. |
| 3 Lifecycle | PASS on exercised paths | Markdown API upload, source/entity review, approved source links, export and DB reopen; PDF ingest/review/DB reopen retrieval retains all three correct raw rows. No live deployed server or clean-machine validation. |
| 4 Explicit failures and regression | PASS for scoped row handling; FAIL overall regression | Invalid direction/unknown populated column warn; uncapturable cropped PDF row emits unsupported_table without table fact/quote. All 93 existing/Developer regression tests pass outside sandbox; one new valid PDF fixture gets blocking nuisance warnings. No prose/model/rag/quote-guard changes are in supplied product diff. |
| 5 Historical boundary and scope | PASS as documented boundary | New raw provenance applies on new ingest. Existing synthesized evidence is not reparsed/repaired by the added evidence-link backfill; historical documents need governed re-ingestion and review. General legacy repair/prose/model work remains outside T3a. |

T3a core provenance is **PASS on the exercised synthetic paths**. The full regression
run is **FAIL** and overall candidate acceptance remains **BLOCKED**, not DONE.
The preserved failure is a pre-existing prose warning. Supervisor inspected its raw
baseline comparison and will assign it as a separate R2 task; T3a does not include prose
tuning. The failing benign-caption test stays intact. No further testing breadth or
product task is taken in this session.

Synthetic reproduction: valid grid PDF has title `Tester synthetic component inventory -
page 1`, SWC Name/Responsibility header, repeated Brake rows with multiline responsibility
`Stops safely` / `under command`; second page repeats one row. Candidate produces two
blocking unsupported_relationship warnings with unresolved action `inventory`, even though
the table entity and all three original spans are correct. The unchanged failing assertion
is tests/test_tester_t3a_provenance.py:87. It is not xfailed or excluded from regression.
An additional core-span check exercises the row provenance despite the retained failure.

The read-only in-memory audit baseline comparison confirms the SAME two
unsupported_relationship warnings at HEAD. Baseline also emits no_entities because it
cannot parse these multiline cells; candidate removes that error and extracts the correct
normalized description. Do not claim the full warning lists are identical; only the two
relationship warnings match. No product correction was made.

## Raw commands/output and evidence

Final commands ran in the existing environment outside the Windows sandbox because
TestClient stalled inside it. UV_CACHE_DIR and PYTEST_DEBUG_TEMPROOT point to the
Tester evidence directory. This is not clean-machine validation.

`uv run ruff check .` — exit 0, stdout: `All checks passed!`, empty stderr.

`uv run pytest` — exit 1, empty stdout, stderr exactly:

```text
error: uv trampoline failed to canonicalize script path
```

`uv run python -m pytest` — exit 1; actual final summary:

```text
FAILED tests/test_tester_t3a_provenance.py::test_pdf_multiline_original_spans_across_pages
================== 1 failed, 112 passed, 1 warning in 5.89s ===================
```

Complete output, including every collected test file/count, full failure traceback and
Starlette warning, is preserved verbatim in:

- evidence/capture-20261008T085652/run-0.stdout.txt and run-0.stderr.txt
- evidence/capture-20261008T085652/run-1.stdout.txt and run-1.stderr.txt
- evidence/capture-20261008T085652/run-2.stdout.txt and run-2.stderr.txt
- evidence/capture-20261008T085652/runs.json (complete before/after identities and hashes)
- evidence/baseline-warning-probe.stdout.txt and baseline-warning-comparison.json
- evidence/t3a-final-identity.json (handoff product and target hash check)

Original fixture Markdown/PDF bytes, extracted blocks/entities/warnings, independently
captured PDF spans, database link/retrieval outputs, SQLite snapshots and API responses
are retained in evidence/t3a-synthetic-v2 and the timestamped evidence/t3a-synthetic-*
directories. Final full run uses the latest timestamped directory. The v2 directory also
has render-1.png and render-2.png; both pages were visually inspected. Poppler emitted
font lookup warnings for Symbol/ArialUnicode but the synthetic pages rendered legibly.

Earlier raw stdout/stderr, errors, miniature runs and partial sandbox runs remain in
evidence/ and this chat's tool transcript. evidence/capture-20261008T084433/runs.json
records an interrupted/stalled module run as running, not successful. The first pre-capture
buffered sandbox run lost its completion handle and has no final count; do not treat it
as a completed regression. The early API fixture failure was a Tester KeyError from the
wrong response key and was corrected from actual output; initial raw output remains in
evidence/t3a-unsandboxed.txt. No initial failure was presented as product acceptance.

## Protected evidence and remaining gaps

Protected acceptance location: **NOT PROVISIONED**. This shared repo evidence directory
contains synthetic/development material only and is NOT restricted to Tester/Supervisor/Sai.
No independent reviewer, second labeler, adjudicated corpus, protected custody or corpus
freeze exists. Real R1–R7 acceptance is BLOCKED, including semantic provenance and effort.
No confidence-supported independent claim is issued.

Still missing: protected product/input/output adapters; global acceptance orchestration;
reviewer-approved occurrence/merged-fact and natural-language revision matching; frozen
semantic sample identities and real second-rater evidence; local-model/prompt/embedding
artifacts and runtime isolation evidence; independent answer/citation/impact judgments;
registered real paired effort data; T5 permission/stale-approval matrix; clean-machine
uv/pytest launcher validation; disposition of the incidental nuisance warning.

No further product task was taken. Supervisor raw evidence spot-check and human custody
work remain required before any DONE or independent acceptance decision.
