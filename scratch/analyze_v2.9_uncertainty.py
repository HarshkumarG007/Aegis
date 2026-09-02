import json
from collections import defaultdict
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))
from aegis_eval.hardened_rag.gates import EvidenceGate

# Initialize gates
gate_C = EvidenceGate(conflict_classifier="C", extractor_mode="E0")
gate_E = EvidenceGate(conflict_classifier="E", extractor_mode="E0")

with open(r"c:\Users\Lenovo\Downloads\Aegis\reports\benchmark-v2.9\adversarial_conditions.json", "r") as f:
    data = json.load(f)

# Track transitions from UNCERTAIN in C to resolved in E
resolved_categories = defaultdict(int)

# Track recovered compatible cases in E
recovered_compatible_categories = defaultdict(int)

for item in data:
    claim_a = item["claim_a"]
    claim_b = item["claim_b"]
    category = item["category"]
    true_label = item["label"]
    
    # Mock chunks
    chunks = [
        {"chunk_id": "A", "text": claim_a},
        {"chunk_id": "B", "text": claim_b}
    ]
    
    # Evaluate with C
    res_c = gate_C.evaluate("query", chunks, -100.0)
    state_c = res_c["state"]
    
    # Evaluate with E
    res_e = gate_E.evaluate("query", chunks, -100.0)
    state_e = res_e["state"]
    
    if state_c == "CONFLICT_UNCERTAIN" and state_e != "CONFLICT_UNCERTAIN":
        resolved_categories[category] += 1
        
    if true_label == "CONDITIONAL_COMPATIBILITY" and state_e == "CONDITIONAL_COMPATIBILITY":
        recovered_compatible_categories[category] += 1

print("--- Resolved Uncertain Fallbacks by Category ---")
for cat, count in resolved_categories.items():
    print(f"{cat}: {count}")

print("\n--- Recovered Compatible Cases by Category ---")
for cat, count in recovered_compatible_categories.items():
    print(f"{cat}: {count}")
