# Portfolio and interview preparation

Use this after reading and practicing the code. Attribute Codex assistance and
describe only work you can explain. Avoid claiming sole authorship if the assistant
did the implementation, or claiming automotive validation from development tests.

## Project description

HLD Navigator is a local architecture-review assistant built with FastAPI,
Streamlit and SQLite. It extracts supported AUTOSAR HLD statements into proposals,
retains exact source provenance, controls approval/export by workspace role,
compares revisions and produces cited component/dependency reports. Optional
local BGE/Qwen services support embedding retrieval and experimental synthesis.

## Evidence to discuss

- An occurrence-specific citation rejects a sentence copied from the wrong page.
- A rejected provenance batch rolls back rather than partially approving facts.
- Source approval and fact approval are separate; unresolved warnings block export.
- A token revocation invalidates all workspace memberships while retaining history.
- SQLite backup uses the backup API to include committed WAL data consistently.
- Revision impact shows before/after declared edges and preserves alternative paths.
- 499 passing regressions are software checks, not a general OEM accuracy score.
- Real learned retrieval did not beat lexical ranking on the small measured set.
- A literal model citation can still support a wrong paraphrase: show A06/C05 in
  the retained final answer run and explain why human review remains necessary.

## Practice without the assistant

1. Run the isolated demo and explain one upload, review, query and export.
2. Trace those actions through `app.py`, extraction, store and report modules.
3. Calculate recall@5 and MRR from the recorded four-question retrieved rankings.
4. Explain the model contract, source-command quarantine and its false-positive risk.
5. Demonstrate a direction/type change, revocation and recovery to a new database.
6. Explain what independent OEM validation would require and what has not been done.

## Resume wording to personalize

"Developed and evaluated an AUTOSAR HLD review prototype with AI coding assistance,
using FastAPI, Streamlit and SQLite; supported source-linked architecture proposals,
governed review, revision impact analysis and cited reports. Verified local HTTP/UI,
OCR and optional model integrations, with 499 passing regressions and retained
failure evidence."

Adjust "developed" to your actual contribution and understanding. If you mainly
directed and reviewed AI-generated work, state that plainly. A strong interview
demonstration comes from explaining tradeoffs and failures, not inflating metrics.
