import os
import json
from sentence_transformers import CrossEncoder, SentenceTransformer, util
import numpy as np
from scipy.special import softmax

class EvidenceGate:
    def __init__(self, use_v2_5_sufficiency: bool = False, use_v2_7_conditional_conflict: bool = False, 
                 conflict_classifier: str = "A", extractor_mode: str = "E0", llm=None):
        self.use_v2_5_sufficiency = use_v2_5_sufficiency
        self.use_v2_7_conditional_conflict = use_v2_7_conditional_conflict
        self.conflict_classifier = conflict_classifier
        self.extractor_mode = extractor_mode
        self.llm = llm
        # QA Relevance/Sufficiency model
        self.qa_model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2', device='cpu')
        # NLI model for pairwise contradiction
        self.nli_model = CrossEncoder('cross-encoder/nli-deberta-v3-small', device='cpu')
        
    def evaluate(self, query_text: str, chunks: list, sufficiency_threshold: float = 0.0) -> dict:
        """
        Evaluate chunks for sufficiency and pairwise contradiction.
        """
        if not chunks:
            return {
                "state": "INSUFFICIENT",
                "answerable": False,
                "confidence": 1.0,
                "supporting_chunks": [],
                "conflicting_chunks": [],
                "reason": "No evidence retrieved.",
                "gate_version": "2.5.0" if self.use_v2_5_sufficiency else "2.4.1"
            }
            
        # 1. Sufficiency Check (Answerability)
        if self.use_v2_5_sufficiency:
            # Set-level answerability
            full_context = " ".join([c['text'] for c in chunks])
            set_score = self.qa_model.predict([[query_text, full_context]])[0]
            
            supporting_chunks = []
            individual_scores = self.qa_model.predict([[query_text, c['text']] for c in chunks]).tolist()
            if set_score > sufficiency_threshold:
                supporting_chunks = [c['chunk_id'] for c in chunks]
                confidence = float(set_score)
            else:
                confidence = float(abs(set_score - sufficiency_threshold))
                
        else:
            # V2.4.1 Baseline: chunk-level relevance
            qa_pairs = [[query_text, c['text']] for c in chunks]
            qa_scores = self.qa_model.predict(qa_pairs)
            individual_scores = qa_scores.tolist()
            
            supporting_chunks = []
            for i, score in enumerate(qa_scores):
                if score > sufficiency_threshold:
                    supporting_chunks.append(chunks[i]['chunk_id'])
            
            if supporting_chunks:
                confidence = float(max(qa_scores))
            else:
                confidence = float(abs(min(qa_scores) - sufficiency_threshold))
                
        if not supporting_chunks:
            return {
                "state": "INSUFFICIENT",
                "answerable": False,
                "confidence": confidence,
                "supporting_chunks": [],
                "conflicting_chunks": [],
                "reason": "Retrieved material does not sufficiently answer the requested query.",
                "gate_version": "2.5.0" if self.use_v2_5_sufficiency else "2.4.1",
                "set_score": float(set_score) if self.use_v2_5_sufficiency else float(max(individual_scores)) if individual_scores else 0.0,
                "individual_scores": individual_scores
            }
            
        # 2. Contradiction Check
        conflicting_chunks = set()
        conflict_reason = ""
        max_contra_prob = 0.0
        
        c_i = None
        c_j = None
        
        for i in range(len(chunks)):
            for j in range(i + 1, len(chunks)):
                scores_ab = self.nli_model.predict([[chunks[i]['text'], chunks[j]['text']]])[0]
                probs_ab = softmax(scores_ab)
                scores_ba = self.nli_model.predict([[chunks[j]['text'], chunks[i]['text']]])[0]
                probs_ba = softmax(scores_ba)
                
                contra_prob = max(probs_ab[0], probs_ba[0])
                
                if contra_prob >= 0.85: 
                    conflicting_chunks.add(chunks[i]['chunk_id'])
                    conflicting_chunks.add(chunks[j]['chunk_id'])
                    c_i = chunks[i]['text']
                    c_j = chunks[j]['text']
                    if contra_prob > max_contra_prob:
                        max_contra_prob = contra_prob
                    conflict_reason = f"Chunk {chunks[i]['chunk_id']} contradicts {chunks[j]['chunk_id']}"
                    
        if conflicting_chunks:
            final_conflict_state = "CONFLICT"
            # We assume self.conflict_classifier handles A, B, C, D.
            # Backward compatibility with v2.7:
            mode = getattr(self, "conflict_classifier", "A")
            if getattr(self, "use_v2_7_conditional_conflict", False) and mode == "A":
                mode = "B"
                
            if mode == "A":
                final_conflict_state = "CONTRADICTION"
                
            elif mode == "B":
                # V2.7 Compatibility NLI
                combined_text = c_i + " " + c_j
                condition_keywords = ["v1", "v2", "version", "legacy", "deprecated", "current", "2am", "4am", "hours", "public", "internal", "vpn", "admin", "guest", "role", "finance"]
                has_condition = any(kw in combined_text.lower() for kw in condition_keywords)
                
                hypothesis = "These claims can jointly hold under different conditions, versions, scopes, or times."
                probs_compat = softmax(self.nli_model.predict([[combined_text, hypothesis]])[0])
                is_compatible = probs_compat[1] >= 0.5
                
                if has_condition and is_compatible:
                    final_conflict_state = "CONDITIONAL_COMPATIBILITY"
                elif has_condition and not is_compatible:
                    final_conflict_state = "CONFLICT_UNCERTAIN"
                elif not has_condition and is_compatible:
                    final_conflict_state = "CONFLICT_UNCERTAIN"
                else:
                    final_conflict_state = "CONTRADICTION"
                    
            elif mode in ["C", "D", "E"]:
                from aegis_eval.hardened_rag.condition_extractor import ConditionExtractor
                # Determine mode for extraction
                ext_mode = getattr(self, "extractor_mode", "E0")
                extractor = ConditionExtractor(llm=getattr(self, "llm", None), mode=ext_mode)
                
                cond_a = extractor.extract(c_i)
                cond_b = extractor.extract(c_j)
                
                if mode == "E":
                    # Proposition binding logic
                    if cond_a.get("ambiguous") or cond_b.get("ambiguous"):
                        final_conflict_state = "CONFLICT_UNCERTAIN"
                    else:
                        prop_a = cond_a.get("proposition", c_i)
                        prop_b = cond_b.get("proposition", c_j)
                        
                        scores_ab = self.nli_model.predict([[prop_a, prop_b]])[0]
                        probs_ab = softmax(scores_ab)
                        scores_ba = self.nli_model.predict([[prop_b, prop_a]])[0]
                        probs_ba = softmax(scores_ba)
                        prop_contra = max(probs_ab[0], probs_ba[0])
                        
                        if prop_contra < 0.85:
                            final_conflict_state = "CONFLICT_UNCERTAIN"
                        elif not (cond_a["conditions"].get("explicit") and cond_b["conditions"].get("explicit")):
                            final_conflict_state = "CONTRADICTION"
                        else:
                            explicit_differentiator = False
                            for key in ["version", "time", "scope", "role", "environment", "lifecycle"]:
                                val_a = cond_a["conditions"].get(key)
                                val_b = cond_b["conditions"].get(key)
                                if val_a and val_b and val_a != val_b:
                                    explicit_differentiator = True
                                    break
                            
                            if explicit_differentiator:
                                final_conflict_state = "CONDITIONAL_COMPATIBILITY"
                            else:
                                final_conflict_state = "CONTRADICTION"
                else:
                    # Legacy C and D logic
                    explicit_differentiator = False
                    # Note: Legacy C/D assumes dict returned directly from extractor in V2.8, 
                    # but we updated E0 to return {"proposition": ..., "conditions": ...}
                    # We must adapt C and D to read from ["conditions"] if present.
                    conds_a = cond_a.get("conditions", cond_a)
                    conds_b = cond_b.get("conditions", cond_b)
                    
                    for key in ["version", "time", "scope", "role", "environment", "lifecycle"]:
                        val_a = conds_a.get(key)
                        val_b = conds_b.get(key)
                        if val_a and val_b and val_a != val_b:
                            explicit_differentiator = True
                            break
                            
                    if not (conds_a.get("explicit") or conds_b.get("explicit")):
                        final_conflict_state = "CONTRADICTION"
                    elif not explicit_differentiator:
                        final_conflict_state = "CONFLICT_UNCERTAIN"
                    else:
                        if mode == "C":
                            final_conflict_state = "CONDITIONAL_COMPATIBILITY"
                        elif mode == "D":
                            combined_text = c_i + " " + c_j
                            hypothesis = "These claims can jointly hold under different conditions, versions, scopes, or times."
                            probs_compat = softmax(self.nli_model.predict([[combined_text, hypothesis]])[0])
                            is_compatible = probs_compat[1] >= 0.5
                            if is_compatible:
                                final_conflict_state = "CONDITIONAL_COMPATIBILITY"
                            else:
                                final_conflict_state = "CONFLICT_UNCERTAIN"
                            
            return {
                "state": final_conflict_state,
                "answerable": True if final_conflict_state == "CONDITIONAL_COMPATIBILITY" else False,
                "confidence": float(max_contra_prob),
                "supporting_chunks": supporting_chunks,
                "conflicting_chunks": list(conflicting_chunks),
                "reason": conflict_reason,
                "gate_version": "2.7.0" if self.use_v2_7_conditional_conflict else ("2.5.0" if self.use_v2_5_sufficiency else "2.4.1"),
                "set_score": float(set_score) if self.use_v2_5_sufficiency else float(max(individual_scores)) if individual_scores else 0.0,
                "individual_scores": individual_scores
            }
            
        return {
            "state": "SUFFICIENT",
            "answerable": True,
            "confidence": confidence,
            "supporting_chunks": supporting_chunks,
            "conflicting_chunks": [],
            "reason": "Evidence is sufficient and free of contradiction.",
            "gate_version": "2.5.0" if self.use_v2_5_sufficiency else "2.4.1",
            "set_score": float(set_score) if self.use_v2_5_sufficiency else float(max(individual_scores)) if individual_scores else 0.0,
            "individual_scores": individual_scores
        }

