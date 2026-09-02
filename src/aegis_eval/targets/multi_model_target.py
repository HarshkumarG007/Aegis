import os
import time
from fastapi import FastAPI
from pydantic import BaseModel
from llama_index.core import VectorStoreIndex, Settings
from llama_index.core.schema import TextNode
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

app = FastAPI()

EVAL_MODEL = os.environ.get("EVAL_MODEL", "unknown-model")
EVAL_PROVIDER = os.environ.get("EVAL_PROVIDER", "mock")
EVAL_TEMPERATURE = float(os.environ.get("EVAL_TEMPERATURE", "0.0"))

print(f"Starting Multi-Model Target: {EVAL_PROVIDER} / {EVAL_MODEL} at T={EVAL_TEMPERATURE}")

# Setup Local Embeddings
Settings.embed_model = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")

# Setup LLM based on provider
if EVAL_PROVIDER == "mock":
    from llama_index.core.llms import MockLLM
    Settings.llm = MockLLM(max_tokens=256)
elif EVAL_PROVIDER == "local":
    from llama_index.llms.llama_cpp import LlamaCPP
    Settings.llm = LlamaCPP(
        model_url=None,
        model_path=os.path.abspath(f"models/{EVAL_MODEL}"),
        temperature=EVAL_TEMPERATURE,
        max_new_tokens=256,
        context_window=2048,
        model_kwargs={"n_gpu_layers": -1},
        verbose=False,
    )
elif EVAL_PROVIDER == "openai":
    from llama_index.llms.openai import OpenAI
    Settings.llm = OpenAI(model=EVAL_MODEL, temperature=EVAL_TEMPERATURE)
elif EVAL_PROVIDER == "anthropic":
    from llama_index.llms.anthropic import Anthropic
    Settings.llm = Anthropic(model=EVAL_MODEL, temperature=EVAL_TEMPERATURE)
elif EVAL_PROVIDER == "gemini":
    from llama_index.llms.gemini import Gemini
    Settings.llm = Gemini(model=EVAL_MODEL, temperature=EVAL_TEMPERATURE)
else:
    raise ValueError(f"Unknown EVAL_PROVIDER: {EVAL_PROVIDER}")

# Same corpus as the independent baseline
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
            "target_id": "multi_model_target",
            "retrieved_chunks": retrieved_chunks,
            "latency_ms": latency_ms,
            "model": EVAL_MODEL,
            "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
            "error": None
        }
    except Exception as e:
        return {
            "status": "DAEMON_CRASH",
            "query_id": request.query_id,
            "target_id": "multi_model_target",
            "model": EVAL_MODEL,
            "error": str(e)
        }
