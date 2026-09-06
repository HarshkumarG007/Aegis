import pytest
import os
import sys

sys.path.append(os.path.abspath("src"))

from aegis_eval.v4.state import (
    CandidateAnswer, DecisionState, AuthorizedAnswer, AuthorizationGrant, AuthorizationLevel
)

def test_manual_pass_substantive_rejected():
    """
    Test that application code cannot instantiate a PASS_SUBSTANTIVE AuthorizedAnswer
    without a valid AuthorizationGrant and full provenance.
    """
    candidate = CandidateAnswer("answer", ["req"], "deriv_hash")
    
    # 1. Missing Grant
    with pytest.raises(ValueError, match="PASS_SUBSTANTIVE requires an AuthorizationGrant"):
        AuthorizedAnswer(
            state=DecisionState.PASS_SUBSTANTIVE,
            candidate=candidate,
            grant=None,
            transition_trace=[],
            provenance={}
        )
        
    # 2. Missing Provenance Fields
    valid_grant = AuthorizationGrant(
        authorization_level=AuthorizationLevel.SUBSTANTIVE,
        obligations_hash="h1",
        evidence_manifest_hash="h2",
        validator_id="v4",
        evidence_event_id="e1"
    )
    
    with pytest.raises(ValueError, match="Missing required provenance keys"):
        AuthorizedAnswer(
            state=DecisionState.PASS_SUBSTANTIVE,
            candidate=candidate,
            grant=valid_grant,
            transition_trace=[],
            provenance={"authorization_event_id": "123"} # Missing all others
        )
        
    # 3. Valid construction passes
    AuthorizedAnswer(
        state=DecisionState.PASS_SUBSTANTIVE,
        candidate=candidate,
        grant=valid_grant,
        transition_trace=[],
        provenance={
            "authorization_event_id": "1",
            "authorization_epoch": "1",
            "q_sem_hash": "2",
            "obligations_hash": "3",
            "evidence_manifest_hash": "4",
            "derivation_hash": "5",
            "validator_version": "6"
        }
    )
    
def test_forged_grant_rejected():
    """
    Test that a grant must bear the SUBSTANTIVE level.
    """
    candidate = CandidateAnswer("answer", ["req"], "deriv_hash")
    
    forged_grant = AuthorizationGrant(
        authorization_level=AuthorizationLevel.NONE, # Forged!
        obligations_hash="h1",
        evidence_manifest_hash="h2",
        validator_id="v4",
        evidence_event_id="e1"
    )
    
    with pytest.raises(ValueError, match="Grant level must be SUBSTANTIVE"):
        AuthorizedAnswer(
            state=DecisionState.PASS_SUBSTANTIVE,
            candidate=candidate,
            grant=forged_grant,
            transition_trace=[],
            provenance={
                "authorization_event_id": "1",
                "authorization_epoch": "1",
                "q_sem_hash": "2",
                "obligations_hash": "3",
                "evidence_manifest_hash": "4",
                "derivation_hash": "5",
                "validator_version": "6"
            }
        )
