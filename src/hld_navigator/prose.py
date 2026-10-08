"""Conservative explicit prose patterns; unmatched architecture is a review issue."""

import re

from .models import Block, Entity

NAME = r"[A-Z](?:[A-Za-z0-9_./-]*[A-Za-z0-9_])?"
SKIP = {"The", "This", "That", "Each", "An", "A", "AUTOSAR"}

# These are noun-phrase heads, not architecture verbs. Bound the phrase at a
# caption terminator or a following capitalized label (PDF prose can include
# table headers). An ordinary lowercase continuation still requires review.
CAPTION_VERSION = (
    r"(?:for\s+)?(?:release|version|revision)(?:\s+|\s*[:=]\s*)"
    r"[vr]?\d+(?:[._-]\d+)*(?!\w|[.-]\w)"
)
INVENTORY_CAPTION = re.compile(
    r"\b(?:components?|interfaces?|ports?|SWCs?|signals?|flows?|dependencies)"
    r"(?:\s*(?:,\s*(?:and\s+)?|\band\s+|&\s*|/\s*)"
    r"(?:components?|interfaces?|ports?|SWCs?|signals?|flows?|dependencies))*"
    r"\s+(?:inventory|catalogue|catalog|list|table|overview|summary|index|definitions)\b"
    rf"(?:\s+{CAPTION_VERSION}|\s*\(\s*{CAPTION_VERSION}\s*\))?"
    r"(?=\s*(?:$|[:|,;.!?\u2014\u2013-]|\d)|\s+(?-i:[A-Z]))",
    re.I,
)


def parse_prose(text, location):
    return _parse_prose(text, Block(text=text, location=location), page_context=False)


def parse_pdf_prose(source: Block, *, interpretation: Block | None = None):
    """Interpret normalized PDF text, quoting its literal original page context.

    The source unit is explicitly the extracted page, not a sentence quote.
    Interpretation may exclude geometrically detected table contents. The
    quotation remains the original complete page; no source search is needed.
    """
    if interpretation is not None and interpretation.location != source.location:
        raise ValueError("PDF prose interpretation and original source must refer to the same page")
    text = source.text if interpretation is None else interpretation.text
    return _parse_prose(" ".join(text.split()), source, page_context=True)


