# T7a independent Tester handback

2026-10-08. Task T7a, requirement R2. **FAIL** on the first independent candidate run.
Original T3a caption blocker: **CLEARED**. All nine unchanged T3a checks pass.
Overall candidate acceptance remains blocked. **Not independently validated**: synthetic
fixtures only, no independent acceptance labels/corpus/reviewer/custody/freeze.
Supervisor controls the fix-cycle count; this report requests no additional product task.

## Identity and scope

HEAD `3518d1b0eac2d74bae93ac529a0a105e2a912677`.
Tracked candidate diff SHA-256:
`f9ef19757e8a32210a7b70241b803126ce3159b28b9fa96ab4ce4e7e338cb415`.
Product manifest SHA-256 before/after ALL three full-run commands:
`2f46de54c7ccc69aef2df21c07e4f2efe5faea30beee23d90c9e5fc1ffd5a475`.
Manifest bytes are sorted UTF-8 `path<TAB>SHA256<LF>` lines, including final LF.
All 14 product files match the supplied handoff; no product drift or Tester product edits.
Candidate prose.py SHA-256 is
`c5b26e51f7afbcb7829e5303cf96f3bd1061ab712c675aa81c6a46f5a5546290`.

All prior Tester tests and checks remain intact. In particular, the previously failing
T3a caption assertion was not changed, skipped or xfailed. Existing/Developer tests were
executed only as regressions, never read/copied as an independent oracle. No threshold,
product, environment/model artifact, corpus or holdout label was edited/downloaded.

New Tester-owned files only:

- tests/test_tester_t7a_captions.py
- tester_acceptance/capture_t7a.py
- tester_acceptance/assess_t7a.py
- this report and new synthetic/raw evidence under tester_acceptance/evidence/

## Per-criterion disposition

| Criterion | Verdict | Evidence/limits |
|---|---|---|
| 1 Benign captions; correct multi-page table evidence | FAIL | `for release 4` and `(release 4)` captions still get blocking unsupported_relationship/inventory warnings in MD and TXT. Targeted PDF table attributes and both exact row spans/locations are correct; strict total-entity counts expose separate caption-name extraction behavior. |
| 2 Real unsupported/qualified relationships remain blocking | PASS on exercised R2 behavior | Eight unknown/supported-then-unknown/near-caption/heading cases warn with original line text/location. Four negated/conditional/uncertain cases warn and emit no unconditional relationship. On both PDF pages, unknown/qualified warnings retain the actual source sentence and correct page. They contain page-wide surrounding text, not an isolated sentence; a stricter new assertion fails and remains retained. This is not blanket suppression or a missing warning. |
| 3 No magic prefix/blanket suppression/severity or policy weakening | PASS on supplied diff and exercised paths | Only noun/predicate-span recognition is added beyond T3a. No severity/export/threshold/model/rag/quote guard changes or parse-error catch is bundled. Unknown statements still block on table pages. Benign caption wording uses new Plant/Deployment/Subsystem/Platform names, not the earlier Tester string. |
| 4 Preserve tests and regression behavior | PASS for preservation/prior regression | All 141 checks present before these new Tester tests pass, including 9 T3a, 11 T2 and 28 new Developer caption regressions. Existing files were not edited; original caption failure is cleared. New Tester failures prevent an overall clean run. |
| 5 Exact lint/pytest/fallback and clean executable regression | FAIL | Ruff exit 0. Exact uv run pytest exit 1 at launcher. Module fallback executes 176 tests: 20 fail, 156 pass. Raw stdout/stderr/exit codes and stable product hashes are retained. |

PASS above is scoped synthetic behavior, not acceptance of R1–R7 or confidence-supported
R2 warning quality. There are nine distinct caption texts, each exercised in MD and TXT:
18 executions are format variants, NOT 18 independent reviewer-labeled statements.
No FDR/FNR/benign-rate acceptance estimate or frozen-corpus score is inferred from them.

## Actionable new synthetic reproductions

Both documents below are benign inventory captions followed by this ordinary table:

```text
| SWC Name | Responsibility |
|---|---|
|  Aster | Monitors pressure |
```

Reproduction A caption:

```text
Subsystem component inventory for release 4
```

Reproduction B caption:

```text
Platform component inventory (release 4)
```

In both MD and TXT, raw output contains:

```json
{
  "code": "unsupported_relationship",
  "severity": "blocking",
  "message": "Architecture relationship is not covered by the current extraction patterns",
  "unresolved_actions": ["inventory"]
}
```

Full warning text is the exact original caption, location line 1. Aster's raw table fact
and attributes are correct. After source and all proposed entities are approved, the API
for reproduction A still returns HTTP 409 on export:

```json
{"detail":"Unresolved extraction warnings: reviewer must assess coverage and explicitly sign the report scope"}
```

The colon/hyphen counterpart exports with HTTP 200. Export policy was not bypassed and no
coverage override was signed. The nuisance warning is the reproducible R2 defect.

## Other strict test failures and boundaries

The full run retains all 20 failures; none was removed to obtain a PASS:

