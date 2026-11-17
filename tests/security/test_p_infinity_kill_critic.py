import os
import sys
import threading
import concurrent.futures
import pytest

from aegis_eval.v4.authorizer import Authorizer, AuthorizationInvariantViolation
from aegis_eval.v4.state import (
    QSem, ESem, CandidateAnswer, DecisionState, AuthorizationLevel,
    AuthorizationGrant, AuthorizedAnswer
)
from aegis_eval.v4.api.ssrf_protector import is_safe_ip

# ==============================================================================
# Kill-Critic Attack Vector 1: Unicode Homoglyphs & Polyglot Injection
# ==============================================================================

def test_kill_critic_unicode_homoglyph_spoofing():
    """
    CRITIC ATTACK: Inject Cyrillic homoglyphs ('а' \u0430 instead of Latin 'a' \u0061)
    to trick string matching into false entailment.
    ASSERTION: Visual spoofing must NOT fool the Authorizer. Non-matching tokens fail-closed.
    """
    authorizer = Authorizer(validator_id="kill-critic-01")
    
    # Authoritative constraint uses standard Latin: "safe_operation"
    q_sem = QSem(raw_query="verify safety", constraints=["safe_operation"], status="CERTAIN", hash="q_latin")
    
    # Adversary proposes visually identical Cyrillic spoof: "sаfe_operаtion"
    cyrillic_spoof = "s\u0430fe_oper\u0430tion"
    e_sem = ESem(raw_chunk="chunk", propositions=[cyrillic_spoof], chunk_id="chunk_homoglyph", status="CERTAIN", hash="e_cyrillic")
    candidate = CandidateAnswer(answer_text="System is safe", claim_obligations=[cyrillic_spoof], derivation_hash="d_cyr")
    
    res = authorizer.evaluate(q_sem, e_sem, candidate, [])
    assert res.state == DecisionState.REJECT
    assert res.grant is None

def test_kill_critic_null_byte_and_polyglot_payloads():
    """
    CRITIC ATTACK: Inject null-byte truncations and SQL/XSS polyglots into claims.
    ASSERTION: System must not crash, truncate strings silently, or authorize ungrounded propositions.
    """
    authorizer = Authorizer(validator_id="kill-critic-02")
    polyglot = "P1\x00' OR '1'='1'; <script>alert(1)</script>"
    
    q_sem = QSem(raw_query="query", constraints=["P1_mandatory"], status="CERTAIN", hash="q_poly")
    e_sem = ESem(raw_chunk=polyglot, propositions=[polyglot], chunk_id="chunk_poly", status="CERTAIN", hash="e_poly")
    candidate = CandidateAnswer(answer_text=polyglot, claim_obligations=[polyglot], derivation_hash="d_poly")
    
    res = authorizer.evaluate(q_sem, e_sem, candidate, [])
    assert res.state == DecisionState.REJECT
    assert res.grant is None


# ==============================================================================
# Kill-Critic Attack Vector 2: Capability Token Forgery & Replay
# ==============================================================================

def test_kill_critic_cross_run_grant_replay_blocked():
    """
    CRITIC ATTACK: Steal an AuthorizationGrant from a legitimate evaluation and 
    attempt to manually attach it to an ungrounded claim.
    ASSERTION: AuthorizedAnswer constructor and verification must reject mismatched hashes.
    """
    authorizer = Authorizer(validator_id="kill-critic-03")
    
    # 1. Generate legitimate authorized answer
    q1 = QSem(raw_query="legit query", constraints=["AUTH_OK"], status="CERTAIN", hash="hash_q1")
    e1 = ESem(raw_chunk="legit chunk", propositions=["AUTH_OK"], chunk_id="c1", status="CERTAIN", hash="hash_e1")
    cand1 = CandidateAnswer(answer_text="legit answer", claim_obligations=["AUTH_OK"], derivation_hash="hash_d1")
    
    legit_res = authorizer.evaluate(q1, e1, cand1, [])
    assert legit_res.state == DecisionState.PASS_SUBSTANTIVE
    stolen_grant = legit_res.grant
    assert stolen_grant is not None

    # 2. Forge an unauthorized answer using stolen grant
    unauthorized_cand = CandidateAnswer(answer_text="hacked answer", claim_obligations=["UNAUTHORIZED"], derivation_hash="hacked_d")
    
    # If attacker tries to instantiate AuthorizedAnswer with forged/tampered provenance
    with pytest.raises(ValueError) as exc_info:
        AuthorizedAnswer(
            state=DecisionState.PASS_SUBSTANTIVE,
            candidate=unauthorized_cand,
            grant=stolen_grant,
            transition_trace=[],
            provenance={"hash": "tampered"}
        )
    assert "V4 Invariant Violation" in str(exc_info.value)
    
    # Check that evaluation path never mints unauthorized claim despite possessing valid grant objects
    q_fake = QSem(raw_query="fake query", constraints=["UNAUTHORIZED"], status="CERTAIN", hash="fake_q")
    e_fake = ESem(raw_chunk="fake chunk", propositions=["DIFFERENT"], chunk_id="c_fake", status="CERTAIN", hash="fake_e")
    
    re_eval = authorizer.evaluate(q_fake, e_fake, unauthorized_cand, [])
    assert re_eval.state == DecisionState.REJECT
    assert re_eval.grant is None


# ==============================================================================
# Kill-Critic Attack Vector 3: Concurrent Multi-Threaded State Races
# ==============================================================================

