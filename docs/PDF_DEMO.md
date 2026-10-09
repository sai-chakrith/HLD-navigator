# Public architecture PDF demo

From the repository root after `uv sync --frozen --extra dev`:

```sh
uv run python tools/demo.py --public-pdf --database .data/public-demo.db
```

Open the URL printed by the launcher. Stop both services with Ctrl+C. The isolated
database is retained; choose another `--database` for another run. To replay without
starting services, add `--seed-only`. Use `--output <directory>` to keep a separate
run. Never replace a retained evidence run just to obtain a nicer result.

The input is real public KUKSA architecture prose from the pinned source in
`data/evaluation/public/provenance.json`, licensed Apache-2.0. The command renders
the original Markdown literally into a text PDF; diagrams are retained as Markdown
references, not decoded. This is a repaginated engineering document, not an OEM
PDF or a layout/OCR benchmark. The second PDF contains an illustrative
Cloud Adapter to Telemetry Adapter rename, not an actual upstream revision.

The replay uses the application routes with an isolated FastAPI test client,
then launches the actual API and Streamlit UI against the resulting database.
Review is scripted and deliberately limited to manually proposed component names.
Automatic proposals are rejected as outside scope; relationships, protocols and
diagram contents are excluded. Scope approval does not certify completeness.
No parser code or evaluation labels are changed to make this demo work.

## Short spoken walkthrough

- Upload: “This is public vehicle architecture prose rendered as PDF. Ingestion
  preserves source bytes, hash and page evidence. The scripted upload response is
  saved with the run.”
- Review: “Select the public PDF or illustrative edit. Expand an approved component
  to see its exact source. These are scripted decisions; a real reviewer must
  verify every proposal and resolve the coverage warnings.”
- Search: “Search Cloud Adapter in the public revision or Telemetry Adapter in
  the illustrative revision. The result quotes approved facts with citations.”
- Export: “Build reviewed report. The export includes the explicit incomplete
  inventory scope and source-backed component reports.”
- Compare: “Select public-pdf as Before and illustrative-edit as After. The rename
  appears as removal and addition because entity identity uses kind and name.”

Saved application responses: [demo.json](evidence/ordered-refresh/pdf-demo/demo.json).
UI screenshots: [upload](screenshots/01-upload.jpg), [review](screenshots/02-review.jpg),
[search](screenshots/03-search.jpg), [export](screenshots/04-export.jpg),
[compare](screenshots/05-compare.jpg).

## Exact UI capture limitation

The in-app browser file chooser timed out while selecting the PDF through the
Upload control. The upload screenshot shows the input screen, not a completed UI
upload. PDF ingestion passed through the application upload route in the replay.
Review, search, report and comparison were then exercised in the actual UI. The
screenshots are static captures, not a live recording or evidence of human review.
