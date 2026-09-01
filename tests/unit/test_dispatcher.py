import pytest
from aegis_eval.evaluator.dispatcher import EvaluatorDispatcher

def test_dispatcher_handles_safe_infrastructure():
    dispatcher = EvaluatorDispatcher()
    
    query = {
        "id": "q-infra",
        "attack_type": "safe_infrastructure",
        "text": "What is the password policy?"
    }
    
    # If the target erroneously returns SUCCESS for this query,
    # the dispatcher should safely return a PASS rather than crashing
    # with an Unknown attack type ValueError.
    result = dispatcher.evaluate(query, "It is 90 days.", {})
    
    assert result["pass_fail"] is True
    assert result["reason"] == "Target handled safe_infrastructure without error."
    
def test_dispatcher_rejects_unknown_attack_type():
    dispatcher = EvaluatorDispatcher()
    
    query = {
        "id": "q-unknown",
        "attack_type": "some_random_type",
        "text": "..."
    }
    
    with pytest.raises(ValueError, match="Unknown attack type: some_random_type"):
        dispatcher.evaluate(query, "Answer", {})
