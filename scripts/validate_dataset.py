import json
import sys

def validate_dataset(filepath):
    try:
        with open(filepath, "r") as f:
            queries = json.load(f)
    except Exception as e:
        print(f"FAIL: Could not read {filepath}: {e}")
        return False
        
    if len(queries) != 60:
        print(f"FAIL: Expected 60 queries, found {len(queries)}")
        return False

    ids = set()
    mechanisms = {"contradiction": 0, "out_of_domain": 0, "multi_hop": 0, "ambiguous": 0, "safe_infrastructure": 0, "mixed": 0}
    
    for q in queries:
        if "id" not in q:
            print("FAIL: Query missing 'id'")
            return False
            
        q_id = q["id"]
        if q_id in ids:
            print(f"FAIL: Duplicate ID {q_id}")
            return False
        ids.add(q_id)
        
        mech = q.get("attack_type")
        if mech not in mechanisms:
            print(f"FAIL: Unknown mechanism {mech} in {q_id}")
            return False
        mechanisms[mech] += 1
        
        oracle = q.get("oracle")
        if not oracle:
            print(f"FAIL: Missing oracle metadata in {q_id}")
            return False
            
        if "expected_verdict" not in oracle:
            print(f"FAIL: Missing expected_verdict in {q_id}")
            return False

        if mech == "multi_hop" and not oracle.get("required_premises"):
            print(f"FAIL: Missing required_premises for multi_hop {q_id}")
            return False
            
        if mech == "ambiguous" and not oracle.get("ambiguity_set"):
            print(f"FAIL: Missing ambiguity_set for ambiguous {q_id}")
            return False

    print("Dataset validation passed!")
    print(f"Mechanism counts: {mechanisms}")
    return True

if __name__ == "__main__":
    if validate_dataset("reports/benchmark-v2.2.0/adversarial-v2.2.0.json"):
        sys.exit(0)
    else:
        sys.exit(1)
