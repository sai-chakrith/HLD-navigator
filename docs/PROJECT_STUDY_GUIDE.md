# HLD Navigator: complete project study guide

Based on the repository at commit `01820a9`, inspected on 9 October 2026. This guide describes the current implementation. Recorded test/model results below are existing repository evidence, not new runs performed while writing these notes.

**How to use this guide:** first read sections 1–6 to understand the product and architecture. Then trace the worked example and code in sections 7–16. Finish with the exercises and interview answers. Your goal is to explain each important behavior and find the function that implements it.

Design rationale is distinguished from history: statements labeled **engineering rationale** explain why a choice fits this project; they are not claims that a formal alternatives study or a particular personal decision took place. The evolution section uses actual Git history and retained failure records.

## 1. The project in one sentence

HLD Navigator is a local engineering review assistant that converts supported architecture documents into **source-linked architecture proposals**, lets people correct and approve them, and uses the reviewed inventory for cited search, consistency checks, reports, and revision comparison.

A useful 30-second explanation:

> Engineers need to understand components, interfaces, signals and dependencies scattered across high-level design documents. HLD Navigator extracts supported statements from PDFs, Markdown and text, preserves their exact evidence and location, and asks a reviewer to approve the source and the proposed facts separately. It then provides cited retrieval, component reports, dependency graphs and revision impact paths. FastAPI handles the workflow, Streamlit provides the interface and SQLite stores documents, review state, search data and audit events. Local embeddings and answer synthesis are optional; cited excerpts are the default.

Three distinctions run through the entire project:

1. A document statement is not automatically an approved architecture fact.
2. An exact citation is not automatically proof that an answer is correct.
3. Passing software tests is not automatically proof of accuracy on unfamiliar automotive documents.

## 2. What problem are we trying to solve?

Imagine you receive two large HLD revisions. You need to answer:

- Which components exist and what do they do?
- Who provides an interface and who consumes it?
- Which signal travels through it, with what type and unit?
- Are endpoint ports compatible?
- What changed between revisions?
- Which declared downstream relationships deserve investigation after a change?
- Where exactly does the document support each answer?

Manual reading requires repeatedly searching prose and tables, maintaining a mental dependency map, checking revisions and verifying citations. A plain keyword search gives passages but does not create a reviewed architecture inventory. An unconstrained chatbot may produce a plausible answer while reversing a relationship, merging revisions or omitting a condition.

The project's response is to make document interpretation **structured, traceable and reviewable**. It assists the engineer; the engineer remains responsible for interpretation and decisions.

The intended benefit is easier navigation and review. Actual time savings have not been measured, so describe that as the motivation rather than a demonstrated result.

## 3. Domain concepts you need

These definitions explain the vocabulary used by this pilot. They do not describe the entire AUTOSAR standard.

- **HLD — high-level design:** a document describing major parts of a system, responsibilities and relationships.
- **AUTOSAR:** the automotive software architecture context of this case study. The application recognizes a small set of relevant concepts; it does not implement or certify the full standard.
- **Component / SWC:** a named software unit, such as `EngineControl`.
- **Interface:** a named communication contract, such as `TorqueInterface`.
- **Signal:** a named item of data, such as `Torque`, with attributes such as `type=uint16` and `unit=Nm`.
- **Port:** a named connection point owned by a component and associated with an interface. In this project its direction is `provides` or `requires`.
- **P-Port / R-Port:** table aliases normalized by the parser to `provides` / `requires`.
- **Dependency:** a declared source-to-target relationship, optionally associated with an interface.
- **Flow:** a named source-to-target flow. The analysis code uses dependencies and flows as directed graph edges.
- **Revision:** a separately stored version of a document. A workspace/title/version combination must be unique.
- **Proposal:** a parsed or manually entered entity awaiting a review decision.
- **Provenance:** the link from a proposed fact to the original document, literal extracted text and a specific source occurrence.
- **Coverage review:** a reviewer records the accepted report scope and treatment of warnings. This is not proof that every requirement was extracted.
- **RAG — retrieval-augmented generation:** retrieve evidence first, then provide that evidence to an answer model. This project also supports retrieval without generation.
- **Embedding:** a model-generated numeric representation of text, used to rank passages by similarity.
- **Abstention:** a response that declines to assert an answer when usable evidence or a valid model response is absent.

Remember the direction convention: for a declared `EngineControl -> InstrumentCluster` relationship, the expected source port provides the interface and the expected target port requires it.

## 4. What architecture are we using?

The best description is a **local, layered Python application with a modular backend**, a separate UI process and optional local inference services.

The FastAPI backend is a modular monolith: its parsing, storage, review, retrieval and analysis modules run within one application. Running Streamlit and a local model server as separate processes does not make the project a microservices architecture.

```text
Engineer in browser
        |
        v
Streamlit UI: upload / review / search / report / compare
        |
        | HTTP + individual bearer token + workspace
        v
FastAPI backend (app.py)
        |
        +--> Extraction: extraction.py, prose.py, tables.py, ocr.py
        |
        +--> Storage and review: store.py, models.py
        |          |
        |          v
        |        SQLite
        |        originals + blocks + entities + evidence links
        |        review state + audit + FTS5 + optional embeddings
        |
        +--> Retrieval: store.search() OR store.vector_search()
        |          |
        |          v
        |        rag.answer()
        |        default: cited source excerpts
        |        optional: local synthesis + citation validation
        |
        +--> Analysis/reporting: analysis.py, reports.py

Optional local processes:
  Tesseract for image-only pages
  Ollama or llama.cpp for learned embeddings / synthesized answers
```

There are several layers of responsibility:

1. **Presentation:** `ui.py` collects inputs and displays API results.
2. **Application workflow:** `app.py` enforces roles and coordinates upload, review, query, export and comparison.
3. **Domain processing:** parsers interpret supported statements; analysis checks inventories and compares revisions.
4. **Persistence:** `Store` manages SQLite transactions, provenance links, review state and retrieval eligibility.
5. **Adapters:** PDF extraction, OCR and local model transport connect the application to external tools.

This separation is useful but not a strict framework-enforced clean architecture. For example, retrieval eligibility and vector persistence live together in `Store`, and the embedding module reuses transport safeguards from `rag.py`.

## 5. Why these choices fit the project

### FastAPI and Pydantic

**Implemented:** FastAPI provides typed HTTP routes; Pydantic models validate requests, locations, entities and answer contracts. Many models use strict validation and forbid extra fields.

**Engineering rationale:** the review workflow needs explicit operations and predictable request shapes. Validation catches malformed data before it reaches persistence. An API also makes the UI replaceable and allows automated integration tests.

**Trade-off:** valid JSON can still encode a false interpretation. Type validation establishes shape, not engineering truth.

### Streamlit

**Implemented:** a Python UI with Upload, Review, Search and Report / Compare tabs, communicating with the API using `requests`.

**Engineering rationale:** it provides a quick interface for document inspection, forms, JSON results and graph display without maintaining a separate JavaScript frontend.

**Trade-off:** the interface is a pilot workflow. A more complex multiuser product may benefit from a dedicated frontend and different interaction model.

### SQLite, FTS5 and direct SQL

**Implemented:** one local database stores originals, evidence, entities, roles, review decisions, audit events, FTS5 search rows and optional vectors. Python's `sqlite3` is used directly; there is no ORM or separate vector database.

**Engineering rationale:** one database keeps deployment small and allows related records to be committed or rolled back together. It also makes an isolated demo and local backup practical.

**Trade-off:** this does not establish large-scale concurrent performance. Vector ranking is exhaustive, and broad enterprise operation would need qualification. Direct SQL keeps queries visible but makes `store.py` a substantial module to maintain.

### Conservative patterns instead of LLM extraction

**Implemented:** explicit declaration parsing, regular-expression prose patterns and table header aliases. The optional answer model is not the extraction engine.

**Engineering rationale:** supported patterns are reproducible, auditable and easy to test against negation, qualifiers and unsupported clauses. Failures can become visible warnings instead of silently accepted architecture assertions.

**Trade-off:** unfamiliar wording, naming conventions and layouts cause misses. The finite warning vocabulary cannot guarantee that every unsupported statement is detected.

### Human review and evidence preservation

**Implemented:** source approval, entity review, manual evidence-backed proposals, coverage sign-off and export gates.

**Engineering rationale:** a recognizer proposes an interpretation; an engineer decides whether it is suitable for the inventory. Literal evidence allows inspection and correction.

**Trade-off:** review costs effort and may still miss errors. A person clicking approve is not an independent completeness assessment.

### Local inference, optional embeddings and excerpt defaults

**Implemented:** model endpoints must be loopback; learned retrieval and synthesis can be enabled independently. Without an answer model, the application returns source blocks with citations.

**Engineering rationale:** local services fit sensitive engineering documents and avoid requiring cloud inference for the basic workflow. Excerpts offer an inspectable baseline. Embeddings need to earn their place through measurement.

**Evidence:** the retained four-question BGE run did not outperform lexical retrieval: both had recall@5 of 0.75, while lexical MRR was 0.75 versus 0.625 for embeddings. This supports retaining the simpler default for the tested setup, not a universal claim that lexical retrieval is superior.

### Declared graphs and bounded impact paths

**Implemented:** graphs are built from approved dependency/flow entities; impact traversal follows at most two edges.

**Engineering rationale:** declared edges provide traceable paths. A bounded traversal makes results inspectable and limits graph expansion.

**Trade-off:** two hops can omit more distant consequences. Paths express possible investigation targets, not simulated behavior or safety analysis.

## 6. How the project reached this approach

This is a reconstruction from commit subjects and retained validation notes, not an invented account of who made each decision.

1. **Initial review pilot — `c7a2e0a`.** The project began as ArchLens, an AUTOSAR HLD review pilot. Explicit declarations remain supported, for example `Signal: Torque | type=uint16 | unit=Nm`.
2. **Rename — `c31ec1a`.** The project/package became HLD Navigator.
3. **Ordinary prose, review fixes and local vectors — `cbf6aed`.** The workflow expanded beyond custom declarations to supported prose and tables, while tightening review behavior and adding local learned retrieval.
4. **Compound statements and visible gaps — `4fc8908`.** Failures showed that extracting one relationship could hide later unsupported clauses. The parser and warning behavior were improved, with limitations retained.
5. **Recipients, units and real model experiments — `954600e`.** Multiple peers and compound unit expressions needed preservation. Public documents and actual local model execution exposed weaknesses that synthetic checks alone did not show.
6. **Exact extraction evidence — `37d262f`.** Interpretation and citation were separated more carefully: normalization may assist parsing, but evidence must retain captured text. PDF page context and table row boundaries became important.
7. **Occurrence-specific provenance — `7e90273`.** Literal text alone was insufficient when the same sentence appeared on different pages. Exact text plus canonical location and persistent block links became an enforced boundary, with quarantine and legacy handling.
8. **Reports, impact paths and inference safeguards — `2e6ce6b`.** Reviewed component reports, graph exports, before/after paths and local inference safeguards were developed further.
9. **Recorded public/OCR/answer runs — `3ac3c91`.** Actual integrations and several answer candidates were evaluated. Earlier failures remain retained alongside the final development run.
10. **Submission package and handoff — `01820a9`.** Source, evidence, reports, presentation and demo artifacts were packaged.

The design lesson is that successive defects shaped the trust boundary: **parse proposals, preserve evidence, review facts, control retrieval eligibility, validate citations, and separately assess semantics**.