- Sixteen MD/TXT checks stop at `len(entities) == 1`: captions such as `Plant component
  inventory - revision 7` also produce component Plant (or analogous heading name).
  The parser can interpret `Plant component` as a named component. This strict fixture
  invariant is broader than R2's action-warning criterion; this report does NOT request
  that the Developer delete noun extraction or count all sixteen as warning defects.
  Two actual unwanted-warning caption texts are separately confirmed from raw outputs.
- Two PDF checks stop at the same total-entity-count invariant. The target Aster table
  entity still has the expected normalized description and original row references on
  both pages. A separate retained-output assessment checks those table contributions
  against our authoring geometry and independently cropped original PDF text, without
  erasing any other entity or source record.
- One PDF qualified-warning check expects an isolated sentence. Actual blocking warning
  text includes the page caption/table and the exact original qualified sentence, with
  the correct page. This source-granularity limit remains recorded; it is not classified
  as an injection/abstention pass or independently validated warning provenance.
- One API export check fails with HTTP 409 for reproduction A above.

Assessment is diagnostic, not a replacement test suite: source/outputs, all strict
assertions and failing full-suite output are retained. The first assessment incorrectly
filtered the target entity by primary location.table, excluding a merged entity whose
primary source was prose. It printed false for table sources. The corrected assessment
locates Aster then checks its TABLE contributions while retaining the complete entity
and all prose sources. Initial/corrected assessment stdout are both preserved. This
does not convert broader page-wide prose provenance into exact row provenance.

## Raw commands and environment

Existing environment outside Windows sandbox, because TestClient previously stalled
inside it. Python 3.14.8, pytest 9.1.1, anyio 4.15.1; no clean-machine validation.
UV_CACHE_DIR points to Tester evidence/uv-cache; PYTEST_DEBUG_TEMPROOT points to this
capture directory. Raw runs.json retains before/after hashes and byte hashes for streams.

`uv run ruff check .` — exit 0, stdout exactly:

```text
All checks passed!
```

`uv run pytest` — exit 1, empty stdout, stderr exactly:

```text
error: uv trampoline failed to canonicalize script path
```

`uv run python -m pytest` — exit 1, actual final summary:

```text
================= 20 failed, 156 passed, 1 warning in 17.21s ==================
```

The entire unsanitized stdout contains all 176 collected checks, every failure traceback,
all failed case IDs, and the Starlette deprecation warning. It is in
evidence/t7a-capture-20261008T092604/run-2.stdout.txt; separate stderr is retained too.
No reported failure was hidden by a catch or threshold change.

Facet command:
`.venv\Scripts\python.exe tester_acceptance/assess_t7a.py tester_acceptance/evidence/t7a-synthetic-20261008T092610271621`.
Final facet output records 4 warning executions of 18 caption variants, 8 original
unsupported warnings, 4 original qualified warnings, and correct targeted PDF table spans.
All four PDF page/statement pairs independently map to the original source sentence.
These are synthetic raw counts, not independently validated rates.

Final assessment-only lint `uv run ruff check .` also passed. Tests were not changed after
the captured full run. PDF rendering used pdftoppm; both benign pages were visually
inspected. Poppler font lookup warnings for Symbol/ArialUnicode are retained in the chat
transcript; generated page content was legible.

## Evidence and custody

Raw capture:
`tester_acceptance/evidence/t7a-capture-20261008T092604/`:

- runs.json: exact commands, stream hashes, before/after product manifests/diffs/file hashes
- run-0.stdout.txt / run-0.stderr.txt: full lint output
- run-1.stdout.txt / run-1.stderr.txt: exact launcher result
- run-2.stdout.txt / run-2.stderr.txt: full executable regression and 20 failures
- assessment.stdout.txt: initial diagnostic error output
- assessment-v2.stdout.txt / assessment-final.stdout.txt: corrected diagnostics
- assessment-final-ruff.stdout.txt: final assessment lint
- synthetic-artifact-hashes.json: source/output byte hashes at initial run completion
- final-evidence-hashes.json: final source/warning/API/assessment/render/capture hashes
- final-identity.json: final product identity and unchanged prior Tester-test hash checks

Raw synthetic inputs/outputs:
`tester_acceptance/evidence/t7a-synthetic-20261008T092610271621/`:

- benign-0..8.md/.txt and their outputs.json: exact caption/table source and warnings/facts
- unsupported-0..7.md and outputs.json: near-caption/unknown/supported-then-unknown sources
- qualified-0..3.txt and outputs.json: original negated/conditional/uncertain sources
- multipage-benign/unknown/qualified.pdf and outputs.json: source PDF bytes and full outputs
- multipage-qualified.original-spans.json: independently cropped row evidence from test
- facet-assessment.json: original page/row text, stored table contributions, full target
  entities/prose sources, raw warnings and API results for all exercised facets
- api-0.json / api-7.json: raw upload/source-review/entity/review/export route bodies/statuses
- benign-render-1.png / benign-render-2.png: visually inspected original PDF pages

Protected acceptance evidence location is still **NOT PROVISIONED**. This shared directory
contains only synthetic/development evidence. No named independent acceptance reviewer,
adjudicated labels, verified protected custody or acceptance-corpus freeze has been supplied.
No fixed human target was changed and no independently validated R1–R7 claim is made.

T7a requires a Developer fix for the retained benign-modifier caption warning, then a new
identifiable READY_FOR_TEST handoff. No fix or additional product task was performed here.
