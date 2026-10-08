# T3c independent Tester handback

2026-10-08. **Scoped T3c PASS on exercised synthetic paths. Full-suite status FAIL.**
All existing checks remain unchanged. Overall acceptance/DONE requires Supervisor
adjudication; **not independently validated** R1–R7. No protected corpus was available.

## Identity and scope

HEAD: `3518d1b0eac2d74bae93ac529a0a105e2a912677`.
Product manifest SHA-256 before/after all four commands:
`fc234061fabe9f8bc297d97d17cf7ac57423f7f2aa1f23ea8343e978a05c2b5b`.
Tracked diff SHA-256:
`e89270ac5b87a5765aee04cf7587f7df6236b403cba0ce245461e1536c31dbb1`.
All 14 supplied product file hashes match; no product drift or Tester product edit.
Manifest bytes are sorted UTF-8 path/TAB/SHA256/LF lines including trailing LF.
prose.py SHA-256: `ae81e10ef9cbd295818df7feeebe7fdf09577a95bfd593d9ea01503e8978354a`.

New Tester-owned files only: tests/test_tester_t3c_captions.py,
tester_acceptance/capture_t3c.py, tester_acceptance/audit_t3c_remaining.py, this report
and timestamped synthetic/raw evidence. Existing Tester/Developer tests were not altered,
disabled, xfailed or skipped. No product, warning severity, export/coverage policy, frozen
target, corpus/label, model or environment artifact was changed. No Developer rationale
or tests were used as an oracle. No warning-granularity implementation task was taken.

## Per criterion

| Criterion | Verdict | Independent miniature evidence |
|---|---|---|
| 1 Caption labels not entities; source caption retained | PASS | 12 MD/TXT executions of 6 new captions cover component/interface/signal/port/flow/dependency headings and metadata. Only the two actual table components remain; caption text stays in source blocks. New PDF labels do not become entities. All previous caption entity-count failures are cleared. |
| 2 Real statements/attributes/contributing sources survive | PASS | 6 mixed text executions retain all 6 entity types, 7 expected facts, full payload/type/unit/owner/direction/interface/source/target/description attributes, and every exact original line contribution. Mixed caption heading/colon/sentence contexts retain real names. Four PDF cases retain the expected actual entities and all original row plus prose-page contributions. |
| 3 R2 warning safety and policy guards | PASS on exercised paths | All 32 cycle1 R2 checks pass. New real-plus-unknown/qualified PDF statements still warn on both pages. Unknown/qualified reviewed API documents still export HTTP 409; benign reviewed inventory exports HTTP 200. No unconditional relationship is invented from a qualified statement. |
| 4 Raw evidence/lifecycle and implementation scope | PASS for scoped behavior | All 9 T3a checks pass. New raw MD contributions and exact PDF rows/page/table/row match original inputs. API ingest/review/retrieval/export and DB reopen retain attributes/sources. Only prose.py changed since the preceding product candidate. No broad entity-kind filtering, post-hoc deletion or fuzzy source matching is in supplied change. Source-audit representation distinctions below remain explicit. |
| 5 Preserve checks and execute/report required commands | PASS for preservation/execution/reporting; full suite FAIL | Required commands were executed and all outputs/errors retained. New scoped tests: 25 pass. Full fallback: 2 fail, 290 pass. Both failures are retained oracle assumptions under the supplied contract allowing all contributing sources and correct page context; no existing assertion was changed. |

These PASS judgments apply to independently authored synthetic behavior only. They do
not satisfy independent corpus minima, semantic rater evidence or confidence gates.

## New fixture evidence

Captions include `Mission component inventory for release 14.2`, `Service interface
catalogue (revision r6)`, `Monitoring signal definitions (for version v3.1)`, mixed
component/interface/signal summary, port overview and flow/dependency index. Each caption
is retained as a block with its original text/line. It emits no label-derived entity.

Mixed heading/colon/sentence contexts preserve these explicitly authored facts:

- components Auriga/Boreal with table descriptions Processes requests/Receives requests;
- interface ControlBus with payload TorqueRequest;
- signal TorqueRequest with type uint16 and unit Nm;
- port ControlIn: owner Auriga, direction requires, interface ControlBus;
- dependency Auriga -> Boreal through ControlBus;
- flow TorqueCycle from Auriga to Boreal.

Every MD/TXT stored contribution is compared with its actual original line. Auriga retains
both its explicit statement and its table row, rather than deleting a real source to
match a table-only count.

New two-page PDFs use different captions/names/geometry from previous fixtures. Both
pages have a wrapped Auriga row with description `Processes requests` / `within limits`.
Independent crop coordinates derive from our authoring grid: (42,106,566,164). Exact row
text is `Auriga Processes requests\nwithin limits`, table 1 row 2 on each page. Variants
have no statement, a supported dependency, supported-plus-unknown predicate, or qualified
dependency. The expected real entities remain; captions do not generate Mission/Service
entities. All contributions to every extracted entity are recorded and checked, including
page context. Both pages of the supported-statement PDF were visually inspected.

New API outputs: benign source/entities approved -> export HTTP 200; unknown or qualified
source/entities approved -> export HTTP 409. Source/entity review, inventory, export and
reopened approved retrieval outputs are retained. No coverage override was signed.

## The two remaining failures: raw demonstration and oracle rationale

The unchanged function is test_new_pdf_captions_do_not_hide_real_statements in
tests/test_tester_t7a_captions.py. This task changes no assertion in that file.

**Unknown relationship PDF, line 143:** the source set for the actual Aster component is:

