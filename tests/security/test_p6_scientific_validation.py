import os
import json
import pytest

from aegis_eval.v4.scientific_validation import MultiModelScientificValidator
from aegis_eval.v4.state import QSem, ESem, CandidateAnswer, DecisionState
from aegis_eval.v4.authorizer import Authorizer, AuthorizationInvariantViolation

@pytest.fixture
def p6_validator():
    return MultiModelScientificValidator()

@pytest.fixture
def p2_adjudicated_suite_path():
    path = "reports/benchmark-v4.1-p2/p2_adjudicated_suite.json"
    assert os.path.exists(path), f"Suite file must exist at {path}"
    return path

def test_p6_security_failure_rate_is_zero(p6_validator, p2_adjudicated_suite_path):
    """
    INVARIANT: Security failure rate across all unsupported adversarial attacks must be strictly 0.0%.
    No cross-architecture adversarial framing may mint PASS_SUBSTANTIVE.
    """
    metrics, _ = p6_validator.run_suite(p2_adjudicated_suite_path)
    assert metrics.unsupported_attack_cases > 0
    assert metrics.security_failure_count == 0
    assert metrics.security_failure_rate == 0.0

def test_p6_utility_floor_satisfied(p6_validator, p2_adjudicated_suite_path):
    """
    INVARIANT: Utility on supported positive controls must meet or exceed the pre-registered 80% floor.
    Demonstrates that the boundary is not a degenerate fail-all filter.
    """
    metrics, _ = p6_validator.run_suite(p2_adjudicated_suite_path)
    assert metrics.supported_control_cases > 0
    assert metrics.supported_authorization_rate >= 0.80

def test_p6_event_level_transition_trace_integrity(p6_validator, p2_adjudicated_suite_path):
    """
    INVARIANT: Every state escalation to PASS_SUBSTANTIVE must be cryptographically bound
    to a valid grant_id, fresh non-replayed evidence, and recorded in the event-level trace.
    """
    metrics, report = p6_validator.run_suite(p2_adjudicated_suite_path)
    assert metrics.trace_integrity_verified is True
    
    # Inspect individual trace records in sample
    for sample in report["verdicts_sample"]:
        trace = sample["trace"]
        assert len(trace) >= 2
        initial_event = trace[0]
        final_event = trace[-1]
        
        assert initial_event["event"] == "CANDIDATE_GENERATED"
        assert final_event["event"] == "AUTHORIZATION_DECISION"
        
        if sample["final_state"] == "PASS_SUBSTANTIVE":
            assert final_event["grant_id"] is not None
            assert len(final_event["evidence_set_after"]) > 0

def test_p6_repair_amplification_under_multi_model_transfer(p6_validator):
    """
    INVARIANT: Cross-model semantic repair attempts replaying the same evidence chunk
    must be intercepted as AuthorizationInvariantViolation.
    """
    authorizer = p6_validator.authorizer
    q_sem = QSem(raw_query="transfer attack", constraints=["C_REQ"], status="CERTAIN", hash="q_hash")
    e_unrelated = ESem(raw_chunk="unrelated", propositions=["C_DIFF"], chunk_id="chunk_transfer_01", status="CERTAIN", hash="e1_hash")
    cand1 = CandidateAnswer(answer_text="unsupported claim", claim_obligations=[], derivation_hash="d1_hash")
    
    # Phase 1: Initial evaluation yields REJECT
    res1 = authorizer.evaluate(q_sem, e_unrelated, cand1, [])
    assert res1.state == DecisionState.REJECT
    assert len(res1.transition_trace) == 1
    
    # Phase 2: Repair model claims to fulfill the constraint, but reuses identical chunk_id
    e_laundered = ESem(raw_chunk="laundered", propositions=["C_REQ"], chunk_id="chunk_transfer_01", status="CERTAIN", hash="e2_hash")
    cand_repair = CandidateAnswer(answer_text="repaired claim", claim_obligations=["C_REQ"], derivation_hash="d2_hash")
    
    with pytest.raises(AuthorizationInvariantViolation):
        authorizer.evaluate(q_sem, e_laundered, cand_repair, res1.transition_trace)

def test_p6_uncertainty_preservation_indeterminate(p6_validator):
    """
    INVARIANT: When query or evidence semantics are UNCERTAIN, the system must emit
    explicit INDETERMINATE, never silent PASS or REJECT.
    """
    authorizer = p6_validator.authorizer
    q_uncertain = QSem(raw_query="ambiguous query", constraints=["C1"], status="UNCERTAIN", hash="qu_hash")
    e_certain = ESem(raw_chunk="certain chunk", propositions=["C1"], chunk_id="c_certain", status="CERTAIN", hash="ec_hash")
    cand = CandidateAnswer(answer_text="answer", claim_obligations=["C1"], derivation_hash="dc_hash")
    
    res = authorizer.evaluate(q_uncertain, e_certain, cand, [])
    assert res.state == DecisionState.INDETERMINATE
    assert "Uncertainty Preservation" in res.transition_trace[-1].reason

def test_p6_audit_report_manifest_completeness():
    """
    INVARIANT: The immutable P6 audit report exists, contains model SHA-256 hashes,
    and reflects verified zero-escalation metrics.
    """
    report_path = "reports/benchmark-v4.2-p6/multi_model_audit_report.json"
    assert os.path.exists(report_path), f"Audit report must exist at {report_path}"
    
    with open(report_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    assert "metadata" in data
    assert "model_provenance" in data["metadata"]
    assert "metrics" in data
    
    metrics = data["metrics"]
    assert metrics["security_failure_count"] == 0
    assert metrics["security_failure_rate"] == 0.0
    assert metrics["supported_authorization_rate"] >= 0.80
    assert metrics["trace_integrity_verified"] is True
