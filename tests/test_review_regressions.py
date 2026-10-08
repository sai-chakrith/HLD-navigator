import io

from reportlab.pdfgen import canvas
from test_pilot import api as api
from test_pilot import approve, upload

from hld_navigator.analysis import findings
from hld_navigator.extraction import extract
from hld_navigator.rag import supported


def test_negation_cannot_be_cropped_out_of_citation():
    evidence = [{"text": "It is false that Engine controls braking."}]
    assert not supported("Engine controls braking [1]", evidence)
    assert supported("It is false that Engine controls braking. [1]", evidence)


def test_valid_pdf_followed_by_blank_page():
    stream = io.BytesIO()
    pdf = canvas.Canvas(stream)
    pdf.drawString(50, 750, "Component: Engine")
    pdf.showPage()
    pdf.showPage()
    pdf.save()
    _, entities, warnings = extract("blank-tail.pdf", stream.getvalue())
    assert len(entities) == 1
    assert any(w.get("code") == "blank_page" for w in warnings)


def test_ordinary_hld_prose_without_special_syntax():
    paragraph = (
        "The EngineControl component provides the TorqueInterface interface "
        "to the InstrumentCluster component. "
        "The TorqueInterface interface carries the Torque signal. "
        "The Torque signal has type uint16 and unit Nm."
    )
    _, entities, _ = extract("ordinary.md", paragraph.encode())
    inventory = {(e.kind, e.name): e.attributes for e in entities}
    assert ("component", "EngineControl") in inventory
    assert ("component", "InstrumentCluster") in inventory
    assert inventory[("interface", "TorqueInterface")]["payload"] == "Torque"
    assert inventory[("signal", "Torque")]["type"] == "uint16"
    assert any(
        e.kind == "dependency"
        and e.attributes.get("source") == "EngineControl"
        and e.attributes.get("target") == "InstrumentCluster"
        for e in entities
    )


def test_no_affirmative_edge_from_negated_relationship():
    _, entities, warnings = extract(
        "negation.md",
        b"The Engine component does not provide the Torque interface to the Cluster component.",
    )
    assert not any(e.kind in {"dependency", "port"} for e in entities)
    assert any(w.get("code") == "ambiguous_prose" for w in warnings)


def test_requires_requires_dependency_is_incompatible():
    def entity(kind, name, **attrs):
        return {
            "id": name,
            "kind": kind,
            "name": name,
            "attributes": attrs,
            "location": {"page": 1},
        }

    rows = [
        entity("component", "A"),
        entity("component", "B"),
        entity("interface", "I"),
        entity("port", "PA", owner="A", interface="I", direction="requires"),
        entity("port", "PB", owner="B", interface="I", direction="requires"),
        entity("dependency", "D", source="A", target="B", interface="I"),
    ]
    assert any(f["kind"] == "port_direction_mismatch" for f in findings(rows))


def test_zero_entity_export_is_blocked(api):
    client, _, reviewer, _ = api
    document = upload(api, content=b"An unrecognized architecture description.")
    approve(api, document)
    assert (
        client.get(
            "/workspaces/pilot/export", headers=reviewer, params={"document_id": document}
        ).status_code
        == 409
    )


def test_unresolved_extraction_warning_blocks_export(api):
    client, _, reviewer, _ = api
    document = upload(api, content=b"Component: Engine\nPort: Bad | owner=Engine")
    approve(api, document)
    assert (
        client.get(
            "/workspaces/pilot/export", headers=reviewer, params={"document_id": document}
        ).status_code
        == 409
    )


def test_rejected_entity_statement_not_returned_as_fact(api):
    client, _, reviewer, _ = api
    document = upload(api, content=b"Component: UntrustedEngine")
    approve(api, document)
    entity = client.get("/workspaces/pilot/entities", headers=reviewer).json()[0]
    client.post(
        f"/workspaces/pilot/entities/{entity['id']}/review",
        headers=reviewer,
        json={"status": "rejected", "reason": "Incorrect source declaration"},
    )
    response = client.post(
        "/workspaces/pilot/query",
        headers=reviewer,
        json={"text": "UntrustedEngine", "document_id": document},
    )
    assert response.json()["evidence"] == []
