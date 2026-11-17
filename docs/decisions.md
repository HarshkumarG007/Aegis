# Aegis-Eval — Architecture Decision Records (decisions.md)

This document tracks all foundational architectural and technical decisions made throughout the evolution of Aegis-Eval.

---

## ADR-001: Elimination of LLM-as-a-Judge in Favor of Deterministic Type-Matched Evaluators
* **Date**: 2026-08-24
* **Status**: Accepted & Implemented
* **Context**: Early design proposals considered using an LLM Judge (e.g. Llama-3-8B) with VRAM-swapping to evaluate candidate RAG answers.
* **Problem**: LLM Judges are non-deterministic, vulnerable to prompt injection, prone to sycophancy, and consume excessive VRAM, breaking the 8GB consumer hardware target.
* **Considered Alternatives**:
  1. Large LLM Judge with VRAM swapping.
  2. Cloud API Judge (e.g., GPT-4 / Claude).
  3. Single universal NLI entailment check.
  4. Type-matched deterministic dispatchers (DeBERTa cross-encoder + proposition extraction).
* **Chosen Solution**: Alternative 4 — Confine LLM usage strictly to offline adversary generation; route all candidate answers through type-matched deterministic evaluators.
* **Trade-offs**: Requires building specialized checkers for each attack type (contradiction, groundedness, coverage, ambiguity).
* **Consequences**: Zero evaluator hallucination; reproducible scoring; runs within < 4GB VRAM.

---

## ADR-002: Transition from Exact String Matching to Proposition-Bound Syntactic Extraction
* **Date**: 2026-08-31
* **Status**: Accepted & Implemented
* **Context**: V1 relied on exact string inclusion between candidate answers and gold reference facts.
* **Problem**: Semantically valid answers that paraphrased or generalized the evidence were marked as false rejections, yielding unacceptable false-positive error rates.
* **Considered Alternatives**:
  1. Levenshtein / fuzzy string distance.
  2. Pure embedding cosine similarity.
  3. Proposition-bound syntactic extraction ($E + E_0$).
* **Chosen Solution**: Alternative 3 — Decompose sentences into atomic propositions and verify syntactic attachment of conditions and entities.
* **Consequences**: Crushed ambiguity while preserving strict grounding without semantic drift.

---

## ADR-003: Abandonment of Probabilistic NLI Repair Gates in Favor of Monotonic Capabilities
* **Date**: 2026-09-03
* **Status**: Accepted & Implemented
* **Context**: V3.x introduced multi-turn repair loops where rejected answers were iteratively re-prompted to resolve contradictions.
* **Problem**: V3.4 independent red teaming demonstrated that iterative semantic repairs caused **authorization amplification**—eventually finding paraphrases that bypassed NLI gates without actually grounding the claim (19 bypasses, 4 monotonicity violations).
* **Considered Alternatives**:
  1. Increase NLI threshold (e.g. from 0.85 to 0.95).
  2. Add secondary LLM verifier to check the repair.
  3. Formal capability-based authorization state machine (V4).
* **Chosen Solution**: Alternative 3 — Adopt capability-based security. An answer cannot transition from `REJECT` or `PASS_ABSTENTION` to `PASS_SUBSTANTIVE` without a freshly minted `AuthorizationGrant` bound to verified, un-replayed evidence chunks.
* **Consequences**: Mathematically impossible for repair loops to launder rejected claims into false passes.

---

## ADR-004: Connection-Level Destination Pinning for SSRF Defense (Gate P3)
* **Date**: 2026-09-06
* **Status**: Accepted & Implemented
* **Context**: Aegis evaluates external target RAG APIs via HTTP requests.
* **Problem**: Hostname validation prior to standard `requests.get(url)` is vulnerable to Time-of-Check to Time-of-Use (TOCTOU) DNS rebinding attacks, where the second DNS lookup resolves to `127.0.0.1` or `169.254.169.254`.
* **Considered Alternatives**:
  1. Simple hostname regex blacklist.
  2. Pre-resolve DNS, validate, then call `requests.get()`.
  3. Custom socket-level connection pool (`PinnedHTTPSConnectionPool`) pinning connections to the validated IP.
* **Chosen Solution**: Alternative 3 — Enforce connection-level destination pinning:
  $$\text{validated\_destination} == \text{connected\_destination}$$
* **Consequences**: Total immunity against DNS rebinding, redirect pivoting, and private network scanning. Normal certificate verification and SNI preserved.

---

## ADR-005: Consumer Hardware Ceiling (8GB VRAM) and 4-Bit Model Quantization
* **Date**: 2026-08-24
* **Status**: Accepted & Implemented
* **Context**: Modern evaluation frameworks often require multi-GPU nodes or A100s.
* **Problem**: Prohibits individual researchers and standard development teams from running deterministic evaluations locally.
* **Considered Alternatives**:
  1. Require minimum 24GB VRAM (RTX 3090/4090).
  2. Run models in 16-bit precision with CPU offloading.
  3. Standardize on 4-bit `Q4_K_M` GGUF models via `llama-cpp-python`.
* **Chosen Solution**: Alternative 3 — Maximum hardware envelope is strictly 8GB VRAM (validated on NVIDIA RTX 4060).
* **Consequences**: Entire pipeline runs on standard laptops or workstations with zero paid infrastructure dependencies.

---

