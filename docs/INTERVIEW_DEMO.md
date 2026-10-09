# HLD Navigator interview walkthrough

Run from the repository root with the existing virtual environment:

```powershell
uv sync --frozen --extra dev
uv run python tools/demo.py
```

Open http://127.0.0.1:8511. In the sidebar set API to
http://127.0.0.1:8011, workspace to `demo`, and enter the private token printed
in your terminal. The launcher creates `.data/interview-demo.db` and refuses to
overwrite it. For another fresh demonstration use `--database .data/demo-2.db`.
Ctrl+C stops the services and retains the database. Models are disabled for this
self-contained workflow; the optional local model setup is documented separately.

## Seven-minute live demonstration (recording still required)

1. Select **Synthetic Powertrain · v1** in Review. Explain that every entity keeps
   literal evidence and a source location. The fictional demo fixtures are seeded
   as approved for demonstration; they are not real engineering sign-offs.
2. Search that revision for `TorqueInterface`. Open the cited evidence. Explain
   the difference between reviewed fields, unreviewed original context and synthesized claims.
3. In Report / Compare, export **Synthetic Powertrain · v1**. Show the dependency
   graph and the Engine component report, including incoming/outgoing relationships
   and cited ports. Download the complete JSON inventory.
4. Export **Synthetic Powertrain · v2**. Show the candidate port-direction and
   data-type mismatches. Compare v1 against v2 and trace the before/after impact
   evidence. Impact analysis follows declared paths up to two hops; it does not
   simulate ECU behavior.
5. Select **Public KUKSA Architecture** in Review. This source remains unapproved.
   Show the warnings and correction workflow. Explain why unreviewed public
   architecture is excluded from approved answers and exports.

## What to be ready to explain

- Trace an upload from FastAPI through extraction and the SQLite transaction.
- Explain occurrence-level provenance: identical text on two pages is two sources.
- Explain workspace authorization and why a source approval does not approve its facts.
- Compare lexical retrieval with learned embedding retrieval using the retained results.
- Explain why a literal citation can still support an incorrect paraphrase.
- Explain backup consistency when SQLite has a WAL file, and demonstrate restoration.
- Describe limitations accurately: unfamiliar phrasing, diagram topology, real OEM
  generalization and human usefulness remain unproven by synthetic tests.

## Portfolio wording to adapt after practicing

"Implemented an AUTOSAR HLD review assistant with FastAPI, Streamlit and SQLite,
supporting source-linked architecture inventories, controlled human review,
workspace access control, cited retrieval, revision comparison and dependency
visualization. Added recovery tooling and regression coverage for provenance,
review-state enforcement, architecture mismatches and change-impact paths."

Use wording that matches your own contribution and understanding. Do not claim
measured time savings, production deployment, OEM accuracy or independent
architecture validation without supporting evidence. Follow the supplied
AI-assistance declaration when submitting the project.

## Timed real-time recording script

Record continuous system behavior with your screen recorder for 5–10 minutes.
The old still-image sequence is a historical visual backup and does not meet this requirement.
This environment exposes browser snapshots but no authorized continuous screen-recording
API; a compliant recording is an outstanding student action, not a completed deliverable.

- 0:00–1:00: launch a fresh demo database and identify revision/source provenance.
- 1:00–2:30: upload `examples/review-granularity.md`; approve source and only Torque.
  Ask `What ASIL does Engine have?` in facts mode: show abstention. Switch to source
  mode: show unreviewed context containing Engine ASIL D.
- 2:30–3:30: ask `What type and unit does Torque have?`; show deterministic approved
  fields and separately labeled original context. Explain the review boundary.
- 3:30–4:30: reject/edit a proposal and show stale text is excluded; show export blocker.
- 4:30–5:30: review the seeded v1 inventory, graph, export and revision impact.
- 5:30–7:00: explain one public parser miss, synthetic label limits and the synthesis
  false-unit check. Explain that general semantic correctness is not guaranteed.

Do not record bearer tokens or other personal desktop content. Student narration and
code-ownership explanations must be your own. Do not substitute this script for the recording.
