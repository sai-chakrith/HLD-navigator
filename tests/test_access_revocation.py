import pytest
from fastapi.testclient import TestClient

from hld_navigator.app import create_app
from hld_navigator.store import Store


def test_revoke_denies_old_token_everywhere_and_retains_history(tmp_path):
    database = str(tmp_path / "access.db")
    store = Store(database)
    store.provision("architect", "first", "reviewer")
    token = store.provision("architect", "second", "reviewer")
    client = TestClient(create_app(database))
    headers = {"Authorization": "Bearer " + token}
    assert client.get("/workspaces/first/documents", headers=headers).status_code == 200
    assert client.get("/workspaces/second/documents", headers=headers).status_code == 200
    store.revoke("architect")
    for workspace in ("first", "second"):
        assert client.get(f"/workspaces/{workspace}/documents", headers=headers).status_code == 403
        result = client.post(
            f"/workspaces/{workspace}/documents",
            headers=headers,
            data={"title": "Denied", "version": "1"},
            files={"file": ("denied.md", b"Component: Engine")},
        )
        assert result.status_code == 403
        assert not store.documents(workspace)
    with store.connection() as db:
        assert db.execute("SELECT count(*) FROM memberships").fetchone()[0] == 2
        assert db.execute("SELECT action FROM audit ORDER BY id DESC LIMIT 1").fetchone()[0] == (
            "revoke_access"
        )
    new_token = store.provision("architect", "first", "reviewer")
    assert store.principal(new_token, "first") is not None
    assert store.principal(token, "first") is None


def test_revoke_unknown_user_fails_without_changing_existing_identity(tmp_path):
    store = Store(str(tmp_path / "access.db"))
    token = store.provision("existing", "pilot", "viewer")
    with pytest.raises(KeyError):
        store.revoke("missing")
    assert store.principal(token, "pilot")["role"] == "viewer"
