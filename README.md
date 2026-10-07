# ArchLens

Case Study 1: **AUTOSAR HLD Document Analysis Assistant**. A separate local repository from SpecProbe. This first slice provides controlled document ingestion, an evidence-backed architecture inventory, approved-source search, reviewer decisions, inventory revision comparison and JSON export.

## Run on Windows

Python 3.11+ and uv are required. Run from this repository:

```powershell
uv sync --frozen --extra dev
uv run python -m archlens.admin engineer --workspace pilot --role reviewer
# Copy the returned token privately; it is stored only as a hash.
uv run uvicorn archlens.app:app --host 127.0.0.1 --port 8010
```

In a second terminal:

```powershell
uv run streamlit run src/archlens/ui.py --server.port 8510 --server.address 127.0.0.1
```

Open [the UI](http://127.0.0.1:8510) and enter the token with workspace `pilot`. [API docs](http://127.0.0.1:8010/docs) describe all endpoints. The API refuses unauthenticated access to documents; viewer/editor/reviewer permissions are enforced server-side. The CLI is a trusted local operator interface and requires access to the database filesystem. Provisioning an existing user rotates their token across all memberships. Enterprise IAM, account revocation tooling and deployment hardening remain future work.

1. Upload `examples/powertrain.md` with a title and version.
2. Inspect warnings, then approve the source and each extracted entity as a reviewer.
3. Search a selected revision and inspect the cited page/section/line evidence.
4. Export the reviewed inventory and potential unresolved-reference findings.
5. Change the example signal type, upload version 2 with the same title, review it and compare inventories.

## Supported extraction template

Text PDFs, UTF-8 Markdown and TXT are supported; maximum 10 MB. Explicit declarations are recognized:

```text
Component: Engine | description=Computes torque
Signal: Torque | type=uint16 | unit=Nm
Interface: TorqueInterface | kind=sender_receiver | payload=Torque
Port: TorqueOut | owner=Engine | interface=TorqueInterface | direction=provides
Dependency: TorqueDisplay | source=Engine | target=Cluster | interface=TorqueInterface
Flow: DisplayTorque | source=Engine | target=Cluster
```

PDF tables use `Kind`, `Name` and supported attribute columns. Unknown/ambiguous tables and malformed declarations are reported, not converted into invented architecture. PDFs with a page containing no extractable text are blocked with an OCR requirement. Diagram-only architecture, arbitrary OEM tables, natural-language entity extraction and OCR are not yet implemented. PDF line numbers are extracted-text ordinals, not raw PDF source coordinates. Table page/table/row references and Markdown section/line references are preserved. Original bytes and SHA-256 are persisted.

## Search and local AI

The default uses SQLite FTS5 ranked lexical retrieval and returns exact approved source excerpts. It is **not embedding retrieval or a benchmarked AI answer model**. Entity approval controls reports; source approval controls source search. Evidence from proposed/rejected source statements can still appear when the containing source is approved, so citations are source evidence rather than approved design decisions.

Optional local Ollama integration:

```powershell
$env:ARCHLENS_OLLAMA_URL='http://127.0.0.1:11434'
$env:ARCHLENS_OLLAMA_MODEL='<installed model tag>'
# Restart the API with these variables.
```

The model must return exact source-supported quotes with citations. Unsupported claims abstain; unavailable configured models return 503. Quote support does not establish relevance or semantic correctness, and quoted source instructions remain untrusted content. Requests spanning multiple document versions require explicit revision selection. Local inference/learned embeddings and prompt-injection resilience still need model-level evaluation with approved HLDs.

## Checks and next steps

```powershell
uv run pytest -q
uv run python tools/smoke.py
uv run ruff check src tests tools
uv run ruff format --check src tests tools
```

[STATUS](STATUS.md) records implemented versus pending capabilities. [Validation procedure](docs/VALIDATION.md) defines genuine architect-reviewed evaluation and remaining dependencies. Do not interpret synthetic tests as OEM accuracy or measured productivity benefits. Use only a controlled local pilot until deployment acceptance.
