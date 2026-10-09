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
    ports = [e for e in entities if e["kind"] == "port"]
    interfaces = {e["name"]: e for e in entities if e["kind"] == "interface"}
    signals = {e["name"]: e for e in entities if e["kind"] == "signal"}
    for edge in entities:
        attrs = edge["attributes"]
        if edge["kind"] not in {"dependency", "flow"} or not attrs.get("interface"):
            continue
        source = [
            p
            for p in ports
            if p["attributes"].get("owner") == attrs.get("source")
            and p["attributes"].get("interface") == attrs["interface"]
        ]
        target = [
            p
            for p in ports
            if p["attributes"].get("owner") == attrs.get("target")
            and p["attributes"].get("interface") == attrs["interface"]
        ]
        if not source or not target:
            results.append(
                {
                    "kind": "missing_port_metadata",
                    "entity_ids": [edge["id"]],
                    "location": edge["location"],
                    "message": (
                        "Declared dependency lacks explicit endpoint port metadata; "
                        "compatibility unverified"
                    ),
                }
            )
        elif not any(p["attributes"].get("direction") == "provides" for p in source) or not any(
            p["attributes"].get("direction") == "requires" for p in target
        ):
            results.append(
                {
                    "kind": "port_direction_mismatch",
                    "entity_ids": [edge["id"], *[p["id"] for p in source + target]],
                    "location": edge["location"],
                    "message": (
                        "Dependency requires a providing source port and a requiring target port"
                    ),
                }
            )
        for provider in source:
            for consumer in target:
                first = provider["attributes"].get("type")
                second = consumer["attributes"].get("type")
                if first and second and first != second:
                    results.append(
                        {
                            "kind": "port_type_mismatch",
                            "entity_ids": [provider["id"], consumer["id"]],
                            "message": f"Endpoint data types differ: {first} versus {second}",
                        }
                    )
    for port in ports:
        interface = interfaces.get(port["attributes"].get("interface"))
        if not interface:
            continue
        payload = signals.get(interface["attributes"].get("payload"))
        expected = interface["attributes"].get("type") or (
            payload["attributes"].get("type") if payload else None
        )
        actual = port["attributes"].get("type")
        if expected and actual and expected != actual:
            results.append(
                {
                    "kind": "interface_type_mismatch",
                    "entity_ids": [port["id"], interface["id"]],
                    "message": (
                        f"Port type {actual} conflicts with declared payload type {expected}"
                    ),
                }
            )
    return results


def compare(before, after):
    left = {(e["kind"], e["name"]): e for e in before}
    right = {(e["kind"], e["name"]): e for e in after}
    if len(left) != len(before) or len(right) != len(after):
        raise ValueError("Conflicting duplicate definitions must be resolved before comparison")
    result = {
        "added": [right[k] for k in sorted(right.keys() - left.keys())],
        "removed": [left[k] for k in sorted(left.keys() - right.keys())],
        "changed": [
            {"before": left[k], "after": right[k]}
            for k in sorted(left.keys() & right.keys())
            if left[k]["attributes"] != right[k]["attributes"]
        ],
    }

    result["impact_paths"] = []
    for revision, inventory, triggers in (
        (
            "before",
            before,
            [*result["removed"], *[change["before"] for change in result["changed"]]],
        ),
        ("after", after, [*result["added"], *[change["after"] for change in result["changed"]]]),
    ):
        result["impact_paths"].extend(
            {**path, "revision": revision} for path in impact_paths(inventory, triggers)
        )
    result["impact_scope"] = "Declared paths up to two hops in the before and after inventories"
    return result


def impact_paths(entities, triggers):
    edges = [e for e in entities if e["kind"] in {"dependency", "flow"}]
    ports = [e for e in entities if e["kind"] == "port"]
    paths = []
    for trigger in triggers:
        kind, name = trigger["kind"], trigger["name"]
        seeds = {name} if kind == "component" else set()
        interfaces = (
            {name}
            if kind == "interface"
            else {
                e["name"]
                for e in entities
                if kind == "signal"
                and e["kind"] == "interface"
                and e["attributes"].get("payload") == name
            }
        )
        seeds.update(
            p["attributes"].get("owner")
            for p in ports
            if p["attributes"].get("interface") in interfaces
        )
        seeds.update(
            e["attributes"].get("source")
            for e in edges
            if e["attributes"].get("interface") in interfaces
            or (kind in {"dependency", "flow"} and e["id"] == trigger["id"])
        )
        if kind == "port":
            seeds.add(trigger["attributes"].get("owner"))
        for seed in sorted(s for s in seeds if s):
            queue = [([seed], [])]
            while queue:
                nodes, identifiers = queue.pop(0)
                if len(identifiers) >= 2:
                    continue
                for edge in edges:
                    if edge["attributes"].get("source") != nodes[-1]:
                        continue
                    target = edge["attributes"].get("target")
                    if not target or target in nodes:
                        continue
                    next_nodes = [*nodes, target]
                    next_ids = [*identifiers, edge["id"]]
                    paths.append(
                        {
                            "trigger": {"kind": kind, "name": name},
                            "path": next_nodes,
                            "edge_ids": next_ids,
                            "basis": (
                                "possible impact over declared edges; not functional equivalence"
                            ),
                        }
                    )
                    queue.append((next_nodes, next_ids))
    return paths
