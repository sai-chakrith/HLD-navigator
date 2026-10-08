# Second review: acceptance record

The 5/10 assessment identifies real omissions. The fixes here address its reproduced parser defects, not its entire acceptance decision.

## Reproduce the corrected failure cases

Run `uv run pytest tests/test_compound_prose.py -q`. Before-fix records are `evidence/compound-before.txt` (nine failures) and `evidence/predicate-before.txt` (two additional failures). Supported compound producer/receiver clauses now produce separate edges. Every recognized action is checked against consumed source spans; unknown component predicates also require review. Conditions and exceptions produce blocking warnings with original text/location, rather than an unconditional edge. Conditional topology is not modeled. A signed report can exclude unresolved scope; it cannot certify that scope complete.

Upload `examples/revision-review/v1.md` and `v2.md` as two revisions of one title. Review source and every entity. The first has two declared dependencies and no findings; the second changes TorqueIn to uint32 and BrakeIn to a provided port. Export flags direction, port-type and interface-type mismatches; Compare lists the two changed ports and possible impacts. This is a developer-authored mixed prose/table regression example. It contains no real OCR or independently confirmed ECU defects.

## Independent document acceptance (pending)

Required inputs: permission to use HLD documents, a separate evaluation custodian and two architecture reviewers. Before opening documents for development, the custodian selects and hashes documents by family/revision, retains an inaccessible holdout and records provenance/license. Reviewers independently annotate components, interfaces, ports, signals, qualified edges and source locations; adjudicate differences and retain both initial annotations. Add agreed supported fields to the evaluation manifest, and separately inventory unsupported/qualified requirements so those misses are never hidden by narrowing the schema.

Run `uv run python tools/evaluate.py --manifest <frozen-manifest.json> --output <report.json> --models`. Keep the report, manifest, source hashes and annotations. Report TP/FP/FN and correction minutes per field, including relationships the schema cannot represent. Record warning precision/recall separately. Do not alter the holdout after observing failures. None of the included examples qualifies as this independent corpus.

## Model-answer acceptance (pending)

Required inputs: running local Ollama, installed embedding and answer artifacts, their exact `/api/tags` digests, hardware/runtime record and independent question annotations. Configure README variables. The evaluation report now records manifest/document hashes, runtime, embedding identity, retrieved evidence, raw model response and its hash. The answer tag is recorded; its digest must be captured by the operator and remains explicitly pending in the report. Archive `/api/tags` with the run.

Annotate questions before running: direct facts, multi-clause relationships, absent requirements, contradictory statements/revisions, exceptions, irrelevant but lexically similar passages, and malicious instructions embedded in sources. For each query, record expected behavior in the manifest. Review the report's semantic_review fields against the full source: relevance, entailment, necessary evidence completeness, contradiction handling, appropriate abstention and injection resistance. Use true/false/not-applicable with justification, reviewer identity and active review seconds. Have a second reviewer adjudicate. Report each dimension separately with its evaluated denominator and confidence intervals; full-block quote support is only a citation-integrity measure. It does not score these dimensions. Lexical recall/MRR and embedding recall/MRR remain separate retrieval metrics.

## Real OCR demonstration (pending)

Required inputs: Tesseract executable/language data and authorized genuine scanned HLD pages with checked transcription and architecture annotations. Follow README OCR configuration, ingest a scan and record page/line errors, missed requirements and correction time. Include a diagram-only page to demonstrate unresolved topology. Mock TSV and digitally generated PDF tests cannot substitute for this run.

## Supervised value measurement (pending)

Recruit architects/testers and register matched tasks, sample size, acceptance thresholds and exclusions before execution. Counterbalance manual-first and assisted-first tasks using different comparable documents to reduce learning effects. Log participant/task/document hashes, assigned method, active authoring seconds, active review seconds, correction seconds, proposed/accepted cases, missed requirements and findings independently confirmed by a second reviewer. Retain rejected proposals and all time intervals. Compare matched task times and coverage; publish raw anonymized measurements and uncertainty. No time savings or engineering benefit is currently measured.

## Remaining product limitations

The parser recognizes a limited grammar and identifiers; arbitrary phrasing, pronouns, units and diagram topology can still be missed. Conservative warnings can produce false positives. Qualifiers are blocked, not interpreted. The quote checker can accept a fully quoted but irrelevant or contradictory answer; this is an unresolved answer-quality limitation. Real OEM extraction, genuine OCR, learned model behavior, independent reviewer acceptance and measured value are NOT_RUN. These dependencies cannot be replaced with synthetic scores.
