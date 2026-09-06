# Aegis-Eval: The Evolution of Adversarial RAG Evaluation 🛡️

Aegis-Eval is a rigorous, open-source evaluation framework designed to test Retrieval-Augmented Generation (RAG) pipelines against deterministic, type-matched adversarial attacks. 

After traversing through exact-match brittleness, NLI hallucinations, conditional extraction failures, and representation limits, Aegis has evolved into a production-ready security framework enforcing **Authorization-State Monotonicity**.

## 🚀 The Aegis Journey & Architectures

### V1: The Foundation
*The beginning of adversarial generation and basic matching.*
```text
Adversary Model ──> Target RAG ──> Exact Match Evaluator
(Generates query)                      (String inclusion)
```
- **The Problem**: Exact string matching is far too brittle for abstract concepts, leading to false negatives.

### V2.x: Hardened RAG & Deterministic Extraction
*Externalizing grounding policy and structurally extracting conditions.*
```text
                         Query + Evidence
                                │
                                ▼
                        ┌───────────────┐
                        │ Evidence Gate │ (MS-MARCO + NLI)
                        └───────┬───────┘
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
               INSUFFICIENT  CONFLICT   SUFFICIENT
                    │           │           │
                 ABSTAIN    constrained   grounded
                            generation    generation
                                │           │
                                └─────┬─────┘
                                      ▼
                      ┌──────────────────────────────┐
                      │ Syntactic Extractor (E0)     │ (Proposition Binding)
                      └──────────────┬───────────────┘
                                     │
                                PASS/REJECT
```
- **The Breakthrough**: Ripped grounding out of the LLM and placed it into discrete NLI gates. Replaced probabilistic NLI with Proposition-Bound structural extraction (E+E0) to crush ambiguity.

### V3.x: End-to-End Recovery & Representation Attacks
*Eliminating the NLI trigger, but discovering the representation boundary flaws.*
```text
Generator ──> Claim Extraction ──> Asymmetric Repair Loop ──> Authorized State
```
- **The Discovery**: V3.4 Independent Black-Box Red Teaming proved that perfect representation is impossible. Abstraction loss combined with pipeline repair bypasses leads directly to **authorization amplification**.

### V4: Authorization-State Monotonicity (Production Readiness)
*The shift from semantic extraction to capability-based security. Implementing immutable authorization capabilities bound by strict network and orchestration boundaries.*
```text
External Request
      │
      ▼
┌──────────────┐
│  Middleware  │ (Auth & Rate Limiting, Audit Logging)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ SSRF Defense │ (Connection-level DNS pinning, strict IP validation)
└──────┬───────┘
       │
       ▼
┌──────────────┐    ┌──────────────────────────────────┐
│ Orchestration│───>│          V4 Authorizer           │ (The Singleton)
└──────┬───────┘    │  Enforces monotonic transitions  │
       │            └────────────────┬─────────────────┘
       │                             │ Mints Capability
       ▼                             ▼
┌──────────────┐    ┌──────────────────────────────────┐
│   Response   │<───│         AuthorizedAnswer         │ (Runtime Validated)
└──────────────┘    └──────────────────────────────────┘
```
- **The Breakthrough**: 
  - **Gate P0-P2**: Replaced implicit state with a mathematically monotonic Authorization State Machine. A repair operation can never mint `PASS_SUBSTANTIVE` without a cryptographically bound `AuthorizationGrant`.
  - **Gate P3**: Hardened the API layer against SSRF, DNS Rebinding, and fail-closed the orchestration to prevent API-level capability forgery.

---

## 📂 Repository Git Tree

