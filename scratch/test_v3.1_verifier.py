import os
import json
from aegis_eval.hardened_rag.gates import PostGenerationVerifier

def run_verifier_test():
    chunks = [
        {"chunk_id": "c_v1", "text": "In v1, the timeout is 30 seconds."},
        {"chunk_id": "c_v2", "text": "In v2, the timeout is 60 seconds."}
    ]
    
    # We must synthesize a condition graph that EvidenceGate would produce
    condition_graph = {
        "c_v1": {
            "status": "EXPLICIT",
            "proposition": "the timeout is 30 seconds.",
            "conditions": {"version": ["v1"], "temporal": [], "scope": [], "role": [], "environment": []}
        },
        "c_v2": {
            "status": "EXPLICIT",
            "proposition": "the timeout is 60 seconds.",
            "conditions": {"version": ["v2"], "temporal": [], "scope": [], "role": [], "environment": []}
        }
    }
    
    test_cases = [
        {
            "claim": "In v1, the timeout is 30 seconds.",
            "expected_V1": "SUPPORTED",
            "desc": "Direct source claim"
        },
        {
            "claim": "The timeout depends on API version.",
            "expected_V1": "SUPPORTED",
            "desc": "Valid derived claim"
        },
        {
            "claim": "The timeout depends on API version and deployment environment.",
            "expected_V1": "REJECT",
            "desc": "Adversarially plausible but unsupported claim"
        },
        {
            "claim": "The timeout depends on API version because production traffic is higher.",
            "expected_V1": "REJECT",
            "desc": "Unsupported causal extension"
        },
        {
            "claim": "Version 2 has a longer timeout.",
            "expected_V1": "SUPPORTED",
            "desc": "Comparison"
        },
        {
            "claim": "Version 2 is more reliable.",
            "expected_V1": "REJECT",
            "desc": "Semantic extrapolation"
        }
    ]
    
    modes = ["V0", "V1", "V2"]
    verifiers = {mode: PostGenerationVerifier(verifier_mode=mode) for mode in modes}
    
    results = {}
    
    for tc in test_cases:
        print(f"\n--- Claim: '{tc['claim']}' ---")
        results[tc['claim']] = {}
        for mode in modes:
            # PostGenerationVerifier.verify extracts claims internally using an LLM.
            # To test deterministic logic, we will bypass the extractor and directly inject the claim.
            # Wait, verify() takes an answer string and extracts claims.
            # We can mock the extractor to just return [tc['claim']]
            verifiers[mode].claim_extractor.extract_claims = lambda x: [x]
            
            res = verifiers[mode].verify(tc['claim'], chunks, condition_graph=condition_graph)
            
            # Use the status of the first claim for reporting
            claim_status = res["verified_claims"][0]["status"] if res.get("verified_claims") else res["state"]
            results[tc['claim']][mode] = claim_status
            
            icon = "[OK]" if (mode == "V1" and claim_status == tc["expected_V1"]) or mode != "V1" else "[FAIL]"
            if mode == "V1":
                print(f"{mode} Result: {claim_status} (Expected: {tc['expected_V1']}) {icon}")
                print(f"   Reason: {res['verified_claims'][0]['reason'] if res.get('verified_claims') else ''}")
                print(f"   Confidence: {res['verified_claims'][0]['confidence'] if res.get('verified_claims') else ''}")
            else:
                print(f"{mode} Result: {claim_status}")
                
    with open("reports/v3.1_verifier_diagnostics.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    run_verifier_test()
