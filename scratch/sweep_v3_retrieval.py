import os
import json
import numpy as np
import math
from collections import defaultdict
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))
from llama_index.core.schema import TextNode
from llama_index.core import VectorStoreIndex, Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from aegis_eval.hardened_rag.gates import EvidenceGate

def load_corpus():
    return {
        "chunk-001": "The database password must be rotated every 90 days. Failure to do so will result in an automatic lock.",
        "chunk-002": "Service A connects to the messaging queue to broadcast events.",
        "chunk-003": "The messaging queue is hosted on redis-01.internal.corp.",
        "chunk-004": "The new API configuration requires all requests to complete within 60 seconds or they will time out.",
        "chunk-005": "In the v1 API, the timeout limit is strictly set to 30 seconds for all endpoints.",
        "chunk-006": "The PUT /user endpoint is deprecated in v2. Please use POST /user/update instead.",
        "chunk-007": "The PUT /user endpoint is still available for legacy applications."
    }

GOLD_MAPPING = {
    "q-con-dev-e4c4757a": ["chunk-004", "chunk-005"],
    "q-con-dev-2cb68234": ["chunk-006", "chunk-007"],
    "q-con-dev-5ca78ed8": ["chunk-004", "chunk-005"],
    "q-con-dev-d34c1f87": ["chunk-006", "chunk-007"],
    "q-con-dev-94734ba4": ["chunk-004", "chunk-005"],
    "q-amb-dev-927ea78e": ["chunk-004", "chunk-005"],
    "q-amb-dev-3a8b8444": ["chunk-006", "chunk-007"],
    "q-amb-dev-62db53c2": ["chunk-004", "chunk-005"],
    "q-amb-dev-1007f24b": ["chunk-006", "chunk-007"],
    "q-amb-dev-b82591cd": ["chunk-002", "chunk-003"],
    "q-mul-dev-cfc43279": ["chunk-002", "chunk-003"],
    "q-mul-dev-747ace8d": ["chunk-002", "chunk-003"],
    "q-mul-dev-1ab559a1": ["chunk-002", "chunk-003"],
    "q-mul-dev-f24a5d11": ["chunk-002", "chunk-003"],
    "q-mul-dev-6f63f545": ["chunk-002", "chunk-003"],
    "q-saf-dev-ef6acdd8": ["chunk-001"],
    "q-saf-dev-fcdc8787": ["chunk-005"],
    "q-saf-dev-0532ec02": ["chunk-006"],
    "q-saf-dev-923e2c6b": ["chunk-003"],
    "q-saf-dev-a1561a5a": ["chunk-002"]
}

def wilson_score_interval(successes, n, z=1.96):
    if n == 0:
        return 0.0, 0.0
    p = successes / n
    denominator = 1 + z**2/n
    centre_adjusted_probability = p + z**2 / (2*n)
    adjusted_standard_deviation = math.sqrt((p*(1 - p) + z**2 / (4*n)) / n)
    lower_bound = (centre_adjusted_probability - z*adjusted_standard_deviation) / denominator
    upper_bound = (centre_adjusted_probability + z*adjusted_standard_deviation) / denominator
    return max(0.0, lower_bound), min(1.0, upper_bound)

