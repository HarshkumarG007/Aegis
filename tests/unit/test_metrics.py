import os
import uuid
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from aegis_eval.data.schema import (
    Base, BenchmarkManifest, EvaluationRun, AdversarialQuery, TargetResponse, 
    EvaluationVerdict, EvaluationVerdictClaim
)
from aegis_eval.evaluator.metrics import BenchmarkMetrics

@pytest.fixture
def mock_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    manifest_sha256 = "test-hash-123"
    manifest = BenchmarkManifest(
        manifest_sha256=manifest_sha256,
        benchmark_version="2.2.0",
        query_set="test",
        query_set_sha256="test-set-hash",
        corpus_sha256="corpus-hash",
        models="model-a",
        embedding_model="embed-b",
        evaluator_version="v2.1",
        code_revision="rev-1",
        random_seed=42,
        retrieval_config={},
        thresholds={}
    )
    session.add(manifest)

    run_id = str(uuid.uuid4())
    run = EvaluationRun(run_id=run_id, manifest_sha256=manifest_sha256, target_name="test_target")
    session.add(run)

    # Add queries explicitly designed for macro imbalance testing
    queries = [
        # 10 Easy Contradiction (all pass)
        *[("contradiction", "easy", True, "SUCCESS", True, "CONTRADICTED") for _ in range(10)],
        # 2 Hard Multi-hop (all fail)
        *[("multi_hop", "hard", True, "SUCCESS", False, "UNSUPPORTED") for _ in range(2)],
        # 1 Safe infra (passes by timing out)
        ("safe_infrastructure", "easy", False, "TIMEOUT", False, None)
    ]

    for idx, (mech, diff, expected, status, v_pass, c_status) in enumerate(queries):
        q_id = f"q-{idx}"
        q = AdversarialQuery(
            query_id=q_id,
            run_id=run_id,
            attack_type=mech,
            query_text="text",
            source_chunk_ids="[]",
            metadata_json={"oracle": {"difficulty": diff, "expected_verdict": expected}}
        )
        session.add(q)
        
        r = TargetResponse(
            response_id=q_id,
            run_id=run_id,
            status=status,
            latency_ms=100
        )
        session.add(r)
        
        if status == "SUCCESS":
            v_id = f"v-{idx}"
            v = EvaluationVerdict(
                verdict_id=v_id,
                response_id=q_id,
                run_id=run_id,
                mechanism_used=mech,
                pass_fail=v_pass,
                primary_evidence="{}"
            )
            session.add(v)
            if c_status:
                c = EvaluationVerdictClaim(
                    claim_id=f"c-{idx}",
                    verdict_id=v_id,
                    claim_text="claim",
                    status=c_status
                )
                session.add(c)
                
    session.commit()
    return session, engine, run_id

def test_metrics_generation_and_macro_average(mock_db):
    session, engine, run_id = mock_db
    
    # We pass the engine URL directly but in our mock we need to pass the same engine
    # So we slightly modify BenchmarkMetrics to accept engine for test injections
    metrics_engine = BenchmarkMetrics("sqlite:///:memory:")
    metrics_engine.engine = engine
    metrics_engine.Session = sessionmaker(bind=engine)
    
    report = metrics_engine.generate_report(run_id)
    
    assert report["benchmark_version"] == "2.2.0"
    assert report["total_queries"] == 13
    
    # Micro-average pass rate: 10 pass, 2 fail, 1 pass (infra) = 11 / 13 = 84.6%
    assert round(report["overall"]["pass_rate"], 3) == 0.846
    
    # Macro-average check:
    # Contradiction: 10/10 = 1.0
    # Multi-hop: 0/2 = 0.0
    # Safe infra: 1/1 = 1.0
    # Macro = (1.0 + 0.0 + 1.0) / 3 = 0.666
    assert round(report["overall"]["macro_mechanism_rate"], 3) == 0.667

    # Mechanism scores
    assert report["mechanism"]["contradiction"]["score"] == 1.0
    assert report["mechanism"]["multi_hop"]["score"] == 0.0
    assert report["mechanism"]["safe_infrastructure"]["score"] == 1.0
    
    # Infra failures
    assert report["overall"]["infra_failure_rate"] == 1 / 13

    # Difficulty breakdown
    assert report["difficulty"]["easy"]["score"] == 1.0 # 11 / 11
    assert report["difficulty"]["hard"]["score"] == 0.0 # 0 / 2
