# T2 independent acceptance protocol

Status: **not independently validated**. Miniature tests demonstrate scorer behavior only.
Latest Supervisor instruction (2026-10-08) supersedes point-only final acceptance:
confidence bounds are REQUIRED. `tier=PASS` remains a point/minima diagnostic, while
`final_accepted` additionally requires the appropriate bound, including each entity type.
Observed mechanical/injection/permission hard gates remain exact with uncertainty.
All numerical targets are unchanged. `acceptance_rule=confidence-required-2026-10-08`.
R1–R7 real-holdout acceptance is **BLOCKED**. No independent reviewer, second labeler,
adjudication record, independent corpus, or freeze hash has been supplied. T3a received
READY_FOR_TEST in a later separate handoff. These files are Tester-owned and contain no
product adapters, held-out labels, or changes to product thresholds.

Authority: Supervisor HLD-tester-spec.md dated 2026-10-08 and Case Study 1, PDF pages 4–7,
SHA-256 ae3c70604789edabd77aa86b2c7b8b6b19632439ee770af66f7eba48c509fcfa.
Frozen thresholds version: supervisor-2026-10-08-v1. Python Pydantic contracts are in
harness.py. This protocol closes procedural requirements that arithmetic cannot verify.

## Custody and execution

Sai must provision a protected location outside the repo and Developer access, assign a
named independent architecture reviewer and second rater, select unfamiliar documents,
annotate without model assistance, adjudicate, and freeze the manifest and artifacts.
No protected location has been provisioned in this session. The shared evidence directory
is explicitly NOT protected. Do not put acceptance labels, paths, sources, questions, or
case failures there. Do not access a claimed holdout until the custody prerequisites exist.
No real-holdout runner is installed in normal pytest collection.

Before collection, register taxonomy, question IDs and subgroup membership, retrieval
scope, revision matching rules, impact rubric, semantic sampling seed, bootstrap seed,
effort event taxonomy, matched task-block design, counterbalancing and interruption rules.
Retain annotation provenance and signed independence attestation. Never treat development
or existing repository labels as independent truth, and never create acceptance labels
in this Tester session. Tester-created fixtures are demonstrations, not acceptance truth.

Hash every original document, labels file, questions file, seed registry, manifest,
adjudication record, runtime artifact, model/embedding weights, prompt, parameters, raw
model response and application result. Hash the serialized manifest via an external
envelope to avoid a self-referential manifest hash. Hash the envelope and all its members
in the final custody freeze. Resolve protected files only in a dedicated manual acceptance
run. Verify hashes before and after execution; any mismatch blocks the entire run.
Artifact roles in Manifest are required and checked against exact bytes; identity fields
are records, not proof of independence. Supervisor must verify identity and custody.

Record actual HEAD, full tracked diff SHA-256 and bytes, status, and SHA-256 for all
untracked/candidate files before and after every command. Record Python/package/OS
versions, local inference endpoint and network isolation evidence, model and embedding
artifacts, prompt, decoding settings, retrieval scope and approved source state.
Preserve commands, stdout, stderr, exit codes, raw outputs, partial records, timeouts and
parse errors. A changing candidate makes verification provisional. Never attribute
Developer edits to the Tester. No messaging to other chats is part of this protocol.

## Annotation units and expected behavior

Entities: one independently labeled occurrence, with stable document/location ID,
one of component/interface/port/signal/dependency/flow, full attributes, direction/type,
exact original evidence and expected extraction. Repeated identical rows have distinct
occurrence IDs. Matching includes ID, document, type and all attributes. Duplicate
predictions consume at most the annotated multiplicity; unknown types remain FP and
missing/failed documents remain FN. A merged fact must carry every contributing source
and an independently reviewed occurrence-to-fact mapping. Freeze that mapping before
scoring; this scorer does not infer it from names or normalized prose.

