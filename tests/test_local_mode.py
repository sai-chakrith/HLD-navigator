from pathlib import Path
from urllib.parse import urlparse

from fastapi.testclient import TestClient

from hld_navigator.app import create_app
from tools.demo import seed


def test_local_app_opens_without_login_and_keeps_workspace_scope(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest

    database = tmp_path / "local.db"
    seed(database)
    monkeypatch.setenv("HLD_NAVIGATOR_LOCAL_WORKSPACE", "demo")
    client = TestClient(create_app(str(database)))
    assert client.get("/workspaces/demo/documents").status_code == 200
    assert client.get("/workspaces/other/documents").status_code == 403

    def request(method, url, **kwargs):
        kwargs.pop("timeout", None)
        assert kwargs.pop("allow_redirects") is False
        assert kwargs["headers"] == {}
        return client.request(method, urlparse(url).path, **kwargs)

    monkeypatch.setattr("requests.request", request)
    app = AppTest.from_file(str(Path(__file__).parents[1] / "src/hld_navigator/ui.py")).run()
    assert not app.exception
    assert len(app.tabs) == 4
    assert not any(
        field.label in {"Workspace", "Individual access token"} for field in app.text_input
    )
    assert any(box.label == "Source revision" for box in app.selectbox)