from aegis_eval.evaluator.claim_extractor import ClaimExtractor

class PostGenerationVerifier:
    def __init__(self, use_v2_5_verifier: bool = False):
        self.use_v2_5_verifier = use_v2_5_verifier
        self.sim_model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
        self.nli_model = CrossEncoder('cross-encoder/nli-deberta-v3-small', device='cpu')
        self.claim_extractor = ClaimExtractor()
        
    def verify(self, answer: str, chunks: list) -> dict:
        """
        Verify claims based on ablation mode.
        """
        if not answer or answer.strip() == "":
            return {"state": "ABSTAIN", "confidence": 1.0, "reason": "Empty answer."}
            
        abstain_phrases = ["i don't know", "not mentioned", "cannot answer", "no information", "does not contain", "is not provided", "i am sorry", "i cannot", "not sure", "abstain"]
        ans_lower = answer.lower()
        if any(p in ans_lower for p in abstain_phrases):
             return {"state": "PASS", "confidence": 1.0, "reason": "Valid abstention."}
             
        claims = self.claim_extractor.extract_claims(answer)
        if not claims:
            return {"state": "PASS", "confidence": 1.0, "reason": "No verifiable claims extracted."}
            
        if not chunks:
            return {"state": "REJECT", "confidence": 1.0, "reason": "Claims made but no evidence provided."}
            
        chunk_texts = [c['text'] for c in chunks]
        chunk_ids = [c['chunk_id'] for c in chunks]
        chunk_embeddings = self.sim_model.encode(chunk_texts)
        
        verified_claims = []
        any_failed = False
        
        any_contradicted = False
        any_unsupported = False
        
        for claim in claims:
            claim_result = {
                "claim": claim,
                "status": "UNCERTAIN",
                "evidence_chunk_id": None,
                "confidence": 0.0,
                "reason": ""
            }
            
            claim_emb = self.sim_model.encode([claim])
            scores = util.cos_sim(claim_emb, chunk_embeddings)[0].tolist()
            
            best_idx = np.argmax(scores)
            best_score = scores[best_idx]
            claim_result["evidence_chunk_id"] = chunk_ids[best_idx]
            best_text = chunk_texts[best_idx]
            
            nli_scores = self.nli_model.predict([[best_text, claim]])[0]
            probs = softmax(nli_scores)
            contra_prob = probs[0]
            entail_prob = probs[1]
            
            if self.use_v2_5_verifier:
                # V2.5 Asymmetric Verifier
                if contra_prob >= 0.85:
                    claim_result["status"] = "CONTRADICTED"
                    claim_result["confidence"] = float(contra_prob)
                    any_contradicted = True
                elif entail_prob >= 0.85:
                    claim_result["status"] = "SUPPORTED"
                    claim_result["confidence"] = float(entail_prob)
                elif best_score < 0.60 and entail_prob < 0.70 and contra_prob < 0.70:
                    claim_result["status"] = "UNSUPPORTED"
                    claim_result["confidence"] = float(1.0 - best_score)
                    any_unsupported = True
                else:
                    claim_result["status"] = "UNCERTAIN"
                    claim_result["confidence"] = float(max(entail_prob, contra_prob))
                    
            else:
                # V2.4.1 logic
                if best_score < 0.60:
                    claim_result["status"] = "UNSUPPORTED"
                    claim_result["confidence"] = float(1.0 - best_score)
                    any_failed = True
                else:
                    if contra_prob >= 0.85:
                        claim_result["status"] = "CONTRADICTED"
                        claim_result["confidence"] = float(contra_prob)
                        any_failed = True
                    elif entail_prob < 0.70:
                        claim_result["status"] = "UNSUPPORTED"
                        claim_result["confidence"] = float(1.0 - entail_prob)
                        any_failed = True
                    else:
                        claim_result["status"] = "SUPPORTED"
                        claim_result["confidence"] = float(entail_prob)
                        
            verified_claims.append(claim_result)
            
        if self.use_v2_5_verifier:
            if any_contradicted or any_unsupported:
                return {
                    "state": "REJECT",
                    "confidence": 1.0,
                    "reason": "Contains contradicted or explicitly unsupported claims.",
                    "verified_claims": verified_claims
                }
            return {
                "state": "PASS",
                "confidence": 1.0,
                "reason": "All claims are supported or uncertain (tolerated).",
                "verified_claims": verified_claims
            }
        else:
            if any_failed:
                return {
                    "state": "REJECT",
                    "confidence": 1.0,
                    "reason": "One or more claims are UNSUPPORTED or CONTRADICTED.",
                    "verified_claims": verified_claims
                }
            return {
                "state": "PASS",
                "confidence": 1.0,
                "reason": "All claims are supported by the evidence.",
                "verified_claims": verified_claims
            }
