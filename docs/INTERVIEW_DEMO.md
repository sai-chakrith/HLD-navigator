# HLD Navigator interview walkthrough

Run from the repository root with the existing virtual environment:

```powershell
.venv/Scripts/python.exe tools/demo.py
```

Open http://127.0.0.1:8511. In the sidebar set API to
http://127.0.0.1:8011, workspace to `demo`, and enter the private token printed
in your terminal. The launcher creates `.data/interview-demo.db` and refuses to
overwrite it. For another fresh demonstration use `--database .data/demo-2.db`.
Ctrl+C stops the services and retains the database. Models are disabled for this
self-contained workflow; the optional local model setup is documented separately.

## Five-minute demonstration

1. Select **Synthetic Powertrain · v1** in Review. Explain that every entity keeps
   literal evidence and a source location. The fictional demo fixtures are seeded
   as approved for demonstration; they are not real engineering sign-offs.
2. Search that revision for `TorqueInterface`. Open the cited evidence. Explain
   the difference between retrieved source excerpts and synthesized model answers.
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
