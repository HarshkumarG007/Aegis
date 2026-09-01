import os
import json
import uuid
import pytest
from unittest.mock import patch, MagicMock

from aegis_eval.data.schema import Base, AdversarialQuery, TargetResponse
from aegis_eval.evaluator.aggregator import VerdictAggregator
from aegis_eval.targets.integration_contract import AegisTargetResponse, TargetStatus, RetrievedChunk

# 1. Persistence Test
def test_persistence_preserves_metadata(tmp_path):
    db_path = tmp_path / "test_aegis.db"
    db_url = f"sqlite:///{db_path}"
    
    # Initialize DB schema
    from sqlalchemy import create_engine
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    
    aggregator = VerdictAggregator(db_url=db_url)
    # mock dispatcher so we don't load heavyweight models during tests
    aggregator.dispatcher = MagicMock()
    
    run_id = str(uuid.uuid4())
    aggregator.start_run(run_id, "dummy_manifest_hash", "test_target")
    
    query = {
        "id": "q-123",
        "text": "How does X relate to Y?",
        "attack_type": "multi_hop",
        "required_premises": [
            {"premise_id": "P1", "text": "Premise 1", "evidence_chunk_ids": ["chunk-002"]},
            {"premise_id": "P2", "text": "Premise 2", "evidence_chunk_ids": ["chunk-006"]}
        ],
        "random_extra_metadata": True
    }
    
    response = AegisTargetResponse(
        status=TargetStatus.SUCCESS,
        query_id="q-123",
        target_id="test_target",
        answer="X and Y are related.",
        retrieved_chunks=[RetrievedChunk(chunk_id="chunk-002", rank=1)]
    )
    
    aggregator.store_query_and_raw_response(run_id, query, response)
    
    # Reload from DB and verify exact metadata structure
    with aggregator.Session() as session:
        stored_query = session.query(AdversarialQuery).filter_by(query_id="q-123").first()
        assert stored_query is not None
        assert stored_query.metadata_json is not None
        
        # Verify required_premises survived EXACTLY
        req_premises = stored_query.metadata_json.get("required_premises")
        assert req_premises is not None
        assert len(req_premises) == 2
        
        # Check P1 structure
        p1 = req_premises[0]
        assert p1["premise_id"] == "P1"
        assert p1["text"] == "Premise 1"
        assert p1["evidence_chunk_ids"] == ["chunk-002"]
        
        # Check extra metadata
        assert stored_query.metadata_json.get("random_extra_metadata") is True

# 2. Infrastructure Failure bypass
def test_infrastructure_failure_bypass_semantics(tmp_path):
    from sqlalchemy import create_engine
    db_path = tmp_path / "test_aegis_infra.db"
    db_url = f"sqlite:///{db_path}"
    
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    
    aggregator = VerdictAggregator(db_url=db_url)
    
    # We put a magic mock that raises an exception if called. 
    # This proves the evaluator is entirely bypassed!
    aggregator.dispatcher.evaluate = MagicMock(side_effect=Exception("Semantic evaluator should NOT be called!"))
    
    query = {"id": "q-456", "attack_type": "out_of_domain", "text": "test"}
    
    response = AegisTargetResponse(
        status=TargetStatus.TIMEOUT,
        query_id="q-456",
        target_id="test_target",
        error="Connection Timeout",
        answer=""
    )
    
    pass_fail, evidence = aggregator.evaluate_and_store_verdict(query, response, {})
    
    # Assert
    assert pass_fail is False
    assert "Infrastructure failure: TIMEOUT" in evidence
    # Ensure our Exception was not raised, meaning dispatcher was not called
    aggregator.dispatcher.evaluate.assert_not_called()
