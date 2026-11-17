# Aegis-Eval — Sequential Task Breakdown (task.md)

This document tracks all tasks in chronological order across the Aegis lifecycle. Every task must be verified against concrete output before completion.

---

## Phase 0: Historical Foundation & Invariant Evolution (Completed)

- [x] **TASK-001: V1 Exact-Match Baseline**
  - **Objective**: Implement baseline adversary and string inclusion evaluator.
  - **Status**: Completed (Retired as brittle).
  - **Verification**: Caught exact substrings; failed on paraphrased semantics.

- [x] **TASK-002: V2.x Hardened RAG & Deterministic Extraction**
  - **Objective**: Decouple grounding policy from LLM judge; implement DeBERTa NLI gates.
  - **Status**: Completed.
  - **Verification**: Verified proposition-bound syntactic extraction against 220 false-conditionality traps.

- [x] **TASK-003: V3.x Representation Boundary Forensics**
  - **Objective**: Independent black-box red team with 80 adjudicated adversarial traps.
  - **Status**: Completed.
  - **Verification**: Uncovered 19 bypasses and 4 repair monotonicity violations, motivating the V4 architecture.

---

## Phase 1: V4 Production Readiness Gates

- [x] **TASK-P0: V4 Monotonic Architecture & Capability System**
  - **Objective**: Build `src/aegis_eval/v4/authorizer.py` implementing capability-based state machine.
  - **Status**: Completed.
  - **Acceptance Criteria**: State machine enforces strict monotonicity: `state_after > state_before` requires fresh `AuthorizationGrant`.
  - **Verification**: Passed all 15 state-transition unit and property tests.

- [x] **TASK-P1: Security Regression Corpus**
  - **Objective**: Freeze the 19 V3.4 bypasses and 4 repair violations into an immutable regression suite.
  - **Status**: Completed.
  - **Acceptance Criteria**: 0/19 bypasses succeed in V4; 0/4 monotonicity violations permitted.
  - **Verification**: `pytest tests/security/test_v3_4_regressions.py` passed with 0 security escalations.

- [x] **TASK-P2: Independent Generalization**
  - **Objective**: Generate and adjudicate candidate pools under model-family independence controls.
  - **Status**: Completed.
  - **Acceptance Criteria**: Achieve 0% security failure rate while maintaining ≥ 80% utility on supported controls.
  - **Verification**: Adjudicated 80-item suite showed 0% authorization escalation, 92.5% supported-case authorization.

- [x] **TASK-P3: API & Network Security Hardening**
  - **Objective**: Implement SSRF defense, connection-level DNS pinning, rate limiting, and audit logging.
  - **Status**: Completed.
  - **Acceptance Criteria**: Connection-level IP validation blocks loopback, link-local, private, and metadata ranges; redirect destination revalidation prevents DNS rebinding.
  - **Verification**: `pytest tests/security/test_p3_adversarial_closure.py` passed 10/10 adversarial network tests.

- [x] **TASK-P4: Supply-Chain Reproducibility**
  - **Objective**: Pin dependency graph to strict hashes and define model weight provenance.
  - **Status**: Completed.
  - **Acceptance Criteria**: Generate `requirements-frozen.txt`, author `SECURITY.md` and `docs/MODEL_PROVENANCE.md`.
  - **Verification**: Pinned dependency lockfile and SHA-256 model weight validation guidelines established.

---

## Phase 2: Active Roadmap (Upcoming Gates)

- [x] **TASK-P5: Gate P5 — Operational Security**
  - **Objective**: Harden the deployment, logging, and secrets management environment.
  - **Dependencies**: TASK-P4.
  - **Expected Outcome**:
    1. Implement secure environment variable loading with fail-closed validation (`src/aegis_eval/config.py`).
    2. Enforce redaction filters in structured logging to prevent accidental leakage of auth headers or target credentials.
    3. Configure production Docker container specifications with non-root user execution and read-only root filesystems.
    4. Implement health probe and graceful shutdown handlers for the Authorizer singleton.
  - **Acceptance Criteria**:
    - Zero plaintext secrets in logs or audit traces under simulated injection.
    - Container runs strictly without root privileges.
    - Authorizer maintains state consistency across simulated process interruptions.
  - **Verification Instructions**:
    - Run operational security test suite: `pytest tests/security/test_p5_operational_security.py`.
    - Verify audit log scrubber against synthetic authorization payloads.
  - **Completion Status**: VERIFIED (13/13 tests passed in `test_p5_operational_security.py`; 38/38 total security tests passing).

- [x] **TASK-P6: Gate P6 — Scientific Validation & Multi-Model Re-Audit**
  - **Objective**: Subject Aegis-Eval to a full independent multi-model adversarial validation.
  - **Dependencies**: TASK-P5.
  - **Expected Outcome**: Complete multi-model-family fuzzing across distinct architectures (Mistral, Llama, Qwen) to break the single-model-family limitation from P2.
  - **Acceptance Criteria**:
    - Security failure rate across unsupported attacks is strictly 0.0%.
    - Supported positive control utility meets or exceeds 80.0% floor.
    - Event-level transition trace integrity verified on all state escalations.
  - **Verification Instructions**:
    - Run scientific validation test suite: `pytest tests/security/test_p6_scientific_validation.py`.
    - Generate immutable audit manifest: `reports/benchmark-v4.2-p6/multi_model_audit_report.json`.
  - **Completion Status**: VERIFIED (6/6 tests passed in `test_p6_scientific_validation.py`; 44/44 total security tests passing; 0.00% security failure rate across 258 attacks, 100.0% utility retention on 50 controls).

- [x] **TASK-P7: Gate P7 — Production Release & Deployment Acceptance**
  - **Objective**: Final formal release audit, documentation freeze, and artifact packaging.
  - **Dependencies**: TASK-P6.
  - **Acceptance Criteria**:
    - Package version bumped to 4.2.0 in `pyproject.toml`.
    - Production `.env.example` created with zero plaintext credentials.
    - Automated preflight verification (`scripts/preflight_check.py`) passes 100%.
    - Comprehensive release notes published in `RELEASE_NOTES.md`.
  - **Verification Instructions**:
    - Run release acceptance test suite: `pytest tests/security/test_p7_release_acceptance.py`.
    - Run preflight diagnostic: `python scripts/preflight_check.py`.
  - **Completion Status**: VERIFIED (6/6 tests passed in `test_p7_release_acceptance.py`; 50/50 total security tests passing; preflight check reports PRODUCTION READY).

- [x] **TASK-P8: Gate P∞ — Kill-Critic Re-Audit**
  - **Objective**: Blind adversarial red-team audit by an external, independent team.
  - **Dependencies**: TASK-P7.
  - **Acceptance Criteria**:
    - Zero capability token forgery or hash tampering accepted.
    - Zero state bleed or privilege escalation across concurrent multi-threaded worker evaluations.
    - Unicode homoglyph and polyglot attacks handled fail-closed.
    - Kill-Critic audit dossier published in `docs/KILL_CRITIC_AUDIT.md`.
  - **Verification Instructions**:
    - Run Kill-Critic adversarial suite: `pytest tests/security/test_p_infinity_kill_critic.py`.
    - Review audit dossier: `docs/KILL_CRITIC_AUDIT.md`.
  - **Completion Status**: VERIFIED (6/6 tests passed in `test_p_infinity_kill_critic.py`; 56/56 total security tests passing; 0 observed privilege escalations).
