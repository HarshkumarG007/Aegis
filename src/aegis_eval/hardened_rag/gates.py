import os
import json
from sentence_transformers import CrossEncoder, SentenceTransformer, util
import numpy as np
from scipy.special import softmax

class EvidenceGate:
    def __init__(self, use_v2_5_sufficiency: bool = False, use_v2_7_conditional_conflict: bool = False, 
                 conflict_classifier: str = "A", extractor_mode: str = "E0", llm=None, trigger_mode: str = "T1"):
        self.use_v2_5_sufficiency = use_v2_5_sufficiency
        self.use_v2_7_conditional_conflict = use_v2_7_conditional_conflict
        self.conflict_classifier = conflict_classifier
        self.extractor_mode = extractor_mode
        self.trigger_mode = trigger_mode
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
        final_conflict_state = None
        
        condition_graph = {}
        trace_logs = []
        
        if self.trigger_mode == "T1":
            from aegis_eval.hardened_rag.condition_extractor import ConditionExtractor
            extractor = ConditionExtractor(llm=self.llm, mode=self.extractor_mode)
            
            # O(K) Parsing
            parsed_chunks = []
            for c in chunks:
                cond = extractor.extract(c['text'])
                parsed_chunks.append({"chunk_id": c['chunk_id'], "text": c['text'], "struct": cond})
                condition_graph[c['chunk_id']] = cond
                
            for i in range(len(parsed_chunks)):
                for j in range(i + 1, len(parsed_chunks)):
                    ci = parsed_chunks[i]
                    cj = parsed_chunks[j]
                    
                    # Also compute raw NLI just for logging/telemetry
                    raw_scores = self.nli_model.predict([[ci['text'], cj['text']]])[0]
                    raw_probs_ab = softmax(raw_scores)
                    raw_scores_ba = self.nli_model.predict([[cj['text'], ci['text']]])[0]
                    raw_probs_ba = softmax(raw_scores_ba)
                    raw_contra = max(raw_probs_ab[0], raw_probs_ba[0])
                    raw_nli_triggered = raw_contra >= 0.85
                    
                    prop_a = ci["struct"]["proposition"]
                    prop_b = cj["struct"]["proposition"]
                    
                    scores_ab = self.nli_model.predict([[prop_a, prop_b]])[0]
                    probs_ab = softmax(scores_ab)
                    scores_ba = self.nli_model.predict([[prop_b, prop_a]])[0]
                    probs_ba = softmax(scores_ba)
                    prop_contra = max(probs_ab[0], probs_ba[0])
                    
                    if prop_contra > max_contra_prob:
                        max_contra_prob = prop_contra
                        
                    pair_conflict_state = None
                    if prop_contra >= 0.85:
                        conflicting_chunks.add(ci['chunk_id'])
                        conflicting_chunks.add(cj['chunk_id'])
                        
                        status_a = ci["struct"]["status"]
                        status_b = cj["struct"]["status"]
                        
                        if status_a == "AMBIGUOUS" or status_b == "AMBIGUOUS":
                            pair_conflict_state = "CONFLICT_UNCERTAIN"
                        elif status_a == "EXPLICIT" and status_b == "EXPLICIT":
                            explicit_differentiator = False
                            for key in ["version", "temporal", "scope", "role", "environment"]:
                                vals_a = set(ci["struct"]["conditions"].get(key, []))
                                vals_b = set(cj["struct"]["conditions"].get(key, []))
                                if vals_a and vals_b and not vals_a.intersection(vals_b):
                                    explicit_differentiator = True
                                    break
                            if explicit_differentiator:
                                pair_conflict_state = "CONDITIONAL_COMPATIBILITY"
                            else:
                                pair_conflict_state = "CONTRADICTION"
                        else:
                            pair_conflict_state = "CONTRADICTION"
                            
                        # Keep the most severe conflict state
                        if final_conflict_state is None:
                            final_conflict_state = pair_conflict_state
                        elif pair_conflict_state == "CONTRADICTION":
                            final_conflict_state = "CONTRADICTION"
                        elif pair_conflict_state == "CONFLICT_UNCERTAIN" and final_conflict_state != "CONTRADICTION":
                            final_conflict_state = "CONFLICT_UNCERTAIN"
                            
                        conflict_reason = f"Chunk {ci['chunk_id']} contradicts {cj['chunk_id']}"
                        
                    trace_logs.append({
                        "chunk_i": ci['chunk_id'],
                        "chunk_j": cj['chunk_id'],
                        "raw_nli_triggered": bool(raw_nli_triggered),
                        "e0_status_i": ci["struct"]["status"],
                        "e0_status_j": cj["struct"]["status"],
                        "isolated_proposition_nli": float(prop_contra),
                        "pair_state": pair_conflict_state
                    })
                    
        else:
            # Legacy T0 Mode (Raw NLI Trigger)
            c_i, c_j = None, None
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
                mode = getattr(self, "conflict_classifier", "A")
                if mode == "E":
                    from aegis_eval.hardened_rag.condition_extractor import ConditionExtractor
                    ext_mode = getattr(self, "extractor_mode", "E0")
                    extractor = ConditionExtractor(llm=getattr(self, "llm", None), mode=ext_mode)
                    
                    cond_a = extractor.extract(c_i)
                    cond_b = extractor.extract(c_j)
                    condition_graph["i"] = cond_a
                    condition_graph["j"] = cond_b
                    
                    if cond_a.get("status") == "AMBIGUOUS" or cond_b.get("status") == "AMBIGUOUS":
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
                        elif not (cond_a.get("status") == "EXPLICIT" and cond_b.get("status") == "EXPLICIT"):
                            final_conflict_state = "CONTRADICTION"
                        else:
                            explicit_differentiator = False
                            for key in ["version", "temporal", "scope", "role", "environment"]:
                                vals_a = set(cond_a["conditions"].get(key, []))
                                vals_b = set(cond_b["conditions"].get(key, []))
                                if vals_a and vals_b and not vals_a.intersection(vals_b):
                                    explicit_differentiator = True
                                    break
                            
                            if explicit_differentiator:
                                final_conflict_state = "CONDITIONAL_COMPATIBILITY"
                            else:
                                final_conflict_state = "CONTRADICTION"
                else:
                    final_conflict_state = "CONTRADICTION"

        if conflicting_chunks and final_conflict_state:
            return {
                "state": final_conflict_state,
                "answerable": True if final_conflict_state == "CONDITIONAL_COMPATIBILITY" else False,
                "confidence": float(max_contra_prob),
                "supporting_chunks": supporting_chunks,
                "conflicting_chunks": list(conflicting_chunks),
                "reason": conflict_reason,
                "gate_version": "3.1.0",
                "condition_graph": condition_graph,
                "trace_logs": trace_logs
            }
            
        return {
            "state": "SUFFICIENT",
            "answerable": True,
            "confidence": confidence,
            "supporting_chunks": supporting_chunks,
            "conflicting_chunks": [],
            "reason": "Evidence is sufficient and free of contradiction.",
            "gate_version": "3.1.0",
            "set_score": float(set_score) if self.use_v2_5_sufficiency else float(max(individual_scores)) if individual_scores else 0.0,
            "individual_scores": individual_scores,
            "condition_graph": condition_graph,
            "trace_logs": trace_logs
        }

