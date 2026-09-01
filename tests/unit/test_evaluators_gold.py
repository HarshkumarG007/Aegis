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
    
    query = {
        "id": "1",
        "oracle": {
            "expected_claims": ["Adv1"]
        }
    }
    
    # Exactly 0.60 similarity
    mock_cos_sim.return_value = np.array([[0.60]]) 
    
    with patch('aegis_eval.evaluator.groundedness.softmax') as mock_softmax:
        # Hallucination check fails! (first call expected_claims entail! -> FAIL immediately)
        mock_softmax.side_effect = [np.array([0.10, 0.85, 0.05])]
        result = evaluator.evaluate(query, "answer", {"chunk1": "evidence"})
        assert result["pass_fail"] is False
        assert "hallucinated adversarial claim" in result["reason"]

        # No hallucination (first call no entail), but claim entailment fails (contra=0.85)
        mock_softmax.side_effect = [np.array([0.85, 0.10, 0.05]), np.array([0.85, 0.15, 0.0])]
        evaluator.nli_model.predict = MagicMock(return_value=np.array([[0.85, 0.15, 0.0]]))
        
        result = evaluator.evaluate(query, "answer", {"chunk1": "evidence"})
        assert result["pass_fail"] is False
        assert result["claims"][0]["status"] == "CONTRADICTED"
        
        # Test entailment (first call expected_claims no entail, second call entail claim)
        mock_softmax.side_effect = [np.array([0.85, 0.10, 0.05]), np.array([0.10, 0.70, 0.20])]
        result = evaluator.evaluate(query, "answer", {"chunk1": "evidence"})
        assert result["pass_fail"] is True
        assert result["claims"][0]["status"] == "SUPPORTED"
        
        # Test unsupported due to similarity < 0.60
        mock_cos_sim.return_value = np.array([[0.599]])
        mock_softmax.side_effect = [np.array([0.85, 0.10, 0.05])]
        result = evaluator.evaluate(query, "answer", {"chunk1": "evidence"})
        assert result["pass_fail"] is False
        assert result["claims"][0]["status"] == "UNSUPPORTED"

def test_contradiction_exact_match():
    evaluator = NLIContradictionEvaluator()
    
    query = {
        "id": "1",
        "oracle": {
            "expected_truth": "The device was manufactured in 2024.",
            "expected_claims": ["The device was not manufactured in 2024."]
        }
    }
    
    # Test 1: Answer explicitly contains the truth. NLI is bypassed!
    result = evaluator.evaluate(query, "The device was manufactured in 2024.", {})
    assert result["pass_fail"] is True
    assert "Explicitly contains expected truth" in result["reason"]
    
    # Test 2: Answer explicitly contains the adversarial claim. NLI is bypassed!
    result = evaluator.evaluate(query, "The device was not manufactured in 2024.", {})
    assert result["pass_fail"] is False
    assert "Explicitly contains adversarial claim" in result["reason"]

def test_contradiction_boundary():
    evaluator = NLIContradictionEvaluator()
    
    query = {
        "id": "1",
        "oracle": {
            "expected_truth": "Truth",
            "expected_claims": ["Adv1"]
        }
    }
    
    with patch('aegis_eval.evaluator.nli_contradiction.softmax') as mock_softmax:
        # Test 1: Entails truth (0.85), entails adversarial (0.85) -> FAIL
        mock_softmax.side_effect = [np.array([0.10, 0.85, 0.05]), np.array([0.10, 0.85, 0.05])]
        evaluator.model.predict = MagicMock(return_value=np.array([[1, 0, 0]]))
        
        result = evaluator.evaluate(query, "answer", {})
        assert result["pass_fail"] is False
        
        # Test 2: Entails truth (0.85), does NOT entail adversarial (0.10) -> PASS
        mock_softmax.side_effect = [np.array([0.10, 0.85, 0.05]), np.array([0.85, 0.10, 0.05])]
        result = evaluator.evaluate(query, "answer", {})
        assert result["pass_fail"] is True
        
        # Test 3: Does NOT entail truth -> FAIL
        mock_softmax.side_effect = [np.array([0.85, 0.10, 0.05]), np.array([0.85, 0.10, 0.05])]
        result = evaluator.evaluate(query, "answer", {})
        assert result["pass_fail"] is False

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
            "Interp A",
            "Interp B"
        ]
    }
    
    # Substring match => pass
    result = evaluator.evaluate(query, "Interp A and Interp B", {})
    assert result["pass_fail"] is True

    # NLI match fallback
    with patch('aegis_eval.evaluator.ambiguity.softmax') as mock_softmax:
        # Both interpretations entailed via NLI => Pass
        mock_softmax.side_effect = [np.array([0.0, 0.85, 0.15]), np.array([0.0, 0.85, 0.15])]
        evaluator.nli_model.predict = MagicMock(return_value=np.array([[1]]))
        result = evaluator.evaluate(query, "Something else entirely", {})
        assert result["pass_fail"] is True
        
        # Only A entailed via NLI => Fail
        mock_softmax.side_effect = [np.array([0.0, 0.85, 0.15]), np.array([0.0, 0.10, 0.90])]
        result = evaluator.evaluate(query, "Something else entirely", {})
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
    
    pass_fail, evidence = aggregator.evaluate_and_store_verdict("dummy_run_id", {"id": "1", "attack_type": "contradiction"}, response, {})
    assert pass_fail is False
    assert "Infrastructure failure: TIMEOUT" in evidence
