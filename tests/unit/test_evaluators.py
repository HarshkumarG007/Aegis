import pytest
from aegis_eval.evaluator.nli_contradiction import NLIContradictionEvaluator
from aegis_eval.evaluator.groundedness import GroundednessEvaluator
from aegis_eval.evaluator.coverage import CoverageEvaluator
from aegis_eval.evaluator.ambiguity import AmbiguityEvaluator

def test_nli_contradiction():
    evaluator = NLIContradictionEvaluator()
    chunks = ["The API timeout is 30 seconds."]
    
    # Pass: Answer matches chunk
    pass_fail, msg = evaluator.evaluate("What is timeout?", "The timeout is 30 seconds.", chunks)
    assert pass_fail is True
    
    # Fail: Answer contradicts chunk
    pass_fail, msg = evaluator.evaluate("What is timeout?", "The timeout is 60 seconds.", chunks)
    assert pass_fail is False

def test_groundedness():
    evaluator = GroundednessEvaluator()
    chunks = ["The platform is written in Python."]
    
    # Pass: Grounded claim
    pass_fail, msg = evaluator.evaluate("What language?", "The platform is written in Python.", chunks)
    assert pass_fail is True
    
    # Pass: Abstain
    pass_fail, msg = evaluator.evaluate("How to integrate salesforce?", "I don't know how to do that.", chunks)
    assert pass_fail is True
    
    # Fail: Ungrounded claim
    pass_fail, msg = evaluator.evaluate("How to integrate salesforce?", "You can integrate salesforce using the admin panel.", chunks)
    assert pass_fail is False

def test_coverage():
    evaluator = CoverageEvaluator()
    chunks = [
        "Service A uses Python.",
        "Service B connects to redis."
    ]
    
    # Pass: synthesizes both chunks
    pass_fail, msg = evaluator.evaluate("Describe services", "Service A uses Python and Service B connects to redis.", chunks)
    assert pass_fail is True
    
    # Fail: only uses one chunk
    pass_fail, msg = evaluator.evaluate("Describe services", "Service A uses Python.", chunks)
    assert pass_fail is False

def test_ambiguity():
    evaluator = AmbiguityEvaluator()
    chunks = ["Update profile via PUT in v1. Update profile via POST in v2."]
    
    # Pass: Acknowledges ambiguity
    pass_fail, msg = evaluator.evaluate("How to update?", "It depends on which version you are using. v1 uses PUT and v2 uses POST.", chunks)
    assert pass_fail is True
    
    # Pass: Asks for clarification
    pass_fail, msg = evaluator.evaluate("How to update?", "Which version are you using?", chunks)
    assert pass_fail is True
    
    # Fail: Commits to one interpretation
    pass_fail, msg = evaluator.evaluate("How to update?", "You should use PUT to update the profile.", chunks)
    assert pass_fail is False
