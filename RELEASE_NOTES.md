# Aegis-Eval Release Notes

## V2.2.0-beta.1 (Release Candidate - Signed Off)
- **Tag:** `v2.2.0-beta.1`
- **Commit:** `3ef6a0de`
- **Focus:** 60-query independent benchmark, exact-match contradiction bounding, calibration gates.
- **Calibration Sign-off:** Positive 98.3%, Negative 0.0%, Mixed 48.3%.
- **Independent Baseline:** 46.7% overall (Multi-hop: 91.7%, Contradiction: 16.7%).
- **Key Validation:** Byte-for-byte offline deterministic replay verified on SQLite backend.

## [v2.1.0] - Aegis-Eval V2.1 (Implementation and Benchmark Infrastructure Complete)

V2.1 marks a major milestone for Aegis-Eval. We have completed the transition from a simple deterministic evaluator into a reproducible, target-agnostic adversarial RAG benchmark harness with strict provenance and byte-for-byte deterministic replayability.

The V2.1 baseline is now frozen and acts as a verified benchmark infrastructure. 

### Key Achievements

#### 1. Advanced Semantic Evaluation (Frozen Mechanisms)
The semantic evaluator has been significantly upgraded and frozen:
- **Claim-level Provenance**: Answers are now parsed into atomic claims, isolating the exact evidence verifying or contradicting them.
- **Contradiction Evaluator**: Deterministic logic that compares each claim against *all relevant retrieved chunks*, aggregating via the max contradiction score using a strict 0.85 NLI threshold.
- **Groundedness Evaluator**: Requires every factual claim to be supported by retrieved evidence, mapping to strict deterministic boundaries (`SUPPORTED`, `PARTIAL`, `UNSUPPORTED`).
- **Multi-hop Verification**: Validates whether *all* required factual premises for a query are verifiably supported.
- **Non-lexical Ambiguity**: Applies NLI models to validate if multiple potential interpretations are explicitly acknowledged in the answer.

#### 2. Robust Benchmark Infrastructure
We have established a completely isolated execution and reporting pipeline:
- **Infrastructure/Semantic Separation**: Infrastructure failures (e.g., timeouts, crashes, HTTP errors) instantly yield a verifiable target fail without ever polluting the semantic evaluator.
- **Strict Preflight Verification**: Prior to kicking off heavy model inferences, the `aegis_cli` conducts a robust preflight check ensuring local databases, mandatory hash configurations, target health, and local model artifacts are fully operational.
- **Immutable Run Artifacts**: Every executed run is stored as an immutable structure linking the evaluation manifest, adversarial queries, responses, and exact evaluation verdicts into a JSON artifact bundle.
- **Byte-for-byte Offline Replay**: A completely isolated replay mechanism that recalculates the local metrics directly from the raw data artifacts without hitting the target or changing the evaluation. Replays are 100% byte-for-byte deterministic.

#### 3. Repository & Deployment Hygiene
- Re-architected schema decoupling the payload dictionaries into structured JSON metadata elements for safe offline storage.
- Full git-history audit confirming all large language model `.gguf` binaries and potential DB credentials have been completely purged from the repository timeline.

### Next Steps (V2.2 - Benchmark Expansion)
With the V2.1 evaluator baseline frozen and verified, the focus shifts to scaling the benchmark to measure models (without touching the evaluation instrument):
- Expand the adversarial corpus substantially beyond the baseline 6 queries.
- Add multiple independently authored cases per mechanism.
- Setup known-positive and known-negative target fixtures.
- Test multiple target models under the same immutable manifest.
- Establish aggregate metrics and publish benchmark artifacts.