```text
Aegis/
├── docs/
│   ├── JOURNAL_V1_The_Foundation.md
│   ├── JOURNAL_V2.1_Benchmark_Infrastructure.md
│   ├── JOURNAL_V2.2_Deterministic_Leap.md
│   ├── JOURNAL_V2.3_Llama3_Pilot.md
│   ├── JOURNAL_V2.4_Hardened_RAG.md
│   ├── JOURNAL_V2.4.1_Calibration.md
│   ├── JOURNAL_V2.5_Scientific_Validation.md
│   ├── JOURNAL_V2.6_Causal_Diagnosis.md
│   ├── JOURNAL_V2.7_Conflict_Classifier.md
│   ├── JOURNAL_V2.8_Structured_Conflict.md
│   ├── JOURNAL_V2.9_Adversarial_Safety.md
│   ├── JOURNAL_V3.0_End_to_End_Recovery.md
│   ├── JOURNAL_V3.1_Deterministic_Reconstruction.md
│   ├── JOURNAL_V3.2_Factorial_Recovery.md
│   ├── JOURNAL_V3.3_Representation_Attacks.md
│   └── JOURNAL_V3.4_BlackBox_RedTeam.md
├── experiments/
│   └── v2.3/llama3-8b/
├── reports/
│   ├── benchmark-v3.4/                       # Immutable V3.4 forensic data
│   ├── benchmark-v4.1-p2/                    # Gate P2 Independent Generalization
│   └── benchmark-p3-closure/                 # Gate P3 API & Network Security Reports
├── scripts/
│   └── aegis_cli.py                          # Unified CLI
├── src/
│   └── aegis_eval/
│       ├── data/                             # Manifest structures and DB schemas
│       ├── evaluator/                        # NLI Cross-encoders, Aggregators, Metrics
│       ├── hardened_rag/                     # V2/V3 Evidence Gates & Verification mechanisms
│       ├── targets/                          # Multi-Model target integration contracts
│       └── v4/                               # V4 Production Security Architecture
│           ├── api/                          # SSRF Protections and Middleware
│           ├── state.py                      # Monotonic Authorization States
│           └── authorizer.py                 # Core Authorizer Singleton
└── tests/
    └── security/                             # Comprehensive V4/P1/P2/P3 Security Suites
```

---

## 📚 Essential Reading (The Aegis Lore)

- [📖 **The MAANG Engineer Journal: V3.4 Independent Black-Box Red Teaming**](docs/JOURNAL_V3.4_BlackBox_RedTeam.md)
  *Subjecting the system to 80 valid, independent, adjudicated adversarial traps. Exposing 19 bypasses and 4 repair state monotonicity violations, proving that perfect representation is impossible and we must design for state monotonicity.*
- [📖 **The MAANG Engineer Journal: V3.0 End-to-End Utility Recovery**](docs/JOURNAL_V3.0_End_to_End_Recovery.md)
  *A 2x2 factorial experiment that uncovered the true limits of RAG pipelines.*
- [📖 **The MAANG Engineer Journal: V2.9 Adversarial Safety Generalization**](docs/JOURNAL_V2.9_Adversarial_Safety.md)
  *Stress-testing the conditional logic against 220 false-conditionality traps.*
- [🚀 **Release Notes**](RELEASE_NOTES.md)
  *The formal, meticulous changelog of our relentless march toward benchmarking perfection.*

## 📈 Current Status: V4 Production Readiness Roadmap
Aegis is currently marching through the rigorous Production Readiness gates.
- **[x] Gate P0:** Security Architecture (Monotonicity and Capability Enforcement)
- **[x] Gate P1:** Security Testing & Regression (Frozen V3.4 failure suites)
- **[x] Gate P2:** Independent Generalization (Single-Model-Family Evaluation)
- **[x] Gate P3:** API & Network Security (SSRF, DNS Rebinding, Rate Limits, Auditability)
- **[ ] Gate P4:** Supply-Chain Reproducibility *(Up Next)*

---

## 🛠️ Getting Started (V4 CLI)

Aegis-Eval operates via a unified CLI (`scripts/aegis_cli.py`).

### 1. Environment Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

### 2. Run an Offline Multi-Model Evaluation

Generate the raw responses from a target:
```powershell
python scripts/aegis_cli.py generate --target http://127.0.0.1:8000/query --output runs/my-model-generation.json
```

Evaluate the responses offline:
```powershell
$env:DATABASE_URL="sqlite:///aegis_eval.db"
python scripts/aegis_cli.py evaluate --responses runs/my-model-generation.json --queries reports/benchmark-v2.2.0/adversarial-v2.2.0.json
```
