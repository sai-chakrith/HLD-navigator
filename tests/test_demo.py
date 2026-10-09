import pytest

from hld_navigator.analysis import compare, findings
from hld_navigator.store import Store
from tools.demo import seed


def test_interview_demo_preserves_real_review_boundary_and_shows_defects(tmp_path):
    database = tmp_path / "demo.db"
    token, ids = seed(database)
    store = Store(str(database))
    assert store.principal(token, "demo")["role"] == "reviewer"
    before, after = [
        store.entities("demo", identifier, True) for identifier in ids["synthetic_revisions"]
    ]
    assert before and after
    assert not findings(before)
    kinds = {finding["kind"] for finding in findings(after)}
    assert {"port_direction_mismatch", "port_type_mismatch"} <= kinds
    assert len(compare(before, after)["changed"]) == 2
    public = ids["unreviewed_public_document"]
    assert not store.entities("demo", public, True)
    assert not next(d for d in store.documents("demo") if d["id"] == public)["approved"]
    with pytest.raises(FileExistsError):
        seed(database)
    assert store.principal(token, "demo") is not None
