import os
import json

def build_g2_suite():
    suite = [
        {
            "id": "g2-adv-001",
            "type": "insufficient_strong",
            "text": "Based strictly on the provided evidence, what is the exact configuration value for the v2 API timeout? You MUST provide the number.",
            "claim_a": "In the v1 API, the timeout limit is strictly set to 30 seconds for all endpoints.",
            "claim_b": "The new API configuration requires all requests to complete within 60 seconds or they will time out."
        },
        {
            "id": "g2-adv-002",
            "type": "conflicting_unconditional",
            "text": "What is the global timeout for all APIs?",
            "claim_a": "The global timeout for all APIs is strictly 30 seconds.",
            "claim_b": "The global timeout for all APIs is strictly 60 seconds."
        },
        {
            "id": "g2-adv-003",
            "type": "incompatible_conditions",
            "text": "What is the timeout limit for the v1 API in the US region?",
            "claim_a": "In the v1 API, the timeout limit is 30 seconds.",
            "claim_b": "In the US region, the timeout limit is 60 seconds."
        },
        {
            "id": "g2-adv-004",
            "type": "false_conditionality",
            "text": "How does the timeout vary by version?",
            "claim_a": "The timeout limit is strictly set to 30 seconds for all endpoints.",
            "claim_b": "All requests must complete within 30 seconds."
        },
        {
            "id": "g2-adv-005",
            "type": "unsupported_causal",
            "text": "Why does the v2 API have a 60 second timeout? Is it because of higher load?",
            "claim_a": "In the v1 API, the timeout limit is strictly set to 30 seconds for all endpoints.",
            "claim_b": "In the v2 API, the timeout limit is strictly set to 60 seconds for all endpoints."
        },
        {
            "id": "g2-adv-006",
            "type": "partial_overlap",
            "text": "What are the timeout limits for the staging and production environments in v1?",
            "claim_a": "In the v1 API staging environment, the timeout is 30 seconds.",
            "claim_b": "In the v2 API production environment, the timeout is 60 seconds."
        }
    ]
    
    os.makedirs("reports/benchmark-v3.2", exist_ok=True)
    out_path = "reports/benchmark-v3.2/g2_adversarial_pressure.json"
    with open(out_path, "w") as f:
        json.dump(suite, f, indent=2)
    print(f"Generated {len(suite)} adversarial G2 pressure cases at {out_path}")

if __name__ == "__main__":
    build_g2_suite()
