import pytest
from aegis_eval.targets.integration_contract import validate_target_contract, IntegrationError, TargetStatus

def test_validate_target_contract_happy_path():
    response = {
        "status": "SUCCESS",
        "answer": "This is an answer.",
        "query_id": "q123",
        "target_id": "test_target",
        "retrieved_chunks": [{"chunk_id": "chunk-1", "rank": 1}]
    }
    parsed = validate_target_contract(response)
    assert parsed.status == TargetStatus.SUCCESS
    assert parsed.retrieved_chunks[0].chunk_id == "chunk-1"

def test_validate_target_contract_missing_chunks_on_success():
    response = {
        "status": "SUCCESS",
        "answer": "This is an answer.",
        "query_id": "q123",
        "target_id": "test_target",
        "retrieved_chunks": []
    }
    with pytest.raises(IntegrationError, match="Target RAG returned SUCCESS but no retrieved_chunks."):
        validate_target_contract(response)

def test_validate_target_contract_malformed():
    response = {
        "answer": "This is an answer.",
        "retrieved_chunks": []
    }
    with pytest.raises(IntegrationError, match="malformed response"):
        validate_target_contract(response)

def test_validate_target_contract_daemon_crash():
    response = {
        "status": "DAEMON_CRASH",
        "query_id": "q123",
        "target_id": "test_target",
        "error": "Out of memory"
    }
    parsed = validate_target_contract(response)
    assert parsed.status == TargetStatus.DAEMON_CRASH
    assert parsed.error == "Out of memory"