Do not memorize earlier documentation as the current behavior. The README still contains older OCR/model and whole-block answer descriptions. `docs/pdf-prose-provenance.md` also retains an earlier text-only persistence limitation that the newer occurrence validation addresses. Use current code and the latest sections of `STATUS.md`, `docs/VALIDATION.md`, `docs/provenance-integrity.md` and `docs/s1b-local-answers.md` together.

## 7. Worked example: Torque communication

Start with `data/evaluation/torque-prose.md`. It is a synthetic fixture, not an OEM document.

```text
The EngineControl component provides the TorqueInterface interface
to the InstrumentCluster component.
The TorqueInterface interface carries the Torque signal.
The Torque signal has type uint16 and unit Nm.
The EngineControl component provides the TorqueInterface interface
through port TorqueOut.
The InstrumentCluster component requires the TorqueInterface interface
through port TorqueIn.
The TorqueDelivery flow runs from the EngineControl component
to the InstrumentCluster component.
```

In the actual Markdown fixture, each sentence is on one line. The wrapping above is only for reading this guide; Markdown prose parsing operates line by line.

After parsing and merging, this fixture yields eight proposals:

- Component `EngineControl`.
- Component `InstrumentCluster`.
- Interface `TorqueInterface`, with `payload=Torque`.
- Signal `Torque`, with `type=uint16`, `unit=Nm`.
- Port `TorqueOut`, owned by EngineControl, providing TorqueInterface.
- Port `TorqueIn`, owned by InstrumentCluster, requiring TorqueInterface.
- Dependency `EngineControl->InstrumentCluster:TorqueInterface`.
- Flow `TorqueDelivery`, from EngineControl to InstrumentCluster.

The interface and components appear in several sentences. Merging combines compatible attributes and retains contributing sources rather than discarding earlier evidence.

The review sequence is:

1. Upload the file with a title and new version.
2. Inspect warnings and contributing evidence.
3. Approve the document source as reviewer.
4. Review each entity proposal, correcting or rejecting errors.
5. Resolve the export scope if blocking warnings remain.
6. Search within that revision and export the reviewed report.

For “What type and unit does the Torque signal use?”, default retrieval should return the eligible signal source sentence with its citation metadata. A configured local answer model may synthesize “Torque uses uint16 and Nm,” but that claim must carry a literal supporting snippet and must still be assessed for semantic correctness.

Try the negative counterexample: `EngineControl does not provide TorqueInterface to InstrumentCluster.` The prose parser must not convert that into an affirmative dependency. It emits an interpretation warning for recognized negated architecture language.

## 8. Upload: trace one request through the system

Read `app.py:create_app()` and its nested `upload()` function, then `extraction.py:extract()` and `store.py:Store.ingest()`.

1. Streamlit submits a multipart file, document title and version to `POST /workspaces/{workspace}/documents`.
2. `authorize()` checks the bearer token's workspace membership and requires editor rank or higher.
3. The API rejects blank title/version values and reads at most 10 MB plus one byte to detect an oversized upload.
4. `extract()` chooses PDF, UTF-8 Markdown or TXT handling from the suffix.
5. Extraction returns three collections: source `blocks`, entity proposals and `warnings`.
6. `Store.ingest()` strictly validates all blocks and every proposal's source occurrence before writing.
7. A SQLite transaction inserts the original bytes and SHA256, blocks, FTS rows, proposals, evidence links and upload audit event.
8. Stored lineage is checked again before commit.
9. The API returns the document ID, proposal count and warnings.

**Important failure behavior:** duplicate workspace/title/version produces HTTP 409. Provenance validation or relevant persistence failures roll back candidate records and preserve the original upload as a quarantined document with diagnostics. Invalid extraction normally produces HTTP 422. Oversized uploads produce HTTP 413.

Upload work is performed in the request path. There is no durable task queue or asynchronous ingestion job system in this implementation. Large-file or model throughput should therefore be evaluated before extending the pilot.

## 9. How extraction works

### A. Explicit declarations

`parse_line()` recognizes declarations beginning with `Component:`, `Interface:`, `Signal:`, `Port:`, `Dependency:` or `Flow:`.

```text
Port: TorqueOut | owner=EngineControl | interface=TorqueInterface | direction=provides
```

It checks permitted attributes, required attributes, repeated keys, empty values and port direction. This is a predictable input format, but ordinary documents should not need to be rewritten into it for the supported prose/table cases.

### B. Prose patterns

`prose.py` recognizes selected constructions for named components, interfaces, signal payloads/types/units, named ports, relationships and flows.

Supported examples include:

- `EngineControl is a component.`
- `EngineControl provides TorqueInterface interface to InstrumentCluster.`
- `TorqueInterface interface carries Torque signal.`
- `Torque signal has type uint16 and unit Nm.`
- `EngineControl provides TorqueInterface interface through port TorqueOut.`

Negation, uncertainty and conditions such as `not`, `may`, `if`, `unless` or `when` trigger conservative handling for recognized architecture statements. They must not become unconditional edges. Recognized actions outside supported grammar produce warnings; inventory captions are treated carefully to avoid inventing entities from headings.

The naming pattern generally expects a capitalized identifier. This is one concrete reason unfamiliar writing can be missed.

### C. Tables

`tables.py:table_lines()` finds recognized headers, handles aliases, infers entity kind where possible, and turns supported rows into declarations for parsing.

It recognizes examples such as `SWC Name`, `Responsibility`, `Port Name`, `Component`, `Interface`, `Port Kind` and `Data Type`. It skips repeated headers and handles title rows within its bounded header search. Unknown populated columns, ambiguous headers and inconsistent widths generate warnings.

The generated declaration is an interpretation aid. It is not the quotation. Markdown evidence retains the original row line; PDF evidence is captured from the actual row region.

