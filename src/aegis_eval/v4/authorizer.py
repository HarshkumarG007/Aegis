import hashlib
import time
import uuid
from typing import List, Dict, Optional, Tuple

from aegis_eval.v4.state import (
    AuthorizationLevel, DecisionState, QSem, ESem, CandidateAnswer,
    AuthorizationGrant, AuthorizationTransition, AuthorizedAnswer
)

class AuthorizationInvariantViolation(Exception):
    """Fatal exception thrown when authorization monotonicity is violated."""
    pass

class Authorizer:
    """
    The sole capability boundary that can mint AuthorizedAnswer and PASS_SUBSTANTIVE.
    Enforces the Authorization Monotonicity Invariant.
    """
    
    def __init__(self, validator_id: str = "v4.0.0-core"):
        self.validator_id = validator_id

    def _hash(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
        
    def _check_entailment(self, e_propositions: List[str], required_obligations: List[str]) -> bool:
        # In a real system, this would call the cross-encoder/NLI gate.
        # For this skeleton, we assume exact string subset for demonstration,
        # but the critical part is that `required_obligations` comes from QSem, not Candidate.
        # Here we mock it. 
        if not required_obligations:
            return True
        # Mock subset check
        return all(req in e_propositions for req in required_obligations)

    def evaluate(
        self, 
        q_sem: QSem, 
        e_sem: ESem, 
        candidate: CandidateAnswer, 
        history: List[AuthorizationTransition]
    ) -> AuthorizedAnswer:
        """
        Evaluates a candidate against AUTHORITATIVE obligations defined by QSem.
        Enforces Monotonicity based on the provided transition history.
        """
        # 1. Uncertainty Preservation (V4-S3)
        if q_sem.status == "UNCERTAIN" or e_sem.status == "UNCERTAIN":
            proposed_state = DecisionState.INDETERMINATE
            reason = "Uncertainty Preservation: Cannot authorize uncertain semantics."
        else:
            # 2. Evaluate against AUTHORITATIVE OBLIGATIONS (V4-S1: Not candidate's obligations)
            # The candidate generated claim_obligations, but we MUST check QSem.constraints
            is_entailed = self._check_entailment(e_sem.propositions, q_sem.constraints)
            
            if is_entailed:
                proposed_state = DecisionState.PASS_SUBSTANTIVE
                reason = "Authoritative Obligations Entailed."
            else:
                proposed_state = DecisionState.REJECT
                reason = "Authoritative Obligations NOT Entailed."
                
        # 3. Monotonicity Invariant Enforcement
        highest_past_level = AuthorizationLevel.NONE
        past_evidence_ids = set()
        
        for tx in history:
            if tx.proposed_state == DecisionState.PASS_SUBSTANTIVE:
                highest_past_level = AuthorizationLevel.SUBSTANTIVE
            past_evidence_ids.update(tx.evidence_ids)
            
        is_substantive = (proposed_state == DecisionState.PASS_SUBSTANTIVE)
        
        if is_substantive and highest_past_level == AuthorizationLevel.NONE:
            # We are attempting to escalate to SUBSTANTIVE.
            # This is ONLY allowed if this is the first evaluation, or if NEW evidence is introduced.
            if len(history) > 0:
                # Is there new evidence?
                if e_sem.chunk_id in past_evidence_ids:
                    # FORBIDDEN ESCALATION (Repair Amplification / Laundering)
                    raise AuthorizationInvariantViolation(
                        f"V4-S1 Violation: Attempted to transition from unauthorized history to "
                        f"PASS_SUBSTANTIVE using identical evidence_id '{e_sem.chunk_id}'. "
                        f"Repair cannot independently authorize."
                    )
                    
        # If we reach here, the transition is mathematically valid.
        new_transition = AuthorizationTransition(
            previous_state=history[-1].proposed_state if history else DecisionState.UNSET,
            proposed_state=proposed_state,
            actor="Authorizer",
            reason=reason,
            evidence_ids=[e_sem.chunk_id],
            validator_id=self.validator_id
        )
        
        new_history = history + [new_transition]
        
        # 4. Mint Capability
        grant = None
        if proposed_state == DecisionState.PASS_SUBSTANTIVE:
            grant = AuthorizationGrant(
                authorization_level=AuthorizationLevel.SUBSTANTIVE,
                obligations_hash=q_sem.hash,
                evidence_manifest_hash=e_sem.hash,
                validator_id=self.validator_id,
                evidence_event_id=e_sem.chunk_id
            )
            
        provenance = {
            "authorization_event_id": str(uuid.uuid4()),
            "authorization_epoch": str(len(set(tx.evidence_ids[0] for tx in new_history if tx.evidence_ids))),
            "q_sem_hash": q_sem.hash,
            "obligations_hash": self._hash("".join(q_sem.constraints)),
            "evidence_manifest_hash": e_sem.hash,
            "derivation_hash": candidate.derivation_hash,
            "validator_version": self.validator_id,
        }
            
        return AuthorizedAnswer(
            state=proposed_state,
            candidate=candidate,
            grant=grant,
            transition_trace=new_history,
            provenance=provenance
        )
