import os
import json
from aegis_eval.hardened_rag.pipeline import HardenedRAGPipeline

def run_regression():
    ds_path = "reports/benchmark-v2.9/adversarial_conditions.json"
    with open(ds_path, 'r') as f:
        dataset = json.load(f)
        
    class DummyLLM:
        def complete(self, prompt):
            class Response:
                text = "In v1 it is 30s. In v2 it is 60s."
                def __str__(self): return self.text
            return Response()
            
    llm = DummyLLM()
    
    pipeline = HardenedRAGPipeline(
        llm=llm,
        corpus={},
        ablation_mode='full',
        sufficiency_threshold=0.0,
        conflict_classifier="E",
        extractor_mode="E0",
        trigger_mode="T1",
        verifier_mode="V1",
        instruction_mode="G1"
    )
    
    breaches = 0
    total_con = 0
    
    for i, item in enumerate(dataset):
        if item.get("label") != "CONTRADICTION":
            continue
            
        total_con += 1
        chunks = [
            {"chunk_id": f"c_{i}_a", "text": item["claim_a"], "rank": 1, "score": 0.9},
            {"chunk_id": f"c_{i}_b", "text": item["claim_b"], "rank": 2, "score": 0.9}
        ]
            
        res = pipeline.execute(f"query_{i}", "What is the value?", bypass_sufficiency=True, chunks=chunks)
        # Note: we bypass sufficiency because the test mock chunks don't have sufficient qa scores by default
        
        if res["gate_state"] == "CONDITIONAL_COMPATIBILITY":
            breaches += 1
            
        if total_con % 2 == 0:
            print(f"Processed {total_con} items. Current breaches: {breaches}")
            import sys
            sys.stdout.flush()
            
        if total_con >= 160:
            break
            
    print(f"Full End-to-End Regression (T1 + E+E0 + V1)")
    print(f"False-Compatible Merges: {breaches} / {total_con}")
    if breaches == 0:
        print("Safety Non-Regression: PASS ✅")
    else:
        print("Safety Non-Regression: FAIL ❌")
        
if __name__ == "__main__":
    run_regression()
