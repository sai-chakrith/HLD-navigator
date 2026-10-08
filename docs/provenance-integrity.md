# Provenance integrity and legacy boundary

Newly ingested architecture entities are valid only when every evidence item is
nonblank, has one permitted source-location shape, and resolves by exact literal
text plus canonical location to one source block in the same document. The block
ID is the stored occurrence identity. Matching text on another page, row, line,
document, or workspace is a different occurrence and is never substituted.

Accepted locations are:

- PDF page context: `page` only.
- PDF text line: `page` and `line`.
- Markdown/TXT line: `line`, optionally with `section`.
- PDF table row: `page`, `table`, and `row`.
- Markdown/TXT table row: `line`, `table`, and `row`, optionally with `section`.
- OCR line: `page`, `line`, `origin=ocr`, and `confidence`.

Unknown fields, blank evidence, incomplete table coordinates, contradictory
page/section coordinates, and misplaced OCR confidence are rejected. Ingestion
validates the complete block/entity batch before writing and validates its stored
links again in the transaction. Any validation or database failure rolls back the
candidate blocks, search rows, entities, links, and review state together. After
rollback, validation/persistence failures retain only a quarantined document row
with the original bytes, original extraction warnings, a provenance diagnostic,
and an audit event. The quarantined title/version is not silently reused; governed
re-ingestion uses a new revision and fresh review.

Verified documents are audited before approval, reviewed-fact retrieval, coverage
sign-off, manual proposals, and export. A later integrity failure moves the
document to `quarantined`, clears source approval, and blocks those operations.
Existing entity review records remain visible for audit but have no approved-fact
or export effect and cannot transfer to replacement occurrences.

Databases created before schema version 3 are migrated without rewriting or
deleting evidence. Their existing documents become `legacy_unverified`; review,
approved retrieval, indexing, and export require governed re-ingestion from the
original file. Re-ingestion creates new occurrence identities and requires fresh
review. This migration does not certify historical joined or synthesized evidence.

The pilot has no automatic repair for legacy or quarantined lineage. Operators
must retain the old database for audit, upload the original source as a new
revision, inspect extraction warnings and exact evidence, and repeat source and
entity review. This boundary is mechanical provenance enforcement, not proof of
architecture completeness or independent pilot validation.
