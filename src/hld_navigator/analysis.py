def findings(entities):
    names = {
        kind: {e["name"] for e in entities if e["kind"] == kind}
        for kind in ("component", "interface", "signal")
    }
    results = []
    seen = {}
    for entity in entities:
        key = (entity["kind"], entity["name"])
        if key in seen and seen[key]["attributes"] != entity["attributes"]:
            results.append(
                {
                    "kind": "conflicting_definition",
                    "entity_ids": [seen[key]["id"], entity["id"]],
                    "message": "Definitions differ; inspect revision and variant scope",
                }
            )
        seen[key] = entity
        checks = []
        if entity["kind"] == "port":
            checks = [("owner", "component"), ("interface", "interface")]
        if entity["kind"] in {"dependency", "flow"}:
            checks = [("source", "component"), ("target", "component"), ("interface", "interface")]
        if entity["kind"] == "interface":
            checks = [("payload", "signal")]
        for attribute, kind in checks:
            value = entity["attributes"].get(attribute)
            if value and value not in names[kind]:
                results.append(
                    {
                        "kind": "unresolved_reference",
                        "entity_ids": [entity["id"]],
                        "attribute": attribute,
                        "value": value,
                        "location": entity["location"],
                        "message": "Not found in approved inventory; may be external or missing",
                    }
                )
    return results


def compare(before, after):
    left = {(e["kind"], e["name"]): e for e in before}
    right = {(e["kind"], e["name"]): e for e in after}
    if len(left) != len(before) or len(right) != len(after):
        raise ValueError("Conflicting duplicate definitions must be resolved before comparison")
    return {
        "added": [right[k] for k in sorted(right.keys() - left.keys())],
        "removed": [left[k] for k in sorted(left.keys() - right.keys())],
        "changed": [
            {"before": left[k], "after": right[k]}
            for k in sorted(left.keys() & right.keys())
            if left[k]["attributes"] != right[k]["attributes"]
        ],
    }
