# Aegis-Eval Release Notes

## V2.5.0 (Asymmetric Verifier & Set-Level Sufficiency)
- **Focus:** Recovering utility without compromising the pristine safety boundary.
- **Milestone:** Replaced binary chunk-level sufficiency with holistic Set-Level Sufficiency evaluating the unified context via `cross-encoder`. Upgraded the post-generation verifier to an Asymmetric Claim-Level Repair loop (`SUPPORTED`, `UNSUPPORTED`, `CONTRADICTED`, `UNCERTAIN`).
- **Key Validation:** Strict 6-arm ablation matrix (Arms A–F) on an independent 30-query challenge set for Mistral 7B and Llama 3 8B.
- **The Tradeoff:** Perfect 100% OOD interception (zero leakage) maintained. However, utility recovery was minimal (Answerable queries retained: 22% Mistral, 17% Llama). The primary bottleneck is extreme False Abstention.


## V2.4.1 (Calibration and Deterministic Control - Frozen)
- **Focus:** Deterministic conflict abstention, claim-level mapping, and repair loops.
- **Milestone:** Neutralized the Generative "Compulsion to Merge" and "Compulsion to Stitch".
- **Key Validation:** Unseen Holdout validation across Mistral 7B and Llama 3 8B. 100% OOD safety (median latency 0.08s).
- **The Tradeoff:** Answerable preservation collapsed to 10-15%. Verifier rigidity is the next boundary.

## V2.4.0 (Hardened RAG Pipeline - Mechanism Validated)
- **Focus:** Externalizing grounding policy.
- **Milestone:** Introduced MS-MARCO sufficiency gate and DeBERTa-v3 post-generation verifier.
- **Key Validation:** Strict 5-way paired ablation isolating the failures of LLM prompting against external gates.

## V2.3.0 (The Offline Multi-Model Scientific Pilot)
- **Focus:** Decoupling generation from evaluation for mathematically provable provenance.
- **Milestone:** Bypassed Uvicorn/FastAPI threading instabilities and 8GB VRAM contention limits.
- **Discovery:** 7B+ models demonstrate severe "confident hallucination" regression compared to 1.5B models on OOD data.

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
