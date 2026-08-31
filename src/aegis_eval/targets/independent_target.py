import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.llama_cpp import LlamaCPP

app = FastAPI()

# Setup Local Embeddings
Settings.embed_model = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")

# Setup Local LLM
model_path = os.path.abspath("models/qwen2.5-1.5b-instruct-q4_k_m.gguf")
llm = LlamaCPP(
    model_url=None,
    model_path=model_path,
    temperature=0.1,
    max_new_tokens=256,
    context_window=2048,
    generate_kwargs={},
    model_kwargs={"n_gpu_layers": 0},
    verbose=False,
)
Settings.llm = llm

from llama_index.core.schema import TextNode
CORPUS = {
    "chunk-001": "The default timeout for the v1 API is 30 seconds.",
    "chunk-002": "API requests will time out after 60 seconds by default in the new configuration.",
    "chunk-003": "Service A connects to the messaging queue.",
    "chunk-004": "The messaging queue is hosted on redis-01.",
    "chunk-005": "The user profile can be updated via the PUT /user endpoint.",
    "chunk-006": "The PUT /user endpoint is deprecated in v2, use POST /user/update.",
    "chunk-007": "All database passwords must be rotated every 90 days."
}

nodes = [TextNode(text=text, id_=cid) for cid, text in CORPUS.items()]
index = VectorStoreIndex(nodes)
query_engine = index.as_query_engine(similarity_top_k=2)

import time

class QueryRequest(BaseModel):
    query: str
    query_id: str = "unknown"

@app.post("/query")
def query_target(request: QueryRequest):
    start_time = time.time()
    try:
        response = query_engine.query(request.query)
        retrieved_chunks = []
        for i, node in enumerate(response.source_nodes):
            retrieved_chunks.append({
                "chunk_id": node.node.node_id,
                "rank": i + 1,
                "score": node.score
            })
            
        latency_ms = int((time.time() - start_time) * 1000)
        return {
            "status": "SUCCESS",
            "answer": str(response),
            "query_id": request.query_id,
            "target_id": "independent_llama_target",
            "retrieved_chunks": retrieved_chunks,
            "latency_ms": latency_ms,
            "model": "qwen2.5-1.5b-instruct-q4_k_m.gguf",
            "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
            "error": None
        }
    except Exception as e:
        return {
            "status": "DAEMON_CRASH",
            "query_id": request.query_id,
            "target_id": "independent_llama_target",
            "error": str(e)
        }
