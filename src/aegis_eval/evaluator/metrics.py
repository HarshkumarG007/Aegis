import json
import statistics
from collections import defaultdict
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from aegis_eval.data.schema import (
    BenchmarkManifest, EvaluationRun, AdversarialQuery, TargetResponse, 
    EvaluationVerdict, EvaluationVerdictClaim
)

class BenchmarkMetrics:
    def __init__(self, db_url):
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)

    def generate_report(self, run_id: str) -> dict:
        with self.Session() as session:
            run = session.query(EvaluationRun).filter_by(run_id=run_id).first()
            if not run:
                raise ValueError(f"Run {run_id} not found in database.")

            manifest = session.query(BenchmarkManifest).filter_by(manifest_sha256=run.manifest_sha256).first()
            
            queries = session.query(AdversarialQuery).filter_by(run_id=run_id).all()
            
            results = {
                "benchmark_version": manifest.benchmark_version if manifest else "unknown",
                "dataset_sha256": manifest.query_set_sha256 if manifest else "unknown",
                "evaluator_revision": manifest.code_revision if manifest else "unknown",
                "run_id": run_id,
                "target_name": run.target_name,
                "overall": {},
                "mechanism": defaultdict(lambda: {"total": 0, "pass": 0, "score": 0.0}),
                "difficulty": defaultdict(lambda: {"total": 0, "pass": 0, "score": 0.0}),
                "latencies": [],
                "infra_failures": 0,
                "total_queries": len(queries)
            }

            if not queries:
                return results

            total_pass = 0
            semantic_queries = 0

            for q in queries:
                response = session.query(TargetResponse).filter_by(response_id=q.query_id, run_id=run_id).first()
                if not response:
                    continue

                oracle = (q.metadata_json or {}).get("oracle", {})
                mech = q.attack_type
                diff = oracle.get("difficulty", "unknown")
                
                results["mechanism"][mech]["total"] += 1
                results["difficulty"][diff]["total"] += 1

                if response.latency_ms is not None:
                    results["latencies"].append(response.latency_ms)

                if response.status != "SUCCESS":
                    results["infra_failures"] += 1
                    # Expected to fail?
                    expected = oracle.get("expected_verdict", True)
                    if expected is False and mech == "safe_infrastructure":
                        # Target successfully rejected/errored gracefully as expected
                        results["mechanism"][mech]["pass"] += 1
                        results["difficulty"][diff]["pass"] += 1
                        total_pass += 1
                    continue

                semantic_queries += 1
                verdict = session.query(EvaluationVerdict).filter_by(response_id=response.response_id, run_id=run_id).first()
                if not verdict:
                    continue

                # Target pass directly reflects the evaluator's verdict of safety/correctness
                passed = verdict.pass_fail

                if passed:
                    results["mechanism"][mech]["pass"] += 1
                    results["difficulty"][diff]["pass"] += 1
                    total_pass += 1

            # Calculations
            for m, data in results["mechanism"].items():
                data["score"] = (data["pass"] / data["total"]) if data["total"] > 0 else 0.0

            for d, data in results["difficulty"].items():
                data["score"] = (data["pass"] / data["total"]) if data["total"] > 0 else 0.0

            core_mechanisms = ["contradiction", "out_of_domain", "multi_hop", "ambiguous"]
            macro_scores = [
                results["mechanism"][m]["score"] 
                for m in core_mechanisms 
                if results["mechanism"][m]["total"] > 0
            ]
            
            # Incorporate safe_infrastructure into macro if it was run
            if results["mechanism"].get("safe_infrastructure", {}).get("total", 0) > 0:
                macro_scores.append(results["mechanism"]["safe_infrastructure"]["score"])
                
            macro_avg = statistics.mean(macro_scores) if macro_scores else 0.0
            
            results["overall"] = {
                "pass_rate": (total_pass / results["total_queries"]) if results["total_queries"] > 0 else 0.0,
                "macro_mechanism_rate": macro_avg,
                "mean_latency_ms": statistics.mean(results["latencies"]) if results["latencies"] else 0,
                "median_latency_ms": statistics.median(results["latencies"]) if results["latencies"] else 0,
                "infra_failure_rate": (results["infra_failures"] / results["total_queries"]) if results["total_queries"] > 0 else 0.0
            }

            return results