### D. PDF handling

For a text PDF, `pdfplumber` supplies text and detected tables. Wrapped page prose is normalized for interpretation, but prose evidence retains the complete original extracted page text and a page location.

Detected table characters are excluded from prose interpretation by coordinates. Otherwise a responsibility cell could accidentally become an independent relationship. Table rows use page/table/row evidence.

The quoted page is extracted text, not the PDF's binary bytes. It can include unrelated context. PDF line ordinals refer to extracted text lines, not byte offsets.

### E. OCR

Blank pages without graphical content are skipped with an informational warning. Image/graphical pages without usable text require opt-in Tesseract OCR.

`ocr.py:page_ocr()` renders a page, invokes local Tesseract with TSV output, groups words into lines and assigns each line the minimum word confidence. The location records page, line, OCR origin and confidence. Every OCR page gets a blocking review warning.

OCR recognizes text; it does not infer arrows or diagram topology. The real seven-page OCR run confirms integration, not HLD transcription accuracy.

### F. Merging

`merge_entities()` groups proposals by `(kind, name)`. Compatible attributes are combined with contributing sources. Conflicting attributes produce a blocking warning and retain distinct interpretations instead of silently selecting a winner.

## 10. Data model and provenance

The schema is in `Store.__init__()`. Current schema version is **3**.

The main records are:

- `users`: individual IDs and token hashes.
- `memberships`: user/workspace/role assignments.
- `documents`: title/version/workspace, filename, original BLOB, SHA256, warnings, source approval and provenance status.
- `blocks`: literal text, location JSON and document ID.
- `entities`: kind/name, current attributes, original attributes, primary evidence/location and review status.
- `entity_evidence`: many-to-many links between entities and contributing source blocks.
- `search`: FTS5 index of block text.
- `audit`: actor, action, target, details and timestamp.
- `coverage_reviews`: scope/reason/actor bound to a snapshot fingerprint.
- `embeddings`: block/model identity, text fingerprint and serialized vector.

Relationships to remember:

```text
User -> memberships -> workspace access
Document -> many Blocks
Document -> many Entities
Entity <-> Blocks through entity_evidence
Block -> FTS search row and optional model-specific vector
Document -> coverage review for a particular snapshot
Actions -> audit events
```

### Why source occurrences matter

Suppose the same sentence appears on pages 2 and 8. String equality does not identify which occurrence supports a proposal.

The current ingestion key is **literal text + canonical validated location**, resolved within the candidate document. After storage, a persistent block ID identifies that occurrence. Links must remain in the same document and workspace context.

Accepted location forms include PDF page context, PDF page/line, Markdown line/optional section, PDF page/table/row, Markdown line/table/row and OCR page/line/confidence.

Unknown fields, missing coordinates, impossible combinations and nonresolving evidence are rejected. `Store._validate_batch()` checks input; `_lineage_issues()` checks stored relationships; `_assert_document_verified()` enforces the boundary during protected operations.

### Verified, legacy and quarantined

- **verified:** mechanically validated provenance, eligible for normal lifecycle checks.
- **legacy_unverified:** historical records retained without a current provenance certificate; governed re-ingestion and fresh review are required.
- **quarantined:** invalid lineage or a rejected persistence batch; original source remains for investigation, but approved use is blocked.

“Verified” means verified lineage, not verified architecture accuracy. The SHA256 establishes a file identity/check, not source truth or a digital signature.

## 11. Review and export: the central trust boundary

Document approval and entity approval answer different questions:

- **Source approval:** is this source acceptable for this review workflow?
- **Entity approval:** is this particular interpreted fact acceptable, including any correction?

Entities start as `proposed` and a reviewer sets `approved` or `rejected`. A reviewer can update permitted attributes with a reason. `original_attributes` remain stored, so the system knows that the original source statement was edited.

An editor can add a manual proposal from a selected evidence block. The block must belong to the document/workspace and the entity name must occur in its text. The declaration is validated and the proposal still requires reviewer approval. This is a mechanical evidence check, not proof that every manually entered attribute is entailed.

### Export conditions

`app.py:export()` requires:

1. The document exists in the authorized workspace.
2. Provenance is verified and passes the stored-lineage check.
3. The source document is approved.
4. No entity remains `proposed`.
5. At least one entity is approved.
6. If noninformational extraction warnings remain, a current coverage review exists.

Rejected proposals can remain in history; they do not appear in the approved export.

### Coverage scope and invalidation

The fingerprint binds source hash, warnings and entity IDs/statuses/attributes. Coverage review records a specific scope and reason. Later source/entity decisions or manual proposals invalidate coverage; a mismatch also prevents retrieving the earlier signature as current.

This prevents an old scope from silently authorizing a changed inventory. It does not make the inventory complete, and it does not mean all warnings are automatically solved.

Architecture findings are reported as candidates. Export is not conditional on the absence of every reported type/direction finding; extraction and review gates are a separate mechanism.

## 12. How search and answers work

The query route first authorizes workspace access, chooses a retrieval method, checks source/revision conditions and then calls `rag.answer()`.

### Eligibility is more important than ranking

`Store.eligible_blocks()` decides which blocks may be used as facts:

- Documents must have verified provenance and, for normal queries, source approval.
- An eligible fact block must link to approved entities with unchanged original attributes.
- Any rejected or edited interpretation makes the block disputed.
- Proposed links or no reviewed links leave it unreviewed unless the implemented state rules classify otherwise.

Block-level filtering matters. If several proposals share a PDF page-context block, one disputed interpretation can exclude that whole block from fact retrieval. This preserves the conservative trust boundary but can reduce recall.

**Correction subtlety:** an edited, approved entity can appear in an export. Its original source block is not automatically promoted as an approved statement of the corrected attributes. Search retrieves source text, not newly fabricated text representing the correction.

