# HLD Navigator

Current verification: **499 passing tests**; actual HTTP/browser workflow, local
Qwen 7B synthesis, BGE retrieval and Tesseract integration executed. See
[completion report](docs/submission/COMPLETION_REPORT.md) for artifacts and limits.
The default answers remain cited source excerpts; optional synthesized claims need
review and still have documented semantic failures.

For a repeatable interview demonstration, run `python tools/demo.py` using the
project virtual environment. It creates an isolated demo database with two fictional
reviewed revisions and one public document for manual review. See
[the walkthrough](docs/INTERVIEW_DEMO.md).

Case Study 1: AUTOSAR HLD Document Analysis Assistant. Ingest supported ordinary prose and tables, review extracted components/interfaces/signals/ports/dependencies/flows, search cited facts and compare architecture revisions. This remains an engineering pilot; broad OEM document quality and learned-model performance are not established.

## Launch

Python 3.11+ and uv. Existing users/tokens/database survive the additive schema update. Do not provision an existing user again unless you intend to rotate their token. Back up `.data/hld_navigator.db` before upgrading, then restart API/UI.

```powershell
cd C:\Users\peddi\Downloads\chakrithdump\HLD-navigator
uv sync --frozen --extra dev
# First use only: provision a reviewer and save the returned token privately.
uv run python -m hld_navigator.admin engineer --workspace pilot --role reviewer
uv run uvicorn hld_navigator.app:app --host 127.0.0.1 --port 8010
```

Second terminal:

```powershell
cd C:\Users\peddi\Downloads\chakrithdump\HLD-navigator
uv run streamlit run src/hld_navigator/ui.py --server.port 8510 --server.address 127.0.0.1
```