```text
(page 1, table null, row null)  original page prose context
(page 1, table 1, row 2)        exact original table row
(page 2, table null, row null)  original page prose context
(page 2, table 1, row 2)        exact original table row
```

The original page prose contains `Aster component arbitrates GateBudget.` It contributes
the real component mention while the unsupported predicate is warned. The table supplies
its supported description. All 4 source records were checked independently against
actual original page text and our table geometry. Table subset is precisely [(1,1,2),
(2,1,2)] and no wrong-location source is present. The old assertion sorts ALL locations
and assumes only table sources, raising exactly:

```text
TypeError: '<' not supported between instances of 'int' and 'NoneType'
```

Under the current requirement to retain every contributing prose and table source, the
extra two page references are required contributions. Their existence is not a product
defect. A table-only expected set is an invalid oracle for the complete source list.
The failing assertion remains intact; its failure is not converted to a green pytest run.

**Qualified relationship PDF, line 157:** the actual entity correctly has only the two
exact table sources. Qualified prose contributes no unconditional relationship/entity.
The blocking ambiguous_prose warning on each page contains the original qualified
sentence `Aster component may provide the IAct interface to Lumen.` plus its surrounding
page context, with the correct page. Independently extracted original PDF page text
contains that sentence at recorded character offsets. Both statements/warnings/pages
were checked; severity/category are correct and the statement is not missing.
The assertion requires warning.text to equal ONLY the isolated sentence. The supplied
contract permits correct original page context, so that equality is an oracle assumption,
not evidence of a missing warning or incorrect entity. It remains failing and unchanged.

The audit uses a strict Pydantic SourceCheck contract and retains every source, warning,
original page text, independently cropped row, location and representation classification.
For the unknown PDF there are 4 sources (2 rows + 2 page contexts); for the qualified PDF
there are 2 row sources. All source CONTENT and PAGE identity match. All 4 table quotes
are exact literal original row spans. Page context uses the existing extractor's line
joins and is not a literal newline-preserving substring of original page text. This is
explicitly recorded as false in literal_original_text_substring for the 2 prose contexts.
Content/location verification does NOT relabel those as exact raw row quotes or establish
a 100% mechanical-provenance acceptance metric. The broader original-span/representation
rubric remains an independent acceptance question; no repair or granularity work was
silently added. Within the supplied T3c context-allowed contract, the two pytest failures
are oracle assumptions and do not establish a remaining T3c product defect.

## Actual commands/output

Existing Windows environment outside sandbox due the previously demonstrated TestClient
stall. Python 3.14.8, pytest 9.1.1, anyio 4.15.1; not clean-machine validation.
UV_CACHE_DIR and PYTEST_DEBUG_TEMPROOT use Tester evidence directories.

`uv run ruff check .` — exit 0:

```text
All checks passed!
```

`uv run pytest` — exit 1, empty stdout, stderr:

```text
error: uv trampoline failed to canonicalize script path
```

`uv run python -m pytest` — exit 1:

```text
================== 2 failed, 290 passed, 1 warning in 9.36s ===================
```

`uv run python -m pytest tests/test_tester_t3c_captions.py -q` — exit 0:

```text
25 passed, 1 warning in 1.15s
```

Starlette TestClient/httpx deprecation warning is preserved. The 25-case scoped run
supplements the complete 292-case run; it does not erase its failures. Final full Ruff
after the new audit helper was added also passed. Tests were not changed after capture.
Tester-only lint wrapping and a postrun summary glob KeyError were corrected without
product/test-oracle changes; their raw errors remain in this chat. The KeyError came from
reading dictionary-form reopened JSON as a list; it was not a failed product API request.

## Raw evidence locations

`tester_acceptance/evidence/t3c-capture-20261008T102037/`:

- runs.json: exact commands, exit codes, complete before/after product manifests/diffs/hashes
- run-0.stdout.txt / stderr.txt: full lint output
- run-1.stdout.txt / stderr.txt: exact launcher failure
- run-2.stdout.txt / stderr.txt: all 292 checks, both complete failures and warning
- run-3.stdout.txt / stderr.txt: scoped 25-case run
- remaining-source-audit.json: strict structured original PDF/source/warning verification
- remaining-source-audit.stdout.txt / stderr.txt: 4-source/2-source demonstrations
- final-ruff.stdout.txt: final audit-helper lint
- artifact-hashes.json: initial capture/source/output byte hashes
- final-identity.json: final product hash and all previous Tester-test preservation checks
- final-evidence-hashes.json: final source/API/audit/render/report hashes

Full-run new fixtures:
`tester_acceptance/evidence/t3c-synthetic-20261008T102039362738/`.
Scoped-run new fixtures:
`tester_acceptance/evidence/t3c-synthetic-20261008T102049854457/`.
Both preserve exact MD/TXT/PDF bytes, complete extraction outputs, every PDF entity-source
audit, raw API decision/export bodies and reopened entity/retrieval data. The scoped
directory has render-real-1.png and render-real-2.png, visually inspected. Poppler's
Symbol/ArialUnicode font lookup warnings are preserved in the chat; content is legible.

The unchanged earlier test's original PDFs and outputs on this candidate are in
`tester_acceptance/evidence/t7a-synthetic-20261008T102039366252/`.
The remaining-source audit reads those exact files rather than candidate-provided source
claims. All previous candidate failures/evidence remain in their timestamped directories.

Protected acceptance evidence location is **NOT PROVISIONED**. Missing reviewer/labels/
custody/freeze still forbid independently validated R1–R7 claims. This assigned T3c
verification is complete; Supervisor must adjudicate the oracle findings before DONE.
No additional product task or assertion edit was performed.
