import pytest
import json
from aegis_eval.evaluator.aggregator import VerdictAggregator
from aegis_eval.targets.integration_contract import AegisTargetResponse, TargetStatus

from unittest.mock import patch

def test_failure_boundaries_bypass_evaluation():
    with patch('aegis_eval.evaluator.aggregator.EvaluatorDispatcher') as mock_dispatcher:
        aggregator = VerdictAggregator()
        mock_dispatcher.return_value.evaluate.side_effect = RuntimeError("Evaluator should not be called!")
        
        failure_statuses = [
            TargetStatus.TIMEOUT,
        TargetStatus.HTTP_ERROR,
        TargetStatus.DAEMON_CRASH,
        TargetStatus.MALFORMED
    ]
    
    query = {"id": "test_q", "attack_type": "contradiction"}
    
    for status in failure_statuses:
        response = AegisTargetResponse(
            status=status,
            answer="",
            query_id="test_q",
            target_id="test",
            retrieved_chunks=[]
        )
        
        pass_fail, evidence = aggregator.evaluate_and_store_verdict("dummy_run_id", query, response, {})
        assert pass_fail is False
        evidence_dict = json.loads(evidence)
        assert "Infrastructure failure" in evidence_dict["reason"]
        assert status.value in evidence_dict["reason"]
