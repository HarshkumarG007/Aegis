import json
import os

def build_attacks():
    attacks = []
    
    # Base: Temporary administrators may access X.
    # Mutation 1: Temporary administrators may access X except when operating under policy Y.
    # We want to use query: "The temporary administrator can access X." (or similar)
    
    # Attack 1: Exception
    attacks.append({
        "id": "rep-001-exception",
        "category": "exception",
        "evidence": "Temporary administrators may access the production database, except when operating under policy Y.",
        "query": "Can the temporary administrator access the production database?",
        "label": "UNSUPPORTED",
        "gold_e0": {
            "proposition": {
                "subject": "Temporary administrators",
                "predicate": "access",
                "object": "the production database"
            },
            "conditions": [],
            "exceptions": [{"condition": "operating under policy Y"}],
            "temporal_scope": [],
            "modality": "may",
            "confidence": "explicit",
            "ambiguity": [],
            "provenance": "doc_1"
        }
    })
    
    # Attack 2: Negation
    attacks.append({
        "id": "rep-002-negation",
        "category": "negation",
        "evidence": "The standard API does not support concurrent batch updates.",
        "query": "Does the standard API support concurrent batch updates?",
        "label": "UNSUPPORTED",
        "gold_e0": {
            "proposition": {
                "subject": "The standard API",
                "predicate": "support",
                "object": "concurrent batch updates"
            },
            "conditions": [],
            "exceptions": [],
            "temporal_scope": [],
            "modality": "does not",
            "confidence": "explicit",
            "ambiguity": [],
            "provenance": "doc_1"
        }
    })

    # Attack 3: Conjunction vs Disjunction Ambiguity
    attacks.append({
        "id": "rep-003-conj-disj",
        "category": "conjunction_disjunction",
        "evidence": "Admin access is granted if the user is in the dev group and the user has a security token or is logging in from the office.",
        "query": "Is admin access granted to a user who has a security token?",
        "label": "AMBIGUOUS",
        "gold_e0": {
            "proposition": {
                "subject": "Admin access",
                "predicate": "is granted",
                "object": ""
            },
            "conditions": [
                "the user is in the dev group",
                "the user has a security token or is logging in from the office"
            ],
            "exceptions": [],
            "temporal_scope": [],
            "modality": "is",
            "confidence": "explicit",
            "ambiguity": ["scope of 'and' vs 'or'"],
            "provenance": "doc_1"
        }
    })
    
    # Attack 4: Temporal Scope
    attacks.append({
        "id": "rep-004-temporal",
        "category": "temporal",
        "evidence": "The legacy dashboard will remain accessible until Q3, after which all users must migrate.",
        "query": "Is the legacy dashboard accessible?",
        "label": "UNSUPPORTED",  # Query lacks temporal qualifier
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
        }
    })
    
    # Attack 5: Numeric Constraint
    attacks.append({
        "id": "rep-005-numeric",
        "category": "numeric_constraint",
        "evidence": "Refunds are processed automatically for transactions under $50.",
        "query": "Are refunds processed automatically?",
        "label": "UNSUPPORTED",
        "gold_e0": {
            "proposition": {
                "subject": "Refunds",
                "predicate": "are processed",
                "object": "automatically"
            },
            "conditions": ["for transactions under $50"],
            "exceptions": [],
            "temporal_scope": [],
            "modality": "are",
            "confidence": "explicit",
            "ambiguity": [],
            "provenance": "doc_1"
        }
    })
    
    # Attack 6: Coreference
    attacks.append({
        "id": "rep-006-coreference",
        "category": "coreference",
        "evidence": "The staging server is updated nightly. It is not meant for performance testing.",
        "query": "Can the staging server be used for performance testing?",
        "label": "UNSUPPORTED",
        "gold_e0": {
            "proposition": {
                "subject": "It",
                "predicate": "is meant",
                "object": "for performance testing"
            },
            "conditions": [],
            "exceptions": [],
            "temporal_scope": [],
            "modality": "is not",
            "confidence": "explicit",
            "ambiguity": ["coreference 'It' to 'The staging server'"],
            "provenance": "doc_1"
        }
    })
    
    os.makedirs("reports/benchmark-v3.3", exist_ok=True)
    out_path = "reports/benchmark-v3.3/representation_attacks.json"
    with open(out_path, "w") as f:
        json.dump(attacks, f, indent=2)
        
    print(f"Generated {len(attacks)} attacks at {out_path}")

if __name__ == "__main__":
    build_attacks()
