import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from hld_navigator.vectors import LlamaCppEmbedding, OllamaEmbedding


@contextmanager
def endpoint(redirect=False):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if redirect:
                self.send_response(302)
                self.send_header("Location", "https://example.com/collect")
                self.end_headers()
                return
            body = json.dumps(
                {"models": [{"name": "fixture", "digest": "abc"}], "data": [{"id": "fixture"}]}
            ).encode()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"embeddings":[[1.0,2.0]]}')

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_embedding_backends_bypass_environment_proxy(monkeypatch):
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("http_proxy", "http://127.0.0.1:1")
    monkeypatch.setenv("NO_PROXY", "")
    monkeypatch.setenv("no_proxy", "")
    with endpoint() as base:
        assert OllamaEmbedding(base, "fixture", "abc").embed(["private architecture"]) == [[1, 2]]
        model = LlamaCppEmbedding(base, "fixture", "unused.gguf", "abc")
        assert model.request("/v1/models")["data"] == [{"id": "fixture"}]


def test_embedding_external_redirect_rejected_before_any_source_can_be_forwarded():
    with endpoint(redirect=True) as base:
        with pytest.raises(ValueError, match="loopback"):
            OllamaEmbedding(base, "fixture", "abc").embed(["private architecture"])
        with pytest.raises(ValueError, match="loopback"):
            LlamaCppEmbedding(base, "fixture", "unused.gguf", "abc").request("/v1/models")
