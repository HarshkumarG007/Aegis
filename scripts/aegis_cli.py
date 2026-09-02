import os
import json
import uuid
import argparse
import requests
import subprocess
from aegis_eval.evaluator.aggregator import VerdictAggregator
from aegis_eval.evaluator.metrics import BenchmarkMetrics
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
        models="models/qwen2.5-1.5b-instruct-q4_k_m.gguf",
        embedding_model="nli-deberta-v3-small", # for V1 eval
        evaluator_version="1.0.0",
        code_revision=get_git_revision(),
        random_seed=42,
        retrieval_config={"top_k": 5},
        thresholds={"contradiction": 0.85, "groundedness": 0.75}
    )

def do_run(args):

    
    # 1. Load queries and create manifest
    with open(args.queries, "r") as f:
        query_data = json.load(f)
        
    manifest = create_manifest(args.queries)
    
    from aegis_eval.preflight import run_preflight, PreflightError
    import sys
    try:
        run_preflight(args.target, manifest)
    except PreflightError as e:
        print(f"\n[FATAL] Preflight Failed: {e}")
        sys.exit(1)
        
    aggregator = VerdictAggregator()
    manifest_sha256 = aggregator.store_manifest(manifest)
    
    run_id = str(uuid.uuid4())
    print(f"Starting V2 Evaluation Run: {run_id}")
    run_metadata = {
        "model": args.model,
        "model_sha256": args.model_sha256,
        "provider": args.provider,
        "temperature": args.temperature,
        "aegis_version": "2.3.0",
        "manifest_hash": manifest_sha256
    }
    aggregator.start_run(run_id, manifest_sha256, args.target, metadata=run_metadata)
    
    ref_target = ReferenceTarget() # For fallback corpus mapping
    
    queries_flat = []
    if isinstance(query_data, list):
        for query_obj in query_data:
            q_id = query_obj.get("id", str(uuid.uuid4()))
            queries_flat.append({
                "id": q_id,
                "text": query_obj["text"],
                "attack_type": query_obj.get("attack_type", "unknown"),
                "source_chunks": query_obj.get("source_chunks", []),
                "oracle": query_obj.get("oracle", {}),
                "raw_obj": query_obj
            })
    else:
        for attack_type, queries in query_data.items():
            for query_obj in queries:
                q_id = query_obj.get("id", str(uuid.uuid4()))
                queries_flat.append({
                    "id": q_id,
                    "text": query_obj["text"],
                    "attack_type": attack_type,
                    "source_chunks": [],
                    "raw_obj": query_obj # keep for multi-hop etc
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

        # 3. Validation of Provenance
        if args.model and target_res.status == TargetStatus.SUCCESS:
            if target_res.model != args.model:
                print(f"   [WARNING] Target returned model '{target_res.model}', but CLI requested '{args.model}'.")

        # 4. Persist Raw Response (Before Evaluation)
        aggregator.store_query_and_raw_response(run_id, q, target_res)
        
        # 5. Semantic Evaluation
        chunks_dict = {rc.chunk_id: ref_target.corpus[rc.chunk_id] for rc in target_res.retrieved_chunks if rc.chunk_id in ref_target.corpus}
        
        eval_q = q.copy()
        raw_obj = q["raw_obj"].copy()
        
        oracle = raw_obj.get("oracle", {})
        if raw_obj["attack_type"] == "multi_hop":
            raw_obj["required_premises"] = [
                {"premise_id": f"p{i}", "text": text, "evidence_chunk_ids": raw_obj.get("source_chunks", [])} 
                for i, text in enumerate(oracle.get("required_premises", []))
            ]
        elif raw_obj["attack_type"] == "ambiguous":
            raw_obj["ambiguity_set"] = oracle.get("ambiguity_set", [])
            
        eval_q["raw_obj"] = raw_obj
        eval_q["attack_type"] = raw_obj["attack_type"]
            
        pass_fail, evidence = aggregator.evaluate_and_store_verdict(run_id, eval_q, target_res, chunks_dict)
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

def do_generate(args):
    with open(args.queries, "r") as f:
        query_data = json.load(f)
        
    manifest = create_manifest(args.queries)
    
    from aegis_eval.preflight import run_preflight, PreflightError
    import sys
    try:
        run_preflight(args.target, manifest)
    except PreflightError as e:
        print(f"\n[FATAL] Preflight Failed: {e}")
        sys.exit(1)
        
    run_id = str(uuid.uuid4())
    print(f"Starting V2 Generation Run: {run_id}")
    
    queries_flat = []
    if isinstance(query_data, list):
        for query_obj in query_data:
            q_id = query_obj.get("id", str(uuid.uuid4()))
            queries_flat.append({
                "id": q_id,
                "text": query_obj["text"],
                "attack_type": query_obj.get("attack_type", "unknown")
            })
    else:
        for attack_type, queries in query_data.items():
            for query_obj in queries:
                q_id = query_obj.get("id", str(uuid.uuid4()))
                queries_flat.append({
                    "id": q_id,
                    "text": query_obj["text"],
                    "attack_type": attack_type
                })
                
    print(f"Loaded {len(queries_flat)} queries. Contacting target...")
    
    generated_responses = []
    
    for i, q in enumerate(queries_flat):
        print(f"[{i+1}/{len(queries_flat)}] Querying target for {q['attack_type']} (ID: {q['id']})...")
        try:
            res = requests.post(args.target, json={"query": q["text"], "query_id": q["id"]}, timeout=30)
            res.raise_for_status()
            target_res_dict = res.json()
        except requests.Timeout:
            target_res_dict = {"status": "TIMEOUT", "query_id": q["id"], "target_id": args.target, "error": "Request timed out"}
        except Exception as e:
            target_res_dict = {"status": "HTTP_ERROR", "query_id": q["id"], "target_id": args.target, "error": str(e)}

        try:
            target_res = validate_target_contract(target_res_dict)
        except IntegrationError as e:
            target_res = AegisTargetResponse(
                status=TargetStatus.MALFORMED,
                query_id=q["id"],
                target_id=args.target,
                error=str(e)
            )
            
        generated_responses.append(target_res.model_dump(mode='json'))
        
    artifact = {
        "run_id": run_id,
        "model": args.model,
        "model_sha256": args.model_sha256,
        "provider": args.provider,
        "temperature": args.temperature,
        "manifest_hash": manifest.compute_sha256(),
        "corpus_hash": manifest.corpus_sha256,
        "retrieval_config_hash": manifest.retrieval_config,
        "responses": generated_responses
    }
    
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(artifact, f, indent=2)
        
    print(f"Generation complete. Raw immutable artifact saved to {args.output}")

def do_evaluate(args):
    import hashlib
    with open(args.responses, "rb") as f:
        raw_bytes = f.read()
    responses_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    
    artifact = json.loads(raw_bytes.decode('utf-8'))
    run_id = artifact.get("run_id", str(uuid.uuid4()))
    print(f"Evaluating V2 Offline Run: {run_id}")
    
    with open(args.queries, "r") as f:
        query_data = json.load(f)
    manifest = create_manifest(args.queries)
    
    aggregator = VerdictAggregator()
    manifest_sha256 = aggregator.store_manifest(manifest)
    
    run_metadata = {
        "model": artifact.get("model"),
        "model_sha256": artifact.get("model_sha256"),
        "provider": artifact.get("provider"),
        "temperature": artifact.get("temperature"),
        "aegis_version": "2.3.0",
        "manifest_hash": manifest_sha256,
        "responses_sha256": responses_sha256
    }
    
    # Store manifest and start run
    aggregator.start_run(run_id, manifest_sha256, "offline_eval", metadata=run_metadata)
    
    ref_target = ReferenceTarget()
    
    queries_flat = []
    if isinstance(query_data, list):
        for query_obj in query_data:
            q_id = query_obj.get("id", str(uuid.uuid4()))
            queries_flat.append({
                "id": q_id,
                "text": query_obj["text"],
                "attack_type": query_obj.get("attack_type", "unknown"),
                "source_chunks": query_obj.get("source_chunks", []),
                "oracle": query_obj.get("oracle", {}),
                "raw_obj": query_obj
            })
    else:
        for attack_type, queries in query_data.items():
            for query_obj in queries:
                q_id = query_obj.get("id", str(uuid.uuid4()))
                queries_flat.append({
                    "id": q_id,
                    "text": query_obj["text"],
                    "attack_type": attack_type,
                    "source_chunks": [],
                    "raw_obj": query_obj
                })
                
    responses_dict = {r["query_id"]: r for r in artifact.get("responses", [])}
    
    run_folder = f"reports/run-{run_id}"
    os.makedirs(run_folder, exist_ok=True)
    with open(os.path.join(run_folder, "manifest.json"), "w") as f:
        f.write(manifest.get_canonical_json())
        
    responses_log = []
    verdicts_log = []
    
    for i, q in enumerate(queries_flat):
        print(f"[{i+1}/{len(queries_flat)}] Evaluating response for {q['attack_type']} (ID: {q['id']})...")
        
        target_res_dict = responses_dict.get(q["id"])
        if not target_res_dict:
            print(f"   [WARNING] Query {q['id']} not found in offline responses!")
            target_res_dict = {"status": "MALFORMED", "query_id": q["id"], "target_id": "offline", "error": "Missing from generation artifact"}
            
        try:
            target_res = validate_target_contract(target_res_dict)
        except IntegrationError as e:
            target_res = AegisTargetResponse(status=TargetStatus.MALFORMED, query_id=q["id"], target_id="offline", error=str(e))
            
        responses_log.append(target_res.model_dump(mode='json'))
        aggregator.store_query_and_raw_response(run_id, q, target_res)
        
        chunks_dict = {rc.chunk_id: ref_target.corpus[rc.chunk_id] for rc in target_res.retrieved_chunks if rc.chunk_id in ref_target.corpus}
        eval_q = q.copy()
        raw_obj = q["raw_obj"].copy()
        
        oracle = raw_obj.get("oracle", {})
        if raw_obj["attack_type"] == "multi_hop":
            raw_obj["required_premises"] = [
                {"premise_id": f"p{idx}", "text": text, "evidence_chunk_ids": raw_obj.get("source_chunks", [])} 
                for idx, text in enumerate(oracle.get("required_premises", []))
            ]
        elif raw_obj["attack_type"] == "ambiguous":
            raw_obj["ambiguity_set"] = oracle.get("ambiguity_set", [])
            
        eval_q["raw_obj"] = raw_obj
        eval_q["attack_type"] = raw_obj["attack_type"]
            
        pass_fail, evidence = aggregator.evaluate_and_store_verdict(run_id, eval_q, target_res, chunks_dict)
        verdicts_log.append({"query_id": q["id"], "pass_fail": pass_fail, "evidence": evidence})
        
        if target_res.status != TargetStatus.SUCCESS:
            print(f"   [{target_res.status.value}] Bypassing semantic evaluation. Error: {target_res.error}")
        else:
            if pass_fail:
                print("   [PASS]")
            else:
                print(f"   [FAIL] Evidence: {evidence}")

    with open(os.path.join(run_folder, "queries.json"), "w") as f:
        json.dump(queries_flat, f, indent=2)
    with open(os.path.join(run_folder, "responses.json"), "w") as f:
        json.dump(responses_log, f, indent=2)
    with open(os.path.join(run_folder, "verdicts.json"), "w") as f:
        json.dump(verdicts_log, f, indent=2)
        
    print(f"Evaluation complete. Artifact scored and persisted to {run_folder}")

def do_replay(args):

    
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
    
    verdicts_log = []
    for i, q in enumerate(queries_flat):
        target_res = AegisTargetResponse(**responses_log[i])
        
        # 1. Re-persist raw (simulating target response without hitting target)
        aggregator.store_query_and_raw_response(replay_run_id, q, target_res)
        
        # 2. Semantic Evaluation
        chunks_dict = {rc.chunk_id: ref_target.corpus[rc.chunk_id] for rc in target_res.retrieved_chunks if rc.chunk_id in ref_target.corpus}
        eval_q = q.copy()
        raw_obj = q.get("raw_obj", q).copy()
        
        oracle = raw_obj.get("oracle", {})
        if raw_obj.get("attack_type") == "multi_hop":
            raw_obj["required_premises"] = [
                {"premise_id": f"p{idx}", "text": text, "evidence_chunk_ids": raw_obj.get("source_chunks", [])} 
                for idx, text in enumerate(oracle.get("required_premises", []))
            ]
        elif raw_obj.get("attack_type") == "ambiguous":
            raw_obj["ambiguity_set"] = oracle.get("ambiguity_set", [])
            
        eval_q["raw_obj"] = raw_obj
        eval_q["attack_type"] = raw_obj.get("attack_type", q.get("attack_type"))
        
        pass_fail, evidence = aggregator.evaluate_and_store_verdict(replay_run_id, eval_q, target_res, chunks_dict)
        verdicts_log.append({"query_id": q["id"], "pass_fail": pass_fail, "evidence": evidence})
        print(f"Replayed {q['id']} - Pass: {pass_fail}")

    replay_folder = f"reports/run-{replay_run_id}"
    os.makedirs(replay_folder, exist_ok=True)
    with open(os.path.join(replay_folder, "verdicts.json"), "w") as f:
        json.dump(verdicts_log, f, indent=2)

    print(f"Replay complete. New run ID: {replay_run_id}. Checking byte-for-byte matching...")
    with open(os.path.join(run_folder, "verdicts.json"), "r") as f:
        original_verdicts = f.read()
    with open(os.path.join(replay_folder, "verdicts.json"), "r") as f:
        replay_verdicts = f.read()
    if original_verdicts == replay_verdicts:
        print("ASSERTION PASSED: 100% byte-for-byte deterministic matching achieved.")
    else:
        print("ASSERTION FAILED: Verdicts differ!")

def do_report(args):
    from aegis_eval.config import get_db_url
    db_url = get_db_url()
    metrics_engine = BenchmarkMetrics(db_url)
    report = metrics_engine.generate_report(args.run_id)
    
    print(f"Aegis-Eval Benchmark {report['benchmark_version']}")
    print(f"Run: {report['run_id']}")
    print(f"Dataset SHA256: {report['dataset_sha256']}")
    print(f"Evaluator Revision: {report['evaluator_revision']}")
    print("")
    print("Overall")
    print("-----------------------------")
    print(f"Pass rate             {report['overall']['pass_rate']*100:.1f}%")
    print(f"Macro mechanism rate  {report['overall']['macro_mechanism_rate']*100:.1f}%")
    print(f"Mean latency          {report['overall']['mean_latency_ms']/1000:.2f}s")
    print(f"Median latency        {report['overall']['median_latency_ms']/1000:.2f}s")
    print(f"Infra failure rate     {report['overall']['infra_failure_rate']*100:.1f}%")
    print("")
    print("Core Mechanisms")
    print("-----------------------------")
    core_mechs = ["contradiction", "out_of_domain", "multi_hop", "ambiguous", "safe_infrastructure"]
    for mech in core_mechs:
        data = report['mechanism'].get(mech)
        if data and data['total'] > 0:
            print(f"{mech.ljust(21)} {data['score']*100:.1f}%")
            
    print("")
    print("Interaction")
    print("-----------------------------")
    interaction_mechs = ["mixed"]
    for mech in interaction_mechs:
        data = report['mechanism'].get(mech)
        if data and data['total'] > 0:
            print(f"{mech.ljust(21)} {data['score']*100:.1f}%")
    print("")
    print("Difficulty")
    print("-----------------------------")
    for diff, data in report['difficulty'].items():
        if data['total'] > 0:
            print(f"{diff.ljust(21)} {data['score']*100:.1f}%")

def do_assert(args):
    import sys
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from aegis_eval.config import get_db_url
    db_url = get_db_url()
    
    # If run_id is not provided, fetch the latest run
    run_id = args.run_id
    if not run_id:
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        from aegis_eval.data.schema import EvaluationRun
        with Session() as session:
            latest = session.query(EvaluationRun).order_by(EvaluationRun.started_at.desc()).first()
            if not latest:
                print("No runs found in database.")
                sys.exit(1)
            run_id = latest.run_id
            
    metrics_engine = BenchmarkMetrics(db_url)
    report = metrics_engine.generate_report(run_id)
    
    failed = False
    
    if args.overall_min is not None:
        overall = report['overall']['pass_rate']
        if overall < args.overall_min:
            print(f"[FAIL] Overall pass rate {overall:.2f} < {args.overall_min}")
            failed = True
        else:
            print(f"[PASS] Overall pass rate {overall:.2f} >= {args.overall_min}")
            
    if args.contradiction_min is not None:
        contra = report['mechanism'].get('contradiction', {}).get('score', 0.0)
        if contra < args.contradiction_min:
            print(f"[FAIL] Contradiction pass rate {contra:.2f} < {args.contradiction_min}")
            failed = True
        else:
            print(f"[PASS] Contradiction pass rate {contra:.2f} >= {args.contradiction_min}")
            
    if failed:
        sys.exit(1)
    else:
        print("All assertions passed.")
        sys.exit(0)

def do_leaderboard(args):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from aegis_eval.config import get_db_url
    db_url = get_db_url()
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    from aegis_eval.data.schema import EvaluationRun, BenchmarkManifest
    
    with Session() as session:
        query = session.query(EvaluationRun)
        
        # Filter by manifest hash if provided
        if args.manifest:
            # We can lookup manifest_sha256 if args.manifest is a partial hash
            query = query.filter(EvaluationRun.manifest_sha256.like(f"{args.manifest}%"))
            
        # Group by configuration signature and get the latest run for each configuration
        runs = query.order_by(EvaluationRun.started_at.desc()).all()
        
    if not runs:
        print("No runs found.")
        return
        
    latest_run_per_config = {}
    config_details = {}
    
    for r in runs:
        m = r.model or r.target_name
        p = r.provider or "unknown"
        t = r.temperature if r.temperature is not None else 0.0
        m_sha = r.model_sha256 or "unknown"
        rc = r.retrieval_config_hash or "unknown"
        cc = r.corpus_hash or "unknown"
        mh = r.manifest_sha256 or "unknown"
        
        config_key = (m, p, t, m_sha, rc, cc, mh)
        
        if config_key not in latest_run_per_config:
            latest_run_per_config[config_key] = r.run_id
            config_details[config_key] = {
                "model": m,
                "provider": p,
                "temperature": t,
                "model_sha256": m_sha,
                "run_id": r.run_id
            }
            
    metrics_engine = BenchmarkMetrics(db_url)
    
    if args.details:
        print("| Model | Provider | Temp | Model SHA256 | Run ID | Overall | Contradiction | OOD | Ambiguous | Multi-hop |")
        print("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    else:
        print("| Model | Overall | Contradiction | OOD | Ambiguous | Multi-hop |")
        print("| :--- | :--- | :--- | :--- | :--- | :--- |")
        
        # Check if we have multiple configurations for the same model
        model_counts = {}
        for (m, p, t, m_sha, rc, cc, mh) in latest_run_per_config.keys():
            model_counts[m] = model_counts.get(m, 0) + 1
        
        has_warnings = False
        for m, count in model_counts.items():
            if count > 1:
                has_warnings = True
                
        if has_warnings:
            print("\n[WARNING] Multiple distinct configurations exist for the same model. Run with `--details` for exact provenance.\n")
    
    for config_key, r_id in latest_run_per_config.items():
        details = config_details[config_key]
        report = metrics_engine.generate_report(r_id)
        
        overall = report['overall']['pass_rate'] * 100
        contra = report['mechanism'].get('contradiction', {}).get('score', 0.0) * 100
        ood = report['mechanism'].get('out_of_domain', {}).get('score', 0.0) * 100
        amb = report['mechanism'].get('ambiguous', {}).get('score', 0.0) * 100
        mh = report['mechanism'].get('multi_hop', {}).get('score', 0.0) * 100
        
        if args.details:
            short_sha = details['model_sha256'][:8] if details['model_sha256'] != 'unknown' else 'unknown'
            print(f"| {details['model']} | {details['provider']} | {details['temperature']} | {short_sha} | {details['run_id'][:8]} | {overall:.1f}% | {contra:.1f}% | {ood:.1f}% | {amb:.1f}% | {mh:.1f}% |")
        else:
            print(f"| {details['model']} | {overall:.1f}% | {contra:.1f}% | {ood:.1f}% | {amb:.1f}% | {mh:.1f}% |")

def main():
    parser = argparse.ArgumentParser(description="Aegis-Eval CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    run_parser = subparsers.add_parser("run", help="Run a new evaluation against a target")
    run_parser.add_argument("--target", type=str, default="reference", help="Target URL or 'reference'")
    run_parser.add_argument("--queries", type=str, default="reports/adversarial_queries_v2.json", help="Query set JSON")
    run_parser.add_argument("--model", type=str, default=None, help="Explicit model provenance string")
    run_parser.add_argument("--model-sha256", type=str, default=None, help="Exact SHA256 of the model weights/GGUF")
    run_parser.add_argument("--provider", type=str, default=None, help="Explicit provider provenance string")
    run_parser.add_argument("--temperature", type=float, default=None, help="Temperature provenance")
    
    replay_parser = subparsers.add_parser("replay", help="Replay an evaluation from stored responses")
    replay_parser.add_argument("run_folder", type=str, help="Path to reports/run-UUID folder")
    
    report_parser = subparsers.add_parser("report", help="Generate benchmark report for a run")
    report_parser.add_argument("run_id", type=str, help="UUID of the run to report on")
    
    assert_parser = subparsers.add_parser("assert", help="Assert that evaluation metrics meet thresholds")
    assert_parser.add_argument("--run-id", type=str, default=None, help="Run ID (defaults to latest)")
    assert_parser.add_argument("--overall-min", type=float, default=None, help="Minimum overall pass rate")
    assert_parser.add_argument("--contradiction-min", type=float, default=None, help="Minimum contradiction pass rate")
    
    leaderboard_parser = subparsers.add_parser("leaderboard", help="Generate comparison matrix for runs")
    leaderboard_parser.add_argument("--manifest", type=str, default=None, help="Filter by manifest hash")
    leaderboard_parser.add_argument("--details", action="store_true", help="Show full provenance for each run")
    leaderboard_parser.add_argument("--latest", action="store_true", help="Only show the latest run for each distinct configuration (default)")
    
    generate_parser = subparsers.add_parser("generate", help="Generate offline responses from target")
    generate_parser.add_argument("--target", type=str, required=True, help="Target URL")
    generate_parser.add_argument("--queries", type=str, default="reports/adversarial_queries_v2.json", help="Query set JSON")
    generate_parser.add_argument("--model", type=str, default=None, help="Explicit model provenance string")
    generate_parser.add_argument("--model-sha256", type=str, default=None, help="Exact SHA256 of the model weights/GGUF")
    generate_parser.add_argument("--provider", type=str, default=None, help="Explicit provider provenance string")
    generate_parser.add_argument("--temperature", type=float, default=None, help="Temperature provenance")
    generate_parser.add_argument("--output", type=str, required=True, help="Output JSON artifact file path")

    evaluate_parser = subparsers.add_parser("evaluate", help="Evaluate offline responses")
    evaluate_parser.add_argument("--responses", type=str, required=True, help="Path to generated JSON artifact")
    evaluate_parser.add_argument("--queries", type=str, required=True, help="Path to original query manifest JSON")
    
    args = parser.parse_args()
    
    if args.command == "run":
        do_run(args)
    elif args.command == "replay":
        do_replay(args)
    elif args.command == "report":
        do_report(args)
    elif args.command == "assert":
        do_assert(args)
    elif args.command == "leaderboard":
        do_leaderboard(args)
    elif args.command == "generate":
        do_generate(args)
    elif args.command == "evaluate":
        do_evaluate(args)

if __name__ == "__main__":
    main()