### Lexical retrieval

`Store.search()` tokenizes the question, removes a small stop-word set, builds an OR query from at most 30 unique words and asks FTS5 to rank candidates with BM25.

The SQL selects approved, verified document candidates and fetches up to 100. The function applies `eligible_blocks()` filtering and returns up to five results. Thus ranking does not bypass the review boundary, although eligibility filtering after a bounded candidate fetch can miss lower-ranked eligible blocks.

### Optional embedding retrieval

`configured_embedder()` selects the configured local backend. `index_vectors()` computes source-block embeddings in batches of 16, validates the complete vector collection, then writes it transactionally. Model calls finish before persistence, so model failures preserve the previous index.

`vector_search()` embeds the query, selects currently eligible blocks, requires model-matching and text-fingerprint-matching vectors, computes cosine similarity exhaustively and returns up to five results.

```text
cosine(q, d) = dot(q, d) / (length(q) * length(d))
```

The adapters reject invalid counts, inconsistent dimensions, nonfinite values and zero vectors. They check configured artifact identity. The BGE llama.cpp adapter also checks input length rather than silently truncating oversized blocks.

No automatic lexical/embedding hybrid is implemented. Configuration chooses one method. This is a custom SQLite vector store, not FAISS, Chroma or an ANN index.

### Source scope versus fact scope

The default question scope is `facts`. `source` allows disputed/unreviewed block states from the approved source documents searched by the normal query path. If retrieved evidence is not all approved facts, the API returns `source_review_required` and shows evidence without presenting it as approved design facts.

The review UI's source-block endpoint can inspect verified documents without source approval; that inspection path is different from normal question retrieval.

### Revision selection

If no document ID is selected and retrieved evidence includes more than one title/version, the API returns `revision_selection_required`. Choose a revision before asking for one architecture answer.

This check applies to returned evidence; it is not a general automatic reconciliation of every revision in the workspace.

### Default answers

With no answer model configured, `rag.answer()` returns complete retrieved block excerpts with numbered citations and accompanying evidence metadata. It does not invent a natural-language summary. With embedding retrieval, the API labels the excerpt mode accordingly.

### Optional synthesized answers

The current model returns strict JSON containing `status`, `claims` and `reason`. Each claim includes natural-language text and citations with request-local IDs such as `S1` and literal snippets.

`filter_answer()` checks the response shape, source IDs, resolvable block IDs and exact substring matches. It returns persistent block IDs alongside accepted citations. It rejects citations to text removed by source-command quarantine.

Conflict responses need at least two distinct cited alternatives. This enforces a contract shape; it does not independently detect that sources contradict.

The old `supported()` helper checks whole-block quote equality and is retained for baseline/adjudication. It is not the current synthesized-claim validator. The two contracts must not be confused.

### Why citations are insufficient

Source: `EngineControl provides TorqueInterface to InstrumentCluster.`

Wrong claim: `InstrumentCluster provides TorqueInterface to EngineControl.`

The wrong claim could cite an exact substring from the real source and pass mechanical citation checks. Relationship direction, relevance, omissions, negation and entailment require separate semantic assessment.

No evidence causes abstention. Invalid contracts/snippets cause explicit abstention reasons. A configured model transport failure produces a reason that the API exposes as HTTP 503. A configured failure is not silently presented as successful model output.

## 13. Architecture findings, reports and comparison

### Findings

`analysis.py:findings()` checks approved inventory data for:

- Conflicting definitions with the same kind/name but different attributes.
- Unresolved references to components, interfaces or payload signals.
- Declared relationships lacking endpoint port metadata.
- Source/target port direction mismatches.
- Endpoint port type mismatches.
- Port types inconsistent with an interface or its payload signal type.

These are candidate review findings. An unresolved reference could be an external component or a missed extraction. Type comparisons are explicit string comparisons, not a full type system or compatibility proof.

### Reports

`reports.py:architecture_report()` creates a dependency map, DOT graph and per-component reports with owned ports, incoming relationships, outgoing relationships and citations. Graph nodes/labels are escaped using JSON string encoding. The graph reflects declared dependency/flow entities, not inferred diagram geometry.

### Revision comparison

The comparison route exports both inventories first, so both must satisfy export gates. They must share a document title.

`compare()` matches entities by `(kind, name)` and reports additions, removals and changed attribute dictionaries. Duplicate kind/name definitions must be resolved before comparison.

Consequences:

- A name change generally appears as remove/add; there is no explicit rename detector.
- A change only in evidence text/location, with unchanged attributes, is not an attribute change.
- This is structured inventory comparison, not an arbitrary document text diff.

### Impact paths

`impact_paths()` chooses starting components from the changed entity:

- Component change: start at that component.
- Port change: start at its owner.
- Interface change: find associated ports/edge sources.
- Signal change: find interfaces carrying that signal, then associated owners/edge sources.
- Dependency/flow change: include the changed edge's source.

It follows outgoing declared dependency/flow edges for at most two hops, preserving alternative paths. A node already on the current path is skipped to stop cycles. Results include trigger, node path, edge IDs and before/after revision basis.

Removed/changed facts are investigated in the before inventory; added/changed facts in the after inventory. This matters when an edge is rerouted or newly introduced.

### Concrete revision exercise

Read `examples/revision-review/v1.md` and `v2.md`:

- `TorqueIn` changes from `uint16` to `uint32`, while the provider remains `uint16` and the Torque payload is `uint16`.
- `BrakeIn` changes from R-Port to P-Port on the declared `ABS -> Engine` BrakeInterface relationship.

Expect endpoint type and payload/interface type candidates for Torque, plus a direction candidate for Brake. These files do not change the Torque signal type itself; inspect the actual changed entity before explaining the impact.

## 14. Access control and local operation

