"""Bounded architecture-field answers from reviewed records, never page approval.

These controls cover named structured fields only. Free synthesis still requires
human review; this module makes no general natural-language entailment claim.
"""

import re

FIELDS = {
    "unit": r"\bunits?\b",
    "type": r"\b(?:type|datatype|data type)\b",
    "owner": r"\b(?:owner|owns|owning|belongs)\b",
    "direction": r"\bdirection\b",
    "source": r"\b(?:source|provider|producer)\b",
    "target": r"\b(?:target|recipient|consumer|receiver|destination)\b",
    "asil": r"\basil\b",
    "payload": r"\bpayload\b",
}


def render_fact(fact):
    return f"{fact['kind'].title()}: {fact['name']}" + "".join(
        f" | {key}={value}" for key, value in sorted(fact["attributes"].items())
    )


def requested_fields(question):
    return [key for key, pattern in FIELDS.items() if re.search(pattern, question, re.I)]


def relevant(question, block):
    facts = block.get("facts")
    if facts is None:
        return True
    fields = requested_fields(question)
    names = [f for f in facts if re.search(rf"(?<!\w){re.escape(f['name'])}(?!\w)", question, re.I)]
    if fields:
        return any(all(key in f["attributes"] for key in fields) for f in names)
    return True


def field_answer(question, evidence):
    """Return deterministic field answers when the question fits the narrow contract."""
    fields = requested_fields(question)
    if not fields or not evidence or any("facts" not in b for b in evidence):
        return None
    # Negation/conditions are not represented by the current positive inventory.
    if re.search(r"\b(?:not|never|unless|when|if|except|revision|version)\b", question, re.I):
        return None
    records = []
    for i, block in enumerate(evidence, 1):
        for fact in block["facts"]:
            if not re.search(rf"(?<!\w){re.escape(fact['name'])}(?!\w)", question, re.I):
                continue
            if all(field in fact["attributes"] for field in fields):
                records.append((i, block, fact))
    if not records:
        return None
    variants = {(f["name"], tuple(f["attributes"][key] for key in fields)) for _, _, f in records}
    conflict = len({v for _, v in variants}) > 1
    claims = []
    for i, block, fact in records:
        text = (
            f"{fact['name']}: "
            + ", ".join(f"{key}={fact['attributes'][key]}" for key in fields)
            + f" (revision {block['version']})."
        )
        claims.append(
            {
                "text": text,
                "citations": [
                    {
                        "source_id": f"S{i}",
                        "block_id": block["id"],
                        "entity_id": fact["entity_id"],
                        "snippet": render_fact(fact),
                        "basis": "reviewed_fields",
                    }
                ],
            }
        )
    return {
        "mode": "source_conflict" if conflict else "reviewed_field_answer",
        "answer": "\n".join(c["text"] for c in claims),
        "claims": claims,
        "evidence": evidence,
        "reason": "contradictory_evidence" if conflict else "",
        "human_review_required": conflict,
        "guarantee_scope": "selected approved structured fields only",
    }


def semantic_violation(text, sources):
    """Reject detectable field/qualifier contradictions; unrecognized prose is unverified."""
    cited = "\n".join(source["text"] for source in sources)
    for field in ("unit", "type", "owner", "direction", "source", "target", "payload"):
        separator = (
            r"(?:is\s+|=|:)"
            if field in {"source", "target", "owner", "payload"}
            else (r"(?:is\s+|=|:)?")
        )
        pattern = (
            rf"\b{field}\b(?:\s+of\s+\w+)?\s*{separator}"
            r"\s*([A-Za-z0-9_./-]+)"
        )
        for match in re.finditer(pattern, text, re.I):
            value = match[1].rstrip(".")
            if not re.search(rf"(?<!\w){re.escape(value)}(?!\w)", cited, re.I):
                return "unsupported_architecture_field"
    negation = r"\b(?:not|never|cannot|doesn't|can't)\b"
    if re.search(negation, cited, re.I) and not re.search(negation, text, re.I):
        return "negation_scope_not_preserved"
    if re.search(r"\b(?:when|unless|if|except|until)\b", cited, re.I) and not re.search(
        r"\b(?:when|unless|if|except|until)\b", text, re.I
    ):
        return "condition_scope_not_preserved"
    if re.search(r"\b(?:revision|version)\s+\w+", cited, re.I) and not re.search(
        r"\b(?:revision|version)\s+\w+", text, re.I
    ):
        return "revision_scope_not_preserved"
    # Exact direction/owner claims that the existing parser understands must
    # agree with cited parsed relations, not merely share words.
    from .models import Location
    from .prose import parse_prose

    claimed, _ = parse_prose(text, Location(line=1))
    supported, _ = parse_prose(cited, Location(line=1))
    from .extraction import parse_line

    for line in cited.splitlines():
        entity, _ = parse_line(line, Location(line=1))
        if entity:
            supported.append(entity)
    for recipient in re.finditer(
        r"\b(\w+)\s+is\s+(?:the\s+)?(?:named\s+)?recipient\s+of\s+(\w+)", text
    ):
        if not any(
            e.kind == "dependency"
            and e.attributes.get("target") == recipient[1]
            and e.attributes.get("interface") == recipient[2]
            for e in supported
        ):
            return "unsupported_architecture_direction"
    for entity in claimed:
        if entity.kind not in {"dependency", "port", "flow"}:
            continue
        if not any(
            e.kind == entity.kind and e.name == entity.name and e.attributes == entity.attributes
            for e in supported
        ):
            return "unsupported_architecture_direction"
    return None
