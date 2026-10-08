"""Learned local embeddings with persistent SQLite vectors and exact cosine ranking."""

import hashlib
import json
import math
import os
from urllib.parse import urlparse
from urllib.request import Request, urlopen


def validate_vectors(vectors, count):
    if not isinstance(vectors, list) or len(vectors) != count or not vectors:
        raise ValueError("Embedding response count mismatch")
    dimension = len(vectors[0]) if isinstance(vectors[0], list) else 0
    for vector in vectors:
        if not dimension or not isinstance(vector, list) or len(vector) != dimension:
            raise ValueError("Embedding dimension mismatch")
        if any(
            isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
            for v in vector
        ):
            raise ValueError("Invalid embedding value")
        norm = sum(v * v for v in vector)
        if not math.isfinite(norm) or norm == 0:
            raise ValueError("Zero embedding vector")


def cosine(left, right):
    validate_vectors([left, right], 2)
    return sum(a * b for a, b in zip(left, right, strict=True)) / (
        math.sqrt(sum(v * v for v in left)) * math.sqrt(sum(v * v for v in right))
    )


class OllamaEmbedding:
    def __init__(self, base, model, digest):
        parsed = urlparse(base)
        if parsed.scheme not in {"http", "https"} or parsed.hostname not in {
            "localhost",
            "127.0.0.1",
            "::1",
        }:
            raise ValueError("Embedding endpoint must be local loopback")
        if not model or not digest:
            raise ValueError("Embedding model name and operator-recorded artifact digest required")
        self.base = base.rstrip("/")
        self.digest = digest.removeprefix("sha256:")
        self.model = model
        self.identity = hashlib.sha256(
            f"{model}|{digest}|{self.base}|cosine-v1".encode()
        ).hexdigest()

    def embed(self, texts):
        with urlopen(self.base + "/api/tags", timeout=10) as response:
            models = json.load(response).get("models", [])
        requested = self.model if ":" in self.model else self.model + ":latest"
        installed = next(
            (m for m in models if m.get("name") == requested or m.get("name") == self.model), None
        )
        if not installed or installed.get("digest", "").removeprefix("sha256:") != self.digest:
            raise ValueError("Installed embedding artifact does not match the configured digest")
        payload = {"model": self.model, "input": texts, "truncate": False}
        request = Request(
            self.base + "/api/embed",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(request, timeout=45) as response:
            result = json.load(response)
        vectors = result.get("embeddings")
        validate_vectors(vectors, len(texts))
        return vectors


def configured_embedder():
    model = os.getenv("HLD_NAVIGATOR_EMBED_MODEL")
    if not model:
        return None
    return OllamaEmbedding(
        os.getenv("HLD_NAVIGATOR_OLLAMA_URL", "http://127.0.0.1:11434"),
        model,
        os.getenv("HLD_NAVIGATOR_EMBED_DIGEST"),
    )
