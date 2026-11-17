# Aegis-Eval — System Architecture Specification (V4.x)

## 1. System Overview
Aegis-Eval is architected as an adversarial evaluation harness and capability-based authorization runtime for Retrieval-Augmented Generation (RAG) systems. The system decouples generative hypothesis formulation from deterministic authorization, ensuring that answers produced by RAG pipelines cannot gain authoritative status without verifiable, non-monotonic evidence grants.

---

## 2. High-Level Architecture

```mermaid
flowchart TD
    subgraph Client / External Boundary
        CLI[Aegis CLI: aegis_cli.py]
        API_REQ[External HTTP Request]
    end

    subgraph Security Perimeter
        MID[Authentication & Rate Limiting Middleware]
        SSRF[SSRF Protector: PinnedHTTPSConnectionPool]
        AUDIT[(Structured Audit Logger)]
    end

    subgraph Generation & Target Pipeline
        ADV[Adversary Generator: Qwen / Mistral GGUF]
        TGT[Target RAG System under Evaluation]
    end

    subgraph Evaluation & Authorization Engine (TCB)
        DISP{Evaluator Dispatcher}
        NLI[DeBERTa-v3 NLI Cross-Encoder]
        EXT[Proposition-Bound Groundedness Checker]
        AUTH[V4 Authorizer Singleton: State Machine]
        CAP[Minted Capability: AuthorizedAnswer]
    end

    API_REQ --> MID
    CLI --> MID
    MID --> AUDIT
    MID --> SSRF
    SSRF --> TGT
    ADV -->|Adversarial Query| TGT
    TGT -->|Raw Answer + Evidence Chunks| DISP
    DISP --> NLI
    DISP --> EXT
    NLI -->|Validation Result| AUTH
    EXT -->|Validation Result| AUTH
    AUTH -->|Grant Validation & Monotonic Transition| CAP
```

---

## 3. Technology Stack & Justification

| Layer | Component | Version / Technology | Justification |
| :--- | :--- | :--- | :--- |
| **Language** | Python | 3.11+ | Broad ecosystem support for ML, asynchronous APIs, and typing. |
| **ML Inference** | `llama-cpp-python` | 0.2.x+ | Enables execution of 4-bit quantized GGUF models on consumer GPUs (≤ 8GB VRAM). |
| **NLI Cross-Encoder** | PyTorch / Transformers | DeBERTa-v3-large | State-of-the-art zero-shot cross-encoder for natural language inference. |
| **Web / API** | FastAPI / Uvicorn | 0.110+ | High-performance asynchronous REST API with native Pydantic schema validation. |
| **Database** | SQLite / PostgreSQL | SQLAlchemy 2.0 | Dual-mode: SQLite for zero-setup local runs; Postgres for enterprise CI/CD. |
| **Networking** | `urllib3` / `requests` | Custom Pinned Pool | Custom socket connection handler for strict connection-level DNS pinning. |
| **Testing** | `pytest` / `hypothesis` | 8.x+ | Property-based fuzzing and deterministic regression verification. |

---

## 4. Backend & Core Engine Architecture

### 4.1 The V4 Authorizer Singleton (`src/aegis_eval/v4/authorizer.py`)
The Authorizer is the central Trusted Computing Base (TCB) of Aegis. It enforces strict mathematical monotonicity over evaluation states.

#### Authorization States
```text
UNINITIALIZED (0)
      │
      ▼
CANDIDATE_GENERATED (1)
      │
      ▼
REPAIR_PROPOSED (2)
      │
      ▼
VALIDATION_PENDING (3)
      │
      ├──────────────────────┬──────────────────────┐
      ▼                      ▼                      ▼
REJECT (10)          PASS_ABSTENTION (20)    PASS_SUBSTANTIVE (30)
```
* **State Monotonicity Invariant**: Once an evaluation path transitions to `REJECT` or `PASS_ABSTENTION`, no subsequent operation or repair loop can promote it to `PASS_SUBSTANTIVE` without a freshly minted, cryptographically verified `AuthorizationGrant` bound to authoritative, un-replayed evidence.

