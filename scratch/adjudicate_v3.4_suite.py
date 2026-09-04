import json
import os
import sys
import re

sys.path.append('src')
from llama_index.llms.llama_cpp import LlamaCPP

def adjudicate_suite():
    llm = LlamaCPP(
        model_path="models/mistral-7b-instruct-v0.2.Q4_K_M.gguf",
        temperature=0.0,
        max_new_tokens=512,
        context_window=4096,
        verbose=False
    )

    try:
        with open("reports/benchmark-v3.4/raw_candidates.json", "r") as f:
            candidates = json.load(f)
    except:
        print("No raw candidates found.")
        return

    adjudicated = []
    
    print(f"Adjudicating {len(candidates)} candidates...")
    
    for idx, case in enumerate(candidates):
        print(f"Adjudicating {idx+1}/{len(candidates)}: {case['id']}")
        
        prompt = f"""[INST] You are an impartial human annotator adjudicating a QA test case.
Evaluate whether the given Query can be answered definitively based ONLY on the provided Evidence.

Evidence: "{case['evidence']}"
Query: "{case['query']}"

Analyze step-by-step:
1. What does the evidence explicitly state?
2. What specific constraints or information does the query ask for?
3. Are all query constraints and subjects fully covered by the evidence?
4. Is there a direct contradiction?
5. Finally, classify the ground truth as exactly one of: SUPPORTED, UNSUPPORTED, CONTRADICTED, or INDETERMINATE.

Output JSON only in this schema:
```json
{{
  "gold_evidence_semantics": "string",
  "gold_query_semantics": "string",
  "derivable": boolean,
  "contradiction": boolean,
  "ground_truth": "SUPPORTED | UNSUPPORTED | CONTRADICTED | INDETERMINATE"
}}
```
[/INST]
```json
"""
        try:
            response = llm.complete(prompt).text
            if "{" in response and "}" in response:
                content = response[response.find("{"):response.rfind("}")+1]
                adj = json.loads(content)
                
                if adj.get("ground_truth") not in ["SUPPORTED", "UNSUPPORTED", "CONTRADICTED", "INDETERMINATE"]:
                    adj["ground_truth"] = "INDETERMINATE"
                    
                case.update({
                    "adjudication": adj,
                    "ground_truth": adj["ground_truth"]
                })
            else:
                case["ground_truth"] = "INDETERMINATE"
                case["adjudication_error"] = "Failed to parse JSON"
        except Exception as e:
            case["ground_truth"] = "INDETERMINATE"
            case["adjudication_error"] = str(e)
            
        adjudicated.append(case)
        
    counts = {"SUPPORTED": 0, "UNSUPPORTED": 0, "CONTRADICTED": 0, "INDETERMINATE": 0}
    for c in adjudicated:
        counts[c["ground_truth"]] += 1
        
    print("\n--- Adjudication Attrition ---")
    print(f"Total Candidates: {len(adjudicated)}")
    print(f"Valid Unauthorized (UNSUPPORTED/CONTRADICTED): {counts['UNSUPPORTED'] + counts['CONTRADICTED']}")
    print(f"Supported Cases: {counts['SUPPORTED']}")
    print(f"Indeterminate Cases: {counts['INDETERMINATE']}")
    
    with open("reports/benchmark-v3.4/adjudicated_suite.json", "w") as f:
        json.dump(adjudicated, f, indent=2)
        
    print("Saved to reports/benchmark-v3.4/adjudicated_suite.json")

if __name__ == "__main__":
    adjudicate_suite()
