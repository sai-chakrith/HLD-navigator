import io
import json
from types import SimpleNamespace

import pytest
from PIL import Image
from reportlab.pdfgen import canvas

from hld_navigator.extraction import extract
from hld_navigator.ocr import page_ocr
from hld_navigator.vectors import OllamaEmbedding, validate_vectors


def test_embedding_actual_protocol_and_digest(monkeypatch):
    seen = []

    class Response(io.BytesIO):
        pass

    def endpoint(request, timeout):
        if isinstance(request, str):
            assert request.endswith("/api/tags")
            return Response(
                json.dumps({"models": [{"name": "fixture:latest", "digest": "abcdef"}]}).encode()
            )
        payload = json.loads(request.data)
        seen.append(payload)
        assert request.full_url.endswith("/api/embed")
        return Response(json.dumps({"embeddings": [[1.0, 2.0], [3.0, 4.0]]}).encode())

    monkeypatch.setattr("hld_navigator.vectors.urlopen", endpoint)
    assert OllamaEmbedding("http://localhost:11434", "fixture", "abcdef").embed(["one", "two"]) == [
        [1.0, 2.0],
        [3.0, 4.0],
    ]
    assert seen[0]["truncate"] is False
    with pytest.raises(ValueError, match="digest"):
        OllamaEmbedding("http://localhost:11434", "fixture", "wrong").embed(["one"])


def test_ocr_tsv_adapter_arguments_and_confidence(monkeypatch):
    monkeypatch.setenv("HLD_NAVIGATOR_OCR", "1")
    monkeypatch.setenv("HLD_NAVIGATOR_TESSERACT", "controlled-fixture-executable")
    image = Image.new("RGB", (50, 50), "white")
    page = SimpleNamespace(
        width=50, height=50, to_image=lambda resolution: SimpleNamespace(original=image)
    )

    def execute(args, **kwargs):
        assert args[0] == "controlled-fixture-executable"
        assert args[-2:] == ["stdout", "tsv"]
        assert kwargs["check"] and kwargs["timeout"] == 60
        return SimpleNamespace(
            stdout="block_num\tpar_num\tline_num\tconf\ttext\n1\t1\t1\t97\tComponent:\n1\t1\t1\t82\tEngine\n"
        )

    monkeypatch.setattr("hld_navigator.ocr.subprocess.run", execute)
    assert page_ocr(page) == [("Component: Engine", 82.0)]


def test_ocr_result_marked_and_not_auto_approved(monkeypatch):
    stream = io.BytesIO()
    pdf = canvas.Canvas(stream)
    pdf.rect(30, 30, 100, 100)
    pdf.showPage()
    pdf.save()
    monkeypatch.setattr(
        "hld_navigator.extraction.page_ocr", lambda page: [("Component: Engine", 67.0)]
    )
    blocks, entities, warnings = extract("scan.pdf", stream.getvalue())
    assert entities[0].location.origin == "ocr"
    assert blocks[0].location.confidence == 67.0
    assert warnings[0]["code"] == "ocr_review" and warnings[0]["severity"] == "blocking"


def test_overflowing_vectors_rejected():
    with pytest.raises(ValueError):
        validate_vectors([[1e308, 1e308]], 1)
