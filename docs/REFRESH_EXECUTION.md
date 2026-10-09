# Ordered execution record

This run stopped at the Step 1 regression gate, as requested. The demo launcher
change is work in progress. It is not a passing release.

## Step 0: partial

Initial local history contained 20 commits, from `git-count.txt`; `git-log.txt`
records their identities. Local main matched origin/main and no local commits
were unpushed. Only local main and remote main existed. A live `git ls-remote`
query also returned only main. `origin/codex/hld-pilot` does not exist, so its
requested range query failed and there is no pilot branch to merge. Existing
origin/HEAD points to main; the earlier saved GitHub metadata also identifies
main as default. No new GitHub metadata read or default-branch mutation was made.

The only initial untracked file was the owner's PowerPoint lock file. It was
preserved and ignored, rather than committed as project work. Tracked-file and
history path checks found no `.data/`, `.env`, token-named files or SQLite
databases. These were path checks, not a full content-level secret audit.
Ignore rules now also cover environment variants, SQLite extensions, token files,
token directories and Office lock files. `.env.example` remains trackable.

The existing PDF helper lint failure was repaired. Commit `929c0f7` was pushed
to main with `git push --all origin`. README contains no hardcoded owner paths.

`gh` is not installed. The previous metadata snapshot already contains the
requested description/topics, but they were not updated or verified live here.
If manual entry is needed, use:

- Description: AUTOSAR HLD analysis assistant with cited extraction, human review,
  search, exports and revision comparison; FastAPI, Streamlit and optional local LLMs.
- Topics: autosar, rag, fastapi, streamlit, local-llm.
- Default branch: main.

Step gate: 521 tests passed; lint and formatting passed. Evidence is under
[refresh-20261009](evidence/refresh-20261009/), in `step-0-*.txt`.
The sandbox initially blocked uv cache access and GitHub DNS. Authorized
execution outside the sandbox allowed the checks and push.

## Step 1: partial, regression gate failed

`tools/demo.py` now selects the public PDF workflow by default; `--synthetic`
selects the old fictional regression demonstration. Existing `--public-pdf`
remains compatible. This launcher change has not passed lint/format validation.

Executed command:

```powershell
uv run python tools/demo.py --seed-only --database .data/refresh-public-demo.db --output docs/evidence/refresh-20261009/pdf-demo
```

The replay completed application-route PDF ingestion, scripted source-backed
component review, cited search, scoped export and revision comparison. Raw
responses and input hashes are in [demo.json](evidence/refresh-20261009/pdf-demo/demo.json).
The input is real pinned KUKSA prose repaginated as PDF, not an original OEM PDF.
The second revision is an illustrative rename. The replay deliberately excludes
relationships and diagrams from its manual review scope. It does not establish
parser completeness or independent human review. No extraction code, annotations
or data/evaluation files were changed.

The existing screenshots and spoken script are in [PDF_DEMO.md](PDF_DEMO.md).
They are historical captures, not new captures from this run. Fresh screenshots
were not captured before the failed gate. The historical upload capture is an
input screen; the browser file chooser previously timed out.

Step gate: 521 tests passed, but lint failed on the new overlong `--synthetic`
argument line and format check requested changes in `tools/demo.py`. Exact
failures are saved in `step-1-lint.txt` and `step-1-format.txt`; pytest output is
in `step-1-pytest.txt`. Implementation stopped without repairing this new
regression, in compliance with the stop rule.

## Steps 2 through 6: blocked by the stop rule

- Answer path: no new controlled-case run or UI/default change; STATUS unchanged.
- Extraction number: no new untouched holdout selected, annotated or evaluated.
- README rewrite: not performed.
- Owner module walkthrough: not written.
- Fresh clone: not performed; no new reproducibility conclusion is supported.

No new precision, recall, answer-quality, OCR-accuracy or performance claim is
made. Historical documentation was not comprehensively audited in this stopped
run. The README's existing test count refers to older evidence; this run's test
count is backed by the saved gate outputs. Independent validation, original-PDF
layout quality, complete extraction and fresh-clone success remain unestablished
by this run.
