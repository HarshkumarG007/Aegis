import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Literal, Dict

class AuthorizationLevel(Enum):
    NONE = "NONE"
    SUBSTANTIVE = "SUBSTANTIVE"

class DecisionState(Enum):
    UNSET = "UNSET"
    INDETERMINATE = "INDETERMINATE"
    REJECT = "REJECT"
    PASS_ABSTENTION = "PASS_ABSTENTION"
    PASS_SUBSTANTIVE = "PASS_SUBSTANTIVE"

@dataclass(frozen=True)
class QSem:
    """Query Semantics: Defines AUTHORITATIVE_OBLIGATIONS."""
    raw_query: str
    constraints: List[str]
    status: Literal["CERTAIN", "UNCERTAIN"]
    hash: str

@dataclass(frozen=True)
class ESem:
    """Evidence Semantics: Raw chunk to structured propositions."""
    raw_chunk: str
    propositions: List[str]
    chunk_id: str
    status: Literal["CERTAIN", "UNCERTAIN"]
    hash: str

@dataclass(frozen=True)
class CandidateAnswer:
    """
    Untrusted Candidate. Emitted by Generator/Repairer.
    Holds 0 authorization authority.
    """
    answer_text: str
    claim_obligations: List[str]
    derivation_hash: str

@dataclass(frozen=True)
class AuthorizationGrant:
    """Explicitly mints PASS_SUBSTANTIVE capability."""
    authorization_level: AuthorizationLevel
    obligations_hash: str
    evidence_manifest_hash: str
    validator_id: str
    evidence_event_id: str

@dataclass(frozen=True)
class AuthorizationTransition:
    """Runtime invariant trace for monotonicity."""
    previous_state: DecisionState
    proposed_state: DecisionState
    actor: str
    reason: str
    evidence_ids: List[str]
    validator_id: str
    timestamp: float = field(default_factory=time.time)

@dataclass(frozen=True)
class AuthorizedAnswer:
    """
    Capability-bearing answer. Can ONLY be created by the Authorizer.
    Wraps the CandidateAnswer with an explicit AuthorizationGrant.
    """
    state: DecisionState
    candidate: CandidateAnswer
    grant: Optional[AuthorizationGrant]
    transition_trace: List[AuthorizationTransition]
    provenance: Dict[str, str]

    def __post_init__(self):
        # Enforce that PASS_SUBSTANTIVE requires a valid grant and complete provenance
        if self.state == DecisionState.PASS_SUBSTANTIVE:
            if not self.grant:
                raise ValueError("V4 Invariant Violation: PASS_SUBSTANTIVE requires an AuthorizationGrant.")
            if self.grant.authorization_level != AuthorizationLevel.SUBSTANTIVE:
                raise ValueError("V4 Invariant Violation: Grant level must be SUBSTANTIVE.")
            
            # Check for required provenance fields
            required_provenance_keys = {
                "authorization_event_id", "authorization_epoch", "q_sem_hash", 
                "obligations_hash", "evidence_manifest_hash", "derivation_hash", "validator_version"
            }
            if not required_provenance_keys.issubset(self.provenance.keys()):
                missing = required_provenance_keys - set(self.provenance.keys())
                raise ValueError(f"V4 Invariant Violation: Missing required provenance keys: {missing}")

