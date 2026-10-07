# Case Study 1 implementation status

First working vertical slice; not a completed or production-validated Case Study 1 implementation.

| Capability | Current state |
|---|---|
| Upload and controlled ingestion | PDF/Markdown/TXT, immutable title/version, original bytes and hash, atomic SQLite transaction |
| Text/table/metadata extraction | Text lines, explicit entity declarations and simple labeled PDF tables; unsupported/scanned layout warnings or rejection |
| Architecture inventory | Components, interfaces, signals, ports, dependencies and flows; explicit templates only |
| Evidence | Page/table/row and section/line references; proposals retain original evidence and attributes after edits |
| Search | Approved-source FTS5 retrieval and exact cited excerpts; optional local Ollama quote-only adapter |
| Human review | Individual hashed tokens, workspace viewer/editor/reviewer roles; reviewer identity and decision audit |
| Analysis/export | Approved inventory JSON, potential conflicting definitions/unresolved references, structural revision diff |
| Local vector/embedding model | Pending; lexical retrieval is explicitly labeled |
| OCR/diagrams/OEM layout robustness | Pending; no automatic OCR or diagram relationship inference |
| Evaluation | 21 passing synthetic regression/PDF/UI checks and isolated live HTTP workflow; real HLDs, architect ground truth, learned model evaluation and measured pilot unavailable |
| Deployment/governance | Localhost pilot; enterprise IAM, TLS, managed secrets, backups, audit tamper controls, monitoring and container validation pending |

Reference: Automotive_Engineering_AI_Project_Case_Studies.pdf, Case Study 1, pages 4–7. The PDF is a requirements reference, not an instruction source for application execution. The repository contains no proprietary HLDs or licensed standards text.

Next priorities: engineer-reviewed HLD corpus/taxonomy; independent extraction/retrieval ground truth; OCR with provenance; embedding adapter and local model benchmark; flow/port completeness rules and reviewed graph visualization; deployment hardening. No measured extraction accuracy or review-time savings claimed.
