# Aegis-Eval — Security Policy & Threat Model (security.md)

## 1. Security Objectives
Aegis-Eval evaluates the safety, grounding, and security of external RAG systems. Consequently, its own runtime must maintain the highest standards of assurance:
1. **Prevent Capability Forgery**: No external input or API interaction may forge an `AuthorizedAnswer` capability.
2. **Enforce Authorization-State Monotonicity**: Once a candidate answer is rejected or abstained, repair loops cannot upgrade it to substantive authorization without fresh, verified evidence.
3. **Defend Network Perimeter**: Prevent Aegis from being weaponized as an SSRF proxy against local or cloud-internal infrastructure.
4. **Supply-Chain Integrity**: Cryptographically bind dependencies, code, and model weights into a verifiable Trusted Computing Base (TCB).

---

## 2. Threat Model (STRIDE Analysis)

| Threat Category | Potential Attack Vector in RAG Evaluation | Aegis-Eval Countermeasure |
| :--- | :--- | :--- |
| **Spoofing** | Attacker spoofs target identity or submits forged API key. | Constant-time HMAC key verification (`hmac.compare_digest`); hashed key storage. |
| **Tampering** | Attacker tampers with authorization grant hash or alters candidate answer post-verification. | Capability token binds answer text, evidence IDs, and timestamp into a cryptographic SHA-256 grant hash. |
| **Repudiation** | Target owner claims evaluation was manipulated or inaccurate. | Append-only structured audit logs capturing raw query, target response, retrieved chunks, and evaluation traces. |
| **Information Disclosure** | Leakage of API credentials or target RAG proprietary data via logs. | Strict audit log sanitization; credentials stripped before formatting; zero secret printing in tracebacks. |
| **Denial of Service** | Flooding evaluation endpoints with massive contexts or slow-read attacks. | Connection/read timeouts (10s), request body limits (1MB), response body limits (5MB), token-bucket rate limiting. |
| **Elevation of Privilege** | Semantic prompt injection causing LLM judge to output false PASS; or SSRF pivoting to `169.254.169.254`. | Decoupled deterministic NLI (no LLM judge); connection-level DNS-pinned socket pool rejecting private subnets. |

---

## 3. Network Security & SSRF Defense

### 3.1 Strict IP Classification
All target URLs registered with Aegis are resolved and verified against prohibited CIDR ranges:
* `127.0.0.0/8` (IPv4 Loopback)
* `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` (RFC 1918 Private Networks)
* `169.254.0.0/16` (Link-Local / Cloud Metadata Services e.g. AWS/GCP/Azure)
* `224.0.0.0/4` (Multicast)
* `0.0.0.0/8` (This network)
* `::1`, `fe80::/10` (IPv6 Loopback and Link-Local)
* `::ffff:0:0/96` (IPv4-mapped IPv6 ranges)

### 3.2 Invariant: Connection-Level DNS Pinning
To defeat DNS rebinding (where hostname resolves to a public IP on validation, but resolves to `127.0.0.1` when `requests.get()` connects):
1. Aegis resolves the hostname *once*.
2. All returned IP addresses are validated. If any IP is private or blocked, the connection fails closed immediately.
3. The HTTP connection is opened directly to the validated IP.
4. The original hostname is supplied only via the HTTP `Host` header and TLS SNI extension.
5. Invariant: `validated_destination == connected_destination`.

---

## 4. Authorization & Capability-Based Security

### 4.1 Capability Token Minting
The `Authorizer` singleton (`src/aegis_eval/v4/authorizer.py`) is the sole entity permitted to mint an `AuthorizedAnswer`. An `AuthorizedAnswer` requires:
* Unique `grant_id` (UUIDv4).
* `claim_hash`: SHA-256 hash of the normalized candidate answer string.
* `evidence_hash`: SHA-256 hash of the set of verified supporting evidence chunks.
* `evaluator_signature`: Cryptographic verification that the deterministic checker passed.

### 4.2 Monotonic State Progression
Evaluation states progress in a strict partial order:
$$\text{UNINITIALIZED} \rightarrow \text{CANDIDATE\_GENERATED} \rightarrow \text{VALIDATION\_PENDING} \rightarrow \{\text{REJECT}, \text{PASS\_ABSTENTION}, \text{PASS\_SUBSTANTIVE}\}$$
Any transition attempting to move from $\{\text{REJECT}, \text{PASS\_ABSTENTION}, \text{INDETERMINATE}\}$ into $\text{PASS\_SUBSTANTIVE}$ raises `MonotonicityViolationError` and emits a critical security alert.

---

## 5. Secrets Management & Operational Security
* **Zero Secrets in Code**: No API keys, database passwords, or private tokens may be hardcoded.
* **Environment-Driven Configuration**: Secrets loaded strictly via environment variables with strict preflight validation.
* **Hash-Pinned Dependencies**: Dependencies locked with exact hashes in `requirements-frozen.txt`.
* **Model Provenance**: Model weights verified against cryptographic SHA-256 hashes per `docs/MODEL_PROVENANCE.md`.

---

## 6. Security Review Checklist (Pre-Merge Gate)
- [ ] Are all new network requests routed through `PinnedHTTPSConnectionPool`?
- [ ] Is input validation enforced on all external parameters via Pydantic schemas?
- [ ] Are SQL queries strictly parameterized via SQLAlchemy ORM (zero raw string formatting)?
- [ ] Does any new code log sensitive variables or authorization headers?
- [ ] Are state transitions strictly monotonic with respect to the `Authorizer` singleton?
- [ ] Have all new dependencies been checked for known vulnerabilities?
