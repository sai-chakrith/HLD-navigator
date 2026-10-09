# Local synthesized answer development experiment

## Executed final development run - 09 October 2026

The current application uses source-command quarantine and llama.cpp's
schema-constrained JSON response format. Original source blocks remain available;
obvious assistant-directed lines are excluded from generation and cannot be cited.
This heuristic is incomplete and can quarantine legitimate lines. Mechanical
citation validity does not establish semantic support.

The separate fixed tester development set was run three times, once per candidate,
with 30 cases each. Earlier raw failures remain in `docs/evidence/answer-run-v1/`
and `answer-run-v2/`. Final identities are `docs/evidence/answer-candidate-v3.json`
and `answer-runtime-v3.json`; outputs/hash-bound judgments are in `answer-run-v3/`.

Final: 29/30 raw contract passes; 8/8 must-abstain; zero instruction-following in
five injection cases. Developer-assessed useful complete: 8/12 answerable,
3/5 conflicts and 4/5 injections. A wrong recipient claim and unsupported revision
recommendations remain failures. Keep excerpt mode as default; synthesis is
experimental and requires human review. Cases used during development are not
an independent holdout, confidence estimate or OEM safety qualification.

End-to-end synthesis is recorded in `docs/evidence/live-model-http.json`: correct
fictional Torque uint16/Nm answer. One integration question is not a quality benchmark.

Reproduce on the same frozen source after starting the model in another terminal:

```powershell
$env:HLD_NAVIGATOR_CHAT_BACKEND='llama_cpp'
$env:HLD_NAVIGATOR_LOCAL_URL='http://127.0.0.1:18883'
$env:HLD_NAVIGATOR_CHAT_MODEL='qwen7b'
uv run python tester_acceptance/s1b_runner.py run --ready-for-test --candidate-identity docs/evidence/answer-candidate-v3.json --runtime-metadata docs/evidence/answer-runtime-v3.json --output .data/new-answer-run
uv run python tools/smoke.py --with-model --question 'What type and unit does the Torque signal use?'
```

Metadata describes the recorded i7-12700H Windows CPU run. On another machine,
record its actual configuration rather than copying that identity. The protocol
is documented in the [pinned llama.cpp release](https://github.com/ggml-org/llama.cpp/blob/b11490/tools/server/README.md#post-v1chatcompletions-openai-compatible-chat-completions-api).

## Earlier developer harness and provisioning

This is a pilot development experiment, not independent validation. No frozen
evaluation corpus or labels are used. The Developer authored 12 synthetic cases
before inference: five answerable, three must-abstain, two conflicts, two injections.
The Tester owns the separate acceptance development set.

## Reproduce

From the repository root, with the existing pinned llama.cpp CPU runtime installed:

```powershell
uv run python tools/setup_s1b_model.py --runtime-dir .data/local-inference
uv run python tools/s1b_experiment.py --runtime-dir .data/local-inference --output docs/evidence/s1b-developer.json
```

The downloader is an explicit development provisioning tool. Its current resume
implementation uses 1 MiB ranges with bounded retries and checks the complete
official SHA256 before accepting either shard. `--workers` controls download
concurrency; it does not affect model inference. Product inference
uses only a configured loopback service and never downloads weights. Official
Qwen2.5-7B-Instruct Q4_K_M shards are pinned to revision
`bb5d59e06d9551d752d08b292a50eb208b07ab1f`, Apache-2.0:

| Shard | Bytes | SHA256 |
| --- | ---: | --- |
| 00001-of-00002 | 3993201344 | dfce12e3862a5283ccfb88221b48480e58745165de856439950d0f22590580db |
| 00002-of-00002 | 689872288 | 539cf93f78e887edea1c04e2d7d8cdaca9d01dae9c9025bcb8accbe29df3d72a |

The official artifact metadata is available at
https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/tree/bb5d59e06d9551d752d08b292a50eb208b07ab1f.
Weights remain ignored under `.data/`. Download requires network access; inference
does not. The runner verifies both hashes before starting a loopback CPU server,
uses four threads, one slot, a 2048-token context and 512-token response budget.
Each inference request has a 180-second bound and no retries. It stops only its own server.

To run a separate verified interactive service after provisioning:

```powershell
python tools/serve_local_model.py answer
python tools/serve_local_model.py embedding
```

Run each in its own terminal. The launcher verifies every deployed runtime file
against the pinned runtime archive, checks model hashes, binds only to loopback,
and prints the API environment configuration. Keep the default excerpt mode until
the answer model's live evaluation has been reviewed. Model weights remain local.

Example product configuration for a separately started local server:

```powershell
$env:HLD_NAVIGATOR_CHAT_BACKEND='llama_cpp'
$env:HLD_NAVIGATOR_LOCAL_URL='http://127.0.0.1:8080'
$env:HLD_NAVIGATOR_CHAT_MODEL='qwen7b'
```

## Contract and limits

Each model claim contains natural-language text and one or more citations. `S1`
means the first eligible retrieved block in this request; the application returns
its persistent `block_id` alongside the exact snippet. IDs are request-local and
must be resolved using that response's evidence. Snippets must be literal nonblank
substrings; whitespace, case and punctuation are not repaired. Unknown IDs,
missing citations, malformed JSON and bad snippets abstain with explicit reasons.
The legacy complete-block `supported()` oracle is retained unchanged for baseline
and Supervisor/Tester adjudication. Existing tests are not rewritten.

Missing evidence abstains. Conflict output must disclose alternatives and cite at
least two distinct cited alternatives (which can occur in one block). Sources
remain untrusted user data; the system prompt prohibits
following embedded instructions. Existing workspace authorization, verified
provenance, source approval, fact review and revision-selection gates remain in
the API before generation. A model outage yields an explicit abstention reason.

Literal snippets do **not** prove relevance, entailment, negation preservation or
contradiction detection. A fabricated claim could cite a real snippet. These need
semantic evaluation and architecture review; the guard does not claim to solve
them. Developer keyword and source-selection checks are only diagnostic proxies.

The report includes all cases, complete prompts, retrieved synthetic blocks, raw
model output, application output, latency, errors and hashes. Baseline uses the
unchanged prompt from commit `7e90273` on exactly the same cases and model. No
relabeling, retries or fallback successes are removed from denominators. Raw
contract validity, answerable abstention, conflict behavior and injection following
are separate observations. Human usefulness/entailment assessment stays pending.
