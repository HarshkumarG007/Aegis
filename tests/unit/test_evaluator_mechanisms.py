import pytest
from aegis_eval.evaluator.nli_contradiction import NLIContradictionEvaluator
from aegis_eval.evaluator.coverage import CoverageEvaluator
from aegis_eval.evaluator.ambiguity import AmbiguityEvaluator
from aegis_eval.evaluator.groundedness import GroundednessEvaluator

def test_contradiction_mechanism_happy_path():
    evaluator = NLIContradictionEvaluator()
    query = "What is the timeout?"
    chunks = [
        "The v1 timeout is 30 seconds.",
        "The v2 timeout is 60 seconds."
    ]
    ans = "The timeout is 30 seconds for v1 and 60 for v2."
    pass_fail, evidence = evaluator.evaluate(query, ans, chunks)
    assert pass_fail == True

def test_contradiction_mechanism_fail():
    evaluator = NLIContradictionEvaluator()
    query = "What is the timeout?"
    chunks = [
        "The v1 timeout is 30 seconds.",
        "The v2 timeout is 60 seconds."
    ]
    ans = "The timeout is strictly 90 seconds for all versions."
    pass_fail, evidence = evaluator.evaluate(query, ans, chunks)
    assert pass_fail == False

def test_multi_hop_mechanism():
    evaluator = CoverageEvaluator()
    query = "Who hosts the API queue?"
    chunks = [
        "The API uses a queue for telemetry.",
        "The queue is hosted on AWS."
    ]
    # Hits both chunks
    ans = "The API telemetry queue is hosted on AWS."
    pass_fail, evidence = evaluator.evaluate(query, ans, chunks)
    assert pass_fail == True

def test_ambiguity_mechanism_pass():
    evaluator = AmbiguityEvaluator()
    query = "How do I update?"
    chunks = ["Use POST for new accounts. Use PUT for old ones."]
    ans = "It depends on whether the account is new or old. You can use either POST or PUT."
    pass_fail, evidence = evaluator.evaluate(query, ans, chunks)
    assert pass_fail == True

def test_ambiguity_mechanism_fail():
    evaluator = AmbiguityEvaluator()
    query = "How do I update?"
    chunks = ["Use POST for new accounts. Use PUT for old ones."]
    ans = "You must always use POST to update."
    pass_fail, evidence = evaluator.evaluate(query, ans, chunks)
    assert pass_fail == False
