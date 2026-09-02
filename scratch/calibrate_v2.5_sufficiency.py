import os
import json
import numpy as np
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

def run_calibration():
    print("Loading Dev dataset...")
    with open("reports/benchmark-v2.4.0/adversarial-dev.json", "r") as f:
        dev_queries = json.load(f)
        
    corpus = load_corpus()
    
    print("Setting up models...")
    Settings.embed_model = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
    nodes = [TextNode(text=text, id_=cid) for cid, text in corpus.items()]
    index = VectorStoreIndex(nodes)
    retriever = index.as_retriever(similarity_top_k=2)
    
    evidence_gate = EvidenceGate(use_v2_5_sufficiency=True)
    
    print("Precomputing Set-Level Sufficiency scores...")
    results = []
    
    for query_obj in dev_queries:
        query_id = query_obj["id"]
        query_text = query_obj["text"]
        
        # Gold answerable for sufficiency
        gold_ans = True
        if "out" in query_id:
            gold_ans = False
            
        # Retrieve chunks
        nodes = retriever.retrieve(query_text)
        chunks = [{"chunk_id": n.node.node_id, "text": n.node.text} for n in nodes]
        
        # We can just call evaluate to get the scores
        gate_res = evidence_gate.evaluate(query_text, chunks, sufficiency_threshold=-100.0)
        set_score = gate_res.get("set_score", 0.0)
        individual_scores = gate_res.get("individual_scores", [])
        
        results.append({
            "query_id": query_id,
            "query": query_text,
            "chunk_ids": [c['chunk_id'] for c in chunks],
            "individual_scores": individual_scores,
            "set_score": set_score,
            "gold_answerable": gold_ans
        })
        
    print(f"Precomputed {len(results)} queries.")
    
    # Sweep thresholds
    thresholds = np.linspace(0.0, 15.0, 61) # 0.0 to 15.0 in 0.25 steps
    
    print("\nSweeping Set-Level Sufficiency Thresholds (Dev)")
    print(f"{'Threshold':<10} | {'TP':<4} | {'FP':<4} | {'TN':<4} | {'FN':<4} | {'OOD Recall':<12} | {'Ans Preserv':<12}")
    
    best_threshold = None
    best_ans_pres = -1
    
    for t in thresholds:
        tp, fp, tn, fn = 0, 0, 0, 0
        ood_tn = 0
        ood_total = 0
        for res in results:
            predicted_ans = (res["set_score"] > t)
            actual_ans = res["gold_answerable"]
            
            if actual_ans and predicted_ans: tp += 1
            elif actual_ans and not predicted_ans: fn += 1
            elif not actual_ans and predicted_ans: fp += 1
            elif not actual_ans and not predicted_ans: tn += 1
            
            if "out" in res["query_id"]:
                ood_total += 1
                if not predicted_ans: ood_tn += 1
                
        # Metrics
        total_ans = tp + fn
        ans_preserv = (tp / total_ans) if total_ans > 0 else 0.0
        ood_recall = (ood_tn / ood_total) if ood_total > 0 else 0.0
        
        print(f"{t:<10.2f} | {tp:<4} | {fp:<4} | {tn:<4} | {fn:<4} | {ood_recall:<12.0%} | {ans_preserv:<12.0%}")
        
        # Predefined rule: Maximize Answerable Preservation while OOD Recall == 100%
        if ood_recall == 1.0:
            if ans_preserv > best_ans_pres:
                best_ans_pres = ans_preserv
                best_threshold = t
                
    print(f"\nSelected Set-Level Sufficiency Threshold: {best_threshold:.2f} (Answerable Preservation: {best_ans_pres:.0%})")
    
    # Save the selected threshold as frozen artifact
    os.makedirs("reports/v2.5", exist_ok=True)
    with open("reports/v2.5/set_level_sufficiency_calibration.json", "w") as f:
        json.dump({
            "selected_threshold": best_threshold,
            "dev_answerable_preservation": best_ans_pres,
            "dev_ood_recall": 1.0,
            "raw_scores": results
        }, f, indent=2)
        
    print("Calibration complete. Raw scores saved to reports/v2.5/set_level_sufficiency_calibration.json")

if __name__ == "__main__":
    run_calibration()
