from aegis_eval.evaluator.nli_contradiction import NLIContradictionEvaluator
from aegis_eval.evaluator.groundedness import GroundednessEvaluator
from aegis_eval.evaluator.coverage import CoverageEvaluator
from aegis_eval.evaluator.ambiguity import AmbiguityEvaluator

class EvaluatorDispatcher:
    def __init__(self):
        self.evaluators = {
            "contradiction": NLIContradictionEvaluator(),
            "out_of_domain": GroundednessEvaluator(),
            "multi_hop": CoverageEvaluator(),
            "ambiguous": AmbiguityEvaluator()
        }
        
    def evaluate(self, query: dict, answer: str, chunks_dict: dict) -> dict:
        attack_type = query.get("attack_type")
        if attack_type not in self.evaluators:
            raise ValueError(f"Unknown attack type: {attack_type}")
            
        evaluator = self.evaluators[attack_type]
        return evaluator.evaluate(query, answer, chunks_dict)