### 4.2 Evaluator Dispatcher (`src/aegis_eval/evaluator/dispatcher.py`)
Replaces universal LLM judges with type-matched evaluators:
1. **Contradiction Evaluator**: Evaluates claim pairs using DeBERTa cross-encoder entailment/contradiction probabilities.
2. **Groundedness Evaluator**: Checks candidate assertions against retrieved chunk spans using proposition binding.
3. **Coverage Evaluator**: Verifies that multi-hop sub-queries are each independently satisfied.
4. **Ambiguity Evaluator**: Detects unresolvable queries and mandates `PASS_ABSTENTION`.

---

## 5. Network & Security Architecture (Gate P3)

### 5.1 Connection-Level DNS Pinning (`src/aegis_eval/v4/api/ssrf_protector.py`)
To prevent DNS rebinding attacks:
1. The hostname is resolved to an IP address.
2. The IP address is classified against blacklists (loopback `127.0.0.0/8`, private `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, link-local `169.254.0.0/16`, IPv6 loopback `::1`, and IPv4-mapped IPv6).
3. The underlying socket connection is established directly to the pre-validated IP address, while preserving the original hostname in TLS Server Name Indication (SNI) and Host headers.
4. Every redirect hop is independently intercepted and re-validated through this same sequence.
5. Invariant: `validated_destination == connected_destination`.

### 5.2 API Middleware & Rate Limiting (`src/aegis_eval/v4/api/middleware.py`)
* **Authentication**: Enforces API keys via constant-time string comparison (`hmac.compare_digest`). API keys are hashed; secrets are never logged.
* **Rate Limiting**: In-memory token-bucket limiter per authenticated principal.
* **Audit Logging**: Structured JSON events recording timestamp, principal, endpoint, target URL, and authorization decisions.

---

## 6. Database & Persistence Architecture
Aegis uses SQLAlchemy with an abstraction layer supporting SQLite and PostgreSQL:
* `runs`: Metadata for benchmark execution runs (ID, start time, target, commit hash, configuration).
* `queries`: Generated adversarial queries (attack type, prompt, expected outcome, seed).
* `verdicts`: Granular evaluation results (verdict, raw model response, evidence spans, grant ID).
* `audit_events`: Security-critical API and authorization transitions.

---

## 7. Folder Structure

```text
Aegis/
├── docs/                   # 9 mandatory workflow & architecture documents
├── experiments/            # Controlled benchmark configurations
├── models/                 # Quantized GGUF models & weight verification
├── reports/                # Immutable execution evidence and test reports
├── scripts/                # Unified CLI entrypoints (aegis_cli.py)
├── src/                    # Core source codebase
│   └── aegis_eval/
│       ├── adversary/      # Query generation & few-shot prompts
│       ├── data/           # Manifests, schemas, models
│       ├── evaluator/      # Deterministic evaluators & NLI cross-encoders
│       ├── hardened_rag/   # Evidence gating and syntactic extractors
│       ├── targets/        # Target RAG contracts & adapters
│       └── v4/             # V4 Capability Authorizer, API, SSRF defense
└── tests/                  # Verification test suites
    ├── integration/        # End-to-end replay & persistence tests
    ├── security/           # Monotonicity, SSRF, DNS rebinding, provenance
    └── unit/               # Deterministic evaluator & contract unit tests
```

---

## 8. Deployment & Hardware Constraints
* **VRAM Ceiling**: Maximum allowable GPU memory footprint is 8GB (strict adherence to consumer hardware, e.g., NVIDIA GeForce RTX 4060).
* **Quantization**: Models run in 4-bit (`Q4_K_M`) quantization via GGUF.
* **Air-Gapped Operation**: All models and dependencies operate completely offline; no cloud inference calls are made.
