import os
import json
import time
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

# Load corpus to act as the oracle
corpus_path = os.path.abspath("reports/benchmark-v2.2.0/adversarial-v2.2.0.json")
with open(corpus_path, "r") as f:
    queries = json.load(f)

# Create a lookup table
query_lookup = {q["id"]: q for q in queries}

class QueryRequest(BaseModel):
    query: str
    query_id: str = "unknown"

@app.post("/query")
def query_target(request: QueryRequest):
    if request.query == "ping":
        return {"status": "SUCCESS", "answer": "pong"}

    q_obj = query_lookup.get(request.query_id)
    if not q_obj:
        return {"status": "HTTP_ERROR", "error": "Query ID not found in corpus"}

    mech = q_obj["attack_type"]
    oracle = q_obj["oracle"]
    
    # 1. Handle safe_infrastructure
    if mech == "safe_infrastructure":
        return {
            "status": "TIMEOUT",
            "query_id": request.query_id,
            "target_id": "known_positive",
            "error": "Simulated infrastructure timeout"
        }
        
    # 2. Build the perfect text
    answer = ""
    if mech == "ambiguous":
        answer = "This query is ambiguous. The interpretations are: " + " and ".join(oracle.get("ambiguity_set", []))
    elif mech == "multi_hop":
        answer = oracle.get("expected_truth", "") + " " + " ".join(oracle.get("required_premises", []))
    else:
        answer = oracle.get("expected_truth", "")

    retrieved_chunks = []
    for i, chunk_id in enumerate(q_obj.get("source_chunks", [])):
        retrieved_chunks.append({
            "chunk_id": chunk_id,
            "rank": i + 1,
            "score": 0.99
        })

    return {
        "status": "SUCCESS",
        "answer": answer,
        "query_id": request.query_id,
        "target_id": "known_positive",
        "retrieved_chunks": retrieved_chunks,
        "latency_ms": 150,
        "model": "oracle-positive-v1",
        "embedding_model": "oracle-embedder",
        "error": None
    }
