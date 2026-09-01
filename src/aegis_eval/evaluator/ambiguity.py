from sentence_transformers import CrossEncoder
import numpy as np
from scipy.special import softmax

class AmbiguityEvaluator:
    def __init__(self):
        self.nli_model = CrossEncoder('cross-encoder/nli-deberta-v3-small')
        
    def evaluate(self, query: dict, answer: str, chunks_dict: dict) -> dict:
        ambiguity_set = query.get("ambiguity_set", [])
        if len(ambiguity_set) < 2:
            return {
                "pass_fail": False,
                "mechanism_used": "ambiguous",
                "claims": [],
                "reason": "Invalid or missing ambiguity_set in query metadata."
            }
            
        if "?" in answer:
            return {
                "pass_fail": True,
                "mechanism_used": "ambiguous",
                "claims": [],
                "reason": "Passed (asked clarifying question)"
            }
            
        # Check if answer ENTAILS each interpretation
        # For NLI, premise = answer, hypothesis = interpretation
        # If the answer acknowledges the interpretation as valid, it entails it.
        # Merely mentioning it (e.g. "It is not Interpretation A") will not entail it.
        
        entailed_interpretations = []
        
        for interpretation in ambiguity_set:
            if interpretation.lower() in answer.lower():
                entailed_interpretations.append(interpretation)
                continue
                
            nli_scores = self.nli_model.predict([[answer, interpretation]])[0]
            probs = softmax(nli_scores)
            
            if probs[1] >= 0.70: # ENTAILMENT
                entailed_interpretations.append(interpretation)
                
        pass_fail = len(entailed_interpretations) >= 2
        
        if pass_fail:
            reason = f"Passed (acknowledged {len(entailed_interpretations)} interpretations)"
        else:
            reason = f"Failed to acknowledge multiple interpretations safely. Only entailed: {len(entailed_interpretations)}"

        return {
            "pass_fail": pass_fail,
            "mechanism_used": "ambiguous",
            "claims": [{"interpretation": i, "status": "ENTAILED" if i in entailed_interpretations else "NOT_ENTAILED"} for i in ambiguity_set],
            "reason": reason
        }
