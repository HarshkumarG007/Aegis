import os
import json
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from aegis_eval.data.schema import EvaluationRun, AdversarialQuery, TargetResponse, EvaluationVerdict
from aegis_eval.evaluator.dispatcher import EvaluatorDispatcher

class VerdictAggregator:
    def __init__(self, db_url=None):
        if db_url is None:
            db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres")
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)
        self.dispatcher = EvaluatorDispatcher()
        
    def aggregate_and_store(self, run_id: str, query: dict, response: dict) -> str:
        """
        query: dict with id, text, attack_type, source_chunks
        response: dict with id, answer_text, retrieved_chunks
        id should be the same for query and response due to schema FK mapping.
        """
        pass_fail, evidence = self.dispatcher.evaluate(
            query["text"], 
            query["attack_type"], 
            response["answer_text"], 
            response["retrieved_chunks"]
        )
        
        # Informational metrics only
        bertscore = 0.0
        rouge_l = 0.0
        
        with self.Session() as session:
            run = session.query(EvaluationRun).filter_by(run_id=run_id).first()
            if not run:
                run = EvaluationRun(run_id=run_id, target_name="ReferenceTarget")
                session.add(run)
                
            q_record = AdversarialQuery(
                query_id=query["id"],
                run_id=run_id,
                attack_type=query["attack_type"],
                query_text=query["text"],
                source_chunk_ids=json.dumps(query.get("source_chunks", []))
            )
            
            r_record = TargetResponse(
                response_id=response["id"],
                answer_text=response["answer_text"],
                retrieved_chunk_ids=json.dumps(response.get("retrieved_chunks", []))
            )
            
            v_id = str(uuid.uuid4())
            v_record = EvaluationVerdict(
                verdict_id=v_id,
                response_id=response["id"],
                mechanism_used=query["attack_type"],
                pass_fail=pass_fail,
                primary_evidence=evidence,
                bertscore=bertscore,
                rouge_l=rouge_l
            )
            
            session.add(q_record)
            session.add(r_record)
            session.add(v_record)
            session.commit()
            
        return v_id
