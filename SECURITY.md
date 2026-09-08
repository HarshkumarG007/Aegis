# Aegis Security Policy

The Aegis framework is an adversarial RAG evaluation harness built to enforce mathematically rigorous, capability-based security bounds over semantic generation.

## Supported Versions

Only the current production version (V4) receives security updates.

| Version | Supported          | Notes                                      |
|---------|--------------------|--------------------------------------------|
| V4.x    | :white_check_mark: | Production Authorization Monotonicity      |
| V3.x    | :x:                | **Deprecated.** Subject to Representation Bypasses |
| V2.x    | :x:                | **Deprecated.** Experimental Deterministic Gates  |
| V1.x    | :x:                | **Deprecated.** Exact-match brittle      |

## Security Model & Boundary

Aegis explicitly bounds its security guarantees around **Authorization-State Monotonicity**. 

### In-Scope for Reporting
The following are considered critical vulnerabilities and should be reported immediately:
- **Authorization Escalation**: Any sequence of API calls, generated inputs, or repair loops that transitions an evaluation state from `REJECT`, `PASS_ABSTENTION`, or `INDETERMINATE` to `PASS_SUBSTANTIVE` without the introduction of an independently validated, non-replayed `AuthorizationGrant`.
- **Capability Forgery**: The ability to mint, launder, replay, or construct an `AuthorizedAnswer` capability via the API or orchestration layer without going through the `Authorizer` singleton.
- **SSRF and Network Pivot**: Bypassing the `ssrf_protector.py` connection-level DNS pinning to access loopback, private, link-local, or cloud metadata IPs (e.g. `169.254.169.254`), or DNS rebinding attacks that result in a connection to an unauthorized IP.
- **Supply-Chain Integrity**: Discoveries of untracked dependencies or vulnerabilities within the `requirements-frozen.txt` bounds.

### Out-of-Scope
The following are accepted risks or outside the formal security boundary:
- **General LLM Hallucinations**: The generator model hallucinating ungrounded claims (the Aegis framework is designed to *catch* these, but the generator itself hallucinating is not an Aegis framework vulnerability).
- **Physical or OS-Level Attacks**: Compromise of the host machine, hypervisor, or OS executing the tests.
- **Malicious Administrator**: An attacker with direct write access to `src/aegis_eval/v4/authorizer.py`.
- **Denial of Service via Overwhelming Valid Traffic**: We implement basic token-bucket rate limiting (non-authoritative for multi-worker), but large-scale DDoS must be mitigated at the load balancer.

## Reporting a Vulnerability

If you discover a vulnerability that breaches the in-scope boundary, please report it via the following process:

1. Draft a reproducible execution trace using the offline evaluation framework (`aegis_cli.py evaluate`). 
2. Capture the immutable `AuthorizationGrant` logs.
3. Submit the proof-of-concept privately to `security@aegis-eval.example.com`.

**Important Methodological Constraint:** 
Do not submit reports based merely on LLM prompt-injections unless they successfully subvert the `Authorizer` state machine or extract an unauthorized `PASS_SUBSTANTIVE` capability.

## Scientific Validation

Aegis adheres to strict adversarial scientific validation. Any patched vulnerability will be accompanied by an immutable, independently adjudicated adversarial closure suite (e.g. `tests/security/test_p3_adversarial_closure.py`) demonstrating the fix without weakening existing regression boundaries.
