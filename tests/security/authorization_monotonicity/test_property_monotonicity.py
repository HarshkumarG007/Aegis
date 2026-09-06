import pytest
from hypothesis import given, strategies as st, settings
from typing import List

import sys
import os
sys.path.append(os.path.abspath("src"))

from aegis_eval.v4.state import (
    QSem, ESem, CandidateAnswer, DecisionState, AuthorizationTransition, AuthorizationLevel
)
from aegis_eval.v4.authorizer import Authorizer, AuthorizationInvariantViolation

# --- Hypothesis Strategies for V4 Types ---

st_decision_state = st.sampled_from(list(DecisionState))

@st.composite
def st_transition(draw) -> AuthorizationTransition:
    return AuthorizationTransition(
        previous_state=draw(st_decision_state),
        proposed_state=draw(st_decision_state),
        actor=draw(st.text(min_size=1, max_size=10)),
        reason="Property test transition",
        evidence_ids=draw(st.lists(st.text(min_size=1, max_size=10), min_size=1, max_size=3)),
        validator_id="v4_test",
        timestamp=1000.0
    )

@st.composite
def st_qsem(draw) -> QSem:
    return QSem(
        raw_query=draw(st.text()),
        constraints=draw(st.lists(st.text(min_size=1), max_size=5)),
        status=draw(st.sampled_from(["CERTAIN", "UNCERTAIN"])),
        hash=draw(st.text())
    )

@st.composite
def st_esem(draw, fixed_chunk_id=None) -> ESem:
    return ESem(
        raw_chunk=draw(st.text()),
        propositions=draw(st.lists(st.text(min_size=1), max_size=5)),
        chunk_id=fixed_chunk_id if fixed_chunk_id else draw(st.text(min_size=1, max_size=10)),
        status=draw(st.sampled_from(["CERTAIN", "UNCERTAIN"])),
        hash=draw(st.text())
    )

@st.composite
def st_candidate(draw) -> CandidateAnswer:
    return CandidateAnswer(
        answer_text=draw(st.text()),
        claim_obligations=draw(st.lists(st.text(min_size=1), max_size=5)),
        derivation_hash=draw(st.text())
    )

# --- The Central Invariant Property Test ---

@given(
    history=st.lists(st_transition(), max_size=10),
    qsem=st_qsem(),
    candidate=st_candidate(),
    raw_esem_data=st.tuples(st.text(), st.lists(st.text(min_size=1), max_size=5), st.sampled_from(["CERTAIN", "UNCERTAIN"]), st.text())
)
@settings(max_examples=100)
def test_monotonicity_property(history: List[AuthorizationTransition], qsem: QSem, candidate: CandidateAnswer, raw_esem_data):
    """
    PROPERTY:
    PASS_SUBSTANTIVE(t+1) and not new_validated_evidence => FAIL
    """
    authorizer = Authorizer()
    
    # Analyze the arbitrary history for highest past level and past evidence IDs
    highest_past_level = AuthorizationLevel.NONE
    past_evidence_ids = set()
    for tx in history:
        if tx.proposed_state == DecisionState.PASS_SUBSTANTIVE:
            highest_past_level = AuthorizationLevel.SUBSTANTIVE
        past_evidence_ids.update(tx.evidence_ids)

    # Strategy: we specifically force a situation where the new ESem uses an ALREADY SEEN evidence_id
    if not past_evidence_ids:
        # If history is empty or has no evidence_ids, then any chunk_id is "new". 
        # This trivially allows PASS_SUBSTANTIVE if constraints match. Skip this branch for the adversarial check,
        # but the authorizer should allow it.
        chunk_id = "new_chunk"
        is_new_evidence = True
    else:
        # Pick an already seen chunk ID to simulate a repair loop (no new evidence)
        chunk_id = list(past_evidence_ids)[0]
        is_new_evidence = False

    esem = ESem(
        raw_chunk=raw_esem_data[0],
        propositions=raw_esem_data[1],
        chunk_id=chunk_id,
        status=raw_esem_data[2],
        hash=raw_esem_data[3]
    )

    try:
        result = authorizer.evaluate(qsem, esem, candidate, history)
        
        # INVARIANT CHECK: If it authorized PASS_SUBSTANTIVE, did it have new evidence?
        if result.state == DecisionState.PASS_SUBSTANTIVE and highest_past_level == AuthorizationLevel.NONE:
            # We escalated to SUBSTANTIVE from NONE.
            assert is_new_evidence, "V4-S1 INVARIANT VIOLATION: Escalated to PASS_SUBSTANTIVE without new evidence!"
            
        # V4-S3 Invariant Check: Uncertainty Preservation
        if qsem.status == "UNCERTAIN" or esem.status == "UNCERTAIN":
            assert result.state == DecisionState.INDETERMINATE, "V4-S3 INVARIANT VIOLATION: Authorized uncertain semantics."
            
        # V4-S1 Authoritative Check: Candidate cannot overrule
        if result.state == DecisionState.PASS_SUBSTANTIVE:
            assert all(req in esem.propositions for req in qsem.constraints), "V4-S1 INVARIANT VIOLATION: Missing authoritative constraints."
            
    except AuthorizationInvariantViolation:
        # The authorizer mechanically rejected an illegal transition. 
        # This is expected and correct behavior when trying to launder authorization.
        # We assert that we were indeed trying to escalate without new evidence.
        assert not is_new_evidence, "Authorizer threw InvariantViolation when evidence was allegedly new!"
