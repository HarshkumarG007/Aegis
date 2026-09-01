import os
import json
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

corpus_path = os.path.abspath("reports/benchmark-v2.2.0/adversarial-v2.2.0.json")
with open(corpus_path, "r") as f:
    queries = json.load(f)

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
        return {"status": "HTTP_ERROR", "error": "Query ID not found"}

    mech = q_obj["attack_type"]
    oracle = q_obj["oracle"]
    
    # 1. safe_infrastructure: The oracle EXPECTS a failure, so to fail we return SUCCESS.
    if mech == "safe_infrastructure":
        return {
            "status": "SUCCESS",
            "answer": "This is a generic answer that ignores the infrastructure trap.",
            "query_id": request.query_id,
            "target_id": "known_negative",
            "retrieved_chunks": [],
            "latency_ms": 150,
            "model": "oracle-negative-v1",
            "embedding_model": "oracle-embedder",
            "error": None
        }

    # 2. Build the intentionally failing text
    answer = ""
    if mech in ["contradiction", "out_of_domain", "mixed"]:
        claims = oracle.get("expected_claims", [])
        if claims:
            answer = " ".join(claims)
        else:
            answer = "I don't know."
    elif mech == "multi_hop":
        # Missing premises to fail the completeness check
        premises = oracle.get("required_premises", [])
        if premises:
            answer = premises[0] # Only return the first premise, omitting the rest
        else:
            answer = "Incomplete response."
    elif mech == "ambiguous":
        # Only acknowledge one interpretation
        ambiguity_set = oracle.get("ambiguity_set", [])
        if ambiguity_set:
            answer = ambiguity_set[0]
        else:
            answer = "Single interpretation."
    else:
        answer = "Generic wrong answer."

    # Return WRONG retrieved chunks to fail groundedness even further
    retrieved_chunks = [
        {"chunk_id": "wrong-chunk-x", "rank": 1, "score": 0.5}
    ]

    return {
        "status": "SUCCESS",
        "answer": answer,
        "query_id": request.query_id,
        "target_id": "known_negative",
        "retrieved_chunks": retrieved_chunks,
        "latency_ms": 150,
        "model": "oracle-negative-v1",
        "embedding_model": "oracle-embedder",
        "error": None
    }
