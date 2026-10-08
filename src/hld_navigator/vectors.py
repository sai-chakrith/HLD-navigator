"""Learned local embeddings with persistent SQLite vectors and exact cosine ranking."""

import hashlib
import json
import math
import os
from pathlib import Path
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
    if os.getenv("HLD_NAVIGATOR_EMBED_BACKEND", "ollama") == "llama_cpp":
        return LlamaCppEmbedding(
            os.getenv("HLD_NAVIGATOR_EMBED_URL", "http://127.0.0.1:18882"),
            model,
            os.getenv("HLD_NAVIGATOR_EMBED_ARTIFACT"),
            os.getenv("HLD_NAVIGATOR_EMBED_DIGEST"),
        )
    if os.getenv("HLD_NAVIGATOR_EMBED_BACKEND", "ollama") != "ollama":
        raise ValueError("Unsupported embedding backend")
    return OllamaEmbedding(
        os.getenv("HLD_NAVIGATOR_OLLAMA_URL", "http://127.0.0.1:11434"),
        model,
        os.getenv("HLD_NAVIGATOR_EMBED_DIGEST"),
    )


class LlamaCppEmbedding:
    """Controlled CPU server adapter; operator starts the verified artifact locally."""

    def __init__(self, base, model, artifact, digest):
        if urlparse(base).scheme not in {"http", "https"} or urlparse(base).hostname not in {
            "localhost",
            "127.0.0.1",
            "::1",
        }:
            raise ValueError("Embedding endpoint must be local loopback")
        if not model or not digest or not artifact:
            raise ValueError("Model alias, local artifact and digest required")
        self.base, self.model = base.rstrip("/"), model
        self.artifact, self.digest = Path(artifact), digest.removeprefix("sha256:")
        self.identity = hashlib.sha256(
            f"{model}|{self.digest}|llama-cpp-mean-v1".encode()
        ).hexdigest()

    def request(self, path, payload=None):
        request = Request(
            self.base + path,
            data=json.dumps(payload).encode() if payload is not None else None,
            headers={"Content-Type": "application/json"},
        )
        with urlopen(request, timeout=90) as response:
            return json.load(response)

    def embed(self, texts):
        with self.artifact.open("rb") as file:
            if hashlib.file_digest(file, "sha256").hexdigest() != self.digest:
                raise ValueError("Local embedding artifact digest mismatch")
        models = self.request("/v1/models")["data"]
        if not any(m.get("id") == self.model for m in models):
            raise ValueError("Embedding server alias does not match configured model")
        for text in texts:
            tokens = self.request("/tokenize", {"content": text, "add_special": True})["tokens"]
            if len(tokens) + 2 > 512:
                raise ValueError("Embedding text exceeds verified BGE context; chunk explicitly")
        rows = self.request("/v1/embeddings", {"model": self.model, "input": texts})["data"]
        if sorted(row["index"] for row in rows) != list(range(len(texts))):
            raise ValueError("Embedding response index mismatch")
        vectors = [row["embedding"] for row in sorted(rows, key=lambda row: row["index"])]
        validate_vectors(vectors, len(texts))
        return vectors
