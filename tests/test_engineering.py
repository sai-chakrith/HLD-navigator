import io

import pytest
from reportlab.platypus import SimpleDocTemplate, Table
from test_pilot import api as api
from test_pilot import approve, upload

from hld_navigator.analysis import compare, findings
from hld_navigator.extraction import extract
from hld_navigator.store import Store
from hld_navigator.tables import table_lines
from hld_navigator.vectors import OllamaEmbedding, cosine, validate_vectors


def test_coverage_signature_invalidated_by_review(api):
    client, store, reviewer, _ = api
    document = upload(api, content=b"Component: Engine\nPort: Bad | owner=Engine")
    approve(api, document)
    decision = {
        "scope": "Components only; port declaration must be corrected in next revision",
        "reason": "Compared unsupported port warning with source and excluded that part",
    }
    response = client.post(
        f"/workspaces/pilot/documents/{document}/coverage-review", headers=reviewer, json=decision
    )
    assert response.status_code == 200, response.text
    assert (
        client.get(
            "/workspaces/pilot/export", headers=reviewer, params={"document_id": document}
        ).status_code
        == 200
    )
    entity = store.entities("pilot", document)[0]
    client.post(
        f"/workspaces/pilot/entities/{entity['id']}/review",
        headers=reviewer,
        json={"status": "approved", "reason": "Rechecked"},
    )
    assert (
        client.get(
            "/workspaces/pilot/export", headers=reviewer, params={"document_id": document}
        ).status_code
        == 409
    )


def test_disputed_sources_explicit_and_edits_do_not_promote_old_text(api):
    client, store, reviewer, _ = api
    document = upload(api, content=b"Component: Engine | description=Controls brakes")
    approve(api, document)
    entity = store.entities("pilot", document)[0]
    client.post(
        f"/workspaces/pilot/entities/{entity['id']}/review",
        headers=reviewer,
        json={
            "status": "approved",
            "attributes": {"description": "Controls torque"},
            "reason": "Corrected requirement",
        },
    )
    response = client.post(
        "/workspaces/pilot/query",
        headers=reviewer,
        json={"text": "Engine", "document_id": document},
    )
    revised = response.json()["evidence"]
    assert revised and "Controls torque" in revised[0]["text"]
    assert "Controls brakes" not in revised[0]["text"]
    assert revised[0]["facts"][0]["field_basis"] == "reviewer_correction"
    assert revised[0]["source_context"]["review_state"] == "disputed_source"
    assert (
        store.search("pilot", "torque", document)[0]["facts"][0]["field_basis"]
        == "reviewer_correction"
    )
    response = client.post(
        "/workspaces/pilot/query",
        headers=reviewer,
        json={"text": "Engine", "document_id": document, "scope": "source"},
    )
    assert response.json()["mode"] == "source_review_required"
    assert response.json()["evidence"][0]["review_state"] == "disputed_source"


def test_table_aliases_port_owner_and_directions():
    table = [
        ["Port Name", "Component", "Interface", "Port Kind"],
        ["TorqueOut", "Engine", "TorqueInterface", "P-Port"],
    ]
    lines, issues = table_lines(table, "Ports", {"page": 4, "table": 1})
    assert not issues
    assert lines == [
        ("Port: TorqueOut | owner=Engine | interface=TorqueInterface | direction=provides", 2)
    ]


def test_varied_pdf_component_table():
    stream = io.BytesIO()
    table = Table([["SWC Name", "Responsibility"], ["EngineControl", "Calculates torque"]])
    table.setStyle([("GRID", (0, 0), (-1, -1), 1, "black")])
    SimpleDocTemplate(stream).build([table])
    _, entities, warnings = extract("ordinary-table.pdf", stream.getvalue())
    assert not warnings
    assert entities[0].name == "EngineControl"
    assert entities[0].attributes["description"] == "Calculates torque"
    assert entities[0].location.row == 2


def test_evidence_locations_survive_prose_merge(api):
    client, store, reviewer, _ = api
    document = upload(
        api,
        content=(
            b"The TorqueInterface interface carries the Torque signal.\n"
            b"The Torque signal has type uint16 and unit Nm."
        ),
    )
    signal = next(e for e in store.entities("pilot", document) if e["kind"] == "signal")
    assert {s["location"]["line"] for s in signal["sources"]} == {1, 2}
    assert signal["attributes"]["type"] == "uint16"


def test_type_mismatch_and_change_impact_paths():
    def entity(kind, name, **attrs):
        return {
            "id": name,
            "kind": kind,
            "name": name,
            "attributes": attrs,
            "location": {"page": 1},
        }

    before = [
        entity("component", "Engine"),
        entity("component", "Cluster"),
        entity("signal", "Torque", type="uint16"),
        entity("interface", "I", payload="Torque"),
        entity("port", "P", owner="Engine", interface="I", direction="provides", type="uint16"),
        entity("port", "R", owner="Cluster", interface="I", direction="requires", type="uint32"),
        entity("dependency", "D", source="Engine", target="Cluster", interface="I"),
    ]
    assert {f["kind"] for f in findings(before)} >= {
        "port_type_mismatch",
        "interface_type_mismatch",
    }
    after = [
        {**e, "attributes": {**e["attributes"], "type": "uint32"}} if e["name"] == "Torque" else e
        for e in before
    ]
    result = compare(before, after)
    assert any(
        p["path"] == ["Engine", "Cluster"] and p["edge_ids"] == ["D"]
        for p in result["impact_paths"]
    )


