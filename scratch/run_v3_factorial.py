import os
import json
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))
from llama_index.llms.llama_cpp import LlamaCPP
from aegis_eval.hardened_rag.pipeline import HardenedRAGPipeline

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

def run_experiment(pipeline, dataset, results_file):
    results = []
    print(f"Running dataset on {len(dataset)} queries...")
    for q in dataset:
        if "out" in q["id"]:
            q["attack_type"] = "out_of_domain"
        trace = pipeline.execute(q["id"], q["text"])
        trace["query_type"] = q.get("attack_type", "unknown")
        results.append(trace)
        
    os.makedirs(os.path.dirname(results_file), exist_ok=True)
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Saved results to {results_file}")

def run_v3_factorial():
    print("Loading Mistral-7B Generator...")
    mistral = LlamaCPP(
        model_url=None,
        model_path=os.path.abspath("models/mistral-7b-instruct-v0.2.Q4_K_M.gguf"),
        temperature=0.0,
        max_new_tokens=256,
        context_window=4096,
        model_kwargs={"n_gpu_layers": -1},
        verbose=False,
    )
    
    corpus = load_corpus()
    
    # We evaluate on the adversarial-v2.5-challenge.json as our offline set since it's fast
    # and has the necessary properties. (In a real setup we might use a larger split, but this is the untouched eval set for V3 here).
    with open("reports/benchmark-v2.5/adversarial-v2.5-challenge.json", "r") as f:
        dataset = json.load(f)
        
    configs = [
        {"arm": "A", "thresh": 5.25, "inst": "G0"}, # Current Retrieval, Current Generator
        {"arm": "B", "thresh": 5.25, "inst": "G1"}, # Current Retrieval, Improved Generator
        {"arm": "C", "thresh": 4.25, "inst": "G0"}, # Optimized Retrieval, Current Generator
        {"arm": "D", "thresh": 4.25, "inst": "G1"}, # Optimized Retrieval, Improved Generator
    ]
    
    for cfg in configs:
        print(f"\n--- Running Arm {cfg['arm']} (Thresh={cfg['thresh']}, Inst={cfg['inst']}) ---")
        pipeline = HardenedRAGPipeline(
            llm=mistral,
            corpus=corpus,
            ablation_mode='full',
            use_v2_5_sufficiency=True,
            sufficiency_threshold=cfg["thresh"],
            use_v2_5_verifier=False,
            repair_mode="old",
            conflict_classifier="E",
            extractor_mode="E0",
            instruction_mode=cfg["inst"]
        )
        outfile = f"reports/v3.0/traces_arm_{cfg['arm']}.json"
        if not os.path.exists(outfile):
            run_experiment(pipeline, dataset, outfile)
        else:
            print(f"Skipping {outfile}, already exists.")

if __name__ == "__main__":
    run_v3_factorial()
