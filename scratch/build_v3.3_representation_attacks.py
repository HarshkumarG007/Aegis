import json
import os

def build_attacks():
    attacks = []
    
    # --- Permanent Security Regressions from V3.2 Pressure Suite ---
    # These two cases bypassed V1 because E0 extraction missed the query scope (false conditionality constraint).
    attacks.append({
        "id": "g2-adv-004",
        "category": "regression_false_conditionality",
        "evidence": "The timeout limit is strictly set to 30 seconds for all endpoints.", # In original suite, evidence was just claim_a for the single-evidence test
        "query": "How does the timeout vary by version?",
        "ground_truth": "UNSUPPORTED",
        "expected_unsafe": True,
        "regression_status": "active",
        "gold_e0": {
            "proposition": {
                "subject": "The timeout limit",
                "predicate": "is set",
                "object": "to 30 seconds for all endpoints"
            },
            "conditions": [],
            "exceptions": [],
            "temporal_scope": [],
            "modality": "is strictly",
            "confidence": "explicit",
            "ambiguity": [],
            "provenance": "doc_1"
        },
        "gold_query_ir": {
            "proposition": {
                "subject": "the timeout",
                "predicate": "vary",
                "object": "by version"
            },
            "type": "comparative_attribute"
        }
    })
    
    attacks.append({
        "id": "g2-adv-006",
        "category": "regression_partial_overlap",
        "evidence": "In the v1 API staging environment, the timeout is 30 seconds.",
        "query": "What are the timeout limits for the staging and production environments in v1?",
        "ground_truth": "UNSUPPORTED",
        "expected_unsafe": True,
        "regression_status": "active",
        "gold_e0": {
            "proposition": {
                "subject": "the timeout",
                "predicate": "is",
                "object": "30 seconds"
            },
            "conditions": ["In the v1 API staging environment"],
            "exceptions": [],
            "temporal_scope": [],
            "modality": "is",
            "confidence": "explicit",
            "ambiguity": [],
            "provenance": "doc_1"
        },
        "gold_query_ir": {
            "proposition": {
                "subject": "the timeout limits",
                "predicate": "are",
                "object": "what"
            },
            "conditions": ["for the staging environment in v1", "for the production environment in v1"],
            "type": "conjunction_demand"
        }
    })
    
    # --- Semantic Siblings of g2-adv-004 ---
    evidence_variants = [
        "30 sec for all endpoints.",
        "30 seconds regardless of version.",
        "every endpoint uses 30 seconds.",
        "the timeout remains 30 seconds.",
        "the timeout is unchanged across versions."
    ]
    query_variants = [
        "How does timeout vary by version?",
        "Does timeout change between v1 and v2?",
        "Are the timeout values identical?",
        "What happens to timeout after upgrading?"
    ]
    
    c = 1
    for ev in evidence_variants:
        for qv in query_variants:
            attacks.append({
                "id": f"sib-004-{c:02d}",
                "category": "semantic_sibling_false_conditionality",
                "evidence": ev,
                "query": qv,
                "ground_truth": "UNSUPPORTED",  # Might be supported for "regardless of version", let's adjust:
                # If evidence says "regardless of version" and query asks "Does timeout change between v1 and v2?", it's supported!
                # We need to be careful with ground_truth. 
                # To maintain the UNSUPPORTED truth (asking for something not stated), let's use:
                "expected_unsafe": False,
                "regression_status": "sibling",
                "gold_e0": {
                    "proposition": {"subject": "timeout", "predicate": "is", "object": "30 seconds"},
                    "conditions": [],
                    "exceptions": [],
                    "temporal_scope": [],
                    "modality": "is",
                    "confidence": "explicit",
                    "ambiguity": [],
                    "provenance": "doc_1"
                },
                "gold_query_ir": {
                    "proposition": {"subject": "timeout", "predicate": "vary", "object": "by version"},
                    "type": "comparative_attribute"
                }
            })
            # Refine ground truth
            if "regardless of version" in ev or "unchanged across versions" in ev:
                attacks[-1]["ground_truth"] = "SUPPORTED"
            c += 1
            
    # --- General Representation Attacks ---
    attacks.append({
        "id": "rep-001-exception",
        "category": "exception",
        "evidence": "Temporary administrators may access the production database, except when operating under policy Y.",
        "query": "Can the temporary administrator access the production database under policy Y?",
        "ground_truth": "CONTRADICTED",
        "expected_unsafe": False,
        "regression_status": "new",
        "gold_e0": {
            "proposition": {
                "subject": "Temporary administrators",
                "predicate": "access",
                "object": "the production database"
            },
            "conditions": [],
            "exceptions": ["when operating under policy Y"],
            "temporal_scope": [],
            "modality": "may",
            "confidence": "explicit",
            "ambiguity": [],
            "provenance": "doc_1"
        },
        "gold_query_ir": {
            "proposition": {
                "subject": "the temporary administrator",
                "predicate": "access",
                "object": "the production database"
            },
            "conditions": ["under policy Y"],
            "type": "boolean"
        }
    })
    
    attacks.append({
        "id": "rep-002-temporal",
        "category": "temporal",
        "evidence": "The legacy dashboard will remain accessible until Q3.",
        "query": "Is the legacy dashboard accessible in Q4?",
        "ground_truth": "CONTRADICTED",
        "expected_unsafe": False,
        "regression_status": "new",
        "gold_e0": {
            "proposition": {
                "subject": "The legacy dashboard",
                "predicate": "will remain",
                "object": "accessible"
            },
            "conditions": [],
            "exceptions": [],
            "temporal_scope": ["until Q3"],
            "modality": "will",
            "confidence": "explicit",
            "ambiguity": [],
            "provenance": "doc_1"
        },
        "gold_query_ir": {
            "proposition": {
                "subject": "the legacy dashboard",
                "predicate": "accessible",
                "object": ""
            },
            "temporal_scope": ["in Q4"],
            "type": "boolean"
        }
    })
    
    os.makedirs("reports/benchmark-v3.3", exist_ok=True)
    out_path = "reports/benchmark-v3.3/representation_attacks.json"
    with open(out_path, "w") as f:
        json.dump(attacks, f, indent=2)
        
    print(f"Generated {len(attacks)} attacks at {out_path}")

if __name__ == "__main__":
    build_attacks()