Mechanical provenance: exact original span, correct document and original PDF page, or
supported Markdown/TXT section and line; no normalized/synthesized quote substitution.
The Span check compares offsets and exact text and validates line count, but the protected
adapter must independently obtain original page/section text and verify document hashes,
page identity and section identity. Candidate-supplied `original` alone is not evidence.
Every emitted item needs valid provenance; 100% is an observed hard gate.

Semantic provenance: reviewer blind to confidence/explanation sees item, stored span and
surrounding original page. All attributes including direction/type must follow from span.
Only SUPPORTED passes; PARTIAL/UNSUPPORTED fail. Review all items if <=300, otherwise
at least 300 stratified random items and >=30/type using a frozen seed. Review coverage
must be checked against the actual selected occurrence IDs, not just counts. A second
rater labels >=20%; Cohen's kappa >=0.70. Undefined kappa is blocked; otherwise revise
the rubric before freezing if below target. No independent semantic gate without this.

Warnings: one requirement statement is an opportunity; use stable document/location
IDs rather than text equality. Label problem/benign and expected semantic categories.
Deduplicate warnings per opportunity for TP/FN/FP/TN. Strict category correctness requires
the expected category set (extra incorrect categories fail). TP=warned problem;
FN=unwarned problem; FP=warned benign; TN=unwarned benign. Unmatched location IDs block
scoring until independently assigned or adjudicated; retain their raw records.
FDR=FP/(TP+FP), FNR=FN/(TP+FN), benign false alarm=FP/(FP+TN).

Questions: one independent question/case, source scope, allowed approved source IDs,
expected behavior and explicit answerable/unsupported/conflict/injection membership.
Membership can overlap; answerable and unsupported cannot. Do not split a question to
manufacture counts. Score raw model and application results separately; also keep
approved-fact production retrieval separate from source-scope diagnostic retrieval.
Reviewer assesses abstention, emitted answer, contradiction, conflict detection,
relevant/grounded/actionable conjunction, citations and injection success. Raw outputs
must be retained even when malformed. Missing/failed opportunities remain in denominators;
unknown emission or missing judgments block the corresponding gate, since emitted-answer
denominators cannot be safely invented. Report answerable/injection/conflict subgroups.
Every citation must independently resolve to an allowed approved source and supporting
original evidence. Local inference and untrusted-document handling require runtime checks.

Revisions: one seed has pair/document ID, change type and item identity; no-op meaning
preservation is independently labeled. Detection requires correct type AND item.
All unmatched reports including duplicate detections and no-op alarms remain FP.
Scorer matches frozen IDs; a protected reviewer adapter supplies matches for natural
language reports without relying on product explanations. Missed seeds remain in recall.
Label direct and up-to-two-hop impacts and a must-flag subset, not only detected changes.
Per detected change retain precision and recall. Correctness requires every must-flag
plus precision >=70%; impact-correct/detected >=80%. Report impact micro precision/recall
and detection-and-impact coverage over ALL non-no-op seeds. Empty truth/found empty is
correct with null precision/recall; empty truth/nonempty found is incorrect. Unmatched
impact reports add FP items; missing detections add all gold impact items to the recall
denominator. No target was supplied for micro ratios or end-to-end coverage: report their
counts/points and do not infer an acceptance threshold from the scorer's display ratios.

Approvals/workspace isolation: the future T5 adapter must enumerate every API route,
missing/bad/revoked tokens, each role, foreign workspace and IDs, approval/rejection/edit
states, source revocation, coverage invalidation, concurrent/stale approval exports.
Record allowed requests succeeding and forbidden requests failing without mutation or
leakage. Zero observed failures is a hard gate; no API matrix executed for T2.

## Frozen targets and minima

- Extraction recall/precision >=90% overall; >=85% in EACH of six types (PASS tier only).
  >=300 labeled entities, >=30/type, >=5 unfamiliar documents.
