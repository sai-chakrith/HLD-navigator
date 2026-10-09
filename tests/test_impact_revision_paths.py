from hld_navigator.analysis import compare, impact_paths


def entity(kind, name, **attributes):
    return {"id": name, "kind": kind, "name": name, "attributes": attributes}


def test_impact_keeps_alternative_paths_and_terminates_on_cycles():
    component = entity("component", "Sensor")
    inventory = [
        component,
        entity("dependency", "direct", source="Sensor", target="Display"),
        entity("dependency", "first", source="Sensor", target="Gateway"),
        entity("dependency", "second", source="Gateway", target="Display"),
        entity("dependency", "cycle", source="Gateway", target="Sensor"),
        entity("dependency", "third", source="Display", target="Logger"),
    ]
    paths = impact_paths(inventory, [component])
    assert {tuple(p["edge_ids"]) for p in paths} >= {
        ("direct",),
        ("first",),
        ("first", "second"),
        ("direct", "third"),
    }
    assert all(len(p["edge_ids"]) <= 2 for p in paths)
    assert not any("cycle" in p["edge_ids"] for p in paths)


def test_added_edges_and_rerouting_have_correct_revision_evidence():
    first = entity("dependency", "speed", source="Sensor", target="Display")
    second = entity("dependency", "speed", source="Sensor", target="Gateway")
    added = entity("dependency", "forward", source="Gateway", target="Display")
    result = compare([first], [second, added])
    paths = result["impact_paths"]
    assert any(p["revision"] == "before" and p["path"] == ["Sensor", "Display"] for p in paths)
    assert any(p["revision"] == "after" and p["edge_ids"] == ["speed", "forward"] for p in paths)
    assert any(p["trigger"]["name"] == "forward" and p["revision"] == "after" for p in paths)
    assert not compare([first], [first])["impact_paths"]