Open [UI](http://127.0.0.1:8510), workspace `pilot`, your individual token. [API](http://127.0.0.1:8010/docs). Viewers read/query; editors ingest/annotate/index; reviewers decide source/entity/coverage approval. The local operator CLI requires trusted filesystem access. Enterprise IAM, TLS, credential lifecycle and managed deployment remain pending.

Reviewed exports include a dependency graph, cited component reports, declared
incoming/outgoing relationships, ports and candidate inconsistencies. Revision
comparison includes additions and before/after evidence for declared impact paths
up to two hops, retaining alternate paths while excluding cycles.

## Backup and recovery

The local operator can take a consistent SQLite snapshot while the API runs:

```powershell
python -m hld_navigator.backup backup .data/hld_navigator.db .data/backups/pilot-2026-10-09.db
python -m hld_navigator.backup restore .data/backups/pilot-2026-10-09.db .data/restored-pilot.db
```

Both commands refuse to replace an existing destination. The tool uses SQLite's
backup API, checks integrity and foreign keys, and prints the snapshot SHA256.
After stopping the API, set `HLD_NAVIGATOR_DB` to the restored database and restart.
Snapshots contain documents and authentication hashes; keep them private.

Revoke an individual's access across all workspaces without deleting audit history:

```powershell
python -m hld_navigator.admin engineer --revoke
```

Provisioning that individual again issues a new token; old tokens stay invalid.

## Demonstration without rewriting the HLD

1. Upload `data/evaluation/torque-prose.md`, a synthetic development document written in ordinary sentences. The older `examples/powertrain.md` declaration format remains supported.
2. Inspect entities and all contributing source references. Approve the source and each proposal. Correct misses directly from selected source evidence; manual proposals require review.
3. Search `TorqueInterface` using Approved extracted facts. Unreviewed, rejected and edited-original statements are excluded. The separate Source statements scope labels disputed/unreviewed evidence and abstains from presenting it as approved design facts.
4. Export the reviewed inventory. Empty inventories and unresolved blocking warnings fail with HTTP 409. Reviewers can sign an explicit scoped report after corrections or documented exclusions; this is not a completeness certificate. Further source/entity decisions invalidate that scope.
5. Change the consumer port to `provides` in a new revision to demonstrate a provider/consumer mismatch. Change the signal type and compare revisions to see possible impact paths with source edge IDs.

## Extraction and OCR boundaries

PDF, UTF-8 Markdown/TXT, maximum 10 MB. Supported affirmative prose includes named components, interfaces carrying signals, signal types/units, named providing/requiring ports, producer-to-consumer links and named flows. Wrapped PDF prose is combined while retaining page references. Negation, uncertainty, unsupported relationships and conflicts require review. This is a conservative pattern parser, not universal natural-language understanding or an evaluated LLM extractor.

PDF/Markdown tables recognize aliases including SWC Name/Responsibility and Port Name/Component/Interface/Port Kind, title rows and repeated headers. P-Port/R-Port normalize to provides/requires. Unknown populated columns produce warnings. Original bytes/hash and contributing page/table/row or section/line references are retained. PDF line ordinals describe extracted text, not raw file offsets.

Blank PDF pages without graphical content are skipped. Nontext graphical/image pages require OCR; diagram topology is not inferred. Optional local Tesseract:

```powershell
$env:HLD_NAVIGATOR_OCR='1'
$env:HLD_NAVIGATOR_TESSERACT='C:\path\to\tesseract.exe'
# Restart API, then ingest the scanned PDF.
```

OCR retains page/line origin and minimum word confidence and creates a blocking review warning. The adapter was tested with controlled TSV responses and image rendering. A genuine Tesseract/OEM scan run was unavailable. Confidence is not a calibrated correctness probability. General OEM layouts and diagrams remain unvalidated.

## Local embeddings and answers

Default: SQLite FTS5 lexical baseline and full source-block excerpts. Optional learned embeddings use local Ollama `/api/embed`; vectors and content/model fingerprints persist in SQLite with exhaustive cosine ranking. This custom local vector store is a small-pilot implementation, not FAISS/Chroma or a scalable ANN index. No synthetic/hash vectors replace a configured model.

Configure an installed embedding model and exact `/api/tags` digest:

```powershell
$env:HLD_NAVIGATOR_OLLAMA_URL='http://127.0.0.1:11434'
$env:HLD_NAVIGATOR_EMBED_MODEL='<installed embedding model:tag>'
$env:HLD_NAVIGATOR_EMBED_DIGEST='<digest from /api/tags>'
# Optional answer model:
$env:HLD_NAVIGATOR_OLLAMA_MODEL='<installed answer model:tag>'
```

Restart the API and use Index this revision in Review. Configured embedding retrieval requires a complete index; failure leaves previous vectors intact. Artifact drift, invalid vectors and dimension mismatch are rejected. The embedding endpoint must be loopback. Oversized model inputs error instead of silently truncating. [Ollama API reference](https://github.com/ollama/ollama/blob/main/docs/openapi.yaml).

Answer models must quote entire retrieved blocks with citations. Cropping negation or qualifiers fails support checks. This rejects fragments and paraphrases; it does not establish semantic entailment or relevance. Empty evidence and invalid quote output abstain; mixed revisions require selection; configured model failures are explicit. Ollama remains unavailable. A verified llama.cpp CPU backend and real BGE benchmark are now available; independent model usefulness remains unproven. See the local validation instructions below.

## Reproduce checks and evaluation

```powershell
uv run pytest -q --junitxml=docs/evidence/pytest.xml
uv run python tools/smoke.py
uv run python tools/evaluate.py --models
uv run ruff check src tests tools
uv run ruff format --check src tests tools
```

The manifest freezes file hashes and field annotations. Reports separate extraction precision/recall, missed/incorrect facts, correction actions, lexical/embedding recall@5/MRR and full-block quote support. Measured correction minutes and human semantic groundedness remain null. The included corpus is development data, not an independently reviewed holdout. Supply `--manifest <approved-manifest.json> --output <report.json>` for external evaluation; never tune on that holdout afterward.

[STATUS](STATUS.md) and [validation record](docs/VALIDATION.md) distinguish local checks from external acceptance.

The CI workflow runs lint, regression tests and the live HTTP smoke workflow on
Windows and Linux. Local verification does not establish that hosted CI has run.
Two additional pinned public KUKSA documents and their license are under
`data/evaluation/public/additional/`; `tools/fetch_public_documents.py` verifies
their recorded hashes when reproducing the fetch. These are developer examples,
not proprietary OEM HLDs or an independent holdout.

The second review and reproducible failure cases are tracked in [REVIEW_ACCEPTANCE](docs/REVIEW_ACCEPTANCE.md). Conditional statements are blocked for interpretation; they never become unconditional edges. The mixed prose/table revision demonstration is in `examples/revision-review/`. Evaluation reports include separate, initially unscored semantic review fields; model citation correctness is not answer quality.

[Local model and unfamiliar-document validation](docs/LOCAL_MODEL_VALIDATION.md) reproduces pinned CPU artifact setup, actual learned retrieval and controlled answer checks. The [architecture reviewer packet](docs/reviewer-packet/INSTRUCTIONS.md) contains blank independent annotation and correction-time records. Recipient lists retain every named peer, and scientific unit expressions retain exponents, multiplication and spacing. Public baseline misses and nuisance warnings remain visible.

The actual Qwen CPU run failed the controlled answer contract and expected raw abstention cases. It is not enabled by default or accepted for pilot answers. See `docs/evidence/local-model.json` and the separate relevance/contradiction assessment in `docs/evidence/local-model-assessment.json`. Real model execution does not imply suitable model behavior.
