import os
import json
from fastapi import FastAPI
from pydantic import BaseModel
from aegis_eval.targets.known_positive_target import query_target as query_positive
from aegis_eval.targets.known_negative_target import query_target as query_negative

app = FastAPI()

class QueryRequest(BaseModel):
    query: str
    query_id: str = "unknown"

@app.post("/query")
def query_target(request: QueryRequest):
    if request.query == "ping":
        return {"status": "SUCCESS", "answer": "pong"}

    # Extract the numeric suffix to pseudo-randomize
    try:
        suffix = int(request.query_id.split("-")[-1])
        if suffix % 2 == 0:
            resp = query_positive(request)
            resp["target_id"] = "known_mixed"
            resp["model"] = "oracle-mixed-v1"
            return resp
        else:
            resp = query_negative(request)
            resp["target_id"] = "known_mixed"
            resp["model"] = "oracle-mixed-v1"
            return resp
    except Exception:
        # Fallback to negative on failure to parse
        resp = query_negative(request)
        resp["target_id"] = "known_mixed"
        resp["model"] = "oracle-mixed-v1"
        return resp
