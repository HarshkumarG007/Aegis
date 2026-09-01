import string
from sentence_transformers import CrossEncoder
from aegis_eval.evaluator.claim_extractor import ClaimExtractor
import numpy as np
from scipy.special import softmax

def normalize_text(text: str) -> str:
    """Normalizes text by lowercasing and removing punctuation for substring matching."""
    if not text:
        return ""
    return text.lower().translate(str.maketrans('', '', string.punctuation)).strip()

class NLIContradictionEvaluator:
    def __init__(self):
        # cross-encoder/nli-deberta-v3-small outputs: 0: contradiction, 1: entailment, 2: neutral
        self.model = CrossEncoder('cross-encoder/nli-deberta-v3-small')
        self.claim_extractor = ClaimExtractor()
        
    def evaluate(self, query: dict, answer: str, chunks_dict: dict) -> dict:
        oracle = query.get("oracle", {})
        expected_truth = oracle.get("expected_truth", "")
        expected_claims = oracle.get("expected_claims", [])
        
        if not expected_truth:
            return {
                "pass_fail": False,
                "mechanism_used": "contradiction",
                "claims": [],
                "reason": "Missing expected_truth in oracle"
            }
            
        ans_norm = normalize_text(answer)
        truth_norm = normalize_text(expected_truth)
        
        truth_exact = truth_norm in ans_norm
        
        adv_exact = False
        failed_exact_claim = None
        for claim in expected_claims:
            if normalize_text(claim) in ans_norm:
                adv_exact = True
                failed_exact_claim = claim
                break
                
        # 1. Exact/normalized adversarial claim present -> strong negative evidence
        if adv_exact:
            return {
                "pass_fail": False,
                "mechanism_used": "contradiction",
                "claims": [{"claim": failed_exact_claim, "status": "ENTAILED_EXACT"}],
                "reason": f"Explicitly contains adversarial claim: {failed_exact_claim}"
            }
            
        # 2. Exact/normalized expected_truth present AND adversarial NOT present -> strong positive evidence
        if truth_exact:
            return {
                "pass_fail": True,
                "mechanism_used": "contradiction",
                "claims": [{"claim": expected_truth, "status": "ENTAILED_EXACT"}],
                "reason": "Explicitly contains expected truth and rejects adversarial claims."
            }
            
        # 3. NLI used as secondary semantic check
        scores_truth = self.model.predict([[answer, expected_truth]])[0]
        probs_truth = softmax(scores_truth)
        entails_truth = bool(probs_truth[1] >= 0.70)
        
        entails_adversarial = False
        failed_claim = None
        for claim in expected_claims:
            scores_adv = self.model.predict([[answer, claim]])[0]
            probs_adv = softmax(scores_adv)
            if probs_adv[1] >= 0.70:
                entails_adversarial = True
                failed_claim = claim
                break
                
        pass_fail = entails_truth and not entails_adversarial
        
        if pass_fail:
            reason = "NLI: Entails expected truth and rejects adversarial claims."
        elif not entails_truth:
            reason = "NLI: Failed to entail expected truth."
        else:
            reason = f"NLI: Entailed adversarial claim: {failed_claim}"
            
        return {
            "pass_fail": pass_fail,
            "mechanism_used": "contradiction",
            "claims": [{"claim": expected_truth, "status": "ENTAILED" if entails_truth else "NOT_ENTAILED"}],
            "reason": reason
        }
