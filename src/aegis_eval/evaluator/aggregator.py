import os
import json
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from aegis_eval.data.schema import BenchmarkManifest, EvaluationRun, AdversarialQuery, TargetResponse, EvaluationVerdict, RetrievedChunk
from aegis_eval.evaluator.dispatcher import EvaluatorDispatcher
from aegis_eval.targets.integration_contract import AegisTargetResponse
from aegis_eval.data.manifest import BenchmarkManifest as PydanticManifest

class VerdictAggregator:
    def __init__(self, db_url=None):
        if db_url is None:
            db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres")
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)
        self.dispatcher = EvaluatorDispatcher()

    def store_manifest(self, manifest: PydanticManifest) -> str:
        sha256 = manifest.compute_sha256()
        with self.Session() as session:
            existing = session.query(BenchmarkManifest).filter_by(manifest_sha256=sha256).first()
            if not existing:
                db_manifest = BenchmarkManifest(
                    manifest_sha256=sha256,
                    benchmark_version=manifest.benchmark_version,
                    query_set=manifest.query_set,
                    query_set_sha256=manifest.query_set_sha256,
                    corpus_sha256=manifest.corpus_sha256,
                    models=manifest.models,
                    embedding_model=manifest.embedding_model,
                    evaluator_version=manifest.evaluator_version,
                    code_revision=manifest.code_revision,
                    random_seed=manifest.random_seed,
                    retrieval_config=manifest.retrieval_config,
                    thresholds=manifest.thresholds
                )
                session.add(db_manifest)
                session.commit()
        return sha256

    def start_run(self, run_id: str, manifest_sha256: str, target_name: str):
        with self.Session() as session:
            run = session.query(EvaluationRun).filter_by(run_id=run_id).first()
            if not run:
                run = EvaluationRun(run_id=run_id, manifest_sha256=manifest_sha256, target_name=target_name)
                session.add(run)
                session.commit()

    def store_query_and_raw_response(self, run_id: str, query: dict, response: AegisTargetResponse):
        with self.Session() as session:
            q_record = session.query(AdversarialQuery).filter_by(query_id=query["id"]).first()
            if not q_record:
                q_record = AdversarialQuery(
                    query_id=query["id"],
                    run_id=run_id,
                    attack_type=query["attack_type"],
                    query_text=query["text"],
                    source_chunk_ids=json.dumps(query.get("source_chunks", []))
                )
                session.add(q_record)

            r_record = session.query(TargetResponse).filter_by(response_id=query["id"]).first()
            if not r_record:
                r_record = TargetResponse(
                    response_id=query["id"],
                    status=response.status.value,
                    answer_text=response.answer,
                    latency_ms=response.latency_ms,
                    error=response.error,
                    model=response.model,
                    embedding_model=response.embedding_model,
                    metadata_json=response.metadata
                )
                session.add(r_record)
                
                for rc in response.retrieved_chunks:
                    chunk = RetrievedChunk(
                        response_id=query["id"],
                        chunk_id=rc.chunk_id,
                        rank=rc.rank,
                        score=rc.score,
                        text_hash=rc.text_hash
                    )
                    session.add(chunk)

            session.commit()

    def evaluate_and_store_verdict(self, query: dict, response: AegisTargetResponse, chunk_contents: list) -> tuple:
        if response.status.value != "SUCCESS":
            return False, f"Infrastructure failure: {response.status.value}"

        pass_fail, evidence = self.dispatcher.evaluate(
            query["text"], 
            query["attack_type"], 
            response.answer or "", 
            chunk_contents
        )
        
        with self.Session() as session:
            v_id = str(uuid.uuid4())
            v_record = EvaluationVerdict(
                verdict_id=v_id,
                response_id=query["id"],
                mechanism_used=query["attack_type"],
                pass_fail=pass_fail,
                primary_evidence=evidence,
                bertscore=0.0,
                rouge_l=0.0
            )
            session.add(v_record)
            session.commit()
            
        return pass_fail, evidence
