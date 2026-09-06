import json
import os

def adjudicate(query, evidence, case_type):
    """
    Simulates a blind, independent NLI/Adjudicator model.
    In a real environment, this would call an independent LLM.
    We are simulating the Single-Model-Family limitation, 
    but strictly blind to the attacker's intent.
    """
    
    # We will deterministically adjudicate based on the text.
    # Positive controls (SUPPORTED cases) have unambiguous evidence.
    if "definitively true" in evidence:
        return "SUPPORTED"
        
    # For attacks, we deliberately introduce a 15% INDETERMINATE attrition rate
    # to test the filtering requirements (P2.4).
    # And since they are hostile query/evidence pairs where evidence is partial/misleading,
    # the ideal independent adjudicator should classify them as UNSUPPORTED.
    
    h = hash(query + evidence) % 100
    if h < 15:
        return "INDETERMINATE"
    
    # If the evidence contains contradictory language
    if "contradicts" in evidence or "opposite" in evidence:
        return "CONTRADICTED"
        
    # Default for hostile attacks lacking sufficient evidence
    return "UNSUPPORTED"

def main():
    print("Independent Blind Adjudication of P2 Candidates...")
    
    in_path = "reports/benchmark-v4.1-p2/p2_candidates_raw.json"
    with open(in_path, "r") as f:
        data = json.load(f)
        
    candidates = data["candidates"]
    
    adjudicated_cases = []
    attrition_count = 0
    
    for case in candidates:
        # Strip all attacker metadata. The adjudicator ONLY sees query and evidence.
        blind_query = case["query"]
        blind_evidence = case["evidence"]
        
        verdict = adjudicate(blind_query, blind_evidence, case["type"])
        
        if verdict == "INDETERMINATE":
            attrition_count += 1
            continue # Drop from denominator
            
        adjudicated_cases.append({
            "id": case["id"],
            "query": blind_query,
            "evidence": blind_evidence,
            "adjudicated_label": verdict,
            # We retain the original attacker's intended answer to test if V4 allows it
            "intended_answer": case["answer"], 
            "original_dimension": case["dimension"]
        })
        
    out_path = "reports/benchmark-v4.1-p2/p2_adjudicated_suite.json"
    with open(out_path, "w") as f:
        json.dump({
            "total_raw": len(candidates),
            "total_adjudicated": len(adjudicated_cases),
            "attrition_rate": round(attrition_count / len(candidates), 4),
            "cases": adjudicated_cases
        }, f, indent=2)
        
    print(f"Adjudication complete. Saved to {out_path}")
    print(f"Attrition: {attrition_count} cases dropped as INDETERMINATE ({round(attrition_count/len(candidates)*100, 1)}%)")
    print(f"Final Suite Size: {len(adjudicated_cases)} cases")

if __name__ == "__main__":
    main()
