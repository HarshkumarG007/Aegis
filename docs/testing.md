# Aegis-Eval — Testing Strategy & Verification Protocol (testing.md)

## 1. Testing Philosophy
In Aegis-Eval, **a passing test suite is not proof that the system is secure or complete**. Tests prove only that the specific execution paths tested did not violate the specific assertions written.

Our testing doctrine follows three foundational tenets:
1. **Adversarial Invariant Verification**: Tests must actively attempt to break the system invariants using fuzzing, property-based inputs, and malformed structures.
2. **First-Class Uncertainty (`INDETERMINATE`)**: Test infrastructure must never silently turn evaluator uncertainty or missing data into a binary PASS or REJECT.
3. **Separation of Security from Utility**: Every regression report must answer two independent questions:
   * *Did an unauthorized claim get authorized?* (Safety failure — release blocker).
   * *Did a legitimate claim lose utility?* (Utility regression — performance issue).

---

## 2. Test Suite Architecture

```text
tests/
├── unit/                                  # Component-level deterministic tests
│   ├── test_evaluators.py                 # NLI, groundedness, coverage checks
│   ├── test_evaluator_mechanisms.py       # Dispatcher routing verification
│   ├── test_failure_boundaries.py         # Type classification failure bounds
│   ├── test_integration_contract.py       # Target RAG payload contracts
│   └── test_metrics.py                    # Metric calculations & aggregations
├── integration/                           # Subsystem integration & persistence
│   └── test_replay.py                     # Deterministic execution replay
└── security/                              # High-assurance security & regression gates
    ├── authorization_monotonicity/        # Property-based monotonicity fuzzing
    │   ├── test_property_monotonicity.py  # Fuzzing out-of-order state transitions
    │   └── test_v3_4_regressions.py       # 19 frozen V3.4 bypasses & 4 repair traps
    ├── provenance/                        # Model & grant integrity
    │   └── test_provenance_tampering.py   # Tampered capability & grant detection
    └── test_p3_adversarial_closure.py     # SSRF, DNS rebinding, redirect chains
```

---

## 3. Detailed Test Categories

### 3.1 Unit Testing (`tests/unit/`)
* **Objective**: Verify individual deterministic evaluators in complete isolation from external networks or GPU hardware.
* **Requirements**: Mock model weights using synthetic probability vectors or deterministic fixture responses. Execution time must remain under 5 seconds.

### 3.2 Security Monotonicity Fuzzing (`tests/security/authorization_monotonicity/`)
* **Core Property**:
  $$\text{state\_after} > \text{state\_before} \implies \text{fresh\_validated\_evidence} \land \text{bound\_grant}$$
* **Fuzz Targets**:
  * Repeated repair attempts on rejected candidates.
  * Out-of-order transitions (e.g., `UNINITIALIZED` directly to `PASS_SUBSTANTIVE`).
  * Contradictory candidates (claiming both $A$ and $\neg A$).
  * Malformed candidate metadata, empty strings, null bytes, and unicode exploits.
  * Transitions from `PASS_ABSTENTION` to `PASS_SUBSTANTIVE`.
  * Transitions from `REJECT` to `PASS_SUBSTANTIVE`.

### 3.3 Historical Regression Corpus (Gate P1)
* **Dataset**: Immutable V3.4 failure corpus (`reports/benchmark-v3.4/`).
* **Assertions**: 
  * All 19 V3.4 black-box bypasses must evaluate to `REJECT`.
  * All 4 repair monotonicity violations must be caught and blocked.
  * Zero original attack strings are modified to make tests pass.

### 3.4 API & Network Security Suites (Gate P3)
* **SSRF & DNS Rebinding**:
  * Tests that DNS resolution 1 returning benign IP followed by DNS resolution 2 returning `127.0.0.1` is completely prevented by connection-level destination pinning.
  * Tests blocking of IPv4-mapped IPv6, decimal/octal/hex IP notations, and cloud metadata (`169.254.169.254`).
* **Redirect Chains**:
  * Validates that redirect hops cannot escape to internal subnets (`HTTPS -> 127.0.0.1`).
* **Authentication & Rate Limiting**:
  * Constant-time credential checks.
  * Token-bucket rate limiting enforcement under burst loads.

---

## 4. Test Execution Instructions

### Running Unit & Integration Tests:
```powershell
pytest tests/unit tests/integration -v
```

### Running the Complete Security Regression Suite:
```powershell
pytest tests/security -v
```

### Running Adversarial Network Closure (SSRF & Rebinding):
```powershell
pytest tests/security/test_p3_adversarial_closure.py -v
```

---

## 5. Coverage Expectations & Release Gates
* **Security Critical Paths (`src/aegis_eval/v4/`)**: **100% statement and branch coverage**.
* **Core Evaluators (`src/aegis_eval/evaluator/`)**: **≥ 90% statement coverage**.
* **Zero Permissive Fallbacks**: Any unhandled exception during evaluation must trigger a fail-closed `REJECT` or explicit `INDETERMINATE`.