`admin.py` provisions an individual user/workspace role. `Store.provision()` creates a random bearer token and stores its SHA256 hash. Reprovisioning the same user rotates the token across memberships. `revoke()` invalidates access without deleting history.

Roles are hierarchical:

- **Viewer:** read, query, export and compare when data gates pass.
- **Editor:** viewer capabilities plus upload, manual proposals and indexing.
- **Reviewer:** editor capabilities plus source/entity decisions and coverage review.

Authorization belongs to the API. Hiding a UI button is not an authorization control. Workspace checks and occurrence validation prevent selecting another workspace's records as evidence through the supported API.

Missing bearer authorization produces HTTP 401; invalid workspace membership or insufficient rank produces HTTP 403. HTTP 409 usually means a state conflict or unmet lifecycle prerequisite. HTTP 422 indicates malformed/unsupported input, and HTTP 503 indicates unavailable/failed configured model operations.

Local inference transport rejects nonloopback destinations and external redirects and bypasses environment proxies. Obvious assistant-directed source lines are excluded from model prompts/citations while originals remain stored. This heuristic can miss attacks or remove legitimate content; it is defense in depth, not a comprehensive classifier.

The audit log is useful history, not tamper-resistant storage. A trusted filesystem operator can alter the database. Enterprise identity integration, TLS deployment, monitoring and load qualification remain future work.

## 15. Backup and recovery

`backup.py:snapshot()` uses SQLite's backup API rather than blindly copying a live database file. This gives a consistent database snapshot, including committed state when a journal/WAL is involved. The application itself does not explicitly turn on WAL mode in `Store.connection()`.

The utility exclusively creates a new destination, verifies database integrity and foreign keys, and returns a SHA256 and schema version. Backup and restore refuse to overwrite an existing destination.

Restore to a new path. Stop the API, set `HLD_NAVIGATOR_DB` to the restored file and restart. Keep snapshots private: they contain original documents and authentication hashes.

## 16. Code reading map

Read in this order rather than trying to read the entire repository linearly:

1. **`models.py`:** entity kinds, locations, review requests and answer contract. Learn which invalid shapes are rejected.
2. **`app.py`:** API routes, role checks and workflow gates. Trace upload, query, export and compare.
3. **`extraction.py`:** format dispatch and source preservation.
4. **`prose.py`:** supported grammar, qualifiers, unmatched actions and merging.
5. **`tables.py`:** header aliases, direction normalization and interpretation values.
6. **`store.py`:** schema, transaction boundaries, occurrence validation, review state, eligibility and fingerprints. Read one method at a time.
7. **`rag.py`:** excerpt baseline, prompt construction, source-command quarantine, local generation and citation validation.
8. **`vectors.py`:** adapters, artifact identities, vector validation and cosine similarity.
9. **`analysis.py`:** findings, structured diff and bounded graph traversal.
10. **`reports.py`, then `ui.py`:** how approved data becomes reports and an interactive workflow.
11. **`admin.py`, `backup.py`, `tools/demo.py`:** how to operate and demonstrate the project.
12. **Tests and evidence:** see how failure behavior is specified and what remains unproven.

Useful test files:

- `tests/test_pilot.py`: lifecycle, roles, versions and persistence.
- `tests/test_review_regressions.py`: negation, blank PDFs, disputed facts and export blockers.
- `tests/test_engineering.py`: coverage invalidation, corrections, tables, vectors and architecture checks.
- `tests/test_developer_provenance_integrity.py`: wrong locations, cross-document links, rollback, quarantine and legacy handling.
- `tests/test_developer_pdf_table_prose_boundary.py`: detected tables must not become prose assertions.
- `tests/test_recipients_units.py`: complete recipient lists and units.
- `tests/test_impact_revision_paths.py`: alternatives, cycles and before/after edge evidence.
- `tests/test_s1b_contract.py`, `tests/test_generation_quarantine.py`: strict model output and source-command handling.
- `tests/test_backup.py`, `tests/test_access_revocation.py`: recovery and access lifecycle.

## 17. Run and study safely in an isolated demo

Run commands from the repository root. Setup requires installed Python/uv; initial dependency or model provisioning can require network access.

```powershell
uv sync --frozen --extra dev
uv run python tools/demo.py --database .data/study-demo-1.db
```

Use a new database filename if it already exists. The launcher refuses to overwrite an existing demo database. It prints a private token; enter it in the sidebar rather than putting it in notes or screenshots.

Open `http://127.0.0.1:8511`; set API to `http://127.0.0.1:8011` and workspace to `demo`. The synthetic revisions are preapproved for demonstration, and the public source remains unapproved. Models are disabled in this self-contained demo.

Practice this sequence:

1. Inspect Synthetic Powertrain v1's entities and citations.
2. Search `TorqueInterface` within v1.
3. Export v1 and explain its graph and component report.
4. Export v2 and explain each candidate mismatch.
5. Compare v1/v2 and trace a before/after impact path using its edge IDs.
6. Show why the unreviewed public source cannot be exported.
7. Upload the Torque prose fixture as a new study document and perform the review yourself.

Ctrl+C stops the launched services and retains the database.

For normal separate API/UI operation, follow `README.md`. For optional real local models, follow `docs/LOCAL_MODEL_VALIDATION.md` and `docs/s1b-local-answers.md`; do not assume demo configuration enables them.

Verification commands for your own later practice:

```powershell
uv run pytest -q
uv run ruff check src tests tools
uv run python tools/smoke.py
```

`tools/smoke.py` launches an isolated real HTTP workflow. Unlike merely calling functions in a unit test, it exercises transport and application integration. It still is not an OEM accuracy benchmark.

## 18. Evaluation: understand the numbers

Separate five questions:

1. Does the implementation follow its software contract?
2. Does extraction find the correct entities and attributes?
3. Does retrieval return useful evidence?
4. Does a model produce valid citations?
5. Does the answer actually convey the correct, complete meaning?