def _parse_prose(text, original: Block, *, page_context):
    location = original.location
    proposals = []
    issues = []

    def add(kind, name, attributes=None):
        if name not in SKIP:
            proposals.append(
                Entity(
                    kind=kind,
                    name=name,
                    attributes=attributes or {},
                    evidence=original.text,
                    location=location,
                )
            )

    sentences = re.split(r"(?<=[.!?])\s+", text)
    for sentence in sentences:
        if re.search(
            r"\b(?:not|never|cannot|no|without|may|might|possibly|false|if|unless|doesn't|isn't|can't|when|while|except|until|provided|depending)\b",
            sentence,
            re.I,
        ):
            if re.search(
                r"\b(?:provide|consume|send|receive|connect|carry|interface|component|signal|port|flow)\w*\b",
                sentence,
                re.I,
            ):
                issues.append(
                    {
                        "code": "ambiguous_prose",
                        "severity": "blocking",
                        "message": (
                            "Negated, uncertain or qualified architecture statement needs "
                            "interpretation"
                        ),
                        "text": original.text if page_context else sentence,
                        "location": location.model_dump(),
                    }
                )
            continue
        nominal_spans = [match.span() for match in INVENTORY_CAPTION.finditer(sentence)]
        for kind, nouns in (
            ("component", r"(?:software\s+component|component|SWC)"),
            ("interface", r"interface"),
            ("signal", r"signal"),
        ):
            for match in re.finditer(rf"\b({NAME})\s+{nouns}\b", sentence):
                # A label before a nominal caption head does not assert an
                # architecture entity. Keep scanning other mentions in context.
                if not any(
                    start < match.end() and match.start() < end for start, end in nominal_spans
                ):
                    add(kind, match[1])
            for match in re.finditer(rf"\b({NAME})\s+is\s+(?:an?\s+)?{nouns}\b", sentence):
                add(kind, match[1])
        covered = []
        subject = None
        peer = (
            rf"(?:the\s+)?{NAME}\b(?:\s+(?:components?|SWCs?))?"
            r"(?!\s+(?:(?:components?|SWCs?)\s+)?"
            r"(?:provides|publishes|sends|receives|consumes|requires|transfers)\b)"
        )
        peers = rf"{peer}(?:\s*(?:,\s*(?:and\s+)?|\band\s+){peer})*"
        relationships = re.finditer(
            rf"\b(?:(?:The\s+|the\s+)?({NAME})\s+(?:component\s+|SWC\s+)?|\band\s+)"
            rf"(provides|publishes|sends|receives|consumes)\s+(?:the\s+)?({NAME})\s+interface\s+"
            rf"(to|for|from)\s+({peers})",
            sentence,
        )
        for relationship in relationships:
            explicit_subject, verb, interface, preposition, peer_text = relationship.groups()
            subject = explicit_subject or subject
            receiving = verb in {"receives", "consumes"}
            if (
                subject is None
                or (receiving and preposition != "from")
                or (not receiving and preposition == "from")
            ):
                continue
            covered.append(relationship.span())
            for peer_match in re.finditer(
                rf"(?:the\s+)?({NAME})(?:\s+(?:components?|SWCs?))?", peer_text
            ):
                peer_name = peer_match[1]
                source, target = (peer_name, subject) if receiving else (subject, peer_name)
                add("component", source)
                add("component", target)
                add("interface", interface)
                add(
                    "dependency",
                    f"{source}->{target}:{interface}",
                    {"source": source, "target": target, "interface": interface},
                )
        payload_matches = re.finditer(
            rf"({NAME})\s+interface\s+(?:carries|contains|transmits)\s+"
            rf"(?:the\s+)?({NAME})\s+signal",
            sentence,
        )
        for payload in payload_matches:
            covered.append(payload.span())
            add("interface", payload[1], {"payload": payload[2]})
            add("signal", payload[2])
        signal_matches = re.finditer(
            rf"({NAME})\s+signal\s+(?:has|uses|is\s+of)\s+(?:data\s+)?type\s+"
            r"([A-Za-z][A-Za-z0-9_]*)"
            r"(?:\s+(?:and|with)\s+units?\s+(.+?)"
            rf"(?=[.!?](?:\s|$)|\s+and\s+(?:the\s+)?{NAME}\s+signal\b|$))?",
            sentence,
        )
        for signal in signal_matches:
            covered.append(signal.span())
            attrs = {"type": signal[2]}
            if signal[3]:
                attrs["unit"] = signal[3].strip()
            add("signal", signal[1], attrs)
        flow_matches = re.finditer(
            rf"({NAME})\s+flow\s+(?:runs|goes)\s+from\s+(?:the\s+)?({NAME})(?:\s+component)?\s+to\s+(?:the\s+)?({NAME})",
            sentence,
        )
        for flow in flow_matches:
            covered.append(flow.span())
            add("flow", flow[1], {"source": flow[2], "target": flow[3]})
        port_matches = re.finditer(
            rf"({NAME})\s+(?:component\s+)?(provides|requires)\s+(?:the\s+)?"
            rf"({NAME})\s+interface\s+(?:through|via|using)\s+(?:the\s+)?"
            rf"(?:port\s+({NAME})|({NAME})\s+port)",
            sentence,
        )
        for port in port_matches:
            covered.append(port.span())
            owner, direction, interface, name1, name2 = port.groups()
            add("component", owner)
            add("interface", interface)
            add(
                "port",
                name1 or name2,
                {"owner": owner, "direction": direction, "interface": interface},
            )
        # Account for every action, including actions after an extracted edge.
        # This vocabulary is intentionally conservative, not a completeness claim.
        actions = re.finditer(
            r"\b(?:provides|requires|connects|consumes|publishes|carries|contains|transmits|"
            r"sends|receives|transfers|routes|exchanges|forwards|delivers|communicates)\b",
            sentence,
            re.I,
        )
        # A component predicate or a coordinated lowercase verb outside the
        # supported grammar also needs review. Avoid pretending a finite verb
        # list recognizes all engineering prose.
        predicates = re.finditer(
            r"\b(?=(?:component|SWC)\s+([a-z]+)\b|and\s+([a-z]+)\b)",
            sentence,
        )
        ignored = {"is", "a", "an", "the", "and", "unit", "with", "of", "in", "to", "from"}
        actions = [(m.group(), *m.span()) for m in actions]
        if re.search(r"\b(?:component|SWC)\b", sentence):
            for match in predicates:
                group = 1 if match[1] else 2
                first, last = match.span(group)
                if match[group] not in ignored and not any(
                    start <= first and last <= end for start, end in nominal_spans
                ):
                    actions.append((match[group], *match.span(group)))
        uncovered = [
            word
            for word, first, last in actions
            if not any(start <= first and last <= end for start, end in covered)
        ]
        if uncovered:
            issues.append(
                {
                    "code": "unsupported_relationship",
                    "severity": "blocking",
                    "message": (
                        "Architecture relationship is not covered "
                        "by the current extraction patterns"
                    ),
                    "text": original.text if page_context else sentence,
                    "unresolved_actions": uncovered,
                    "location": location.model_dump(),
                }
            )
    return proposals, issues


def merge_entities(entities, warnings):
    groups = {}
    for entity in entities:
        groups.setdefault((entity.kind, entity.name), []).append(entity)
    result = []
    for key, group in groups.items():
        attributes = {}
        conflict = False
        for entity in group:
            for name, value in entity.attributes.items():
                if name in attributes and attributes[name] != value:
                    conflict = True
                attributes[name] = value
        if conflict:
            warnings.append(
                {
                    "code": "conflicting_extraction",
                    "severity": "blocking",
                    "message": f"Conflicting definitions for {key[0]} {key[1]}",
                }
            )
            unique = {}
            for entity in group:
                unique.setdefault(tuple(sorted(entity.attributes.items())), entity)
            result.extend(unique.values())
        else:
            result.append(
                group[0].model_copy(
                    update={
                        "attributes": attributes,
                        "sources": [
                            {"text": e.evidence, "location": e.location.model_dump()} for e in group
                        ],
                    }
                )
            )
    return result
