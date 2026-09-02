import json
import os
import math

def check_abstention(answer):
    lower_ans = answer.lower()
    abstain_phrases = ["i don't know", "i cannot answer", "i abstain", "insufficient evidence"]
    for phrase in abstain_phrases:
        if phrase in lower_ans:
            return True
    if len(answer.strip()) < 10:
        return True
    return False

def analyze():
    arms = ["A", "B", "C", "D"]
    metrics = {}
    
    for arm in arms:
        path = f"reports/v3.0/traces_arm_{arm}.json"
        if not os.path.exists(path):
            print(f"Waiting for {path}...")
            return
            
        with open(path, "r") as f:
            traces = json.load(f)
            
        ans_total = 0
        ans_answered = 0
        
        contra_total = 0
        contra_answered = 0
        
        ood_total = 0
        ood_answered = 0
        
        for t in traces:
            qtype = t.get("query_type", "")
            is_abs = check_abstention(t["answer"])
            
            if "out" in qtype:
                ood_total += 1
                if not is_abs: ood_answered += 1
            elif "con" in qtype:
                contra_total += 1
                if not is_abs: contra_answered += 1
            else:
                ans_total += 1
                if not is_abs: ans_answered += 1
                
        metrics[arm] = {
            "ans_pct": ans_answered / ans_total * 100 if ans_total else 0,
            "ans_answered": ans_answered,
            "ans_total": ans_total,
            "contra_pct": contra_answered / contra_total * 100 if contra_total else 0,
            "contra_answered": contra_answered,
            "contra_total": contra_total,
            "ood_pct": ood_answered / ood_total * 100 if ood_total else 0,
            "ood_answered": ood_answered,
            "ood_total": ood_total
        }
        
    print("=== V3.0-C Factorial Results ===")
    print(f"A (Curr Retr 5.25 + Curr Gen G0): Ans {metrics['A']['ans_answered']}/{metrics['A']['ans_total']} | Contra {metrics['A']['contra_answered']}/{metrics['A']['contra_total']} | OOD {metrics['A']['ood_answered']}/{metrics['A']['ood_total']}")
    print(f"B (Curr Retr 5.25 + Impr Gen G1): Ans {metrics['B']['ans_answered']}/{metrics['B']['ans_total']} | Contra {metrics['B']['contra_answered']}/{metrics['B']['contra_total']} | OOD {metrics['B']['ood_answered']}/{metrics['B']['ood_total']}")
    print(f"C (Optm Retr 4.25 + Curr Gen G0): Ans {metrics['C']['ans_answered']}/{metrics['C']['ans_total']} | Contra {metrics['C']['contra_answered']}/{metrics['C']['contra_total']} | OOD {metrics['C']['ood_answered']}/{metrics['C']['ood_total']}")
    print(f"D (Optm Retr 4.25 + Impr Gen G1): Ans {metrics['D']['ans_answered']}/{metrics['D']['ans_total']} | Contra {metrics['D']['contra_answered']}/{metrics['D']['contra_total']} | OOD {metrics['D']['ood_answered']}/{metrics['D']['ood_total']}")
    
    A_ans = metrics['A']['ans_pct']
    B_ans = metrics['B']['ans_pct']
    C_ans = metrics['C']['ans_pct']
    D_ans = metrics['D']['ans_pct']
    
    retr_effect = C_ans - A_ans
    gen_effect = B_ans - A_ans
    interaction = (D_ans - C_ans) - (B_ans - A_ans)
    
    print("\n--- Difference-in-Differences ---")
    print(f"Main Effect (Optimized Retrieval): +{retr_effect:.1f}%")
    print(f"Main Effect (Improved Generator) : +{gen_effect:.1f}%")
    print(f"Interaction ((D-C)-(B-A))        : {interaction:+.1f}%")

if __name__ == "__main__":
    analyze()
