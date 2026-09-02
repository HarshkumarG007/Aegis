import os
import json
import time
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
        print(f"  -> Query: {q['id']}")
        trace = pipeline.execute(q["id"], q["text"])
        trace["query_type"] = q["attack_type"]
        results.append(trace)
        
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Saved results to {results_file}")

def run_v2_5():
    print("Loading models...")
    mistral = LlamaCPP(
        model_url=None,
        model_path=os.path.abspath("models/mistral-7b-instruct-v0.2.Q4_K_M.gguf"),
        temperature=0.0,
        max_new_tokens=256,
        context_window=4096,
        model_kwargs={"n_gpu_layers": -1},
        verbose=False,
    )
    llama = LlamaCPP(
        model_url=None,
        model_path=os.path.abspath("models/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf"),
        temperature=0.0,
        max_new_tokens=256,
        context_window=8192,
        model_kwargs={"n_gpu_layers": -1},
        verbose=False,
    )
    
    with open("reports/benchmark-v2.5/adversarial-v2.5-challenge.json", "r") as f:
        challenge_set = json.load(f)
        
    corpus = load_corpus()
    
    # Ablation matrix definition
    arms = {
        "A": {"use_v2_5_sufficiency": False, "use_v2_5_verifier": False, "repair_mode": "old", "suff_thresh": 1.0},
        "B": {"use_v2_5_sufficiency": True,  "use_v2_5_verifier": False, "repair_mode": "old", "suff_thresh": 5.25},
        "C": {"use_v2_5_sufficiency": True,  "use_v2_5_verifier": True,  "repair_mode": "off", "suff_thresh": 5.25},
        "D": {"use_v2_5_sufficiency": True,  "use_v2_5_verifier": True,  "repair_mode": "whole-answer", "suff_thresh": 5.25},
        "E": {"use_v2_5_sufficiency": True,  "use_v2_5_verifier": True,  "repair_mode": "claim-level", "suff_thresh": 5.25},
        "F": {"use_v2_5_sufficiency": True,  "use_v2_5_verifier": True,  "repair_mode": "observe-only", "suff_thresh": 5.25},
    }
    
    os.makedirs("reports/benchmark-v2.5/arms", exist_ok=True)
    
    for arm_name, config in arms.items():
        print(f"\n==========================================")
        print(f"Executing Arm {arm_name}")
        print(f"Config: {config}")
        print(f"==========================================\n")
        
        # Mistral
        print("Model: Mistral 7B")
        pipeline = HardenedRAGPipeline(
            llm=mistral, 
            corpus=corpus, 
            ablation_mode="full", 
            sufficiency_threshold=config["suff_thresh"],
            use_v2_5_sufficiency=config["use_v2_5_sufficiency"],
            use_v2_5_verifier=config["use_v2_5_verifier"],
            repair_mode=config["repair_mode"]
        )
        run_experiment(pipeline, challenge_set, f"reports/benchmark-v2.5/arms/arm_{arm_name}_mistral.json")
        
        # Llama 3
        print("Model: Llama 3 8B")
        pipeline = HardenedRAGPipeline(
            llm=llama, 
            corpus=corpus, 
            ablation_mode="full", 
            sufficiency_threshold=config["suff_thresh"],
            use_v2_5_sufficiency=config["use_v2_5_sufficiency"],
            use_v2_5_verifier=config["use_v2_5_verifier"],
            repair_mode=config["repair_mode"]
        )
        run_experiment(pipeline, challenge_set, f"reports/benchmark-v2.5/arms/arm_{arm_name}_llama.json")

if __name__ == "__main__":
    run_v2_5()