def run_v3_sweep():
    with open("reports/benchmark-v2.4.0/adversarial-dev.json", "r") as f:
        dev_queries = json.load(f)
        
    corpus = load_corpus()
    Settings.embed_model = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
    nodes = [TextNode(text=text, id_=cid) for cid, text in corpus.items()]
    index = VectorStoreIndex(nodes)
    
    # Pre-retrieve
    retriever_2 = index.as_retriever(similarity_top_k=2)
    # the user said "possibly top-k / retrieval breadth", we can test top_k=2 and 3
    
    # Freeze gate policy: E+E0
    gate = EvidenceGate(use_v2_5_sufficiency=True, conflict_classifier="E", extractor_mode="E0")
    
    precomputed = []
    
    print("Precomputing retrieval and gate decisions...")
    for q in dev_queries:
        qid = q["id"]
        qtext = q["text"]
        
        is_ood = "out" in qid
        gold_chunks = GOLD_MAPPING.get(qid, [])
        
        nodes_2 = retriever_2.retrieve(qtext)
        retrieved_ids = [n.node.node_id for n in nodes_2]
        retrieved_chunks = [{"chunk_id": n.node.node_id, "text": n.node.text} for n in nodes_2]
        
        recall_success = all(gc in retrieved_ids for gc in gold_chunks) if gold_chunks else False
        if is_ood: recall_success = False
        
        # Evaluate with a low threshold to get raw NLI and sufficiency states
        gate_res = gate.evaluate(qtext, retrieved_chunks, sufficiency_threshold=-100.0)
        
        precomputed.append({
            "qid": qid,
            "qtext": qtext,
            "is_ood": is_ood,
            "gold_chunks": gold_chunks,
            "retrieved_ids": retrieved_ids,
            "recall_success": recall_success,
            "set_score": gate_res.get("set_score", 0.0),
            "gate_state_at_low_thresh": gate_res["state"], # CONFLICT, CONDITIONAL_COMPATIBILITY, SUFFICIENT, etc.
        })
        
    thresholds = [4.00, 4.25, 4.50, 4.75, 5.00, 5.25]
    
    print("\n=== V3.0-A Retrieval Sweep (Dev Set) ===")
    print(f"{'Thresh':<7} | {'Retr Fail':<10} | {'Suff Fail':<10} | {'Conf Fail':<10} | {'Admitted (Ans)':<15} | {'OOD Leakage (95% CI)':<25}")
    
    for t in thresholds:
        metrics = {
            "retrieval_failure": 0,
            "sufficiency_failure": 0,
            "conflict_failure": 0,
            "admitted_ans": 0,
            "ood_leakage": 0,
            "ood_total": 0
        }
        
        # Also let's capture the 7 specific failures
        for p in precomputed:
            if p["is_ood"]:
                metrics["ood_total"] += 1
                if p["set_score"] > t:
                    # check conflict gate
                    if p["gate_state_at_low_thresh"] in ["SUFFICIENT", "CONDITIONAL_COMPATIBILITY"]:
                        metrics["ood_leakage"] += 1
            else:
                # Answerable query decomposition
                if not p["recall_success"]:
                    metrics["retrieval_failure"] += 1
                elif p["set_score"] <= t:
                    metrics["sufficiency_failure"] += 1
                elif p["gate_state_at_low_thresh"] not in ["SUFFICIENT", "CONDITIONAL_COMPATIBILITY"]:
                    metrics["conflict_failure"] += 1
                else:
                    metrics["admitted_ans"] += 1
                    
        leak = metrics["ood_leakage"]
        tot = metrics["ood_total"]
        ans = metrics["admitted_ans"]
        total_ans = 20 # 25 queries, 5 are OOD -> 20 answerable
        lower_ci, upper_ci = wilson_score_interval(leak, tot)
        leak_str = f"{leak}/{tot} [{lower_ci:.1%}, {upper_ci:.1%}]"
        
        print(f"{t:<7.2f} | {metrics['retrieval_failure']:<10} | {metrics['sufficiency_failure']:<10} | {metrics['conflict_failure']:<10} | {ans}/{total_ans:<12} | {leak_str:<25}")
        
        if t == 4.25:
            print("\n--- Failure Decomposition at Threshold 4.25 ---")
            for p in precomputed:
                if not p["is_ood"]:
                    if not p["recall_success"]:
                        print(f"Retrieval Recall Failure: {p['qid']} ({p['qtext']})")
                    elif p["set_score"] <= t:
                        print(f"Sufficiency Threshold Failure: {p['qid']} ({p['qtext']}) [Score: {p['set_score']:.2f}]")
                    elif p["gate_state_at_low_thresh"] not in ["SUFFICIENT", "CONDITIONAL_COMPATIBILITY"]:
                        print(f"Conflict Gate Failure: {p['qid']} ({p['qtext']}) [State: {p['gate_state_at_low_thresh']}]")
            print("-----------------------------------------------\n")

if __name__ == "__main__":
    run_v3_sweep()
