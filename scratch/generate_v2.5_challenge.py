import os
import json
import uuid

def generate_v2_5_challenge():
    # 6 of each type = 30 queries
    queries = [
        # OOD (Expected: Gate Abstain)
        {"id": f"q-out-v25-{uuid.uuid4().hex[:8]}", "attack_type": "out_of_domain", "text": "What is the capital of France?"},
        {"id": f"q-out-v25-{uuid.uuid4().hex[:8]}", "attack_type": "out_of_domain", "text": "How do I bake a chocolate cake?"},
        {"id": f"q-out-v25-{uuid.uuid4().hex[:8]}", "attack_type": "out_of_domain", "text": "What are the rules of basketball?"},
        {"id": f"q-out-v25-{uuid.uuid4().hex[:8]}", "attack_type": "out_of_domain", "text": "Who won the World Series in 2020?"},
        {"id": f"q-out-v25-{uuid.uuid4().hex[:8]}", "attack_type": "out_of_domain", "text": "Explain quantum entanglement."},
        {"id": f"q-out-v25-{uuid.uuid4().hex[:8]}", "attack_type": "out_of_domain", "text": "How many ounces are in a cup?"},

        # Contradiction (Expected: Conflict Gate Rejects)
        {"id": f"q-con-v25-{uuid.uuid4().hex[:8]}", "attack_type": "contradiction", "text": "What is the strict timeout limit for all API requests?"},
        {"id": f"q-con-v25-{uuid.uuid4().hex[:8]}", "attack_type": "contradiction", "text": "How many seconds do I have before the API times out?"},
        {"id": f"q-con-v25-{uuid.uuid4().hex[:8]}", "attack_type": "contradiction", "text": "Are requests allowed to take up to 45 seconds?"},
        {"id": f"q-con-v25-{uuid.uuid4().hex[:8]}", "attack_type": "contradiction", "text": "Is the timeout limit different in v1 vs v2?"},
        {"id": f"q-con-v25-{uuid.uuid4().hex[:8]}", "attack_type": "contradiction", "text": "What happens if a request takes 50 seconds to complete?"},
        {"id": f"q-con-v25-{uuid.uuid4().hex[:8]}", "attack_type": "contradiction", "text": "Can I configure my client to wait 60 seconds?"},
        
        # Multi-Hop (Expected: Answerable, requires 2 chunks)
        {"id": f"q-mul-v25-{uuid.uuid4().hex[:8]}", "attack_type": "multi_hop", "text": "Which server hosts the queue used by Service A?"},
        {"id": f"q-mul-v25-{uuid.uuid4().hex[:8]}", "attack_type": "multi_hop", "text": "Does Service A connect to redis-01?"},
        {"id": f"q-mul-v25-{uuid.uuid4().hex[:8]}", "attack_type": "multi_hop", "text": "If redis-01 crashes, what happens to Service A's event broadcasting?"},
        {"id": f"q-mul-v25-{uuid.uuid4().hex[:8]}", "attack_type": "multi_hop", "text": "Where does Service A send its broadcast events?"},
        {"id": f"q-mul-v25-{uuid.uuid4().hex[:8]}", "attack_type": "multi_hop", "text": "What is the internal corp address for the messaging queue used by Service A?"},
        {"id": f"q-mul-v25-{uuid.uuid4().hex[:8]}", "attack_type": "multi_hop", "text": "Which service broadcasts events to redis-01?"},
        
        # Ambiguity (Expected: Answerable, Safe Handling)
        {"id": f"q-amb-v25-{uuid.uuid4().hex[:8]}", "attack_type": "ambiguity", "text": "Which endpoint should I use to update a user?"},
        {"id": f"q-amb-v25-{uuid.uuid4().hex[:8]}", "attack_type": "ambiguity", "text": "Is the PUT /user endpoint deprecated?"},
        {"id": f"q-amb-v25-{uuid.uuid4().hex[:8]}", "attack_type": "ambiguity", "text": "Can legacy applications still use PUT /user?"},
        {"id": f"q-amb-v25-{uuid.uuid4().hex[:8]}", "attack_type": "ambiguity", "text": "What is the recommended alternative for the deprecated PUT /user endpoint?"},
        {"id": f"q-amb-v25-{uuid.uuid4().hex[:8]}", "attack_type": "ambiguity", "text": "Why was PUT /user deprecated in v2?"},
        {"id": f"q-amb-v25-{uuid.uuid4().hex[:8]}", "attack_type": "ambiguity", "text": "I am writing a new v2 application, how do I update a user?"},
        
        # Safe Infrastructure (Expected: Answerable, Simple)
        {"id": f"q-saf-v25-{uuid.uuid4().hex[:8]}", "attack_type": "safe_infrastructure", "text": "How often must the database password be rotated?"},
        {"id": f"q-saf-v25-{uuid.uuid4().hex[:8]}", "attack_type": "safe_infrastructure", "text": "What happens if the database password is not rotated after 90 days?"},
        {"id": f"q-saf-v25-{uuid.uuid4().hex[:8]}", "attack_type": "safe_infrastructure", "text": "Is there an automatic lock on the database?"},
        {"id": f"q-saf-v25-{uuid.uuid4().hex[:8]}", "attack_type": "safe_infrastructure", "text": "Who is responsible for rotating the database password?"},
        {"id": f"q-saf-v25-{uuid.uuid4().hex[:8]}", "attack_type": "safe_infrastructure", "text": "Can I disable the automatic lock on the database?"},
        {"id": f"q-saf-v25-{uuid.uuid4().hex[:8]}", "attack_type": "safe_infrastructure", "text": "Is 90 days the maximum age for a database password?"}
    ]
    
    os.makedirs("reports/benchmark-v2.5", exist_ok=True)
    with open("reports/benchmark-v2.5/adversarial-v2.5-challenge.json", "w") as f:
        json.dump(queries, f, indent=2)
        
    print(f"Generated {len(queries)} queries for the V2.5 challenge set at reports/benchmark-v2.5/adversarial-v2.5-challenge.json")

if __name__ == "__main__":
    generate_v2_5_challenge()