class ScriptedEmbedding:
    identity = "test-only-scripted-not-learned-model"

    def embed(self, texts):
        return [[1.0, 0.0] if "Engine" in t or "motor" in t else [0.0, 1.0] for t in texts]


def test_persistent_vector_ranking_restart_and_isolation(api):
    client, store, reviewer, _ = api
    document = upload(api, content=b"Component: Engine\nComponent: Cluster")
    approve(api, document)
    embedder = ScriptedEmbedding()
    with pytest.raises(ValueError, match="Index"):
        store.vector_search("pilot", "motor", document, embedder)
    store.index_vectors("pilot", document, embedder)
    restarted = Store(store.path)
    assert (
        restarted.vector_search("pilot", "motor", document, embedder)[0]["text"]
        == "Component: Engine"
    )
    assert restarted.vector_search("other", "motor", document, embedder) == []
    with store.connection() as db:
        before = db.execute("SELECT vector FROM embeddings ORDER BY block_id").fetchall()

    class Broken:
        identity = embedder.identity

        def embed(self, texts):
            raise TimeoutError("Interrupted model indexing")

    with pytest.raises(TimeoutError):
        store.index_vectors("pilot", document, Broken())
    with store.connection() as db:
        assert [
            r[0] for r in db.execute("SELECT vector FROM embeddings ORDER BY block_id").fetchall()
        ] == [r[0] for r in before]


@pytest.mark.parametrize(
    "vectors", [[[0.0, 0.0]], [[float("nan"), 1.0]], [[True, 1.0]], [[1.0, 2.0], [1.0]], []]
)
def test_invalid_vectors_rejected(vectors):
    with pytest.raises(ValueError):
        validate_vectors(vectors, 1)


def test_cosine_dimension_and_value_checks():
    assert cosine([1.0, 0.0], [1.0, 0.0]) == 1
    assert cosine([1.0, 0.0], [0.0, 1.0]) == 0
    with pytest.raises(ValueError):
        cosine([1.0], [1.0, 0.0])


def test_embedding_configuration_no_remote_or_unknown_artifact():
    with pytest.raises(ValueError, match="loopback"):
        OllamaEmbedding("https://external.example", "model", "digest")
    with pytest.raises(ValueError, match="digest"):
        OllamaEmbedding("http://localhost:11434", "model", None)


def test_manual_correction_requires_source_and_reviewer(api):
    client, store, reviewer, viewer = api
    document = upload(api, content=b"EngineControl performs the vehicle control computations.")
    approve(api, document)
    block = client.get(f"/workspaces/pilot/documents/{document}/blocks", headers=reviewer).json()[0]
    proposal = {
        "kind": "component",
        "name": "EngineControl",
        "attributes": {},
        "evidence_block_id": block["id"],
    }
    assert (
        client.post(
            f"/workspaces/pilot/documents/{document}/entities", headers=viewer, json=proposal
        ).status_code
        == 403
    )
    response = client.post(
        f"/workspaces/pilot/documents/{document}/entities", headers=reviewer, json=proposal
    )
    assert response.status_code == 200, response.text
    assert store.entities("pilot", document)[0]["status"] == "proposed"
    assert (
        client.get(
            "/workspaces/pilot/export", headers=reviewer, params={"document_id": document}
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/workspaces/other/documents/{document}/entities", headers=reviewer, json=proposal
        ).status_code
        == 403
    )
    proposal["name"] = "HallucinatedName"
    assert (
        client.post(
            f"/workspaces/pilot/documents/{document}/entities", headers=reviewer, json=proposal
        ).status_code
        == 422
    )


def test_port_prose_name_excludes_sentence_punctuation():
    _, entities, _ = extract(
        "ordinary.md",
        b"The Engine component provides the TorqueInterface interface through port TorqueOut.",
    )
    port = next(e for e in entities if e.kind == "port")
    assert port.name == "TorqueOut"


def test_unmodeled_relationship_is_a_blocking_requirement():
    _, entities, warnings = extract(
        "ordinary.md",
        b"The Engine component connects to the Cluster component through a proprietary adaptor.",
    )
    assert entities
    assert any(
        w.get("code") == "unsupported_relationship" and w["severity"] == "blocking"
        for w in warnings
    )


def test_markdown_table_without_custom_declarations():
    text = (
        b"# Components\n| SWC Name | Responsibility |\n| --- | --- |\n"
        b"| EngineControl | Calculates torque |\n"
    )
    _, entities, warnings = extract("table.md", text)
    assert not warnings
    assert len(entities) == 1 and entities[0].name == "EngineControl"
    assert entities[0].location.line == 4 and entities[0].location.row == 3


def test_wrapped_pdf_prose_is_not_lost():
    from reportlab.pdfgen import canvas

    stream = io.BytesIO()
    pdf = canvas.Canvas(stream)
    pdf.drawString(50, 750, "The EngineControl component provides the TorqueInterface interface")
    pdf.drawString(50, 730, "to the InstrumentCluster component.")
    pdf.save()
    _, entities, warnings = extract("wrapped.pdf", stream.getvalue())
    assert not warnings
    edge = next(e for e in entities if e.kind == "dependency")
    assert edge.attributes["target"] == "InstrumentCluster"
    assert edge.location.page == 1 and edge.location.line is None


def test_absent_component_is_not_extracted_as_present():
    _, entities, warnings = extract("absent.md", b"There is no Engine component in this variant.")
    assert not entities
    assert any(w.get("code") == "ambiguous_prose" for w in warnings)
