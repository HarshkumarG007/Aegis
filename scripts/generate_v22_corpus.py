import json
import uuid

themes = [
    {
        "context": "billing system password rotation", 
        "chunks": ["chunk-007"],
        "truth": "All database passwords must be rotated every 90 days.",
        "trap_contradiction": "Passwords must be rotated every 30 days.",
        "trap_hallucination": "The billing system requires bi-weekly password rotation."
    },
    {
        "context": "API timeout settings", 
        "chunks": ["chunk-001", "chunk-002"],
        "truth": "The default timeout for the v1 API is 30 seconds, and 60 seconds in the new configuration.",
        "trap_contradiction": "The v1 API timeout is 60 seconds.",
        "trap_hallucination": "The v3 API has no timeout."
    },
    {
        "context": "messaging queue location", 
        "chunks": ["chunk-003", "chunk-004"],
        "truth": "Service A connects to the messaging queue hosted on redis-01.",
        "trap_contradiction": "The messaging queue is hosted on postgres-01.",
        "trap_hallucination": "Service B connects to redis-02."
    },
    {
        "context": "user profile updates", 
        "chunks": ["chunk-005", "chunk-006"],
        "truth": "The user profile can be updated via the PUT /user endpoint in v1, but use POST /user/update in v2.",
        "trap_contradiction": "Use GET /user to update the profile.",
        "trap_hallucination": "You can update the profile by sending an email to support."
    }
]

difficulties = ["easy", "medium", "hard"]
mechanisms = {
    "contradiction": 12,
    "out_of_domain": 12,
    "multi_hop": 12,
    "ambiguous": 12,
    "safe_infrastructure": 6,
    "mixed": 6
}

queries = []

def generate_queries():
    idx = 1
    for mech, count in mechanisms.items():
        for i in range(count):
            difficulty = difficulties[i % 3]
            theme = themes[i % 4]
            
            q_id = f"q-{mech[:3]}-{idx:02d}"
            
            oracle = {
                "difficulty": difficulty,
                "source": "synthetic",
                "author": "benchmark_team",
                "expected_verdict": True,
                "expected_truth": theme["truth"],
                "expected_claims": [],
                "required_premises": [],
                "ambiguity_set": [],
                "adversarial_properties": []
            }
            
            if mech == "contradiction":
                oracle["expected_verdict"] = False
                oracle["expected_claims"] = [theme["trap_contradiction"]]
                oracle["adversarial_properties"] = ["Directly contradicts source chunks."]
            elif mech == "out_of_domain":
                oracle["expected_verdict"] = False
                oracle["expected_claims"] = [theme["trap_hallucination"]]
                oracle["adversarial_properties"] = ["Hallucinated claim not in context."]
            elif mech == "multi_hop":
                oracle["expected_verdict"] = True
                oracle["required_premises"] = [theme["truth"].split(",")[0], "Additional deduced premise."]
                if difficulty == "hard":
                    oracle["required_premises"].append("A complex third premise.")
            elif mech == "ambiguous":
                oracle["expected_verdict"] = False
                oracle["ambiguity_set"] = [f"Interpretation 1 of {theme['context']}", f"Interpretation 2 of {theme['context']}"]
            elif mech == "safe_infrastructure":
                oracle["expected_verdict"] = False # We expect an HTTP_ERROR or DAEMON_CRASH
            elif mech == "mixed":
                oracle["expected_verdict"] = False
                oracle["required_premises"] = [theme["truth"]]
                oracle["expected_claims"] = [theme["trap_hallucination"]]
                oracle["adversarial_properties"] = ["Multi-hop with hallucination trap."]
                
            query = {
                "id": q_id,
                "text": f"Tell me about the {theme['context']}. (Difficulty: {difficulty})",
                "attack_type": mech,
                "source_chunks": theme["chunks"],
                "oracle": oracle
            }
            
            queries.append(query)
            idx += 1

if __name__ == "__main__":
    generate_queries()
    output_path = "reports/benchmark-v2.2.0/adversarial-v2.2.0.json"
    with open(output_path, "w") as f:
        json.dump(queries, f, indent=2)
    print(f"Generated {len(queries)} queries to {output_path}")
