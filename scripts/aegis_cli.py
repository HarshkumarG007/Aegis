import os
import json
import uuid
import argparse
import requests
import subprocess
from aegis_eval.evaluator.aggregator import VerdictAggregator
from aegis_eval.targets.reference_target import ReferenceTarget
from aegis_eval.targets.integration_contract import validate_target_contract, TargetStatus, AegisTargetResponse, RetrievedChunk, IntegrationError
from aegis_eval.data.manifest import BenchmarkManifest

def get_git_revision():
    try:
        return subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode('utf-8').strip()
    except Exception:
        return "unknown"

def create_manifest(query_set_path: str) -> BenchmarkManifest:
    # Compute query set hash
    with open(query_set_path, 'rb') as f:
        q_bytes = f.read()
    import hashlib
    q_hash = hashlib.sha256(q_bytes).hexdigest()

    return BenchmarkManifest(
        benchmark_version="2.0",
        query_set=query_set_path,
        query_set_sha256=q_hash,
        corpus_sha256="unknown_corpus_hash", # Should be computed from corpus file
        models="qwen2.5-1.5b-instruct-q4_k_m.gguf",
        embedding_model="nli-deberta-v3-small", # for V1 eval
        evaluator_version="1.0.0",
        code_revision=get_git_revision(),
        random_seed=42,
        retrieval_config={"top_k": 5},
        thresholds={"contradiction": 0.85, "groundedness": 0.75}
    )

def do_run(args):
    os.environ["DATABASE_URL"] = "postgresql://postgres:123456@localhost:5433/postgres"
    
    # 1. Load queries and create manifest
    with open(args.queries, "r") as f:
        query_data = json.load(f)
        
    manifest = create_manifest(args.queries)
    
    aggregator = VerdictAggregator()
    manifest_sha256 = aggregator.store_manifest(manifest)
    
    run_id = str(uuid.uuid4())
    print(f"Starting V2 Evaluation Run: {run_id}")
    aggregator.start_run(run_id, manifest_sha256, args.target)
    
    ref_target = ReferenceTarget() # For fallback corpus mapping
    
    queries_flat = []
    for attack_type, queries in query_data.items():
        for text in queries:
            queries_flat.append({
                "id": str(uuid.uuid4()),
                "text": text,
                "attack_type": attack_type,
                "source_chunks": []
            })
            
    print(f"Loaded {len(queries_flat)} queries. Contacting target...")
    
    run_folder = f"reports/run-{run_id}"
    os.makedirs(run_folder, exist_ok=True)
    
    with open(os.path.join(run_folder, "manifest.json"), "w") as f:
        f.write(manifest.get_canonical_json())
        
    responses_log = []
    verdicts_log = []
    
    for i, q in enumerate(queries_flat):
        print(f"[{i+1}/{len(queries_flat)}] Querying target for {q['attack_type']}...")
        
        # 1. Contact Target
        target_res_dict = {}
        if args.target == "reference":
            # Adapt V1 target response to V2 schema manually for regression testing
            v1_res = ref_target.query(q["text"], q["attack_type"])
            target_res_dict = {
                "status": "SUCCESS",
                "answer": v1_res.get("answer_text", ""),
                "query_id": q["id"],
                "target_id": "reference_target",
                "retrieved_chunks": [
                    {"chunk_id": cid, "rank": r+1} for r, cid in enumerate(v1_res.get("retrieved_chunk_ids", []))
                ]
            }
        else:
            try:
                res = requests.post(args.target, json={"query": q["text"], "query_id": q["id"]}, timeout=30)
                res.raise_for_status()
                target_res_dict = res.json()
            except requests.Timeout:
                target_res_dict = {"status": "TIMEOUT", "query_id": q["id"], "target_id": args.target, "error": "Request timed out"}
            except Exception as e:
                target_res_dict = {"status": "HTTP_ERROR", "query_id": q["id"], "target_id": args.target, "error": str(e)}

        # 2. Contract Validation
        try:
            target_res = validate_target_contract(target_res_dict)
        except IntegrationError as e:
            target_res = AegisTargetResponse(
                status=TargetStatus.MALFORMED,
                query_id=q["id"],
                target_id=args.target,
                error=str(e)
            )
            
        responses_log.append(target_res.model_dump(mode='json'))

        # 3. Persist Raw Response (Before Evaluation)
        aggregator.store_query_and_raw_response(run_id, q, target_res)
        
        # 4. Semantic Evaluation
        chunks_dict = {rc.chunk_id: ref_target.corpus[rc.chunk_id] for rc in target_res.retrieved_chunks if rc.chunk_id in ref_target.corpus}
        
        pass_fail, evidence = aggregator.evaluate_and_store_verdict(q, target_res, chunks_dict)
        verdicts_log.append({"query_id": q["id"], "pass_fail": pass_fail, "evidence": evidence})
        
        if target_res.status != TargetStatus.SUCCESS:
            print(f"   [{target_res.status.value}] Bypassing semantic evaluation. Error: {target_res.error}")
        else:
            if pass_fail:
                print("   [PASS]")
            else:
                print(f"   [FAIL] Evidence: {evidence}")

    # Save to replay folder
    with open(os.path.join(run_folder, "queries.json"), "w") as f:
        json.dump(queries_flat, f, indent=2)
    with open(os.path.join(run_folder, "responses.json"), "w") as f:
        json.dump(responses_log, f, indent=2)
    with open(os.path.join(run_folder, "verdicts.json"), "w") as f:
        json.dump(verdicts_log, f, indent=2)
        
    print(f"Run {run_id} complete. Raw data persisted to {run_folder}")

