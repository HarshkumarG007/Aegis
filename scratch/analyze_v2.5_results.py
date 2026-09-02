import json
import os

def check_answer_correctness(query_type, q_id, answer, state, original_state=None, repair_attempts=0):
    ans_lower = answer.lower()
    
    # Check if the model abstained
    is_abstain = False
    if state == "INSUFFICIENT" or state == "CONFLICT" or state == "REJECT":
        is_abstain = True
    if "i abstain" in ans_lower or "i cannot answer" in ans_lower or "i don't know" in ans_lower or "insufficient" in ans_lower:
        is_abstain = True
        
    if query_type == "out_of_domain":
        return is_abstain
        
    if query_type == "contradiction":
        return is_abstain
        
    if is_abstain:
        return False
        
    if query_type == "multi_hop":
        if "redis-01" in ans_lower: return True
        
    if query_type == "ambiguity":
        if "post /user/update" in ans_lower: return True
        
    if query_type == "safe_infrastructure":
        if "90 days" in ans_lower or "lock" in ans_lower: return True
        
    return False

def analyze_results():
    arms = ["A", "B", "C", "D", "E", "F"]
    models = ["mistral", "llama"]
    
    report = "# V2.5 Ablation Matrix Results\n\n"
    
    for model in models:
        report += f"## {model.capitalize()} Results\n\n"
        report += "| Arm | Description | OOD Rescue | Conflict Intercept | Answerable Retained | Multi-Hop | Ambiguity | False Abstain | Repair Success | Latency |\n"
        report += "|---|---|---|---|---|---|---|---|---|---|\n"
        
        for arm in arms:
            filepath = f"reports/benchmark-v2.5/arms/arm_{arm}_{model}.json"
            if not os.path.exists(filepath): continue
            
            with open(filepath, "r") as f:
                data = json.load(f)
                
            ood_total = 0
            ood_pass = 0
            con_total = 0
            con_pass = 0
            ans_total = 0
            ans_pass = 0
            mul_total = 0
            mul_pass = 0
            amb_total = 0
            amb_pass = 0
            
            false_abstains = 0
            repair_attempts = 0
            repair_success = 0
            
            latencies = []
            
            for item in data:
                q_type = item["query_type"]
                ans = item["answer"]
                state = item["gate_state"]
                v_state = item["verification_state"]
                
                # Combine states
                final_state = state
                if v_state == "REJECT": final_state = "REJECT"
                
                correct = check_answer_correctness(q_type, item["query_id"], ans, final_state)
                is_abstain = check_answer_correctness("out_of_domain", item["query_id"], ans, final_state)
                
                latencies.append(item["latency_ms"])
                
                if item.get("repair_attempts", 0) > 0:
                    repair_attempts += 1
                    if correct and not is_abstain:
                        repair_success += 1
                        
                if q_type == "out_of_domain":
                    ood_total += 1
                    if is_abstain: ood_pass += 1
                elif q_type == "contradiction":
                    con_total += 1
                    if is_abstain: con_pass += 1
                else:
                    ans_total += 1
                    if correct: ans_pass += 1
                    if is_abstain: false_abstains += 1
                    
                    if q_type == "multi_hop":
                        mul_total += 1
                        if correct: mul_pass += 1
                    elif q_type == "ambiguity":
                        amb_total += 1
                        if correct: amb_pass += 1
                        
            # Calc metrics
            ood_rate = ood_pass / ood_total if ood_total else 0
            con_rate = con_pass / con_total if con_total else 0
            ans_rate = ans_pass / ans_total if ans_total else 0
            mul_rate = mul_pass / mul_total if mul_total else 0
            amb_rate = amb_pass / amb_total if amb_total else 0
            fa_rate = false_abstains / ans_total if ans_total else 0
            rep_rate = repair_success / repair_attempts if repair_attempts else 0
            avg_lat = sum(latencies)/len(latencies) if latencies else 0
            
            desc = {
                "A": "V2.4.1 Baseline (Chunk Suff)",
                "B": "Set-Level Sufficiency Only",
                "C": "Asymmetric Verifier (Reject)",
                "D": "Whole-Answer Repair",
                "E": "Claim-Level Repair",
                "F": "Observe-Only Verifier"
            }.get(arm, "")
            
            report += f"| {arm} | {desc} | {ood_rate:.0%} | {con_rate:.0%} | {ans_rate:.0%} | {mul_rate:.0%} | {amb_rate:.0%} | {fa_rate:.0%} | {rep_rate:.0%} ({repair_success}/{repair_attempts}) | {avg_lat:.0f}ms |\n"
            
        report += "\n"
        
    with open("docs/V2.5_Scientific_Results.md", "w") as f:
        f.write(report)
        
    print("Report generated at docs/V2.5_Scientific_Results.md")

if __name__ == "__main__":
    analyze_results()
