import pytest

from hld_navigator.rag import generate


def test_answer_backend_rejects_nonlocal_endpoint(monkeypatch):
    monkeypatch.setenv("HLD_NAVIGATOR_CHAT_MODEL", "test")
    monkeypatch.setenv("HLD_NAVIGATOR_LOCAL_URL", "https://remote.example")
    with pytest.raises(ValueError, match="loopback"):
        generate("question", [{"text": "source"}])


def test_answer_backend_rejects_unknown_protocol(monkeypatch):
    monkeypatch.setenv("HLD_NAVIGATOR_CHAT_MODEL", "test")
    monkeypatch.setenv("HLD_NAVIGATOR_LOCAL_URL", "http://127.0.0.1:18880")
    monkeypatch.setenv("HLD_NAVIGATOR_CHAT_BACKEND", "other")
    with pytest.raises(ValueError, match="backend"):
        generate("question", [{"text": "source"}])
