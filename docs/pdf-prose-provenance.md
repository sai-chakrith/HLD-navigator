# PDF prose source evidence

New text-PDF extraction interprets a normalized copy of each page's extracted
text. Prose entity evidence, contributing prose sources, and prose warning text
retain the complete original `pdfplumber` page text, with its original line breaks
and spacing. This is a **page-context quote**, not a sentence quote or a quotation
of the PDF's binary bytes. The page reference accompanies the source text; after
ingestion, the stored document identifies the source file and revision.

The original source unit is supplied directly to the parser. Extraction does not
search for a similar quote or manufacture a span from normalized text. Full page
context can contain unrelated statements; it preserves the existing interpretation
unit and retains all negation and conditions. Warnings still identify unresolved
actions where applicable. Table rows remain captured row spans with page/table/row
references. Markdown and TXT evidence behavior is unchanged.

Detected table regions are interpreted by the table parser. Their characters are
excluded from prose interpretation by their page coordinates, so responsibility
cells such as action descriptions do not become standalone prose relationships.
Prose outside those regions is still interpreted, and its evidence retains the
complete original page, including table context and all surrounding qualifiers.
This boundary relies on `pdfplumber` table detection; undetected tables remain a
pilot limitation.

Historical documents are not repaired by this change. Their existing normalized
evidence remains stored; affected documents need re-ingestion until explicit legacy
quarantine/migration work is implemented. This is a pilot extraction change, not
independent validation of the architecture or model answers.

Non-table persistence currently links evidence by text without requiring the exact
location. Identical prose on multiple pages can therefore attach matching blocks
from more than one location. Literal extraction source references are retained,
but strict location-specific persistence and global provenance validation remain
separate T3b2 work. No storage schema, approval policy, model, or citation-guard
behavior is changed here.
