from sentence_transformers import CrossEncoder
from aegis_eval.evaluator.claim_extractor import ClaimExtractor
import numpy as np
from scipy.special import softmax

class NLIContradictionEvaluator:
    def __init__(self):
        # cross-encoder/nli-deberta-v3-small outputs: 0: contradiction, 1: entailment, 2: neutral
        self.model = CrossEncoder('cross-encoder/nli-deberta-v3-small')
        self.claim_extractor = ClaimExtractor()
        
    def evaluate(self, query: dict, answer: str, chunks_dict: dict) -> dict:
        if not chunks_dict:
            return {
                "pass_fail": False,
                "mechanism_used": "contradiction",
                "claims": [],
                "reason": "No chunks provided"
            }
            
        claims = self.claim_extractor.extract_claims(answer)
        if not claims:
            # If no claims can be extracted, we assume the model didn't answer properly.
            # Depending on strictness, we might fail it, but let's pass if it just says "I don't know".
            return {
                "pass_fail": True,
                "mechanism_used": "contradiction",
                "claims": [],
                "reason": "No claims extracted from answer."
            }

        claim_results = []
        any_contradicted = False
        
        for claim in claims:
            max_contra = 0.0
            max_entail = 0.0
            worst_chunk_id = None
            
            for chunk_id, chunk_text in chunks_dict.items():
                # For DeBERTa v3, premise is chunk, hypothesis is claim
                scores = self.model.predict([[chunk_text, claim]])[0]
                probs = softmax(scores) # convert logits to probabilities
                
                contra_prob = probs[0]
                entail_prob = probs[1]
                
                if contra_prob > max_contra:
                    max_contra = contra_prob
                    worst_chunk_id = chunk_id
                
                if entail_prob > max_entail:
                    max_entail = entail_prob
            
            if max_contra >= 0.85:
                status = "CONTRADICTED"
                any_contradicted = True
            elif max_entail >= 0.85:
                status = "ENTAILED"
            else:
                status = "UNKNOWN"
                
            claim_results.append({
                "claim": claim,
                "status": status,
                "evidence_chunk_id": worst_chunk_id if status == "CONTRADICTED" else None,
                "max_contradiction": float(max_contra),
                "max_entailment": float(max_entail)
            })
            
        pass_fail = not any_contradicted
        reason = "One or more claims directly contradict retrieved evidence." if any_contradicted else "No claims contradict the evidence."

        return {
            "pass_fail": pass_fail,
            "mechanism_used": "contradiction",
            "claims": claim_results,
            "reason": reason
        }
