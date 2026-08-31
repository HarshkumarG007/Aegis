import os
import json
import uuid
import argparse
import requests
from aegis_eval.evaluator.aggregator import VerdictAggregator
from aegis_eval.targets.reference_target import ReferenceTarget

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=str, default="reference", help="Target URL or 'reference'")
    parser.add_argument("--report", type=str, default="reports/reference_validation.json", help="Report output path")
    args = parser.parse_args()

    os.environ["DATABASE_URL"] = "postgresql://postgres:123456@localhost:5433/postgres"
    
    with open("reports/adversarial_queries_v2.json", "r") as f:
        query_data = json.load(f)
        
    aggregator = VerdictAggregator()
    
    if args.target == "reference":
        target = ReferenceTarget()
    else:
        target = None
        
    ref_target = ReferenceTarget() # Always instantiated for corpus access
    
    run_id = str(uuid.uuid4())
    print(f"Starting Evaluation Run: {run_id}")
    
    queries_flat = []
    for attack_type, queries in query_data.items():
        for text in queries:
            queries_flat.append({
                "id": str(uuid.uuid4()),
                "text": text,
                "attack_type": attack_type,
                "source_chunks": []
            })
            
    print(f"Loaded {len(queries_flat)} queries. Running evaluation...")
    
    stats = {"contradiction": {"pass": 0, "fail": 0}, "out_of_domain": {"pass": 0, "fail": 0}, 
             "multi_hop": {"pass": 0, "fail": 0}, "ambiguous": {"pass": 0, "fail": 0}}
             
    for i, q in enumerate(queries_flat):
        print(f"[{i+1}/{len(queries_flat)}] Evaluating {q['attack_type']}...")
        
        status = "SUCCESS"
        error_msg = None
        
        if args.target == "reference":
            target_res = target.query(q["text"], q["attack_type"])
            ans = target_res.get("answer_text", "")
            chunk_ids = target_res.get("retrieved_chunk_ids", [])
            chunk_contents = [target.corpus[cid] for cid in chunk_ids if cid in target.corpus]
        else:
            try:
                res = requests.post(args.target, json={"query": q["text"]})
                res.raise_for_status()
                target_res = res.json()
                status = target_res.get("status", "SUCCESS")
                ans = target_res.get("answer", "")
                chunk_ids = target_res.get("retrieved_chunk_ids", [])
                error_msg = target_res.get("error")
                chunk_contents = [ref_target.corpus[cid] for cid in chunk_ids if cid in ref_target.corpus]
            except Exception as e:
                status = "DAEMON_CRASH"
                error_msg = str(e)
                ans = ""
                chunk_contents = []
        
        resp = {
            "id": q["id"],
            "answer_text": ans,
            "retrieved_chunks": chunk_contents,
            "status": status,
            "error": error_msg
        }
        
        aggregator.aggregate_and_store(run_id, q, resp)
        
        if status != "SUCCESS":
            print(f"   [{status}] Bypassing evaluation. Error: {error_msg}")
            continue
        pass_fail, ev = aggregator.dispatcher.evaluate(q["text"], q["attack_type"], ans, chunk_contents)
        
        if pass_fail:
            stats[q['attack_type']]["pass"] += 1
        else:
            stats[q['attack_type']]["fail"] += 1
            print(f"   [FAIL] Evidence: {ev} | Answer: {ans[:60]}...")
            
    print("\n--- Final Run Results ---")
    formatted_stats = {}
    for atype, counts in stats.items():
        total = counts['pass'] + counts['fail']
        catch_rate = counts['fail'] / total if total > 0 else 0.0
        false_positive_rate = 0.0
        
        formatted_stats[atype] = {
            "catch_rate": catch_rate,
            "false_positive_rate": false_positive_rate
        }
        
        rate = (counts['pass'] / total) * 100 if total > 0 else 0
        print(f"{atype.upper()}: {counts['pass']}/{total} Passed ({rate:.1f}%) | Catch Rate: {catch_rate:.2f}")
        
    os.makedirs(os.path.dirname(args.report) or ".", exist_ok=True)
    with open(args.report, "w") as f:
        json.dump(formatted_stats, f, indent=4)

if __name__ == "__main__":
    main()
