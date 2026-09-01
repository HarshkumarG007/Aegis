from unittest.mock import patch, MagicMock
import numpy as np
import pytest
from aegis_eval.evaluator.groundedness import GroundednessEvaluator
from aegis_eval.evaluator.nli_contradiction import NLIContradictionEvaluator
from aegis_eval.evaluator.coverage import CoverageEvaluator
from aegis_eval.evaluator.ambiguity import AmbiguityEvaluator

@patch('aegis_eval.evaluator.groundedness.util.cos_sim')
def test_groundedness_precedence(mock_cos_sim):
    evaluator = GroundednessEvaluator()
    evaluator.claim_extractor.extract_claims = MagicMock(return_value=["Claim 1"])
    
    # Exactly 0.60 similarity
    mock_cos_sim.return_value = np.array([[0.60]]) 
    
    with patch('aegis_eval.evaluator.groundedness.softmax') as mock_softmax:
        # contra=0.85, entail=0.70 is mathematically impossible since sum > 1.
        # But if the logic just checks contra >= 0.85 first, we can test it like this:
        mock_softmax.return_value = np.array([0.85, 0.15, 0.0])
        evaluator.nli_model.predict = MagicMock(return_value=np.array([[0.85, 0.15, 0.0]]))
        
        result = evaluator.evaluate({"id": "1"}, "answer", {"chunk1": "evidence"})
        assert result["pass_fail"] is False
        assert result["claims"][0]["status"] == "CONTRADICTED"
        
        # Test entailment
        mock_softmax.return_value = np.array([0.10, 0.70, 0.20])
        result = evaluator.evaluate({"id": "1"}, "answer", {"chunk1": "evidence"})
        assert result["pass_fail"] is True
        assert result["claims"][0]["status"] == "SUPPORTED"
        
        # Test unsupported due to similarity < 0.60
        mock_cos_sim.return_value = np.array([[0.599]])
        result = evaluator.evaluate({"id": "1"}, "answer", {"chunk1": "evidence"})
        assert result["pass_fail"] is False
        assert result["claims"][0]["status"] == "UNSUPPORTED"

def test_contradiction_boundary():
    evaluator = NLIContradictionEvaluator()
    evaluator.claim_extractor.extract_claims = MagicMock(return_value=["Claim 1"])
    
    with patch('aegis_eval.evaluator.nli_contradiction.softmax') as mock_softmax:
        # Exactly 0.85 contradiction
        mock_softmax.return_value = np.array([0.85, 0.10, 0.05])
        evaluator.model.predict = MagicMock(return_value=np.array([[1, 0, 0]]))
        
        result = evaluator.evaluate({"id": "1"}, "answer", {"chunk1": "evidence"})
        assert result["pass_fail"] is False
        assert result["claims"][0]["status"] == "CONTRADICTED"
        
        # Entailed (0.85 entailment)
        mock_softmax.return_value = np.array([0.10, 0.85, 0.05])
        result = evaluator.evaluate({"id": "1"}, "answer", {"chunk1": "evidence"})
        assert result["pass_fail"] is True
        assert result["claims"][0]["status"] == "ENTAILED"

@patch('aegis_eval.evaluator.coverage.util.cos_sim')
def test_multihop_coverage(mock_cos_sim):
    evaluator = CoverageEvaluator()
    evaluator.claim_extractor.extract_claims = MagicMock(return_value=["Claim 1", "Claim 2"])
    
    query = {
        "id": "1",
        "required_premises": [
            {"premise_id": "P1", "text": "Premise 1", "evidence_chunk_ids": ["chunk1"]},
            {"premise_id": "P2", "text": "Premise 2", "evidence_chunk_ids": ["chunk2"]}
        ]
    }
    
    mock_cos_sim.side_effect = [np.array([[0.90, 0.10]]), np.array([[0.10, 0.90]])]
    
    with patch('aegis_eval.evaluator.coverage.softmax') as mock_softmax:
        # All calls return 0.9 entailment (groundedness and premise coverage)
        mock_softmax.return_value = np.array([0.0, 0.90, 0.1])
        
        evaluator.nli_model.predict = MagicMock(return_value=np.array([[1]]))
        
        result = evaluator.evaluate(query, "answer", {"chunk1": "text1", "chunk2": "text2"})
        assert result["pass_fail"] is True
        assert "P1" in result["claims"][0]["premises_covered"]
        assert "P2" in result["claims"][1]["premises_covered"]

def test_ambiguity_boundary():
    evaluator = AmbiguityEvaluator()
    query = {
        "id": "1",
        "ambiguity_set": [
            {"interpretation": "A", "text": "Interp A"},
            {"interpretation": "B", "text": "Interp B"}
        ]
    }
    
    with patch('aegis_eval.evaluator.ambiguity.softmax') as mock_softmax:
        # Both interpretations entailed => Pass
        mock_softmax.side_effect = [np.array([0.0, 0.85, 0.15]), np.array([0.0, 0.85, 0.15])]
        evaluator.nli_model.predict = MagicMock(return_value=np.array([[1]]))
        result = evaluator.evaluate(query, "answer", {})
        assert result["pass_fail"] is True
        
        # Only A entailed => Fail
        mock_softmax.side_effect = [np.array([0.0, 0.85, 0.15]), np.array([0.0, 0.10, 0.90])]
        result = evaluator.evaluate(query, "answer", {})
        assert result["pass_fail"] is False

def test_infrastructure_failure():
    from aegis_eval.evaluator.aggregator import VerdictAggregator
    from aegis_eval.targets.integration_contract import AegisTargetResponse, TargetStatus
    
    aggregator = VerdictAggregator("sqlite:///:memory:")
    response = AegisTargetResponse(
        status=TargetStatus.TIMEOUT,
        query_id="1",
        target_id="test",
        error="Timeout",
        answer=""
    )
    
    pass_fail, evidence = aggregator.evaluate_and_store_verdict({"id": "1"}, response, {})
    assert pass_fail is False
    assert "Infrastructure failure: TIMEOUT" in evidence
