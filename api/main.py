from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import uuid

from aegis_eval.evaluator.aggregator import VerdictAggregator
from aegis_eval.targets.reference_target import ReferenceTarget

app = FastAPI(title="Aegis-Eval API")
aggregator = VerdictAggregator()
reference_target = ReferenceTarget()

class QueryDef(BaseModel):
    id: str
    text: str
    attack_type: str
    source_chunks: Optional[List[str]] = []

class RunRequest(BaseModel):
    queries: List[QueryDef]

@app.post("/v1/runs")
def start_run(request: RunRequest, background_tasks: BackgroundTasks):
    run_id = str(uuid.uuid4())
    
    def process_run(r_id, qs):
        for q in qs:
            q_dict = q.dict()
            ans, chunks = reference_target.generate_response(q_dict["text"], q_dict["attack_type"])
            resp = {
                "id": q_dict["id"],
                "answer_text": ans,
                "retrieved_chunks": chunks
            }
            aggregator.aggregate_and_store(r_id, q_dict, resp)
            
    background_tasks.add_task(process_run, run_id, request.queries)
    return {"run_id": run_id, "status": "started"}

@app.get("/v1/health")
def health():
    return {"status": "ok"}
