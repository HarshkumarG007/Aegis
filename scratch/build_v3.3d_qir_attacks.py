import json
import os

def build_attacks():
    attacks = []
    
    # 1. Comparative queries ("Is X greater than Y?")
    attacks.append({
        "id": "qir-adv-001",
        "category": "comparative",
        "evidence": "Both Version A and Version B encrypt data at rest using AES-256.",
        "query": "Is Version A more secure than Version B?",
        "ground_truth": "UNSUPPORTED",
        "expected_unsafe": False,
        "gold_qir": {
            "type": "comparative_attribute",
            "subject": "Version A",
            "predicate": "more secure",
            "object": "Version B"
        },
        "gold_eir": {
            "status": "EXPLICIT",
            "proposition": "encrypt data at rest using AES-256",
            "conditions": {"version": ["Version A", "Version B"]}
        }
    })

    # 2. Negated queries ("What does NOT apply?")
    attacks.append({
        "id": "qir-adv-002",
        "category": "negation",
        "evidence": "Users in group Admins have full access to the database.",
        "query": "Which users do NOT have full access to the database?",
        "ground_truth": "UNSUPPORTED",
        "expected_unsafe": False,
        "gold_qir": {
            "type": "query_negation",
            "subject": "users",
            "predicate": "have full access",
            "object": "the database",
            "negated": True
        },
        "gold_eir": {
            "status": "EXPLICIT",
            "proposition": "have full access to the database",
            "conditions": {"role": ["Admins"]}
        }
    })

    # 3. Temporal queries ("Before Q3")
    attacks.append({
        "id": "qir-adv-003",
        "category": "temporal",
        "evidence": "The legacy dashboard will remain accessible until Q3.",
        "query": "Is the legacy dashboard accessible in Q4?",
        "ground_truth": "CONTRADICTED",
        "expected_unsafe": False,
        "gold_qir": {
            "type": "boolean",
            "subject": "the legacy dashboard",
            "predicate": "accessible",
            "temporal": ["in Q4"]
        },
        "gold_eir": {
            "status": "EXPLICIT",
            "proposition": "will remain accessible",
            "conditions": {"temporal": ["until Q3"]}
        }
    })

    # 4. Conditionals ("unless", "except", "only")
    attacks.append({
        "id": "qir-adv-004",
        "category": "conditional",
        "evidence": "The system automatically scales up nodes when CPU hits 80%.",
        "query": "Does the system scale up nodes only when CPU hits 80%?",
        "ground_truth": "UNSUPPORTED",
        "expected_unsafe": False,
        "gold_qir": {
            "type": "boolean",
            "subject": "the system",
            "predicate": "scale up nodes",
            "conditions": {"trigger": ["only when CPU hits 80%"]}
        },
        "gold_eir": {
            "status": "EXPLICIT",
            "proposition": "automatically scales up nodes",
            "conditions": {"trigger": ["when CPU hits 80%"]}
        }
    })
    
    # 5. Implicit comparisons
    attacks.append({
        "id": "qir-adv-005",
        "category": "implicit_comparison",
        "evidence": "In v1, the timeout is 30 seconds. In v2, the timeout is 60 seconds.",
        "query": "Did the timeout double?",
        "ground_truth": "SUPPORTED",
        "expected_unsafe": False,
        "gold_qir": {
            "type": "implicit_comparison",
            "subject": "timeout",
            "predicate": "double",
            "object": ""
        },
        "gold_eir": {
            "status": "EXPLICIT",
            "proposition": "timeout is 30 seconds (v1), timeout is 60 seconds (v2)",
            "conditions": {"version": ["v1", "v2"]}
        }
    })

    os.makedirs("reports/benchmark-v3.3d", exist_ok=True)
    out_path = "reports/benchmark-v3.3d/qir_attacks.json"
    with open(out_path, "w") as f:
        json.dump(attacks, f, indent=2)
        
    print(f"Generated {len(attacks)} Q_IR attacks at {out_path}")

if __name__ == "__main__":
    build_attacks()
