from pathlib import Path

import pytest
from test_pilot import api as api
from test_pilot import approve, upload

from hld_navigator.extraction import extract


def edges(text):
    _, entities, warnings = extract("review.md", text.encode())
    return [e.attributes for e in entities if e.kind == "dependency"], warnings


def test_receive_clause_retains_original_subject():
    found, warnings = edges(
        "The Engine component provides the TorqueInterface interface to "
        "the Cluster component and receives the BrakeInterface interface from the ABS component."
    )
    assert found == [
        {"source": "Engine", "target": "Cluster", "interface": "TorqueInterface"},
        {"source": "ABS", "target": "Engine", "interface": "BrakeInterface"},
    ]
    assert not warnings


def test_multiple_explicit_senders():
    found, warnings = edges(
        "The Engine component sends the Torque interface to the Cluster "
        "component and the ABS component sends the Brake interface to the Engine component."
    )
    assert len(found) == 2
    assert found[1]["source"] == "ABS"
    assert not warnings


@pytest.mark.parametrize(
    "text",
    [
        "The Engine component transfers Torque to the Cluster component.",
        (
            "The Engine component provides the Torque interface to the "
            "Cluster component and transfers Brake to the ABS component."
        ),
    ],
)
def test_unmodeled_clause_is_blocking_even_after_supported_clause(text):
    _, warnings = edges(text)
    assert any(
        w["code"] == "unsupported_relationship" and w["severity"] == "blocking" for w in warnings
    )


@pytest.mark.parametrize(
    "qualifier",
    [
        "only when ignition is ON",
        "except in limp mode",
        "while ignition is ON",
        "provided that speed is zero",
    ],
)
def test_qualified_edge_never_becomes_unconditional(qualifier):
    text = (
        f"The Engine component provides the Torque interface to the Cluster component {qualifier}."
    )
    found, warnings = edges(text)
    assert not found
    assert any(w["code"] == "ambiguous_prose" and qualifier in w["text"] for w in warnings)


def test_unresolved_second_clause_blocks_export(api):
    client, _, reviewer, _ = api
    document = upload(
        api,
        content=(
            b"The Engine component provides the Torque interface to the "
            b"Cluster component and transfers Brake to the ABS component."
        ),
    )
    approve(api, document)
    response = client.get(
        "/workspaces/pilot/export", headers=reviewer, params={"document_id": document}
    )
    assert response.status_code == 409


@pytest.mark.parametrize(
    "text",
    [
        "The Engine component arbitrates the Torque signal with the Cluster component.",
        (
            "The Engine component provides the Torque interface to the "
            "Cluster component and activates the ABS component."
        ),
    ],
)
def test_unknown_component_predicates_require_review(text):
    _, warnings = edges(text)
    assert any(w["code"] == "unsupported_relationship" for w in warnings)


def test_mixed_prose_table_revision_workflow(api):
    client, store, reviewer, _ = api
    directory = Path(__file__).parents[1] / "examples/revision-review"
    before = upload(api, content=(directory / "v1.md").read_bytes())
    after = upload(api, version="2", content=(directory / "v2.md").read_bytes())
    for document in (before, after):
        assert (
            client.get(
                "/workspaces/pilot/export", headers=reviewer, params={"document_id": document}
            ).status_code
            == 409
        )
        approve(api, document)
    baseline = client.get(
        "/workspaces/pilot/export", headers=reviewer, params={"document_id": before}
    ).json()
    assert not baseline["findings"]
    assert len([e for e in baseline["entities"] if e["kind"] == "dependency"]) == 2
    revised = client.get(
        "/workspaces/pilot/export", headers=reviewer, params={"document_id": after}
    ).json()
    kinds = {finding["kind"] for finding in revised["findings"]}
    assert {"port_direction_mismatch", "port_type_mismatch", "interface_type_mismatch"} <= kinds
    delta = client.get(
        "/workspaces/pilot/compare", headers=reviewer, params={"before": before, "after": after}
    ).json()
    assert {item["after"]["name"] for item in delta["changed"]} == {"TorqueIn", "BrakeIn"}
    assert delta["impact_paths"]
    assert all(e["sources"] for e in store.entities("pilot", after))
