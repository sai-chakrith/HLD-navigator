"""Explicit named documentation declarations; no topology inferred from links.

Development cases use separate invented protocol/server names. Public results
remain a development measurement and the frozen set is not used for tuning.
"""

import re

from .models import Entity


def named_declarations(text, location):
    matches = []
    # Links whose labels are explicitly introduced as a named server or provider.
    for match in re.finditer(
        r"(?:\b(?:server|broker)\s*[-–:]\s*(?:the\s+)?|\bThe\s+)"
        r"\[([^\]]+)\]\([^\)]+\)\s*(?:is an example of (?:an? )?[^.]*provider)?",
        text,
        re.I,
    ):
        if re.search(r"\b(?:server|broker)\s*[-–:]", match[0], re.I) or re.search(
            r"is an example of .*provider", match[0], re.I
        ):
            matches.append(("component", match[1]))
        # Avoid interpreting ordinary documentation/source links as components.
    # Protocol/API labels are inventories, not dependencies or implementation claims.
    for match in re.finditer(r"`([^`]+)`\s+(?:gRPC\s+)?(?:Protocol|API)\b", text):
        matches.append(("interface", match[1]))
    for match in re.finditer(r"\b([A-Z][A-Za-z0-9_.-]*(?:\s+[A-Z][A-Za-z0-9_.-]*)*)\s+API\b", text):
        matches.append(("interface", match[1] + " API"))
    # Explicit typed path examples; do not extract arbitrary backtick identifiers.
    for match in re.finditer(r"\b(?:sensor|actuator|signal)\s+`([A-Za-z_]\w*(?:\.\w+)+)`", text):
        matches.append(("signal", match[1]))
    return [
        Entity(kind=kind, name=name, evidence=text, location=location)
        for kind, name in dict.fromkeys(matches)
    ]
