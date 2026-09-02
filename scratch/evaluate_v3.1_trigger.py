import os
import json
from aegis_eval.hardened_rag.pipeline import HardenedRAGPipeline

def run_ablation():
    # Load dataset
    ds_path = "reports/benchmark-v2.9/adversarial_conditions.json"
    if not os.path.exists(ds_path):
        print(f"Dataset not found at {ds_path}")
        return
        
    with open(ds_path, 'r') as f:
        dataset = json.load(f)
        
    # We only care about T0 vs T1 on the contradiction merges.
    # The dataset contains query clusters.
    
    # Let's mock a simple llm that just returns empty strings since we only care about the gate
    class DummyLLM:
        def complete(self, prompt):
            class Response:
                text = "mock"
                def __str__(self): return "mock"
            return Response()
            
    llm = DummyLLM()
    
    results = {"T0": [], "T1": []}
    
    for mode in ["T0", "T1"]:
        print(f"\nRunning {mode}...")
        pipeline = HardenedRAGPipeline(
            llm=llm,
            corpus={}, # Not used since we manually construct chunks
            ablation_mode='conflict',
            sufficiency_threshold=0.0,
            conflict_classifier="E",
            extractor_mode="E0",
            trigger_mode=mode
        )
        
        breaches = 0
        for i, item in enumerate(dataset):
            if item.get("label") != "CONTRADICTION":
                continue
                
            # Construct chunks
            chunks = [
                {"chunk_id": f"c_{i}_a", "text": item["claim_a"], "rank": 1, "score": 0.9},
                {"chunk_id": f"c_{i}_b", "text": item["claim_b"], "rank": 2, "score": 0.9}
            ]
            
            gate_decision = pipeline.evidence_gate.evaluate("What is the value?", chunks, 0.0)
            
            if mode == "T1":
                logs = gate_decision.get("trace_logs", [])
                if logs:
                    log = logs[0]
                    # Print audit trail
                    # print(f"Audit: RawNLI={log['raw_nli_triggered']} | E0_I={log['e0_status_i']} | E0_J={log['e0_status_j']} | Gate={gate_decision['state']}")
                    
            if gate_decision["state"] == "CONDITIONAL_COMPATIBILITY":
                breaches += 1
                
            results[mode].append({
                "item_id": i,
                "gate_state": gate_decision["state"],
                "logs": gate_decision.get("trace_logs", [])
            })
            
        print(f"{mode} False-Compatible Merges: {breaches} / {len(results[mode])}")
        
    with open("reports/v3.1_trigger_ablation.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    run_ablation()