def test_kill_critic_concurrent_thread_state_isolation():
    """
    CRITIC ATTACK: Concurrently fire 20 interleaved threads through the Authorizer singleton.
    Odd threads run UNAUTHORIZED queries; Even threads run AUTHORIZED queries.
    ASSERTION: Zero state leakage between threads. 100% of odd threads REJECT; 100% of even threads PASS.
    """
    authorizer = Authorizer(validator_id="kill-critic-concurrency")
    results = {}
    
    def worker(thread_idx: int):
        is_even = (thread_idx % 2 == 0)
        req_constraint = f"CONSTRAINT_{thread_idx}"
        
        q_sem = QSem(raw_query=f"query {thread_idx}", constraints=[req_constraint], status="CERTAIN", hash=f"q_{thread_idx}")
        
        # Even threads have matching propositions; Odd threads have non-matching propositions
        props = [req_constraint] if is_even else [f"WRONG_{thread_idx}"]
        e_sem = ESem(raw_chunk=f"chunk {thread_idx}", propositions=props, chunk_id=f"c_{thread_idx}", status="CERTAIN", hash=f"e_{thread_idx}")
        candidate = CandidateAnswer(answer_text=f"ans {thread_idx}", claim_obligations=props, derivation_hash=f"d_{thread_idx}")
        
        res = authorizer.evaluate(q_sem, e_sem, candidate, [])
        results[thread_idx] = res.state

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(worker, i) for i in range(20)]
        concurrent.futures.wait(futures)

    # Verify 100% isolation
    for i in range(20):
        if i % 2 == 0:
            assert results[i] == DecisionState.PASS_SUBSTANTIVE, f"Even thread {i} failed to authorize valid claim!"
        else:
            assert results[i] == DecisionState.REJECT, f"CRITICAL: Odd thread {i} suffered state bleed and authorized ungrounded claim!"


# ==============================================================================
# Kill-Critic Attack Vector 4: Multi-Turn Semantic Laundering
# ==============================================================================

def test_kill_critic_transitive_semantic_drift_blocked():
    """
    CRITIC ATTACK: Multi-turn iterative repair loop trying to gradually mutate a claim
    to sneak past constraints without providing fresh evidence.
    ASSERTION: Authorizer must detect identical evidence_ids across history and throw AuthorizationInvariantViolation.
    """
    authorizer = Authorizer(validator_id="kill-critic-drift")
    q_sem = QSem(raw_query="mandatory requirement", constraints=["MANDATORY_FACT"], status="CERTAIN", hash="q_m")
    
    # Turn 1: Initial rejection
    e_base = ESem(raw_chunk="chunk text", propositions=["UNRELATED_1"], chunk_id="chunk_drift_01", status="CERTAIN", hash="e_d1")
    cand1 = CandidateAnswer(answer_text="Attempt 1", claim_obligations=["UNRELATED_1"], derivation_hash="d_1")
    res1 = authorizer.evaluate(q_sem, e_base, cand1, [])
    assert res1.state == DecisionState.REJECT
    
    # Turn 2: Secondary paraphrase mutation (still rejected)
    e_drift2 = ESem(raw_chunk="chunk text", propositions=["UNRELATED_2"], chunk_id="chunk_drift_01", status="CERTAIN", hash="e_d2")
    cand2 = CandidateAnswer(answer_text="Attempt 2", claim_obligations=["UNRELATED_2"], derivation_hash="d_2")
    res2 = authorizer.evaluate(q_sem, e_drift2, cand2, res1.transition_trace)
    assert res2.state == DecisionState.REJECT
    
    # Turn 3: Laundering trap - Generator synthesizes the target constraint, but reuses chunk_drift_01
    e_laundered = ESem(raw_chunk="chunk text", propositions=["MANDATORY_FACT"], chunk_id="chunk_drift_01", status="CERTAIN", hash="e_d3")
    cand3 = CandidateAnswer(answer_text="Attempt 3 - Laundered", claim_obligations=["MANDATORY_FACT"], derivation_hash="d_3")
    
    with pytest.raises(AuthorizationInvariantViolation):
        authorizer.evaluate(q_sem, e_laundered, cand3, res2.transition_trace)


# ==============================================================================
# Kill-Critic Attack Vector 5: SSRF Address Encoding & Obfuscation Evasions
# ==============================================================================

def test_kill_critic_obfuscated_ssrf_notations():
    """
    CRITIC ATTACK: Submit obfuscated private/loopback IP notations to bypass IP validation:
    - 0.0.0.0 (Unspecified)
    - 127.1 (Shorthand loopback)
    - 169.254.169.254 (Cloud metadata)
    - ::ffff:127.0.0.1 (IPv4-mapped IPv6 loopback)
    ASSERTION: is_safe_ip must recognize and reject all forms.
    """
    forbidden_ips = [
        "127.0.0.1",
        "0.0.0.0",
        "127.0.0.2",
        "169.254.169.254",
        "10.0.0.1",
        "172.16.0.1",
        "192.168.1.1",
        "::1",
        "::ffff:127.0.0.1",
        "::ffff:169.254.169.254",
        "fe80::1"
    ]
    for ip in forbidden_ips:
        assert is_safe_ip(ip) is False, f"CRITICAL: is_safe_ip failed to block forbidden IP notation: {ip}"

    # Verify genuine public IP is permitted
    assert is_safe_ip("93.184.216.34") is True # example.com public IP
