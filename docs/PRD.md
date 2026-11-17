# Product Requirements Document (PRD) — Aegis-Eval

## 1. Product Overview
**Aegis-Eval** is a security-grade evaluation framework and capability-based authorization harness designed to test Retrieval-Augmented Generation (RAG) systems against deterministic, type-matched adversarial attacks. 

Unlike conventional evaluation suites that use an LLM-as-a-judge (introducing non-deterministic, hallucinatory scoring) or simplistic string matching (which is brittle and produces false negatives), Aegis enforces a mathematically verified, capability-based security model: **Authorization-State Monotonicity**.

---

## 2. Problem Statement
Enterprise and production RAG pipelines fail silently when confronted with adversarial queries, ambiguous context, ungrounded extrapolations, and representation attacks:
1. **Evaluation Non-Determinism**: Using an LLM to judge another LLM's output introduces evaluator drift, sycophancy, and prompt-injection vulnerability into the evaluation metric itself.
2. **Authorization Escalation via Semantic Repairs**: In iterative RAG architectures, multi-turn repair loops and query re-writers can launder ungrounded claims into authorized responses, converting initial rejections into false passes.
3. **SSRF and Network Vulnerabilities**: Evaluation frameworks that query external or target RAG endpoints without strict network isolation allow DNS rebinding, internal subnet scanning (e.g., `169.254.169.254`, loopback addresses), and redirect attacks.
4. **Supply-Chain Brittleness**: Floating dependencies and unpinned weights allow silent degradation of the trusted computing base (TCB).

---

## 3. Product Vision
To establish the industry-standard benchmark and zero-trust authorization runtime for RAG applications—delivering provable security, reproducible offline evaluation, hardware-honest execution on consumer GPUs (≤ 8GB VRAM), and mathematical state monotonicity guarantees.

---

## 4. Target Audience and User Personas
* **AI Security Engineers & Red Teams**: Require automated, deterministic adversarial fuzzing suites to discover grounding bypasses, representation traps, and prompt injections in enterprise RAG systems.
* **RAG Application Developers**: Require local, rapid, CI/CD-compatible test harnesses to verify that retrieval and generation pipelines abstain correctly when evidence is insufficient or contradictory.
* **Compliance & Model Governance Officers**: Require tamper-evident, append-only audit traces of evaluation decisions with cryptographic model weight provenance.

---

## 5. User Needs and Pain Points
| User Need | Pain Point Addressed |
| :--- | :--- |
| **Deterministic Pass/Fail Decisions** | LLM judges change their verdicts across runs or fail to catch subtle grounding contradictions. |
| **Tamper-Proof Authorization** | Repair pipelines that modify answers until they superficially pass, despite lacking evidence. |
| **Safe API Interactions** | Automated evaluation tools probing untrusted external URLs causing SSRF vulnerabilities. |
| **Zero-Cost Local Execution** | Expensive cloud evaluation APIs ($100s/run) that cannot run in air-gapped or private environments. |

---

## 6. Core Features & Capabilities

### 6.1 Adversarial Query Generation
* Few-shot, constrained adversary model generating four distinct attack types:
  * **Contradiction**: Injects claims conflicting directly with retrieved authoritative chunks.
  * **Out-of-Domain / Unanswerable**: Tests whether the RAG pipeline correctly abstains.
  * **Multi-Hop / Distributed Evidence**: Requires synthesis across non-adjacent chunks.
  * **Representation Traps**: Syntactic and semantic formulations designed to exploit tokenizer and abstraction limits.

### 6.2 Deterministic Evaluator Dispatcher
* Routes candidate responses through type-matched deterministic evaluators:
  * DeBERTa-v3 cross-encoder NLI for factual contradictions.
  * Proposition-bound extraction for conditionality and groundedness.
  * Keyword and semantic coverage checking.
  * Ambiguity detection with strict `INDETERMINATE` tracking.

### 6.3 V4 Capability-Based Authorizer
* Singleton state machine enforcing **Authorization-State Monotonicity**.
* Implements the core invariant: *No sequence of candidate generation, repair, rejection, or retry may convert an unauthorized claim into `PASS_SUBSTANTIVE` without fresh, independently validated semantic evidence.*
* Mints an immutable `AuthorizedAnswer` capability bound to a cryptographic grant hash.

### 6.4 Secure API & Orchestration Layer (Gate P3)
* Token-bucket rate limiting and constant-time API key validation.
* Connection-level DNS pinning and strict IP classification blocking loopback, private ranges, link-local, and cloud metadata targets (`169.254.169.254`).
* Redirect destination re-validation preventing DNS rebinding.
* Append-only structured audit logging.

---

## 7. MVP Scope vs. Production (V4.x)
* **V1 (MVP)**: Basic exact-match adversarial harness (Retired).
* **V2.x**: Hardened RAG with deterministic NLI evidence gates (Retired).
* **V3.x**: End-to-end recovery and representation fuzzing (Retired).
* **V4.x (Current Production)**: 
  * Gates P0–P4 complete: Monotonic Authorizer, Frozen V3.4 Regression Corpus, Independent Generalization, Secure API/Network Layer, Supply-Chain Reproducibility.
  * Gate P5 (Operational Security): Up next.
  * Gate P6 (Scientific Validation) & Gate P7 (Production Release): Scheduled.

---

## 8. Functional Requirements
1. **FR-1**: System must evaluate responses against queries with 0% silent fallback to permissive defaults.
2. **FR-2**: All evaluator uncertainty must emit explicit `INDETERMINATE` states—never silent PASS or REJECT.
3. **FR-3**: Authorizer state transitions must be mathematically strictly monotonic.
4. **FR-4**: API layer must reject any target URL resolving to private/metadata IP spaces before initiating a socket connection.
5. **FR-5**: Evaluator must execute offline using pinned local model weights (GGUF via llama-cpp-python / local DeBERTa).

---

## 9. Non-Functional Requirements
1. **NFR-1 (Hardware Ceiling)**: Maximum VRAM consumption during full evaluation must not exceed 8GB (tested on NVIDIA RTX 4060 8GB).
2. **NFR-2 (Deterministic Reproducibility)**: Replay of an identical seed and query corpus must yield bit-for-bit identical verdicts.
3. **NFR-3 (Infrastructure Cost)**: $0 runtime infrastructure dependency. No paid closed-source API calls required for core evaluation.
4. **NFR-4 (Security Fail-Closed)**: Unauthenticated requests or invalid grants must fail immediately with HTTP 401/403 without invoking authorizer logic.

---

## 10. Success Metrics
* **Security Failure Rate**: 0% authorization escalation across the frozen 80-attack V3.4 regression suite.
* **SSRF Resistance**: 100% block rate on private, loopback, metadata, and DNS-rebinding targets.
* **Adversarial Generalization**: Utility retention ≥ 80% on supported control queries while maintaining 0% false authorizations on adversarial traps.
