from sentence_transformers import SentenceTransformer, util, CrossEncoder
from aegis_eval.evaluator.claim_extractor import ClaimExtractor
import numpy as np
from scipy.special import softmax

class GroundednessEvaluator:
    def __init__(self):
        self.sim_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.nli_model = CrossEncoder('cross-encoder/nli-deberta-v3-small')
        self.claim_extractor = ClaimExtractor()
        
        self.abstain_phrases = [
            "i don't know", "not mentioned", "cannot answer", 
            "no information", "does not contain", "is not provided",
            "i am sorry", "i cannot", "not sure"
        ]
        
    def evaluate(self, query: dict, answer: str, chunks_dict: dict) -> dict:
        ans_lower = answer.lower()
        for p in self.abstain_phrases:
            if p in ans_lower:
                return {
                    "pass_fail": True,
                    "mechanism_used": "out_of_domain",
                    "claims": [],
                    "reason": "Passed via abstention"
                }

        claims = self.claim_extractor.extract_claims(answer)
        if not claims:
            return {
                "pass_fail": True,
                "mechanism_used": "out_of_domain",
                "claims": [],
                "reason": "No claims extracted from answer."
            }

        if not chunks_dict:
            # If no chunks, everything is ungrounded
            return {
                "pass_fail": False,
                "mechanism_used": "out_of_domain",
                "claims": [{"claim": c, "status": "UNSUPPORTED", "evidence_chunk_id": None} for c in claims],
                "reason": "No chunks provided"
            }

        chunk_ids = list(chunks_dict.keys())
        chunk_texts = [chunks_dict[cid] for cid in chunk_ids]
        chunk_embeddings = self.sim_model.encode(chunk_texts)

        claim_results = []
        any_failed = False
        
        for claim in claims:
            claim_emb = self.sim_model.encode([claim])
            scores = util.cos_sim(claim_emb, chunk_embeddings)[0].tolist()
            
            # Find best chunk: highest score, tie-break by chunk_id string (alphabetically first)
            best_chunk_idx = -1
            best_score = -1.0
            best_chunk_id = None
            
            for i, score in enumerate(scores):
                if score > best_score:
                    best_score = score
                    best_chunk_idx = i
                    best_chunk_id = chunk_ids[i]
                elif score == best_score:
                    if best_chunk_id is None or chunk_ids[i] < best_chunk_id:
                        best_score = score
                        best_chunk_idx = i
                        best_chunk_id = chunk_ids[i]
            
            if best_score < 0.60:
                status = "UNSUPPORTED"
                any_failed = True
            else:
                best_text = chunk_texts[best_chunk_idx]
                nli_scores = self.nli_model.predict([[best_text, claim]])[0]
                probs = softmax(nli_scores)
                
                contra_prob = probs[0]
                entail_prob = probs[1]
                
                if contra_prob >= 0.85:
                    status = "CONTRADICTED"
                    any_failed = True
                elif entail_prob >= 0.70:
                    status = "SUPPORTED"
                else:
                    status = "PARTIAL"
            
            claim_results.append({
                "claim": claim,
                "status": status,
                "evidence_chunk_id": best_chunk_id,
                "similarity_score": float(best_score)
            })

        pass_fail = not any_failed
        reason = "All claims grounded" if pass_fail else "One or more claims are UNSUPPORTED or CONTRADICTED."

        return {
            "pass_fail": pass_fail,
            "mechanism_used": "out_of_domain",
            "claims": claim_results,
            "reason": reason
        }