from aegis_eval.evaluator.claim_extractor import ClaimExtractor

class PostGenerationVerifier:
    def __init__(self, verifier_mode: str = "V1"):
        self.verifier_mode = verifier_mode
        self.sim_model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
        self.nli_model = CrossEncoder('cross-encoder/nli-deberta-v3-small', device='cpu')
        self.claim_extractor = ClaimExtractor()
        
    def verify(self, answer: str, chunks: list, condition_graph: dict = None) -> dict:
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
            
            if self.verifier_mode == "V1":
                if contra_prob >= 0.85:
                    claim_result["status"] = "CONTRADICTED"
                    claim_result["confidence"] = float(contra_prob)
                    any_contradicted = True
                elif entail_prob >= 0.70:
                    claim_result["status"] = "SUPPORTED"
                    claim_result["confidence"] = float(entail_prob)
                else:
                    # 1. Full context check (for comparisons like "Version 2 is longer")
                    combined_text = " ".join(chunk_texts)
                    full_scores = self.nli_model.predict([[combined_text, claim]])[0]
                    full_probs = softmax(full_scores)
                    if full_probs[1] >= 0.70:
                        claim_result["status"] = "SUPPORTED"
                        claim_result["confidence"] = float(full_probs[1])
                    elif full_probs[0] >= 0.85:
                        claim_result["status"] = "CONTRADICTED"
                        claim_result["confidence"] = float(full_probs[0])
                        any_contradicted = True
                    else:
                        # 2. Structural Derivability check (for meta-claims like "It depends on version")
                        differentiators = set()
                        if condition_graph:
                            chunk_ids = list(condition_graph.keys())
                            for i in range(len(chunk_ids)):
                                for j in range(i + 1, len(chunk_ids)):
                                    ci = condition_graph[chunk_ids[i]]
                                    cj = condition_graph[chunk_ids[j]]
                                    if ci["status"] == "EXPLICIT" and cj["status"] == "EXPLICIT":
                                        for key in ["version", "temporal", "scope", "role", "environment"]:
                                            vals_i = set(ci["conditions"].get(key, []))
                                            vals_j = set(cj["conditions"].get(key, []))
                                            if vals_i and vals_j and not vals_i.intersection(vals_j):
                                                differentiators.add(key)
                        
                        if differentiators:
                            is_meta = any(kw in claim.lower() for kw in ["depend", "differ", "varies", "based on", "dependent"])
                            if is_meta:
                                mentioned_diffs = [d for d in differentiators if d in claim.lower()]
                                if mentioned_diffs:
                                    other_conditions = [k for k in ["version", "temporal", "scope", "role", "environment"] if k not in differentiators and k in claim.lower()]
                                    has_causal = any(kw in claim.lower() for kw in ["because", "due to", "since", "therefore"])
                                    
                                    if not other_conditions and not has_causal:
                                        claim_result["status"] = "SUPPORTED"
                                        claim_result["confidence"] = 1.0
                                        claim_result["reason"] = "Deterministically derived from condition graph."
                                
                        if claim_result["status"] == "UNCERTAIN":
                            # If still not supported, it's unsupported
                            claim_result["status"] = "UNSUPPORTED"
                            claim_result["confidence"] = float(1.0 - max(entail_prob, full_probs[1]))
                            any_unsupported = True
                            
            elif self.verifier_mode == "V2":
                # Relaxed semantic mode
                if contra_prob >= 0.85:
                    claim_result["status"] = "CONTRADICTED"
                    claim_result["confidence"] = float(contra_prob)
                    any_contradicted = True
                else:
                    claim_result["status"] = "SUPPORTED"
                    claim_result["confidence"] = float(entail_prob)
                    
            else: # V0
                # Old V2.5 Asymmetric Verifier strict logic
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
                        
            verified_claims.append(claim_result)
            
        if self.verifier_mode in ["V1", "V0"]:
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
            if any_contradicted:
                return {
                    "state": "REJECT",
                    "confidence": 1.0,
                    "reason": "One or more claims are CONTRADICTED.",
                    "verified_claims": verified_claims
                }
            return {
                "state": "PASS",
                "confidence": 1.0,
                "reason": "All claims are supported by the evidence.",
                "verified_claims": verified_claims
            }
