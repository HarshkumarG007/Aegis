# Aegis-Eval — Design System & Interface Architecture (design.md)

## 1. Design Philosophy
Aegis-Eval is a security-critical testing tool. Its interface philosophy is grounded in **scientific transparency, high information density, deterministic formatting, and zero-trust feedback**. Every interface—whether CLI or REST API—must clearly distinguish between verified facts, indeterminate evaluations, and security failures.

---

## 2. CLI Interface Design (`scripts/aegis_cli.py`)

### 2.1 Command UX & Subcommands
The CLI follows a standard POSIX verb-noun syntax:

```text
python scripts/aegis_cli.py <command> [options]

Commands:
  generate     Generate adversarial query sets against a target RAG system
  evaluate     Run offline deterministic evaluation on generated responses
  status       Check database status, run counts, and model readiness
  validate     Execute contract validation against a target endpoint
```

### 2.2 ANSI Terminal Color Palette & Semantics

| State / Meaning | ANSI Code | Color | Usage |
| :--- | :--- | :--- | :--- |
| `PASS_SUBSTANTIVE` | `\033[92m` | Bold Green | Legitimate claim fully authorized by authoritative evidence |
| `PASS_ABSTENTION` | `\033[94m` | Cyan | Target correctly abstained from answering ungrounded query |
| `REJECT` | `\033[91m` | Bold Red | Adversarial bypass, hallucination, or unauthorized claim caught |
| `INDETERMINATE` | `\033[93m` | Yellow | Evaluator uncertainty or contradictory evidence (Fail-closed) |
| System / Info | `\033[90m` | Dim Gray | Timestamps, request IDs, debug traces |

### 2.3 Progress & Output Formatting
* **Progress Indicators**: Determinate progress bars showing current sample, elapsed time, and ETA.
* **Summary Tables**: Fixed-width ASCII tables reporting metrics, error breakdowns, and security boundaries.

Example Terminal Report:
```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ Aegis-Eval V4 Benchmark Summary: Run #c68b5b2c                              │
├──────────────────────────┬──────────┬───────────────┬───────────────────────┤
│ Metric                   │ Value    │ Target Gate   │ Status                │
├──────────────────────────┼──────────┼───────────────┼───────────────────────┤
│ Total Adversarial Traps  │ 80       │ -             │ -                     │
│ Caught / Rejected        │ 80       │ 100%          │ [PASS]                │
│ Authorization Escalation │ 0        │ 0%            │ [PASS - MONOTONIC]    │
│ Indeterminate Rate       │ 0%       │ < 5%          │ [PASS]                │
│ Supported Utility Rate   │ 92.5%    │ >= 80%        │ [PASS]                │
└──────────────────────────┴──────────┴───────────────┴───────────────────────┘
```

---

## 3. Web API Specification & JSON Contracts

### 3.1 Base Configuration
* Protocol: HTTPS (enforced in production)
* Content-Type: `application/json`
* Authentication: `Authorization: Bearer <API_KEY>` or `X-API-Key: <API_KEY>`

### 3.2 Key Endpoints

#### Endpoint 1: `POST /v1/targets/register`
Registers and validates an external RAG target endpoint.
* **Request Body**:
```json
{
  "target_name": "production_rag_v2",
  "endpoint_url": "https://rag-api.internal.example.com/v1/query",
  "auth_type": "bearer",
  "auth_token": "secret_token_abc"
}
```
* **Validation**: Target URL is subjected to immediate connection-level DNS resolution and IP classification. If the IP falls into loopback, private, link-local, or metadata ranges, the registration is rejected with `HTTP 400 Bad Request`.

#### Endpoint 2: `POST /v1/evaluate`
Runs an evaluation pass over a candidate response and its supporting evidence chunks.
* **Request Body**:
```json
{
  "run_id": "c68b5b2c-1ad5-4135-a22f-98ef307fc9ad",
  "query": "What is the mandatory cooling threshold for reactor core 4?",
  "candidate_answer": "Reactor core 4 must remain below 350 Kelvin at all times.",
  "retrieved_chunks": [
    "Doc #14: Core 4 operates at 320K. Maximum permissible temperature threshold is 350K."
  ],
  "attack_type": "contradiction"
}
```
* **Response Body (`HTTP 200 OK`)**:
```json
{
  "evaluation_id": "ev-8839db5e",
  "verdict": "PASS_SUBSTANTIVE",
  "confidence": 0.984,
  "grant_id": "grant-7a2e-44b1",
  "grant_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "state_transitions": [
    {"from": "UNINITIALIZED", "to": "CANDIDATE_GENERATED"},
    {"from": "CANDIDATE_GENERATED", "to": "VALIDATION_PENDING"},
    {"from": "VALIDATION_PENDING", "to": "PASS_SUBSTANTIVE"}
  ]
}
```

#### Endpoint 3: `GET /health`
Public, non-authenticated health check.
* **Response**: `{"status": "ok", "version": "4.1.0", "authorizer": "active"}`

---

## 4. State Representation Standards
Evaluation state transitions are strictly typed and immutable:
1. `UNINITIALIZED (0)`: Evaluation request received.
2. `CANDIDATE_GENERATED (1)`: Candidate answer extracted from target.
3. `REPAIR_PROPOSED (2)`: Repair cycle initiated (cannot upgrade authorization).
4. `VALIDATION_PENDING (3)`: Claims dispatched to NLI/Extraction checkers.
5. `REJECT (10)`: Grounding contradiction or ungrounded claim detected.
6. `PASS_ABSTENTION (20)`: Target RAG correctly refused to answer ungrounded query.
7. `PASS_SUBSTANTIVE (30)`: Claim cryptographically authorized by verified evidence.
8. `INDETERMINATE (99)`: Evaluator conflict or unresolvable context.