### Extraction

- **True positive:** an expected fact was correctly extracted under the evaluator's matching rules.
- **False positive:** an extracted fact is not in the reference annotations.
- **False negative:** an expected fact was missed.
- **Precision:** `TP / (TP + FP)`.
- **Recall:** `TP / (TP + FN)`.

If ten expected facts yield eight correct facts and two incorrect extractions, precision is `8/10 = 0.8` and recall is `8/10 = 0.8`. These example counts are illustrative, not this project's benchmark.

Field-level labels, warning accounting and correction actions provide different information. Edit counts are not correction minutes. Reference labels need independent validation before strong accuracy claims.

### Retrieval

In the project's selected question benchmark, recall@5 reflects whether expected evidence appears among the first five results. MRR averages reciprocal ranks of the first expected evidence, with zero for a miss.

For first-hit ranks `1, 1, 2, missing`, MRR is `(1 + 1 + 0.5 + 0) / 4 = 0.625`, and three of four questions have evidence within five results. This arithmetic illustrates how the reported embedding values can arise; consult raw reports for actual per-question ranks.

### Recorded current evidence

The latest repository records report:

- **499 passing tests** and passing lint at the recorded completion check.
- Actual HTTP/browser upload, review, graph, compare and export-blocker workflows.
- **BGE:** four selected public questions; recall@5 0.75 for both methods; MRR 0.75 lexical and 0.625 embedding.
- **Qwen 7B final development run:** 29/30 raw contract passes, 8/8 required abstentions, no instruction-following judged in five injection cases. Useful-complete judgments were 8/12 answerable, 3/5 conflicts and 4/5 injection cases.
- Wrong recipient and unsupported revision recommendation claims remained semantic failures despite valid literal citations.
- **Tesseract:** seven image-only instruction pages, 312 OCR blocks and seven mandatory page-review warnings.
- **Three-document public extraction baseline:** 18 missed facts and one unexpected fact against selected provisional agent labels; this is not exhaustive independent ground truth.

The cases were used during development and judgments were developer/assistant assessments, not independent architect acceptance. Do not convert 29/30 contract passes into “96.7% answer accuracy.” The denominator measures a different property.

The CI configuration runs lint, tests and HTTP smoke on Windows/Linux, but the repository completion record does not establish observed hosted CI execution.

## 19. Known limitations and reasonable next improvements

Know the limits before proposing more features:

- Pattern extraction misses unfamiliar prose and unsupported naming/layout conventions.
- Detected-table separation depends on PDF table detection; undetected tables remain a boundary.
- No automatic diagram topology interpretation.
- Page-context evidence preserves qualifiers but can be broad, noisy and too long for configured embedding context.
- Review-state filtering can reduce retrieval coverage, especially on shared blocks and corrected attributes.
- Exact citations do not establish relevance, entailment or contradiction detection.
- Prompt-injection quarantine is heuristic and incomplete.
- Comparison uses kind/name identity; renames and variants are not comprehensively modeled.
- Impact analysis stops after two declared edges and does not simulate a vehicle system.
- No measured human correction-time or productivity benefit.
- No independently annotated authorized OEM holdout establishing generalization.
- No enterprise deployment/load or safety/AUTOSAR conformance qualification.

A defensible improvement order:

1. Freeze an authorized unfamiliar-document holdout by family, with independent architect labels.
2. Measure extraction errors, warning usefulness and actual reviewer correction time.
3. Design smaller evidence spans/chunks without losing qualifiers or occurrence identity; evaluate retrieval again.
4. Improve supported prose/table coverage against development data, retaining negative and conditional cases.
5. Evaluate semantic answer usefulness, conflicts and injections separately from citation validity.
6. Add explicit rename/variant handling and diagram annotation workflows where justified.
7. Qualify concurrency, identity/TLS, monitoring and recovery before a managed deployment.

Changing database or adding a bigger model should follow a measured need. Neither automatically solves document interpretation.

## 20. Interview and viva questions with answer outlines

**What architecture did you use?**

A local layered Python application: Streamlit UI, FastAPI modular backend, SQLite persistence/search, domain parsers/analysis and optional local OCR/model adapters. The backend is a modular monolith.

**What is the main contribution?**

Turning document interpretation into a reviewed, source-linked architecture inventory, then reusing that inventory for controlled search, consistency candidates, component reports and revision paths.

**Why not just put the PDF into a chatbot?**

The workflow needs review state, revision isolation, structured relationships and auditable evidence. A chatbot alone does not enforce those requirements. Generation is one optional consumer of controlled evidence.

**Why not use an LLM to extract everything?**

The current extractor uses predictable supported patterns and warnings. LLM extraction could be evaluated later, but would still need source occurrence validation, correction/review and unfamiliar-document assessment.

**Why SQLite?**

It keeps local deployment small, supports relational evidence links and transactions, includes FTS5 and allows consistent snapshots. Its suitability at larger scale has not been established.

**Is this a knowledge graph?**

It maintains structured architecture entities and builds directed dependency graphs from them. Storage is relational SQLite, not a dedicated graph database, and it does not implement a formal ontology/reasoner.

**What is the difference between a block and an entity?**

A block is literal source text at a location. An entity is a structured interpretation of that text. Several blocks may support one entity and one block may support several entities.

**Why keep original and current attributes?**

To preserve the extraction interpretation when a reviewer corrects it. The old text must not be presented as an unchanged approved statement of the corrected attributes.

**Why is document approval separate from entity approval?**

Accepting the source does not accept every extracted interpretation. Both gates are needed.

**How do you prevent wrong-page citations?**

Validate literal text and canonical location, then link the entity to the exact stored block occurrence in the same document. Matching the words somewhere else is insufficient.

