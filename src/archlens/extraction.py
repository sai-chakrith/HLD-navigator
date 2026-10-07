import io
import re
from pathlib import Path

import pdfplumber

from .models import Block, Entity, Location

KINDS = {"component", "interface", "signal", "port", "dependency", "flow"}
ALLOWED = {
    "component": {"description"},
    "interface": {"kind", "payload", "description"},
    "signal": {"type", "unit", "description"},
    "port": {"owner", "interface", "direction", "description"},
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

    def accept(text: str, location: Location) -> None:
        entity, error = parse_line(text, location)
        if entity:
            entities.append(entity)
        if error:
            warnings.append({"message": error, "location": location.model_dump(), "text": text})

    suffix = Path(name).suffix.lower()
    if suffix in {".md", ".txt"}:
        text = content.decode("utf-8-sig")
        section = None
        for number, line in enumerate(text.splitlines(), 1):
            if line.startswith("#"):
                section = line.lstrip("#").strip()
            if line.strip():
                location = Location(section=section, line=number)
                blocks.append(Block(text=line, location=location))
                accept(line, location)
    elif suffix == ".pdf":
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page_number, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""
                if not text.strip():
                    raise ValueError(f"Page {page_number} has no extractable text; OCR is required")
                for number, line in enumerate(text.splitlines(), 1):
                    if line.strip():
                        location = Location(page=page_number, line=number)
                        blocks.append(Block(text=line, location=location))
                        accept(line, location)
                for index, table in enumerate(page.extract_tables(), 1):
                    if not table or not table[0]:
                        continue
                    headers = [(h or "").strip().lower() for h in table[0]]
                    if not {"kind", "name"}.issubset(headers):
                        warnings.append(
                            {
                                "message": "Unsupported table header",
                                "page": page_number,
                                "table": index,
                            }
                        )
                        continue
                    if len(set(headers)) != len(headers) or any(not h for h in headers):
                        warnings.append(
                            {
                                "message": "Ambiguous table header",
                                "page": page_number,
                                "table": index,
                            }
                        )
                        continue
                    for row_number, row in enumerate(table[1:], 2):
                        if len(row) != len(headers):
                            warnings.append(
                                {
                                    "message": "Unequal table row width",
                                    "page": page_number,
                                    "table": index,
                                    "row": row_number,
                                }
                            )
                            continue
                        values = dict(zip(headers, [(v or "").strip() for v in row], strict=True))
                        kind = values.pop("kind").lower()
                        entity_name = values.pop("name")
                        line = f"{kind.title()}: {entity_name}" + "".join(
                            f" | {k}={v}" for k, v in values.items() if v
                        )
                        location = Location(page=page_number, table=index, row=row_number)
                        if kind not in KINDS:
                            warnings.append(
                                {
                                    "message": f"Unknown entity kind: {kind}",
                                    "location": location.model_dump(),
                                }
                            )
                            continue
                        blocks.append(Block(text=line, location=location))
                        accept(line, location)
    else:
        raise ValueError("Supported files are text PDFs, UTF-8 Markdown and TXT")
    if not blocks:
        raise ValueError("Document has no usable text")
    # Retain duplicate evidence locations, but one semantic proposal per entity definition.
    unique = {}
    for entity in entities:
        key = (entity.kind, entity.name, tuple(sorted(entity.attributes.items())))
        unique.setdefault(key, entity)
    if not unique:
        warnings.append({"message": "No template entities recognized; review/normalize the layout"})
    return blocks, list(unique.values()), warnings
