import pytest
from aegis_eval.targets.integration_contract import validate_target_contract, IntegrationError

def test_validate_target_contract_happy_path():
    response = {
        "answer_text": "This is an answer.",
        "retrieved_chunk_ids": ["chunk-1", "chunk-2"]
    }
    # Should not raise any exception
    validate_target_contract(response)

def test_validate_target_contract_missing_chunks():
    response = {
        "answer_text": "This is an answer.",
    }
    with pytest.raises(IntegrationError, match="Target RAG did not return retrieved_chunk_ids."):
        validate_target_contract(response)

def test_validate_target_contract_empty_chunks():
    response = {
        "answer_text": "This is an answer.",
        "retrieved_chunk_ids": []
    }
    with pytest.raises(IntegrationError, match="Target RAG did not return retrieved_chunk_ids."):
        validate_target_contract(response)