**What if provenance fails halfway through ingestion?**

The candidate transaction rolls back. Relevant validation/persistence failures retain the original in quarantine with diagnostics rather than leaving partially accepted records.

**What happens when an entity is rejected or edited?**

Its original source block becomes disputed for fact retrieval under the block-state rules. Rejected entities are excluded from exports; approved corrections can appear in exports. Review changes invalidate coverage scope.

**How do you handle uncertainty and negation?**

Recognized qualified/negated architecture sentences are blocked for interpretation rather than converted into unconditional facts. Unsupported cases can still be missed, which is why human review and evaluation remain essential.

**Are embeddings always better?**

No. Their quality depends on evidence units, model, questions and corpus. In the recorded four-question experiment they matched lexical coverage but had lower MRR.

**Does a citation prove an answer is grounded?**

It proves only the checked literal source reference. A claim can reverse a relationship while citing real words. Semantic support is a separate question.

**How does change impact work?**

Compare approved inventories by kind/name and attributes, find graph seeds from changed facts and follow declared outgoing edges up to two hops in before and after graphs. Keep edge IDs, alternatives and cycle protection.

**What do the tests prove?**

They verify implemented behaviors on the tested inputs, including negative paths and integration. They do not establish unfamiliar OEM document accuracy or human productivity.

**What would you change first?**

Get independent labels and timed review on unfamiliar authorized documents, then improve the largest observed errors. Retain raw failures and separate citation validity from semantic usefulness.

## 21. Hands-on exercises that build proficiency

For every exercise, explain the behavior before running it, then locate the function enforcing it.

1. **Trace upload.** Draw the path from the UI form to `Store.ingest()`. Name the records written and where rollback occurs.
2. **Parse the Torque fixture.** Predict all eight entities and their attributes. Inspect their contributing sources.
3. **Negation and conditions.** In separate study revisions try `does not provide` and `provides ... when ...`. Confirm that no unconditional relationship is accepted automatically.
4. **Unsupported wording.** Try a new architecture verb and inspect warnings/misses. Explain why no warning is not proof of completeness.
5. **Two identical occurrences.** Create a small document with repeated text at different lines/sections. Explain why they need distinct block IDs.
6. **Review gates.** Attempt export before source approval, before all proposals are reviewed and with no approved entities. Explain each blocker.
7. **Correction and retrieval.** Correct a proposal's attributes, then compare its export representation with the original block's retrieval state.
8. **Coverage invalidation.** Sign a valid scoped report, make a review change and show that the earlier scope is no longer current.
9. **Revision mismatches.** Use the v1/v2 examples and explain Torque type and Brake direction findings from their source rows.
10. **Graph traversal.** On paper use `A -> B -> C -> A` plus `A -> D -> C`. List one/two-hop paths, explain alternatives and show why cycles stop.
11. **Citation versus truth.** Write a wrong-direction claim citing a real sentence. Explain which mechanical checks pass and which semantic assessment fails.
12. **Metrics by hand.** Compute precision, recall and MRR from a tiny set of labeled facts and ranks without using a tool.
13. **Recovery.** Back up your isolated study DB to a new path, restore to another path, restart against it and verify records.
14. **Roles.** In an isolated DB provision viewer/editor/reviewer accounts. Predict which operations each can perform and test API rejection paths.

Do not experiment with deliberate database tampering on your working database. Read the temporary-database provenance tests for those scenarios.

## 22. A five-session learning plan

**Session 1 — product and architecture:** read sections 1–7, run the isolated demo and give the 30-second explanation without reading it.

**Session 2 — extraction and storage:** read `models.py`, `extraction.py`, relevant parser functions and the ingest transaction. Trace the eight-proposal fixture from text to evidence links.

**Session 3 — trust and retrieval:** read review/export gates, `eligible_blocks()`, `search()` and `filter_answer()`. Explain edited-source filtering and valid-but-wrong citations.

**Session 4 — analysis and operation:** read findings/diff/traversal/report code, demonstrate v1/v2, and practice backup/recovery and roles.

**Session 5 — evaluation and presentation:** read current evidence, calculate metrics manually, answer the viva questions and perform the five-minute demo without assistance.

You are ready to discuss the project confidently when you can predict a failure case, identify its enforcing function, demonstrate it in an isolated workflow, and explain the remaining limitation honestly.

## 23. Source references for further study

Repository-relative paths below are intended for navigation from this saved guide.

- [README and normal launch](../README.md)
- [Current status and historical notes](../STATUS.md)
- [Current validation and retained failures](VALIDATION.md)
- [Occurrence-specific provenance](provenance-integrity.md)
- [PDF extraction context, including historical boundaries](pdf-prose-provenance.md)
- [Local model validation](LOCAL_MODEL_VALIDATION.md)
- [Current synthesized-answer contract and recorded runs](s1b-local-answers.md)
- [Interview demo](INTERVIEW_DEMO.md)
- [Submission completion report](submission/COMPLETION_REPORT.md)
- [Earlier design-decision study draft](submission/viva-design-decisions-draft.md)
- [API workflow](../src/hld_navigator/app.py)
- [Data and answer models](../src/hld_navigator/models.py)
- [Extraction coordinator](../src/hld_navigator/extraction.py)
- [Prose parser](../src/hld_navigator/prose.py)
- [Table parser](../src/hld_navigator/tables.py)
- [Storage, review and retrieval](../src/hld_navigator/store.py)
- [Answers and citation validation](../src/hld_navigator/rag.py)
- [Local embedding adapters](../src/hld_navigator/vectors.py)
- [Findings and revision paths](../src/hld_navigator/analysis.py)
- [Architecture reports](../src/hld_navigator/reports.py)

These notes were prepared with AI assistance from code and repository evidence. Practice the traces and adapt explanations to your own understanding and contribution.