def do_replay(args):
    os.environ["DATABASE_URL"] = "postgresql://postgres:123456@localhost:5433/postgres"
    
    run_folder = args.run_folder
    print(f"Replaying run from {run_folder}...")
    
    with open(os.path.join(run_folder, "manifest.json"), "r") as f:
        manifest_data = json.load(f)
    manifest = BenchmarkManifest(**manifest_data)
    
    with open(os.path.join(run_folder, "queries.json"), "r") as f:
        queries_flat = json.load(f)
        
    with open(os.path.join(run_folder, "responses.json"), "r") as f:
        responses_log = json.load(f)
        
    aggregator = VerdictAggregator()
    ref_target = ReferenceTarget()
    
    # Store manifest (if new DB)
    manifest_sha256 = aggregator.store_manifest(manifest)
    
    # Generate new run ID for replay
    replay_run_id = str(uuid.uuid4())
    aggregator.start_run(replay_run_id, manifest_sha256, f"replay_{run_folder}")
    
    for i, q in enumerate(queries_flat):
        target_res = AegisTargetResponse(**responses_log[i])
        
        # 1. Re-persist raw (simulating target response without hitting target)
        aggregator.store_query_and_raw_response(replay_run_id, q, target_res)
        
        # 2. Semantic Evaluation
        chunks_dict = {rc.chunk_id: ref_target.corpus[rc.chunk_id] for rc in target_res.retrieved_chunks if rc.chunk_id in ref_target.corpus}
        pass_fail, evidence = aggregator.evaluate_and_store_verdict(q, target_res, chunks_dict)
        
        print(f"Replayed {q['id']} - Pass: {pass_fail}")

    print(f"Replay complete. New run ID: {replay_run_id}")

def main():
    parser = argparse.ArgumentParser(description="Aegis-Eval CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    run_parser = subparsers.add_parser("run", help="Run a new evaluation against a target")
    run_parser.add_argument("--target", type=str, default="reference", help="Target URL or 'reference'")
    run_parser.add_argument("--queries", type=str, default="reports/adversarial_queries_v2.json", help="Query set JSON")
    
    replay_parser = subparsers.add_parser("replay", help="Replay an evaluation from stored responses")
    replay_parser.add_argument("run_folder", type=str, help="Path to reports/run-UUID folder")
    
    args = parser.parse_args()
    
    if args.command == "run":
        do_run(args)
    elif args.command == "replay":
        do_replay(args)

if __name__ == "__main__":
    main()
