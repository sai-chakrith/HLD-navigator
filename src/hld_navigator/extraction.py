import io
import re
from pathlib import Path

import pdfplumber

from .models import Block, Entity, Location
from .ocr import page_ocr
from .prose import merge_entities, parse_prose
from .tables import table_lines

KINDS = {"component", "interface", "signal", "port", "dependency", "flow"}
ALLOWED = {
    "component": {"description"},
    "interface": {"kind", "payload", "type", "description"},
    "signal": {"type", "unit", "description"},
    "port": {"owner", "interface", "direction", "type", "description"},
    "dependency": {"source", "target", "interface", "description"},
    "flow": {"source", "target", "interface", "description"},
}
REQUIRED = {
    "port": {"owner", "interface", "direction"},
    "dependency": {"source", "target"},
    "flow": {"source", "target"},
}


def parse_line(text: str, location: Location) -> tuple[Entity | None, str | None]:
    match = re.match(r"^\s*(Component|Interface|Signal|Port|Dependency|Flow):\s*(.*)$", text, re.I)
    if not match:
        return None, None
    kind = match[1].lower()
    parts = [p.strip() for p in match[2].split("|")]
    if not parts[0]:
        return None, "Missing entity name"
    attributes = {}
    for item in parts[1:]:
        if "=" not in item:
            return None, f"Expected key=value attribute: {item}"
        key, value = (s.strip() for s in item.split("=", 1))
        key = key.lower()
        if key not in ALLOWED[kind] or not value or key in attributes:
            return None, f"Unknown, empty or repeated attribute: {key}"
        attributes[key] = value
    missing = REQUIRED.get(kind, set()) - attributes.keys()
    if missing:
        return None, f"Missing attributes: {', '.join(sorted(missing))}"
    if kind == "port" and attributes["direction"] not in {"provides", "requires"}:
        return None, "Port direction must be provides or requires"
    return Entity(
        kind=kind, name=parts[0], attributes=attributes, evidence=text, location=location
    ), None


def extract(name: str, content: bytes) -> tuple[list[Block], list[Entity], list[dict]]:
    blocks: list[Block] = []
    entities: list[Entity] = []
    warnings: list[dict] = []

    def accept(text: str, location: Location, prose=True) -> None:
        entity, error = parse_line(text, location)
        if entity:
            entities.append(entity)
        elif not error and prose:
            parsed, issues = parse_prose(text, location)
            entities.extend(parsed)
            warnings.extend(issues)
        if error:
            warnings.append(
                {
                    "code": "invalid_declaration",
                    "severity": "blocking",
                    "message": error,
                    "location": location.model_dump(),
                    "text": text,
                }
            )

    suffix = Path(name).suffix.lower()
    if suffix in {".md", ".txt"}:
        text = content.decode("utf-8-sig")
        section = None
        markdown_tables = []
        pending = []
        for number, line in enumerate(text.splitlines(), 1):
            if line.strip().startswith("|"):
                pending.append((number, line))
            elif pending:
                markdown_tables.append(pending)
                pending = []
            if line.startswith("#"):
                section = line.lstrip("#").strip()
            if line.strip():
                location = Location(section=section, line=number)
                blocks.append(Block(text=line, location=location))
                if not line.strip().startswith("|"):
                    accept(line, location)
        if pending:
            markdown_tables.append(pending)
        for table_index, rows in enumerate(markdown_tables, 1):
            table = []
            for _, line in rows:
                cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
                table.append(
                    [None] * len(cells) if all(re.fullmatch(r":?-+:?", c) for c in cells) else cells
                )
            declarations, issues = table_lines(table, text, {"table": table_index})
            warnings.extend(issues)
            for declaration, row in declarations:
                location = Location(table=table_index, row=row, line=rows[row - 1][0])
                blocks.append(Block(text=declaration, location=location))
                accept(declaration, location)
    elif suffix == ".pdf":
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page_number, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""
                if not text.strip():
                    if not page.images and not page.rects and not page.curves and not page.lines:
                        warnings.append(
                            {
                                "code": "blank_page",
                                "severity": "info",
                                "message": "Blank page skipped",
                                "page": page_number,
                            }
                        )
                        continue
                    ocr_lines = page_ocr(page)
                    if not ocr_lines:
                        raise ValueError(f"Page {page_number}: OCR produced no usable text")
                    for number, (line, confidence) in enumerate(ocr_lines, 1):
                        location = Location(
                            page=page_number, line=number, origin="ocr", confidence=confidence
                        )
                        blocks.append(Block(text=line, location=location))
                        accept(line, location)
                    warnings.append(
                        {
                            "code": "ocr_review",
                            "severity": "blocking",
                            "message": "OCR text requires comparison with the rendered page",
                            "page": page_number,
                        }
                    )
                    continue
                for number, line in enumerate(text.splitlines(), 1):
                    if line.strip():
                        location = Location(page=page_number, line=number)
                        blocks.append(Block(text=line, location=location))
                        accept(line, location, prose=False)
                # Combine wrapped prose for interpretation; retain original lines independently.
                joined = " ".join(text.split())
                parsed, issues = parse_prose(joined, Location(page=page_number))
                if parsed or issues:
                    blocks.append(Block(text=joined, location=Location(page=page_number)))
                    entities.extend(parsed)
                    warnings.extend(issues)
                for index, table in enumerate(page.extract_tables(), 1):
                    if not table or not table[0]:
                        continue
                    declarations, issues = table_lines(
                        table, text, {"page": page_number, "table": index}
                    )
                    warnings.extend(issues)
                    for line, row_number in declarations:
                        location = Location(page=page_number, table=index, row=row_number)
                        blocks.append(Block(text=line, location=location))
                        accept(line, location)
    else:
        raise ValueError("Supported files are text PDFs, UTF-8 Markdown and TXT")
    if not blocks:
        raise ValueError("Document has no usable text")
    merged = merge_entities(entities, warnings)
    if not merged:
        warnings.append(
            {
                "code": "no_entities",
                "severity": "blocking",
                "message": "No template entities or supported prose patterns recognized",
            }
        )
    return blocks, merged, warnings
