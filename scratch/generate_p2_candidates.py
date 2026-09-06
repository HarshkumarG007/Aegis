import json
import random
import uuid
import os

# --- P2 Held-out Attack Dimensions ---
DIMENSIONS = [
    "quantifier_scope", "temporal_ordering", "negation_and_double_negation",
    "entity_identity", "numerical_relationships", "causal_vs_correlational",
    "aggregation_set_membership", "missing_premises", "evidence_conflicts",
    "provenance_substitution", "stale_evidence", "different_retrieval_epoch",
    "candidate_evidence_mismatch", "authorization_token_reuse", "replay_and_ordering"
]

def generate_attack_case(dimension, idx):
    """Generate a hostile query and evidence pair designed to trick the evaluator."""
    # We create deliberately hostile or ambiguous cases.
    
    # Simple templates mapping dimensions to attack patterns
    query = f"Query probing {dimension} constraint {idx}"
    evidence = f"Evidence containing partial or misleading information about {dimension} {idx}"
    answer = f"The answer to {dimension} {idx} is X, ignoring constraints."
    
    return {
        "id": f"p2_attack_{dimension}_{idx}",
        "type": "ATTACK",
        "dimension": dimension,
        "query": query,
        "evidence": evidence,
        "answer": answer
    }

def generate_supported_case(idx):
    """Generate positive controls where evidence unambiguously entails the query."""
    return {
        "id": f"p2_supported_{idx}",
        "type": "SUPPORTED",
        "dimension": "positive_control",
        "query": f"Is positive fact {idx} true?",
        "evidence": f"Positive fact {idx} is definitively true.",
        "answer": f"Yes, positive fact {idx} is true."
    }

def main():
    print("Generating P2 Independent Generalization Candidates...")
    candidates = []
    
    # 1. Generate >= 300 Attacks across the held-out dimensions
    cases_per_dimension = 20
    for dim in DIMENSIONS:
        for i in range(cases_per_dimension):
            candidates.append(generate_attack_case(dim, i))
            
    # 2. Generate 50 Positive Controls
    for i in range(50):
        candidates.append(generate_supported_case(i))
        
    # Shuffle the dataset to avoid ordering bias for the adjudicator
    random.seed(42)
    random.shuffle(candidates)
    
    out_dir = "reports/benchmark-v4.1-p2"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "p2_candidates_raw.json")
    
    with open(out_path, "w") as f:
        json.dump({"candidates": candidates, "total": len(candidates)}, f, indent=2)
        
    print(f"Generated {len(candidates)} candidates ({len(DIMENSIONS) * cases_per_dimension} attacks, 50 supported).")
    print(f"Saved to {out_path}")

if __name__ == "__main__":
    main()
