# T7a fix cycle 1: independent Tester handback

2026-10-08. **Scoped R2 caption-warning behavior: PASS on exercised synthetic cases.**
**Full executable regression: FAIL. Overall candidate acceptance: BLOCKED.**
All 9 unchanged T3a checks pass. This is **not independently validated** R1–R7 acceptance.
No protected corpus, reviewer, adjudicated labels, custody or corpus freeze is supplied.
No further product task or fix cycle is automatically assigned by this report.

## Candidate integrity

HEAD: `3518d1b0eac2d74bae93ac529a0a105e2a912677`.
Product manifest, before and after all four recorded commands:
`3829ac0a74ab3258f9f4664f33ef7d413cc8e592a0329c0066b1989481dcb585`.
Tracked candidate diff:
`169c423e9ca7e1cab127774985821f18fc4c6464f0c2ecdbbebd42089c388d54`.
All 14 supplied product hashes match. Manifest serialization is sorted UTF-8
`path<TAB>SHA256<LF>`, final LF included. No product drift occurred.
prose.py SHA-256:
`3540cdbb3d9ea56932cbf77f72e27d725732b56a48b6b30948d9774302383e6f`.

The prior T2, T3a and initial T7a Tester-test hashes match the preceding handback exactly.
None of their assertions, fixtures, skips or expected values was changed. Product files,
existing/Developer tests, fixed targets and corpus files were not edited. Developer test
code/rationale was not used as a verification oracle. No heldout labels were accessed.

New Tester-owned files: tests/test_tester_t7a_cycle1.py,
tester_acceptance/capture_t7a_cycle1.py, this report and timestamped synthetic/raw evidence.
The existing assessment script was executed against new outputs, without editing it.

## Criteria

| Criterion | Result | Evidence |
|---|---|---|
| 1 Benign captions and table evidence | PASS scoped R2 | Sixteen new MD/TXT executions of eight caption texts have no warnings. Release/version/revision, dotted/prefixed numeric values, parenthesized modifiers, optional `for`, and ordinary captions exercised. New two-page PDFs retain normalized target attributes and exact original row spans/page/table/row. Prior two failing caption texts also now have no warnings in MD/TXT. Strict total-entity findings remain separate below. |
| 2 Unsupported/unknown/qualified relationships | PASS on exercised behavior | Six new unsupported continuations/adjacent headings/supported-then-unknown clauses retain blocking warnings and original line text/location. Four negated/conditional/uncertain cases retain ambiguous_prose without unconditional relationships. Actual unknown/qualified statements on both PDF table pages still block with the original statement and correct page. |
| 3 No blanket suppression or policy weakening | PASS on supplied candidate and tests | Compared with the previous product manifest, only prose.py changed. Numeric nominal-modifier handling is added; unknown lowercase continuations are not swallowed. Export, severity, thresholds, extraction, models, store, rag and table bytes match the previous handoff. No parse-error hiding or model/environment task was bundled. Real unknown statement still causes export HTTP 409. |
| 4 Preserve checks and prior behavior | PASS for preservation and scoped regression | All nine T3a checks pass, including original caption reproduction; eleven T2 checks pass. Previously failing R2 reviewed export now passes. Prior test hashes are unchanged. All 19 retained whole-suite failures remain visible rather than being weakened or fixed outside this task. |
| 5 Commands and all-checks-green requirement | FAIL for whole suite | Ruff passes. Exact uv pytest launcher fails. Full module fallback: 19 failed, 223 passed. New scoped cycle1 suite: 32 passed. The whole suite does not satisfy the all-executable-checks-pass clause. |

The scoped R2 PASS does not claim that the whole T7a acceptance specification is satisfied
or authorize DONE. Supervisor must resolve the documented unrelated regression blockers.
It must not expand this fix into R1 caption-name extraction or PDF warning-granularity work
merely to force a green suite.

## Concrete source, warning and export evidence

New caption texts include:

```text
Fleet component inventory for release 12.7
Subsystem component inventory (release 4)
Runtime component catalogue version 2.5
Integration component table (revision r6)
Build component inventory (for version v8.2)
Package component definitions revision: 9
Operational component inventory for revision 7-2
Lab component inventory
```

Each is followed by the independently authored Lyrik SWC table. Their full warnings arrays
are empty in both MD and TXT. Two approved benign-caption API fixtures export with HTTP
200 and raw inventory/source outputs retained. No coverage override was used.

Adversarial examples include:

```text
Fleet component inventory for release 12.7 routes telemetry to Mistral.
Fleet component inventory (version v8.2) and arbitrates RateBudget.
Fleet component inventory (release 4) synchronizes Lyrik.
Fleet component inventory for release 12.7; Lyrik component provides the ILog interface to Mistral and arbitrates RateBudget.
```

These remain blocking. The supported dependency Lyrik -> Mistral via ILog is retained
where the source contains it; no dependency to RateBudget is invented. New heading-plus-
statement fixtures preserve original unsupported line 2. Qualified fixtures preserve their
original text/location and emit no dependency, port or interface from the qualified claim.

