"""Conservative explicit prose patterns; unmatched architecture is a review issue."""

import re

from .models import Entity

NAME = r"[A-Z](?:[A-Za-z0-9_./-]*[A-Za-z0-9_])?"
SKIP = {"The", "This", "That", "Each", "An", "A", "AUTOSAR"}


def parse_prose(text, location):
    proposals = []
    issues = []

    def add(kind, name, attributes=None):
        if name not in SKIP:
            proposals.append(
                Entity(
                    kind=kind,
                    name=name,
                    attributes=attributes or {},
                    evidence=text,
                    location=location,
                )
            )

    sentences = re.split(r"(?<=[.!?])\s+", text)
    for sentence in sentences:
        if re.search(
            r"\b(?:not|never|cannot|no|without|may|might|possibly|false|if|unless|doesn't|isn't|can't)\b",
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
                        "message": "Negated/uncertain architecture statement needs interpretation",
                        "text": sentence,
                        "location": location.model_dump(),
                    }
                )
            continue
        for kind, nouns in (
            ("component", r"(?:software\s+component|component|SWC)"),
            ("interface", r"interface"),
            ("signal", r"signal"),
        ):
            for match in re.finditer(rf"\b({NAME})\s+{nouns}\b", sentence):
                add(kind, match[1])
            for match in re.finditer(rf"\b({NAME})\s+is\s+(?:an?\s+)?{nouns}\b", sentence):
                add(kind, match[1])
        relationship = re.search(
            rf"(?:The\s+)?({NAME})\s+(?:component\s+|SWC\s+)?"
            rf"(?:provides|publishes|sends)\s+(?:the\s+)?({NAME})\s+interface\s+"
            rf"(?:to|for)\s+(?:the\s+)?({NAME})(?:\s+(?:component|SWC))?",
            sentence,
        )
        if relationship:
            source, interface, target = relationship.groups()
            add("component", source)
            add("component", target)
            add("interface", interface)
            add(
                "dependency",
                f"{source}->{target}:{interface}",
                {"source": source, "target": target, "interface": interface},
            )
        payload = re.search(
            rf"({NAME})\s+interface\s+(?:carries|contains|transmits)\s+"
            rf"(?:the\s+)?({NAME})\s+signal",
            sentence,
        )
        if payload:
            add("interface", payload[1], {"payload": payload[2]})
            add("signal", payload[2])
        signal = re.search(
            rf"({NAME})\s+signal\s+(?:has|uses|is\s+of)\s+(?:data\s+)?type\s+"
            r"([A-Za-z][A-Za-z0-9_]*)"
            r"(?:\s+(?:and|with)\s+unit\s+([A-Za-z°/]+))?",
            sentence,
        )
        if signal:
            attrs = {"type": signal[2]}
            if signal[3]:
                attrs["unit"] = signal[3]
            add("signal", signal[1], attrs)
        flow = re.search(
            rf"({NAME})\s+flow\s+(?:runs|goes)\s+from\s+(?:the\s+)?({NAME})(?:\s+component)?\s+to\s+(?:the\s+)?({NAME})",
            sentence,
        )
        if flow:
            add("flow", flow[1], {"source": flow[2], "target": flow[3]})
        port = re.search(
            rf"({NAME})\s+(?:component\s+)?(provides|requires)\s+(?:the\s+)?"
            rf"({NAME})\s+interface\s+(?:through|via|using)\s+(?:the\s+)?"
            rf"(?:port\s+({NAME})|({NAME})\s+port)",
            sentence,
        )
        if port:
            owner, direction, interface, name1, name2 = port.groups()
            add("component", owner)
            add("interface", interface)
            add(
                "port",
                name1 or name2,
                {"owner": owner, "direction": direction, "interface": interface},
            )
        if not any((relationship, payload, signal, flow, port)) and re.search(
            r"\b(?:provides|requires|connects|consumes|publishes|carries|sends|receives)\b",
            sentence,
            re.I,
        ):
            issues.append(
                {
                    "code": "unsupported_relationship",
                    "severity": "blocking",
                    "message": (
                        "Architecture relationship is not covered "
                        "by the current extraction patterns"
                    ),
                    "text": sentence,
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
