"""Header aliases and section context, preserving raw cell row references."""

import re

ALIASES = {
    "kind": {"kind", "entity type", "category"},
    "name": {
        "name",
        "component",
        "component name",
        "swc",
        "swc name",
        "interface",
        "interface name",
        "signal",
        "signal name",
        "port",
        "port name",
        "dependency",
        "flow",
    },
    "owner": {"owner", "swc owner", "owning component", "component owner"},
    "source": {"source", "provider", "producer", "source component"},
    "target": {"target", "consumer", "receiver", "destination component"},
    "interface": {"interface ref", "interface reference", "interface type"},
    "direction": {"direction", "port direction", "p r", "port kind"},
    "type": {"data type", "datatype", "signal type", "type"},
    "unit": {"unit", "units"},
    "payload": {"payload", "data element", "signal reference"},
    "description": {"description", "purpose", "responsibility"},
}


def normal(value):
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def table_lines(table, context, location):
    if not table:
        return [], []
    output, issues = [], []
    # Find a header after title rows; reject duplicate/unknown populated columns.
    header_index = next(
        (
            i
            for i, row in enumerate(table[:6])
            if sum(normal(c or "") in set().union(*ALIASES.values()) for c in row) >= 2
        ),
        None,
    )
    if header_index is None:
        return [], [
            {
                "code": "unsupported_table",
                "severity": "blocking",
                "message": "No recognized architecture table header",
                **location,
            }
        ]
    raw_headers = [normal(c or "") for c in table[header_index]]
    inferred = "port" if "port" in raw_headers or "port name" in raw_headers else None
    for kind in ("component", "interface", "signal", "port", "dependency", "flow"):
        if (
            any(h in {kind, kind + " name", "swc", "swc name"} for h in raw_headers)
            and inferred is None
        ):
            inferred = "component" if "swc" in raw_headers or "swc name" in raw_headers else kind
    if inferred is None:
        for kind in ("component", "interface", "signal", "port", "dependency", "flow"):
            if re.search(rf"\b{kind}s?\b", context, re.I):
                inferred = kind
                break
    headers = []
    for raw in raw_headers:
        header = next((key for key, aliases in ALIASES.items() if raw in aliases), None)
        # 'Interface' is a reference column in a port/dependency table.
        if raw in {"interface", "interface name"} and inferred in {"port", "dependency", "flow"}:
            header = "interface"
        if raw in {"component", "component name", "swc", "swc name"} and inferred == "port":
            header = "owner"
        headers.append(header)
    if "name" not in headers or len([h for h in headers if h]) != len(set(h for h in headers if h)):
        return [], [
            {
                "code": "ambiguous_table",
                "severity": "blocking",
                "message": "Missing or duplicate entity name/attribute columns",
                **location,
            }
        ]
    for row_index, row in enumerate(table[header_index + 1 :], header_index + 2):
        if [normal(c or "") for c in row] == raw_headers or not any(row):
            continue
        values = [(c or "").strip() for c in row]
        if len(values) != len(headers) or any(
            v for h, v in zip(headers, values, strict=False) if h is None
        ):
            issues.append(
                {
                    "code": "unsupported_table",
                    "severity": "blocking",
                    "message": "Unknown populated column or inconsistent row width",
                    **location,
                    "row": row_index,
                }
            )
            continue
        attrs = {h: v for h, v in zip(headers, values, strict=True) if h and v}
        kind = attrs.pop("kind", inferred)
        name = attrs.pop("name", "")
        if not kind:
            issues.append(
                {
                    "code": "ambiguous_table",
                    "severity": "blocking",
                    "message": "Entity kind cannot be inferred",
                    **location,
                    "row": row_index,
                }
            )
            continue
        if kind == "port" and "direction" in attrs:
            attrs["direction"] = {
                "p-port": "provides",
                "p port": "provides",
                "provided": "provides",
                "r-port": "requires",
                "r port": "requires",
                "required": "requires",
            }.get(attrs["direction"].lower(), attrs["direction"].lower())
        output.append(
            (
                f"{kind.title()}: {name}" + "".join(f" | {k}={v}" for k, v in attrs.items()),
                row_index,
            )
        )
    return output, issues
