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
# Ensure the path points to the correct location in models/
model_path = os.path.abspath("models/qwen2.5-1.5b-instruct-q4_k_m.gguf")
llm = LlamaCPP(
    model_url=None,
    model_path=model_path,
    temperature=0.1,
    max_new_tokens=256,
    context_window=2048,
    generate_kwargs={},
    model_kwargs={"n_gpu_layers": 0}, # using CPU to guarantee it runs without cuBLAS issues on arbitrary machines
    verbose=False,
)
Settings.llm = llm

# Load documents
documents = SimpleDirectoryReader("./data/corpus").load_data()
parser = SentenceSplitter(chunk_size=128, chunk_overlap=0)
nodes = parser.get_nodes_from_documents(documents)

index = VectorStoreIndex(nodes)
query_engine = index.as_query_engine(similarity_top_k=2)

class QueryRequest(BaseModel):
    query: str

@app.post("/query")
def query_target(request: QueryRequest):
    response = query_engine.query(request.query)
    
    retrieved_chunks = [node.node.get_content() for node in response.source_nodes]
    
    return {
        "answer_text": str(response),
        "retrieved_chunks": retrieved_chunks
    }
