import pytest
import os
import tempfile
import json
from unittest.mock import patch

from aegis_eval.data.schema import Base, TargetResponse, EvaluationVerdict, EvaluationVerdictClaim
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from aegis_eval.evaluator.aggregator import VerdictAggregator
from aegis_eval.targets.integration_contract import AegisTargetResponse

@pytest.fixture
def mock_db():
    fd, temp_db = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    engine = create_engine(f"sqlite:///{temp_db}")
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    yield Session
    
    engine.dispose()
    os.remove(temp_db)

def test_replay_equivalence(mock_db):
    # Tests that executing aggregator twice (run, then replay) produces equivalent verdicts
    with patch('aegis_eval.evaluator.aggregator.EvaluatorDispatcher') as mock_dispatcher:
        mock_dispatcher.return_value.evaluate.return_value = {
            "pass_fail": False,
            "mechanism_used": "contradiction",
            "claims": [
                {
                    "claim": "Claim 1",
                    "status": "CONTRADICTED",
                    "evidence_chunk_id": "c1"
                }
            ],
            "reason": "Test"
        }
        
        aggregator = VerdictAggregator()
        aggregator.Session = mock_db # Inject test sqlite db
        
        query = {"id": "q1", "attack_type": "contradiction", "text": "Query text"}
        target_res = AegisTargetResponse(
            status="SUCCESS",
            answer="Test answer",
            query_id="q1",
            target_id="test",
            retrieved_chunks=[]
        )
        
        # 1. First run
        aggregator.store_query_and_raw_response("run_id_1", query, target_res)
        pass_fail_1, evidence_1 = aggregator.evaluate_and_store_verdict(query, target_res, {"c1": "text"})
        
        # 2. Replay
        # Since logic is deterministic, evaluate_and_store_verdict should produce same output
        pass_fail_2, evidence_2 = aggregator.evaluate_and_store_verdict(query, target_res, {"c1": "text"})
        
        assert pass_fail_1 == pass_fail_2
        
        ev1_json = json.loads(evidence_1)
        ev2_json = json.loads(evidence_2)
        assert ev1_json["pass_fail"] == ev2_json["pass_fail"]
        assert ev1_json["claims"][0]["status"] == ev2_json["claims"][0]["status"]
        
        # Check DB structures for provenance
        with mock_db() as session:
            verdicts = session.query(EvaluationVerdict).all()
            assert len(verdicts) == 2
            
            claims = session.query(EvaluationVerdictClaim).all()
            assert len(claims) == 2
            
            assert claims[0].status == "CONTRADICTED"
            assert claims[1].status == "CONTRADICTED"
