import pytest
from unittest.mock import patch, MagicMock

from aegis_eval.evaluator.nli_contradiction import NLIContradictionEvaluator
from aegis_eval.evaluator.groundedness import GroundednessEvaluator
from aegis_eval.evaluator.coverage import CoverageEvaluator
from aegis_eval.evaluator.ambiguity import AmbiguityEvaluator

# Mock models to avoid heavy downloads during unit tests
@pytest.fixture
def mock_nli_model():
    with patch('aegis_eval.evaluator.nli_contradiction.CrossEncoder') as mock:
        instance = mock.return_value
        # By default, predict neutral
        instance.predict.return_value = [[-1.0, -1.0, 5.0]]
        yield instance

@pytest.fixture
def mock_sim_model():
    with patch('aegis_eval.evaluator.groundedness.SentenceTransformer') as mock:
        instance = mock.return_value
        instance.encode.return_value = [[0.1, 0.2]]
        yield instance

@pytest.fixture
def mock_claim_extractor():
    with patch('aegis_eval.evaluator.nli_contradiction.ClaimExtractor') as mock:
        instance = mock.return_value
        instance.extract_claims.return_value = ["extracted claim 1", "extracted claim 2"]
        yield instance

def test_contradiction_evaluator(mock_nli_model, mock_claim_extractor):
    evaluator = NLIContradictionEvaluator()
    evaluator.claim_extractor = mock_claim_extractor
    evaluator.model = mock_nli_model
    
    query = {
        "id": "1", 
        "attack_type": "contradiction",
        "oracle": {
            "expected_truth": "Truth is out there.",
            "expected_claims": ["Fake claim"]
        }
    }
    chunks = {"c1": "Chunk 1 text", "c2": "Chunk 2 text"}

    # Truth is contradicted, meaning not entailed
    mock_nli_model.predict.return_value = [[5.0, -1.0, -1.0]]

    res = evaluator.evaluate(query, "answer text", chunks)
    assert res["pass_fail"] is False
    assert res["mechanism_used"] == "contradiction"
    assert res["claims"][0]["status"] == "NOT_ENTAILED"

def test_groundedness_evaluator():
    with patch('aegis_eval.evaluator.groundedness.SentenceTransformer') as mock_sim, \
         patch('aegis_eval.evaluator.groundedness.CrossEncoder') as mock_nli, \
         patch('aegis_eval.evaluator.groundedness.ClaimExtractor') as mock_ce, \
         patch('aegis_eval.evaluator.groundedness.util.cos_sim') as mock_cos:
        
        evaluator = GroundednessEvaluator()
        evaluator.claim_extractor = mock_ce.return_value
        evaluator.claim_extractor.extract_claims.return_value = ["claim1"]
        
        # Mock high similarity
        import torch
        mock_cos.return_value = torch.tensor([[0.9, 0.8]])
        
        # Mock entailment (SUPPORTED)
        evaluator.nli_model.predict.return_value = [[-1.0, 5.0, -1.0]]
        
        res = evaluator.evaluate({}, "answer text", {"c1": "text1", "c2": "text2"})
        assert res["pass_fail"] is True
        assert res["claims"][0]["status"] == "SUPPORTED"
        assert res["claims"][0]["evidence_chunk_id"] == "c1"

def test_coverage_evaluator():
    with patch('aegis_eval.evaluator.coverage.SentenceTransformer') as mock_sim, \
         patch('aegis_eval.evaluator.coverage.CrossEncoder') as mock_nli, \
         patch('aegis_eval.evaluator.coverage.ClaimExtractor') as mock_ce, \
         patch('aegis_eval.evaluator.coverage.util.cos_sim') as mock_cos:
         
        evaluator = CoverageEvaluator()
        evaluator.claim_extractor = mock_ce.return_value
        evaluator.claim_extractor.extract_claims.return_value = ["claim1"]
        
        import torch
        mock_cos.return_value = torch.tensor([[0.9, 0.8]])
        
        # Mock entailment for both groundedness and premise NLI
        evaluator.nli_model.predict.return_value = [[-1.0, 5.0, -1.0]]
        
        query = {
            "required_premises": [
                {"premise_id": "P1", "text": "Premise 1", "evidence_chunk_ids": ["c1"]},
                {"premise_id": "P2", "text": "Premise 2", "evidence_chunk_ids": ["c2"]}
            ]
        }
        
        res = evaluator.evaluate(query, "answer", {"c1": "text1", "c2": "text2"})
        
        # Since it entails P1 and P2 via NLI, it should pass
        assert res["pass_fail"] is True
        assert "P1" in res["claims"][0]["premises_covered"]

def test_ambiguity_evaluator():
    with patch('aegis_eval.evaluator.ambiguity.CrossEncoder') as mock_nli:
        evaluator = AmbiguityEvaluator()
        
        # Mock entails
        mock_nli.return_value.predict.return_value = [[-1.0, 5.0, -1.0]]
        
        query = {
            "ambiguity_set": ["interpretation 1", "interpretation 2"]
        }
        
        res = evaluator.evaluate(query, "answer", {})
        assert res["pass_fail"] is True
        assert len(res["claims"]) == 2
        assert res["claims"][0]["status"] == "ENTAILED"