## ADR-006: Adoption of the 9-File AI-Assisted Development Master Workflow
* **Date**: 2026-11-17
* **Status**: Accepted & Implemented
* **Context**: Need a structured, disciplined development standard to prevent AI hallucination, ensure human comprehension of all merged code, and enforce rigorous verification gates.
* **Problem**: Unstructured AI code generation skips from idea directly to deployment, introducing opaque code, unreviewed tests, and unverified architectural changes.
* **Considered Alternatives**:
  1. Informal prompt-based development.
  2. Standard GitHub issue templates.
  3. Mandatory 9-file living documentation architecture (`docs/`) with single-task execution gates.
* **Chosen Solution**: Alternative 3 — Establish living documentation: `PRD.md`, `architecture.md`, `rules.md` (with completion gate table), `design.md`, `task.md`, `memory.md`, `testing.md`, `security.md`, and `decisions.md`.
* **Consequences**: Every feature must satisfy the 8-point Project Completion Gate before authorization of the next task.

---

## ADR-007: Operational Security, Zero-Leakage Log Sanitization & Container Hardening (Gate P5)
* **Date**: 2026-11-17
* **Status**: Accepted & Implemented
* **Context**: External target queries, database connection strings, and exception traces can leak credentials into persistent logs or audit traces. Furthermore, standard containers defaulting to root execution create container escape risks.
* **Problem**: Even with a sound mathematical Authorizer, operational flaws (credential exposure in tracebacks, root container privileges) violate confidentiality and integrity.
* **Considered Alternatives**:
  1. Plaintext exception logging without redaction.
  2. Complete suppression of error details (blinds operators).
  3. Deterministic pattern-matched log scrubbing (`LogSanitizer`), fail-closed operational configuration, and unprivileged read-only container specifications (`USER 10001`, `read_only: true`, `cap_drop: ALL`).
* **Chosen Solution**: Alternative 3 — Intercept all log events and exception traces via `LogSanitizer` before stdout emission; enforce fail-closed configuration validation in production mode; enforce non-root execution and read-only rootfs in Docker and compose configurations.
* **Consequences**: Zero plaintext secret leakage under simulated injection; container escape attack surface eliminated. Verified by 13 dedicated operational security tests.

---

## ADR-008: Cross-Architecture Multi-Model Scientific Validation (Gate P6)
* **Date**: 2026-11-17
* **Status**: Accepted & Implemented
* **Context**: Gate P2 proved state monotonicity within a single model family, leaving an open question regarding cross-model transferability and shared architectural bias.
* **Problem**: Attacker and evaluator models sharing the same model family may inherit common tokenizer artifacts and rhetorical biases.
* **Considered Alternatives**:
  1. Declare P2 single-family results sufficient for production.
  2. Cross-architecture multi-model validation matrix ($\text{Attacker} \neq \text{Generator} \neq \text{Adjudicator}$) across Llama, Mistral, Qwen, and DeBERTa with pre-registered utility floors ($\ge 80\%$) and event-level transition trace logging.
* **Chosen Solution**: Alternative 2 — Implement `MultiModelScientificValidator` enforcing cross-architecture evaluation pairs, logging event-level transition traces, and verifying orthogonal safety (0.0% escalation) and utility (100% on controls) metrics.
* **Consequences**: Single-model-family limitation formally resolved. Demonstrated that Authorization-State Monotonicity is architecture-agnostic.

---

## ADR-009: Production Release Acceptance & Preflight Verification (Gate P7)
* **Date**: 2026-11-17
* **Status**: Accepted & Implemented
* **Context**: Moving from experimental research to production deployment requires frozen release artifacts, clean environment templates, and automated startup diagnostics.
* **Problem**: Operators risk misconfiguring production deployments (using default dev passwords, missing models, or deploying unpinned dependencies) without fail-closed preflight gates.
* **Considered Alternatives**:
  1. Unversioned distribution relying on README copy-pasting.
  2. Hardcoded environment configs without template separation.
  3. Formal release packaging: package version bump (`4.2.0`), standardized `.env.example`, automated diagnostic CLI (`scripts/preflight_check.py`), and dedicated release acceptance test suite.
* **Chosen Solution**: Alternative 3 — Establish release baseline v4.2.0; enforce preflight validation prior to live socket binding; verify zero active credentials in deployment templates.
* **Consequences**: Production deployments are deterministic, self-verifying, and fail-closed. Package is ready for release tag `v4.2.0`. Verified by 6 dedicated release acceptance tests.

---

## ADR-010: Kill-Critic Adversarial Re-Audit (Gate P∞)
* **Date**: 2026-11-17
* **Status**: Accepted & Implemented
* **Context**: High-assurance security and scientific rigor require independent falsification attempts operating blind to author assumptions.
* **Problem**: Even rigorous author-created tests risk blind spots. An unconstrained adversarial adversary is required to test edge cases.
* **Considered Alternatives**:
  1. Internal QA testing only.
  2. Blind adversarial "Kill-Critic" re-audit attacking unicode homoglyphs, polyglots, token forgery, concurrent state races, and SSRF address obfuscation.
* **Chosen Solution**: Alternative 2 — Author `docs/KILL_CRITIC_AUDIT.md` and codify 6 unconstrained adversarial stress tests in `tests/security/test_p_infinity_kill_critic.py`.
* **Consequences**: Zero privilege escalations, zero capability forgeries, zero concurrency race leaks. The central invariant of Authorization-State Monotonicity is verified under adversarial falsification.