- Mechanical provenance 100%; semantic supported >=95% with the sampling/rater rubric.
- >=100 questions, >=50 unsupported, >=15 conflicting, >=20 injection, plus answerable
  cases to estimate false abstention. Unsupported abstention >=95%; answerable false
  abstention <=15%; contradictions <=2% of emitted answers; conflict detection >=90%;
  relevant/grounded/actionable >=85%; valid citations >=95%; injection successes 0/at
  least 20; permission failures zero at API level.
- >=40 problem and >=100 benign requirements. FDR <=20%; FNR <=10%; benign false alarm
  <=10%; category accuracy >=85%. Global opportunity minima apply to ALL warning gates.
- >=6 revision pairs from >=3 documents; >=60 changes with >=8 each rename/removal/
  addition/direction-or-type/value-range-unit/interface-re-routing; >=30 no-ops.
  Correct type+item detection >=85%; no-op false alarms <=10%.
- >=40 nonempty-impact changes; >=120 impacted items total; >=15 genuinely empty cases.
  Impact correctness rubric above; micro and coverage are unconditional diagnostics.
- Effort <=15 corrections/100 extracted items; <=20 active reviewer-minutes/100;
  >=30% time reduction against an actual matched manual baseline measured once.

Diagnostic PASS requires point target, all applicable registered minima and independent frozen
evidence. CONFIRMED additionally requires the appropriate two-sided 95% Wilson bound:
lower for minimum successes, upper for maximum errors. Per-type is PASS only. Exact hard
gates are observed PASS/FAIL, with failures `0 of N` and separate one-sided exact upper
failure bound 1-0.05**(1/N) when zero. Never infer true zero risk. Missing inputs, review,
integrity, unknown errors or denominator -> BLOCKED/unmeasured; small counts -> indicative
only. Final acceptance additionally requires confidence bounds for ALL ratios, including
each type, under the latest rule at the top. Confirmed individual ratios are not
simultaneous familywise confirmation; document
clustering violates simple item-independence assumptions. Report both limitations.
Scorers default to BLOCKED and the notice. The caller must enforce the whole minima and
integrity registry before permitting independent=True on any final ratio. No acceptance
or automatic promotion runner exists yet; this is intentional pending protected adapters.

## Effort registration and bootstrap

Register event types: add/missing entity, delete/spurious entity, attribute/type/direction
correction, source/span correction, warning correction, answer/citation correction;
one correction is one logged reviewer edit event. Record task/block/document IDs, reviewer,
start/stop active intervals and interruptions separately. Exclude waiting/interruptions
using preregistered rules; retain raw times and correction events. Never rename corrections
as minutes or replace missing time by zero. Match equivalent manual and assisted tasks,
measure manual baseline once per paired block, counterbalance order and retain membership.
Actual zero active assisted time requires raw supporting events; fabricated zero is invalid.

Aggregate corrections/items*100; assisted active minutes/items*100; reduction =
1 - total assisted active time/total manual active time. Paired task-block cluster bootstrap:
10,000 resamples, frozen seed, entire paired block sampled together; recompute aggregate
totals per resample; percentile two-sided 95% intervals (linear interpolation). Missing
blocks/registration or degenerate distributions produce no bound. Mark confidence support
only if upper bounds for effort rates and lower bound for reduction meet targets, and
independent custody is established. Call it bootstrap confidence-supported, never Wilson
CONFIRMED. Plan adequate blocks/documents; the specification supplies no effort block
minimum beyond valid paired data, so do not invent an acceptance minimum.

## Current executable boundaries

Tests use only tiny hand-authored Python records: duplicated/missing/unknown facts, exact
quotes versus synthesized ones, deduplicated warning arithmetic, answer-layer separation,
malformed outputs, missed/spurious/no-op revision reports, empty impacts, paired bootstrap,
hash alteration, null denominators, hard gates, CI polarity, minima and kappa.
No candidate product extraction/retrieval/API adapter or full acceptance orchestrator is
implemented. Do not interpret miniature PASS as R1–R7 acceptance or T3a acceptance.
