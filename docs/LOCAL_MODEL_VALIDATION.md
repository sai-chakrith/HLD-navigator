# Reproduce actual CPU model and unfamiliar-document evaluation

The default application still uses lexical retrieval until a learned model is explicitly configured. Learned retrieval is not assumed better.

## Pinned artifacts

`tools/setup_local_models.py` downloads the official llama.cpp Windows CPU build b11490, the publisher's Qwen2.5-0.5B-Instruct Q4_K_M GGUF at revision 9217f5db79a29953eb74d5343926648285ec7e67, and ggml-org's BGE-small-en-v1.5 f16 conversion at revision 499bc8821c6b12b4e53c5bffcb21ec206f212d81. Exact URLs, byte sizes and SHA-256 values are in the script and `.data/local-inference/artifacts.json` after setup. BGE is a converted artifact; its source and hash are recorded rather than assuming publisher equivalence. Downloads stay under ignored `.data`. Range downloads check content ranges and final full-file hashes. Incomplete artifacts cannot execute.

```powershell
uv run python tools/setup_local_models.py
uv run python tools/local_benchmark.py
# Independent learned retrieval run:
uv run python tools/local_benchmark.py --embeddings-only --output docs/evidence/local-embedding.json
# Untuned public-document extraction and warning baseline:
uv run python tools/evaluate.py --manifest data/evaluation/public/manifest.json --output docs/evidence/public-baseline.json
```

The benchmark verifies model/archive hashes, starts task-owned CPU servers on loopback with free ports, uses four CPU threads, and stops them afterward. It uses the application's persistent indexing/search and raw answer-generation code. The answer and embedding servers use separate processes; they are run sequentially to reduce resource pressure. No ECU hardware or cloud inference is used. The setup requires internet access for public artifact downloads; inference runs locally. Disk usage is approximately 650 MB plus runtime extraction and logs.

The learned retrieval experiment uses four agent-selected questions across three frozen public KUKSA documents. Source statements are accessed in an isolated benchmark workspace, without asserting that the extracted inventory is approved. Full relevant passages and their ranks are retained. Model inputs beyond the BGE context limit fail explicitly instead of being silently truncated. BGE uses mean pooling with no query instruction prefix; this configuration is part of the result, not a general verdict on all embedding models.

Ten controlled answer cases include public-document facts, multiple recipients, compound units, negation, irrelevant evidence, missing requirements, contradictory units/directions and source prompt injection. Each stores the raw output, response hash, elapsed seconds, complete-quote integrity, raw abstention and application abstention. Preselected relevant evidence is checked separately from citation integrity. Raw failure hidden by the application's citation filter is still a model failure. These exact-evidence rules are a narrow controlled assessment; they do not prove general semantic entailment. Architecture reviewers must assess the raw responses against the full source.

## Interactive configuration

After hash verification, start the answer server using the flags retained in `local-model.json`, binding to loopback. Set `HLD_NAVIGATOR_CHAT_BACKEND=llama_cpp`, `HLD_NAVIGATOR_CHAT_MODEL=qwen` and `HLD_NAVIGATOR_LOCAL_URL=http://127.0.0.1:<answer-port>` before starting the API. The existing Ollama adapter remains available.

For the BGE server, use embedding/mean-pooling flags in the report. Set `HLD_NAVIGATOR_EMBED_BACKEND=llama_cpp`, `HLD_NAVIGATOR_EMBED_MODEL=bge`, `HLD_NAVIGATOR_EMBED_URL=http://127.0.0.1:<embedding-port>`, `HLD_NAVIGATOR_EMBED_ARTIFACT=<absolute path to bge.gguf>` and `HLD_NAVIGATOR_EMBED_DIGEST=f0b2fef971e8366438bfd2d9aefea1b0115919389448806d290237f638bae999`. Restart API and explicitly index the reviewed revision. Artifact drift, wrong server alias, oversized text, duplicate response indices and invalid vectors fail. The operator is responsible for starting the server with the verified artifact; the alias is not remote attestation of server internals.

## Independent review still required

Public files are frozen with commit, hashes and Apache-2.0 license in `data/evaluation/public/`. Their provisional selected-fact/warning annotations were written after baseline inspection. They are not exhaustive, independent, or OEM ground truth. Baseline failures are retained and extraction was not tuned on these results. Warning scores measure location/code matches against provisional annotations; an architecture reviewer must judge warning reason correctness and nuisance warnings.

The blank packet at `docs/reviewer-packet/reviewer-input.json` records independent annotations, unsupported requirements and actual active annotation/review/correction seconds. Follow its INSTRUCTIONS before opening baseline predictions. No reviewer identity, qualification, acceptance or correction time has been fabricated. Model results, public baseline scores and regression counts do not demonstrate automotive reliability or productivity gains.

## Recorded outcome

The real Qwen run completed ten cases: zero correct quote-format outputs and zero correct raw abstentions among four expected abstention cases. Required source text appears in five of six answerable cases, but this is only a content-presence check. Separate inspection found missing conversion evidence, unnecessary TLS evidence, unresolved contradictory echoes, irrelevant answers and injected-instruction contamination. The citation filter rejected every response. This model configuration is not accepted for pilot answers. The raw failures are preserved rather than replacing them with a more favorable prompt/run. Independent architecture reviewer assessment remains pending.
