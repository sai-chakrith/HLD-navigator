import hashlib

import pytest

from hld_navigator.vectors import LlamaCppEmbedding


def adapter(tmp_path):
    artifact = tmp_path / "model.gguf"
    artifact.write_bytes(b"fixture artifact, no model inference")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    return LlamaCppEmbedding("http://127.0.0.1:18882", "bge", artifact, digest)


def test_cpu_adapter_rejects_artifact_drift(tmp_path):
    model = adapter(tmp_path)
    model.artifact.write_bytes(b"changed")
    with pytest.raises(ValueError, match="digest"):
        model.embed(["text"])


def test_cpu_adapter_checks_context_before_embedding(tmp_path, monkeypatch):
    model = adapter(tmp_path)

    def request(path, payload=None):
        if path == "/v1/models":
            return {"data": [{"id": "bge"}]}
        assert path == "/tokenize"
        return {"tokens": list(range(513))}

    monkeypatch.setattr(model, "request", request)
    with pytest.raises(ValueError, match="context"):
        model.embed(["overlong text"])


def test_cpu_adapter_reorders_vectors_and_rejects_duplicate_indices(tmp_path, monkeypatch):
    model = adapter(tmp_path)
    rows = [{"index": 1, "embedding": [0.0, 1.0]}, {"index": 0, "embedding": [1.0, 0.0]}]

    def request(path, payload=None):
        if path == "/v1/models":
            return {"data": [{"id": "bge"}]}
        if path == "/tokenize":
            return {"tokens": [1, 2]}
        return {"data": rows}

    monkeypatch.setattr(model, "request", request)
    assert model.embed(["one", "two"]) == [[1.0, 0.0], [0.0, 1.0]]
    rows[1]["index"] = 1
    with pytest.raises(ValueError, match="index"):
        model.embed(["one", "two"])
