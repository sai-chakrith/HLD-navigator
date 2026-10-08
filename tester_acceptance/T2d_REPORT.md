# T2d Tester-only oracle correction report

**PASS for the authorized baseline repair.** The two archived Supervisor-approved proposals were applied exactly at the source-line level while preserving each file's existing newline style. No product file, fixture, parametrization, threshold, warning category/severity or protected data changed. This is synthetic regression evidence, not an independent R1-R7 or pilot-validation claim.

## Results

| Check | Result |
|---|---|
| Exact archived proposal application | PASS. All five edited files have the same source lines as their archived `.PROPOSED.txt` counterparts. Byte differences from proposal files are newline-style preservation only. |
| Structural scope | PASS. The AST audit reports only the five authorized top-level targets changed: three T2c helper nodes, one T2c test, one T3c test, one T7a test and two supplemental T3b1 tests. Function signatures and decorators are unchanged; every other top-level AST node is identical to its byte-exact pre-edit archive. |
| Ruff | PASS, exit 0. |
| Exact `uv run pytest` | BLOCKED, exit 1: `error: uv trampoline failed to canonicalize script path`. Raw stdout/stderr retained separately. |
| Directly affected complete files | PASS: **129 passed**, one existing Starlette deprecation warning, 5.36s. |
| Complete T3a/T7a/T3c/T3b1 plus T2c files | PASS: **196 passed**, one existing warning, 7.14s. |
| Full module fallback | PASS: **412 passed**, one existing warning, 14.76s. |
| Product identity | PASS. Every before/after command identity and the final audit match manifest `86b4a75690c00f850a5713a00754a25b0e6ac59d8c535dfc58d24a89575bf76e` with no mismatches. |

The repaired oracles now require literal independently extracted page text, including newlines, for PDF page-context contributors and warnings. The old joined representation is retained as a negative control and must fail literal validation. Exact table-row checks remain unchanged. Wrong page/row, altered table quote, omitted/extra contributor, altered/missing qualifier, wrong warning category/severity/context and real unsupported prose remain negative cases. All those controls passed in the scoped and full runs.

The supplemental characterization now compares the independently extracted PDF representation rather than authoring-time glyph spacing. It permits removal only of the demonstrated false `Receives` table-responsibility warning while preserving every genuine unsupported predicate and qualifier blocker. Detected and undetected table-boundary probes, repeated-page identities, mixed prose/table contributors, lifecycle/query/export/reopen checks, MD/TXT evidence and earlier T3a/T7a/T3c safety cases all pass.

## Evidence

- `tester_acceptance/evidence/t2d-oracle-correction-20261008T153500/` contains byte-exact before/after copies, `applied-oracle.diff`, `application-audit.json`, the reproducible AST/exact-proposal audit and final evidence hashes.
- `tester_acceptance/evidence/t2d-capture-20261008T154352/` contains `runs.json`, complete stdout/stderr for all five commands, exit codes, stream hashes and product/target identities before and after each command.
- `tester_acceptance/evidence/t3b1-fix1-review/` retains the two authorized proposed diffs and independent source proof used by the Supervisor.
- Prior negative baselines remain intact: `t3b1-baseline-20261008T105907` (**4 failed, 332 passed**), `t3b1-first-scoped.stdout.txt` (**8 failed, 16 passed**), `t3b1-fix1-baseline-20261008T151907` (**12 failed, 374 passed**) and `t3b1-fix1-scoped-20261008T152134` (**12 failed, 400 passed** full run before this correction). These records are not overwritten or relabeled.

The current green baseline establishes only that the authorized synthetic oracle correction matches the new literal-source contract and does not regress the covered engineering behavior. Repeated-page non-table persistence lineage, legacy re-ingestion/quarantine, independent corpus custody and frozen acceptance remain outside T2d.
