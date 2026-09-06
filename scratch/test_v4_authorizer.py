import sys
import os
sys.path.append(os.path.abspath("src"))

from aegis_eval.v4.state import (
    QSem, ESem, CandidateAnswer, DecisionState, AuthorizationTransition
)
from aegis_eval.v4.authorizer import Authorizer, AuthorizationInvariantViolation

def test_v4_invariants():
    authorizer = Authorizer()
    
    print("--- Running V4 Architectural Invariant Tests ---\n")
    
    # 1. Base Setup
    q_sem_strict = QSem("foo only if bar", ["foo", "bar"], "CERTAIN", "q_hash_1")
    e_sem_missing = ESem("foo", ["foo"], "chunk_001", "CERTAIN", "e_hash_1")
    e_sem_complete = ESem("foo and bar", ["foo", "bar"], "chunk_002", "CERTAIN", "e_hash_2")
    
    candidate_lossy = CandidateAnswer("yes", ["foo"], "derivation_1")
    
    # Test A: Generator Self-Defines Weak Obligations (V4-S1 Authoritative Obligations)
    # The generator claims it only needs "foo" (which the evidence has). 
    # But QSem requires "foo" AND "bar". The Authorizer MUST reject.
    auth_1 = authorizer.evaluate(q_sem_strict, e_sem_missing, candidate_lossy, [])
    assert auth_1.state == DecisionState.REJECT, f"FAILED: Generator overrode obligations. State was {auth_1.state}"
    print("[PASS] V4-S1: Authoritative Obligations Enforced (Generator cannot weaken constraints)")
    
    # Test B: Repair Amplification / Laundering Attempt (V4-S2)
    # The pipeline tries to repair by submitting a new candidate, but using the same evidence ID.
    candidate_repair = CandidateAnswer("yes indeed", ["foo"], "derivation_2")
    
    # We pass the history from the first evaluation (which was a REJECT).
    # If the authorizer somehow thinks this entails (e.g. if we maliciously passed a weak QSem, 
    # but let's test the monotonicity lock). Let's simulate the repairer trying to pass 
    # the complete evidence, but illegally claiming it's the SAME chunk_id to launder authorization.
    e_sem_laundered = ESem("foo and bar", ["foo", "bar"], "chunk_001", "CERTAIN", "e_hash_1")
    
    try:
        auth_2 = authorizer.evaluate(q_sem_strict, e_sem_laundered, candidate_repair, auth_1.transition_trace)
        assert False, "FAILED: Allowed repair amplification without new evidence."
    except AuthorizationInvariantViolation as e:
        print("[PASS] V4-S2 & V4-S7: Repair Amplification / Laundering Blocked (Exception raised)")
        
    # Test C: Valid Epoch Escapement (V4-S?)
    # New retrieval occurs. Different chunk_id.
    auth_3 = authorizer.evaluate(q_sem_strict, e_sem_complete, candidate_repair, auth_1.transition_trace)
    assert auth_3.state == DecisionState.PASS_SUBSTANTIVE, "FAILED: Valid new evidence was rejected."
    assert auth_3.grant is not None, "FAILED: Capability not minted."
    print("[PASS] Epoch Escapement: New evidence ID successfully authorized.")
    
    # Test D: Semantic Uncertainty Preservation (V4-S3)
    q_sem_uncertain = QSem("is this foo?", ["foo"], "UNCERTAIN", "q_hash_unc")
    auth_4 = authorizer.evaluate(q_sem_uncertain, e_sem_complete, candidate_repair, [])
    assert auth_4.state == DecisionState.INDETERMINATE, "FAILED: Uncertain query was authorized."
    assert auth_4.grant is None, "FAILED: Capability minted for uncertain query."
    print("[PASS] V4-S3: Semantic Uncertainty Preservation Enforced.")
    
    print("\nAll architectural invariants successfully held against python evaluation.")

if __name__ == "__main__":
    test_v4_invariants()