With `Build component inventory (for version v8.2)` plus
`Lyrik component arbitrates RateBudget.`, source/entity approval does NOT erase the warning;
the API still returns HTTP 409 on export. Raw route bodies/statuses are in api-4.json.
Benign api-0.json and api-1.json end in HTTP 200.

New PDFs have captions with `for release 12.7` and `(for version v8.2)`, an SWC Name/
Responsibility table and a wrapped Lyrik row. Normalized description is `Records events
within limits`; captured original row is `Lyrik Records events\nwithin limits`. The source
row on each page is table 1, row 2. Expected crop coordinates come from Tester authoring
geometry, not candidate-provided bounding boxes. Original page text, row crops and all
stored/prose contributions are retained. Both rendered benign pages were visually inspected.

Re-running the unchanged prior-output assessment on this candidate gives zero nuisance
caption warnings across 18 old format executions (nine caption texts). Prior bad-caption
reviewed API export is now HTTP 200. Old unknown/qualified warnings and table row spans
remain intact. These correlated format variants are not independent acceptance samples;
no warning FDR/FNR/benign-rate confidence claim is made.

## Preserved unrelated whole-suite failures

The 19 remaining failures are exactly:

- 16 strict MD/TXT total-entity-count assertions from the original T7a Tester file;
- 2 strict PDF total-entity-count assertions from that same file;
- 1 strict isolated-PDF-warning-sentence assertion from that same file.

Caption names such as Plant/Deployment still produce additional component/interface
proposals. PDF warnings still contain page-wide surrounding text with the actual sentence
and correct page instead of returning only the isolated sentence. These are retained
R1/source-granularity issues, NOT R2 warning misses. They have not been deleted, xfailed,
skipped, fixed or reclassified as successes. No test in tests/test_tester_t7a_cycle1.py fails.
The original T3a caption test passes without alteration, and the prior R2 API export
failure is cleared. New scoped tests supplement, rather than replace, the strict checks.

## Exact commands and actual output

Existing Windows environment outside sandbox due the documented TestClient stall there.
Python 3.14.8, pytest 9.1.1, anyio 4.15.1. No clean-machine validation or model download.
UV_CACHE_DIR points to Tester evidence/uv-cache, PYTEST_DEBUG_TEMPROOT to this capture.

`uv run ruff check .` — exit 0, stdout:

```text
All checks passed!
```

`uv run pytest` — exit 1, empty stdout, stderr:

```text
error: uv trampoline failed to canonicalize script path
```

`uv run python -m pytest` — exit 1; actual final summary:

```text
================= 19 failed, 223 passed, 1 warning in 11.15s ==================
```

`uv run python -m pytest tests/test_tester_t7a_cycle1.py -q` — exit 0:

```text
32 passed, 1 warning in 1.08s
```

Both full and scoped runs also retain the Starlette TestClient/httpx deprecation warning.
The scoped run was recorded explicitly to separate task evidence from retained unrelated
failures; it does not erase or supersede the full-suite result. Minor initial Tester-only
line-length lint errors were fixed before these runs; their raw output remains in the chat.

## Raw locations and hashes

Capture directory:
`tester_acceptance/evidence/t7a-cycle1-capture-20261008T095209/`:

- runs.json: all four commands, exit codes, before/after manifests, product/file hashes,
  actual tracked diff and byte hashes for stdout/stderr
- run-0.stdout.txt / run-0.stderr.txt: complete lint output
- run-1.stdout.txt / run-1.stderr.txt: exact launcher output
- run-2.stdout.txt / run-2.stderr.txt: all 242 collected cases, 19 full tracebacks/failure IDs
- run-3.stdout.txt / run-3.stderr.txt: complete scoped 32-case output
- prior-fixture-assessment.stdout.txt / stderr.txt: unchanged prior fixture diagnostic
- artifact-hashes.json: first complete command/source/output hashes
- final-identity.json: final product integrity and prior Tester-test preservation
- final-evidence-hashes.json: final raw evidence, source/warning/API/render/report hashes

Full-run cycle1 fixtures:
`tester_acceptance/evidence/t7a-cycle1-synthetic-20261008T095211628146/`.
Scoped-run cycle1 fixtures:
`tester_acceptance/evidence/t7a-cycle1-synthetic-20261008T095223943252/`.
Both retain exact source MD/TXT/PDF bytes, complete extracted blocks/entities/warnings,
original PDF page/row span records and raw API upload/review/inventory/export responses.
The scoped directory also has render-benign-1.png and render-benign-2.png. Poppler's
Symbol/ArialUnicode font lookup warnings are preserved in the chat; both pages are legible.

Unchanged prior T7a fixtures executed on the cycle1 candidate:
`tester_acceptance/evidence/t7a-synthetic-20261008T095211614236/`, including its
facet-assessment.json, old captions/warnings, original PDFs and API output now ending 200.
All prior failed-candidate raw evidence remains at its original timestamped location.

Protected acceptance evidence location: **NOT PROVISIONED**. No real holdout was used.
This handback is complete for the assigned scoped cycle1 verification; no further product
work or additional testing scope is taken automatically.
