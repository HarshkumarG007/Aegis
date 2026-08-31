from sentence_transformers import SentenceTransformer, util, CrossEncoder
from aegis_eval.evaluator.claim_extractor import ClaimExtractor
import numpy as np
from scipy.special import softmax

class CoverageEvaluator:
    def __init__(self):
        self.sim_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.nli_model = CrossEncoder('cross-encoder/nli-deberta-v3-small')
        self.claim_extractor = ClaimExtractor()
        
    def evaluate(self, query: dict, answer: str, chunks_dict: dict) -> dict:
        required_premises = query.get("required_premises", [])
        if not required_premises:
            return {
                "pass_fail": False,
                "mechanism_used": "multi_hop",
                "claims": [],
                "reason": "No required_premises in query metadata"
            }
            
        claims = self.claim_extractor.extract_claims(answer)
        if not claims:
            return {
                "pass_fail": False,
                "mechanism_used": "multi_hop",
                "claims": [],
                "reason": "No claims extracted from answer."
            }

        chunk_ids = list(chunks_dict.keys())
        if chunk_ids:
            chunk_texts = [chunks_dict[cid] for cid in chunk_ids]
            chunk_embeddings = self.sim_model.encode(chunk_texts)
        
        covered_premises = set()
        claim_results = []
        
        for claim in claims:
            supported_chunk_id = None
            
            # Groundedness Check
            if chunk_ids:
                claim_emb = self.sim_model.encode([claim])
                scores = util.cos_sim(claim_emb, chunk_embeddings)[0].tolist()
                
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
                            
                if best_score >= 0.60:
                    nli_scores = self.nli_model.predict([[chunk_texts[best_chunk_idx], claim]])[0]
                    probs = softmax(nli_scores)
                    if probs[1] >= 0.70: # ENTAILED
                        supported_chunk_id = best_chunk_id
            
            claim_result = {
                "claim": claim,
                "supported_chunk_id": supported_chunk_id,
                "premises_covered": []
            }
            
            # Check which premises this claim covers
            for premise in required_premises:
                p_id = premise["premise_id"]
                p_text = premise["text"]
                p_chunks = premise.get("evidence_chunk_ids", [])
                
                covers = False
                # 1. Traces back to required evidence chunk
                if supported_chunk_id and supported_chunk_id in p_chunks:
                    covers = True
                
                # 2. Or directly entails the premise text
                if not covers:
                    nli_scores = self.nli_model.predict([[claim, p_text]])[0]
                    probs = softmax(nli_scores)
                    if probs[1] >= 0.70:
                        covers = True
                        
                if covers:
                    covered_premises.add(p_id)
                    claim_result["premises_covered"].append(p_id)
                    
            claim_results.append(claim_result)
            
        pass_fail = len(covered_premises) >= len(required_premises)
        
        if pass_fail:
            reason = f"Synthesized all {len(required_premises)} required premises."
        else:
            missing = [p["premise_id"] for p in required_premises if p["premise_id"] not in covered_premises]
            reason = f"Failed to synthesize premises: {missing}"

        return {
            "pass_fail": pass_fail,
            "mechanism_used": "multi_hop",
            "claims": claim_results,
            "reason": reason
        }
