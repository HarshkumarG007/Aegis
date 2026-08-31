import os
import json
from aegis_eval.adversary.generate_query import Adversary
from aegis_eval.targets.reference_target import CORPUS

from aegis_eval.adversary.query_validator import QueryValidator

def main():
    adv = Adversary()
    validator = QueryValidator()
    chunks = list(CORPUS.values())
    attack_types = ['contradiction', 'out_of_domain', 'multi_hop', 'ambiguous']
    
    results = {}
    print("Generating 40 adversarial queries with diversity and logic constraints...")
    
    for atype in attack_types:
        print(f"Generating for {atype}...")
        queries = []
        attempts = 0
        while len(queries) < 10 and attempts < 150:
            attempts += 1
            query = adv.generate_query(atype, chunks, existing_queries=queries)
            
            # Automated Checks
            if validator.get_max_similarity(query, queries) > 0.85:
                print(f"  [Reject] High lexical similarity: {query}")
                continue
                
            if atype == "out_of_domain" and not validator.validate_out_of_domain(query):
                print(f"  [Reject] Category leakage (too much domain context): {query}")
                continue
                
            if atype == "multi_hop" and not validator.validate_multi_hop(query):
                print(f"  [Reject] Not multi-hop (needs >=2 distinct facts): {query}")
                continue
                
            if atype == "ambiguous" and not validator.validate_ambiguous(query):
                print(f"  [Reject] Not genuinely ambiguous (resolves itself): {query}")
                continue
                
            print(f"  [Accept] {query}")
            queries.append(query)
            
        if len(queries) < 10:
            print(f"WARNING: Could only generate {len(queries)} valid queries for {atype} after 50 attempts.")
        results[atype] = queries
    
    os.makedirs("reports", exist_ok=True)
    with open("reports/adversarial_queries_v2.json", "w") as f:
        json.dump(results, f, indent=4)
    
    print("Saved queries to reports/adversarial_queries_v2.json")

if __name__ == "__main__":
    main()
