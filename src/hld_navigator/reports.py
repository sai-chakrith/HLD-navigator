"""Cited summaries generated only from the inventory passed by the export gate."""

import json


def reference(entity):
    return {
        "entity_id": entity["id"],
        "review_scope": "entity name and structured attributes only",
        "context_review_state": "unreviewed_source_context",
        "evidence": entity["evidence"],
        "sources": entity.get("sources") or [],
        "location": entity["location"],
    }


def architecture_report(entities):
    components = []
    edges = []
    for entity in entities:
        attributes = entity["attributes"]
        if entity["kind"] == "component":
            components.append(
                {"name": entity["name"], "attributes": attributes, "citation": reference(entity)}
            )
        elif entity["kind"] in {"dependency", "flow"}:
            edges.append(
                {
                    "kind": entity["kind"],
                    "name": entity["name"],
                    "source": attributes.get("source"),
                    "target": attributes.get("target"),
                    "interface": attributes.get("interface"),
                    "citation": reference(entity),
                }
            )
    summaries = []
    for component in components:
        name = component["name"]
        summaries.append(
            {
                **component,
                "ports": [
                    {"name": e["name"], "attributes": e["attributes"], "citation": reference(e)}
                    for e in entities
                    if e["kind"] == "port" and e["attributes"].get("owner") == name
                ],
                "incoming": [e for e in edges if e["target"] == name],
                "outgoing": [e for e in edges if e["source"] == name],
            }
        )
    # DOT strings are escaped, so source text cannot inject graph directives.
    lines = ["digraph architecture {", "rankdir=LR;", "node [shape=box];"]
    for component in components:
        lines.append(f"{json.dumps(component['name'])};")
    for edge in edges:
        if edge["source"] and edge["target"]:
            label = edge["interface"] or edge["kind"]
            lines.append(
                f"{json.dumps(edge['source'])} -> {json.dumps(edge['target'])} "
                f"[label={json.dumps(label)}];"
            )
    lines.append("}")
    return {
        "component_reports": summaries,
        "dependency_map": edges,
        "graph_dot": "\n".join(lines),
        "basis": "Approved declared relationships; no inferred diagram topology",
    }
