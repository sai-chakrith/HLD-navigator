from fastapi.testclient import TestClient

from hld_navigator.app import create_app
from tools.demo import seed


def test_cited_reports_follow_export_authorization_and_real_review_state(tmp_path):
    database = tmp_path / "reports.db"
    token, ids = seed(database)
    client = TestClient(create_app(str(database)))
    headers = {"Authorization": "Bearer " + token}
    identifier = ids["synthetic_revisions"][0]
    url = "/workspaces/demo/export"
    assert client.get(url, params={"document_id": identifier}).status_code == 401
    result = client.get(url, params={"document_id": identifier}, headers=headers)
    assert result.status_code == 200
    report = result.json()
    assert len(report["dependency_map"]) == 2
    engine = next(c for c in report["component_reports"] if c["name"] == "Engine")
    assert len(engine["ports"]) == 2
    assert engine["incoming"][0]["source"] == "ABS"
    assert engine["outgoing"][0]["target"] == "Cluster"
    ids = {e["id"] for e in report["entities"]}
    assert all(edge["citation"]["entity_id"] in ids for edge in report["dependency_map"])
    assert all(edge["citation"]["evidence"] for edge in report["dependency_map"])
    assert '"Engine" -> "Cluster"' in report["graph_dot"]
    assert (
        client.get(
            "/workspaces/foreign/export", params={"document_id": identifier}, headers=headers
        ).status_code
        == 403
    )
    client.post(
        f"/workspaces/demo/documents/{identifier}/review",
        headers=headers,
        json={"approved": False, "reason": "Revoked"},
    )
    assert client.get(url, params={"document_id": identifier}, headers=headers).status_code == 409


def test_demo_ui_renders_reviewed_dependency_map_and_component_reports(tmp_path, monkeypatch):
    from pathlib import Path
    from urllib.parse import urlparse

    from streamlit.testing.v1 import AppTest

    database = tmp_path / "ui.db"
    token, ids = seed(database)
    client = TestClient(create_app(str(database)))

    def request(method, url, **kwargs):
        kwargs.pop("timeout", None)
        return client.request(method, urlparse(url).path, **kwargs)

    monkeypatch.setattr("requests.request", request)
    app = AppTest.from_file(str(Path(__file__).parents[1] / "src/hld_navigator/ui.py")).run()
    app.text_input[1].set_value("demo")
    app.text_input[2].set_value(token)
    app.run()
    assert not app.exception
    next(box for box in app.selectbox if box.label == "Export revision").set_value(
        ids["synthetic_revisions"][0]
    )
    app.run()
    next(button for button in app.button if button.label == "Build reviewed report").click()
    app.run()
    assert not app.exception
    assert len(app.get("graphviz_chart")) == 1
    assert any(expander.label == "Engine" for expander in app.expander)
