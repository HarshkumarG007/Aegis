import json
import pytest
import os
import sys

sys.path.append(os.path.abspath("src"))

from aegis_eval.v4.state import (
    QSem, ESem, CandidateAnswer, DecisionState
)
from aegis_eval.v4.authorizer import Authorizer, AuthorizationInvariantViolation

@pytest.fixture
def v3_4_fixtures():
    fixture_path = os.path.join(os.path.dirname(__file__), "..", "fixtures_v3_4.json")
    with open(fixture_path, "r") as f:
        return json.load(f)

def test_v3_4_unsafe_bypasses_intercepted(v3_4_fixtures):
    """
    REGRESSION: All 19 V3.4 substantive bypasses must be intercepted.
    """
    authorizer = Authorizer()
    
    for case in v3_4_fixtures:
        # V3.4 failure mode: The generator silently dropped constraints.
        # In V4, Q_sem holds the true authoritative constraints.
        q_sem = QSem(
            raw_query=case["query"],
            constraints=["mock_authoritative_constraint"],
            status="CERTAIN",
            hash="q_" + case["id"]
        )
        
        # The evidence in V3.4 did not contain the constraint, which is why it was unsafe.
        e_sem = ESem(
            raw_chunk=case["evidence"],
            propositions=["other_proposition"], 
            chunk_id="chunk_" + case["evidence"],
            status="CERTAIN",
            hash="e_" + case["id"]
        )
        
        candidate = CandidateAnswer(
            answer_text=case["answer"],
            claim_obligations=["other_proposition"], # The generator claims it only needs this
            derivation_hash="deriv_" + case["id"]
        )
        
        auth_1 = authorizer.evaluate(q_sem, e_sem, candidate, [])
        
        # INVARIANT: The generator cannot weaken the authoritative obligations.
        # It must be REJECTED.
        assert auth_1.state == DecisionState.REJECT, f"Case {case['id']} was not intercepted!"
        
def test_v3_4_repair_amplification_blocked(v3_4_fixtures):
    """
    REGRESSION: The 4 repair monotonicity violations must raise an invariant exception.
    """
    authorizer = Authorizer()
    
    repair_cases = [c for c in v3_4_fixtures if c.get("repair_violation")]
    
    for case in repair_cases:
        # Base setup
        q_sem = QSem(
            raw_query=case["query"],
            constraints=["mock_authoritative_constraint"],
            status="CERTAIN",
            hash="q_" + case["id"]
        )
        
        e_sem = ESem(
            raw_chunk=case["evidence"],
            propositions=["other_proposition"], 
            chunk_id="chunk_" + case["evidence"],
            status="CERTAIN",
            hash="e_" + case["id"]
        )
        
        candidate = CandidateAnswer(
            answer_text=case["answer"],
            claim_obligations=[], 
            derivation_hash="deriv_" + case["id"]
        )
        
        # Initial evaluation yields REJECT
        auth_1 = authorizer.evaluate(q_sem, e_sem, candidate, [])
        assert auth_1.state == DecisionState.REJECT
        
        # REPAIR LAUNDERING ATTEMPT:
        # The repairer somehow gets E_sem to parse a proposition that entails Q_sem,
        # BUT it uses the EXACT same chunk_id (it did not retrieve new evidence).
        e_sem_laundered = ESem(
            raw_chunk="foo",
            propositions=["mock_authoritative_constraint"], # Fake success
            chunk_id="chunk_" + case["evidence"], # SAME ID
            status="CERTAIN",
            hash="e_laundered_" + case["id"]
        )
        
        with pytest.raises(AuthorizationInvariantViolation):
            # This MUST throw an exception preventing the transition to PASS_SUBSTANTIVE
            authorizer.evaluate(q_sem, e_sem_laundered, candidate, auth_1.transition_trace)
