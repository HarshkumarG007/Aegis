import os
import json
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))
from llama_index.llms.llama_cpp import LlamaCPP
from llama_index.core.schema import TextNode
from llama_index.core import VectorStoreIndex, Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from aegis_eval.hardened_rag.gates import EvidenceGate

def load_corpus():
    return {
        "chunk-001": "The database password must be rotated every 90 days. Failure to do so will result in an automatic lock.",
        "chunk-002": "Service A connects to the messaging queue to broadcast events.",
        "chunk-003": "The messaging queue is hosted on redis-01.internal.corp.",
        "chunk-004": "The new API configuration requires all requests to complete within 60 seconds or they will time out.",
        "chunk-005": "In the v1 API, the timeout limit is strictly set to 30 seconds for all endpoints.",
        "chunk-006": "The PUT /user endpoint is deprecated in v2. Please use POST /user/update instead.",
        "chunk-007": "The PUT /user endpoint is still available for legacy applications."
    }

def get_g0_prompt(context_str, query_str, gate_state):
    if gate_state == "CONDITIONAL_COMPATIBILITY":
        return f"The provided evidence contains claims that are conditionally compatible. You MUST explicitly state the conditions (e.g. version, scope, time) under which each claim holds. Do not attempt to merge them into a single unconditional statement.\n\nContext:\n{context_str}\n\nQuery: {query_str}\nAnswer:"
    else:
        return f"Answer ONLY from the accepted evidence provided below. Do not include external knowledge.\n\nContext:\n{context_str}\n\nQuery: {query_str}\nAnswer:"

def get_g1_prompt(context_str, query_str, gate_state):
    base_prompt = get_g0_prompt(context_str, query_str, gate_state)
    instruction = "\n\nCRITICAL INSTRUCTION: Do NOT abstain or claim the information is insufficient if the context provides different answers based on specific conditions (such as version, environment, role, or date). You must synthesize all valid conditionally applicable answers."
    # Insert instruction before the final "Answer:"
    idx = base_prompt.rfind("Answer:")
    return base_prompt[:idx] + instruction + "\n" + base_prompt[idx:]

def check_abstention(answer):
    lower_ans = answer.lower()
    abstain_phrases = ["i don't know", "i cannot answer", "i abstain", "insufficient evidence", "does not contain"]
    for phrase in abstain_phrases:
        if phrase in lower_ans:
            return True
    if len(answer.strip()) < 10:
        return True
    return False

def run_v3_generator_diagnostic():
    with open("reports/benchmark-v2.5/adversarial-v2.5-challenge.json", "r") as f:
        dev_queries = json.load(f)
        
    corpus = load_corpus()
    Settings.embed_model = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
    nodes = [TextNode(text=text, id_=cid) for cid, text in corpus.items()]
    index = VectorStoreIndex(nodes)
    retriever = index.as_retriever(similarity_top_k=2)
    
    gate = EvidenceGate(use_v2_5_sufficiency=True, conflict_classifier="E", extractor_mode="E0")
    
    print("Loading Mistral-7B Generator...")
    llm = LlamaCPP(
        model_url=None,
        model_path=os.path.abspath("models/mistral-7b-instruct-v0.2.Q4_K_M.gguf"),
        temperature=0.0,
        max_new_tokens=256,
        context_window=4096,
        model_kwargs={"n_gpu_layers": -1},
        verbose=False,
    )
    
    print("\nEvaluating G0 vs G1 on the admitted queries (Threshold 4.25)...\n")
    
    g0_abstentions = 0
    g1_abstentions = 0
    total_admitted = 0
    
    for q in dev_queries:
        if "out" in q["id"]: continue
        
        qtext = q["text"]
        nodes_2 = retriever.retrieve(qtext)
        chunks = [{"chunk_id": n.node.node_id, "text": n.node.text} for n in nodes_2]
        
        gate_res = gate.evaluate(qtext, chunks, sufficiency_threshold=4.25)
        
        if gate_res["state"] in ["SUFFICIENT", "CONDITIONAL_COMPATIBILITY"]:
            total_admitted += 1
            context_str = "\n".join([f"[{c['chunk_id']}] {c['text']}" for c in chunks])
            
            p0 = get_g0_prompt(context_str, qtext, gate_res["state"])
            p1 = get_g1_prompt(context_str, qtext, gate_res["state"])
            
            ans0 = str(llm.complete(p0))
            ans1 = str(llm.complete(p1))
            
            is_abs0 = check_abstention(ans0)
            is_abs1 = check_abstention(ans1)
            
            if is_abs0: g0_abstentions += 1
            if is_abs1: g1_abstentions += 1
            
            if is_abs0 and not is_abs1:
                print(f"✅ RECOVERED [{q['id']}]: {qtext}")
                print(f"  G0 (Abstained): {ans0}")
                print(f"  G1 (Answered) : {ans1}\n")
            elif is_abs0 and is_abs1:
                print(f"❌ STILL ABSTAINED [{q['id']}]: {qtext}")
            elif not is_abs0 and not is_abs1:
                pass # Both answered correctly
                
    print(f"\n--- Generator Abstention Summary ---")
    print(f"Total Admitted: {total_admitted}")
    print(f"G0 Abstentions: {g0_abstentions} ({g0_abstentions/total_admitted:.0%})")
    print(f"G1 Abstentions: {g1_abstentions} ({g1_abstentions/total_admitted:.0%})")

if __name__ == "__main__":
    run_v3_generator_diagnostic()
