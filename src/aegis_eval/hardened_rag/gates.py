import os
import json
from sentence_transformers import CrossEncoder, SentenceTransformer, util
import numpy as np
from scipy.special import softmax

class EvidenceGate:
    def __init__(self):
        # QA Relevance/Sufficiency model
        self.qa_model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2', device='cpu')
        # NLI model for pairwise contradiction
        self.nli_model = CrossEncoder('cross-encoder/nli-deberta-v3-small', device='cpu')
        
    def evaluate(self, query_text: str, chunks: list) -> dict:
        """
        Evaluate chunks for sufficiency and pairwise contradiction.
        chunks: list of dicts with 'chunk_id' and 'text'
        Returns structured decision.
        """
        if not chunks:
            return {
                "state": "INSUFFICIENT",
                "answerable": False,
                "confidence": 1.0,
                "supporting_chunks": [],
                "conflicting_chunks": [],
                "reason": "No evidence retrieved.",
                "gate_version": "2.4.0"
            }
            
        # 1. Sufficiency Check (Answerability)
        # Using MS-MARCO CrossEncoder: scores > 0 generally indicate relevance/answerability
        qa_pairs = [[query_text, c['text']] for c in chunks]
        qa_scores = self.qa_model.predict(qa_pairs)
        
        supporting_chunks = []
        for i, score in enumerate(qa_scores):
            if score > 0.0:  # Threshold for answerability
                supporting_chunks.append(chunks[i]['chunk_id'])
                
        if not supporting_chunks:
            return {
                "state": "INSUFFICIENT",
                "answerable": False,
                "confidence": float(abs(min(qa_scores))),
                "supporting_chunks": [],
                "conflicting_chunks": [],
                "reason": "Retrieved material does not sufficiently answer the requested query.",
                "gate_version": "2.4.0"
            }
            
        # 2. Contradiction Check (Pairwise among supporting chunks, or all chunks)
        # Only check contradiction among chunks that are actually relevant or all chunks?
        # Better to check all retrieved chunks to catch poisoned/conflicting context.
        conflicting_chunks = set()
        conflict_reason = ""
        max_contra_prob = 0.0
        
        for i in range(len(chunks)):
            for j in range(i + 1, len(chunks)):
                # Predict NLI (A -> B)
                scores_ab = self.nli_model.predict([[chunks[i]['text'], chunks[j]['text']]])[0]
                probs_ab = softmax(scores_ab)
                # Predict NLI (B -> A)
                scores_ba = self.nli_model.predict([[chunks[j]['text'], chunks[i]['text']]])[0]
                probs_ba = softmax(scores_ba)
                
                # prob[0] is contradiction in nli-deberta-v3-small
                contra_prob = max(probs_ab[0], probs_ba[0])
                
                if contra_prob >= 0.85: # High confidence contradiction
                    conflicting_chunks.add(chunks[i]['chunk_id'])
                    conflicting_chunks.add(chunks[j]['chunk_id'])
                    if contra_prob > max_contra_prob:
                        max_contra_prob = contra_prob
                    conflict_reason = f"Chunk {chunks[i]['chunk_id']} contradicts {chunks[j]['chunk_id']}"
                    
        if conflicting_chunks:
            return {
                "state": "CONFLICT",
                "answerable": False,
                "confidence": float(max_contra_prob),
                "supporting_chunks": supporting_chunks,
                "conflicting_chunks": list(conflicting_chunks),
                "reason": conflict_reason,
                "gate_version": "2.4.0"
            }
            
        return {
            "state": "SUFFICIENT",
            "answerable": True,
            "confidence": float(max(qa_scores)),
            "supporting_chunks": supporting_chunks,
            "conflicting_chunks": [],
            "reason": "Evidence is sufficient and free of contradiction.",
            "gate_version": "2.4.0"
        }

from aegis_eval.evaluator.claim_extractor import ClaimExtractor

class PostGenerationVerifier:
    def __init__(self):
        self.sim_model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
        self.nli_model = CrossEncoder('cross-encoder/nli-deberta-v3-small', device='cpu')
        self.claim_extractor = ClaimExtractor()
        
    def verify(self, answer: str, chunks: list) -> dict:
        """
        Verify that all claims in the generated answer are supported by the chunks.
        """
        if not answer or answer.strip() == "":
            return {
                "state": "ABSTAIN",
                "confidence": 1.0,
                "reason": "Empty answer."
            }
            
        # Check for abstention phrases
        abstain_phrases = ["i don't know", "not mentioned", "cannot answer", "no information", "does not contain", "is not provided", "i am sorry", "i cannot", "not sure", "abstain"]
        ans_lower = answer.lower()
        if any(p in ans_lower for p in abstain_phrases):
             return {
                 "state": "PASS",
                 "confidence": 1.0,
                 "reason": "Valid abstention."
             }
             
        claims = self.claim_extractor.extract_claims(answer)
        if not claims:
            # If no declarative claims, it's probably safe/pass
            return {
                "state": "PASS",
                "confidence": 1.0,
                "reason": "No verifiable claims extracted."
            }
            
        if not chunks:
            return {
                "state": "REJECT",
                "confidence": 1.0,
                "reason": "Claims made but no evidence provided."
            }
            
        chunk_texts = [c['text'] for c in chunks]
        chunk_ids = [c['chunk_id'] for c in chunks]
        chunk_embeddings = self.sim_model.encode(chunk_texts)
        
        any_failed = False
        rejection_reason = ""
        max_fail_confidence = 0.0
        
        for claim in claims:
            claim_emb = self.sim_model.encode([claim])
            scores = util.cos_sim(claim_emb, chunk_embeddings)[0].tolist()
            
            best_idx = np.argmax(scores)
            best_score = scores[best_idx]
            
            if best_score < 0.60:
                any_failed = True
                rejection_reason = f"Claim lacks semantic match in evidence: '{claim}'"
                max_fail_confidence = max(max_fail_confidence, 1.0 - best_score)
            else:
                best_text = chunk_texts[best_idx]
                nli_scores = self.nli_model.predict([[best_text, claim]])[0]
                probs = softmax(nli_scores)
                
                contra_prob = probs[0]
                entail_prob = probs[1]
                
                if contra_prob >= 0.85:
                    any_failed = True
                    rejection_reason = f"Claim contradicted by evidence: '{claim}'"
                    max_fail_confidence = max(max_fail_confidence, contra_prob)
                elif entail_prob < 0.70:
                    any_failed = True
                    rejection_reason = f"Claim unsupported by evidence: '{claim}'"
                    max_fail_confidence = max(max_fail_confidence, 1.0 - entail_prob)
                    
        if any_failed:
            return {
                "state": "REJECT",
                "confidence": float(max_fail_confidence),
                "reason": rejection_reason
            }
            
        return {
            "state": "PASS",
            "confidence": 1.0,
            "reason": "All claims are supported by the evidence."
        }
