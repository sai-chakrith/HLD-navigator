# Ordered refresh: stopped at the demo check gate

## Git hygiene: done

The initial status, branch list and complete log are saved under
`docs/evidence/ordered-refresh/git-*.txt`. Local main matched origin/main. A live
remote query showed only main. There was no codex/hld-pilot branch to merge.
The existing untracked owner study guide was preserved in its own commit.

GitHub main is the default branch. Repository description and requested topics
were updated and read back: [metadata](evidence/ordered-refresh/repo-metadata.json).
README had no hardcoded user-specific paths, so no path replacement was necessary.

The pytest executable initially had a broken uv trampoline. Reinstalling the locked
pytest package repaired it, then exposed missing root imports for `tools`. Adding
the repository root to pytest's pythonpath made the exact requested command pass.
The frozen sync also removed the unlisted imageio-ffmpeg package from the local
environment; this is not a repository dependency change.

Step gate: **521 tests passed**, lint passed, formatting passed. Evidence:
[pytest](evidence/ordered-refresh/step-0-pytest-config.txt),
[lint](evidence/ordered-refresh/step-0-lint-config.txt),
[format](evidence/ordered-refresh/step-0-format-config.txt).
Failed launcher attempts are retained separately rather than overwritten.

## PDF demo: partial

Added `tools/demo.py --public-pdf` and the replay helper. The application replay
completed PDF ingestion, scripted scoped approvals, cited search, export and
comparison: [raw responses](evidence/ordered-refresh/pdf-demo/demo.json).
The public prose is repaginated KUKSA architecture content, not synthetic HLD prose.
The second revision is an explicitly illustrative name change. The inventory is
limited to component names and excludes edges/diagram interpretation.

The real UI displayed approved evidence, returned a cited search result, built
the export and compared the revisions. Screenshots and a short spoken script are
linked in [PDF_DEMO](PDF_DEMO.md). Browser automation timed out opening the upload
file chooser; the upload screenshot is an input screen. API-route PDF upload passed.
Fresh-clone execution has **not** been verified. Scripted review is not human review.

Step gate: **521 tests passed**, formatting passed, **lint failed** on the overlong
coverage-scope string in `tools/public_pdf_demo.py`. Evidence:
[pytest](evidence/ordered-refresh/step-1-pytest.txt),
[lint](evidence/ordered-refresh/step-1-lint.txt),
[format](evidence/ordered-refresh/step-1-format.txt).

The user's instruction says to stop if anything regresses. Work stopped at this
gate; the lint error is deliberately left visible. This is a work-in-progress demo
commit, not a claim that the requested acceptance checks pass.

## Remaining steps: blocked by the stop rule

- Answer path: no new controlled-case run, default change or STATUS update.
- Extraction number: no new untouched document selected, annotated or scored.
- README rewrite: not started.
- Module WALKTHROUGH: not started. The preserved study guide predates this request
  and is not a substitute for the requested module-by-module document.

No new precision/recall, model quality, CPU speed or independent validation claim
was added. No extraction code or evaluation corpus was changed. Existing historical
documentation was not fully audited for unsupported claims in this stopped run;
its older counts must not be interpreted as newly measured results.
