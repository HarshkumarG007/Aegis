import os
import json
from llama_index.core import VectorStoreIndex, Settings
from llama_index.core.schema import TextNode
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from aegis_eval.hardened_rag.gates import EvidenceGate, PostGenerationVerifier

class HardenedRAGPipeline:
    def __init__(self, llm, corpus: dict, ablation_mode: str = "full"):
        """
        ablation_mode: 'baseline', 'evidence', 'conflict', 'verification', 'full'
        """
        self.llm = llm
        self.corpus = corpus
        self.ablation_mode = ablation_mode
        
        # Setup Retrieval
        Settings.embed_model = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
        nodes = [TextNode(text=text, id_=cid) for cid, text in corpus.items()]
        self.index = VectorStoreIndex(nodes)
        self.retriever = self.index.as_retriever(similarity_top_k=2)
        
        # Setup Gates (lazy load to save memory if not needed by ablation)
        self.evidence_gate = EvidenceGate() if ablation_mode in ['evidence', 'conflict', 'full'] else None
        self.verifier = PostGenerationVerifier() if ablation_mode in ['verification', 'full'] else None
        
    def _retrieve(self, query: str):
        nodes = self.retriever.retrieve(query)
        chunks = []
        for i, node in enumerate(nodes):
            chunks.append({
                "chunk_id": node.node.node_id,
                "text": node.node.text,
                "rank": i + 1,
                "score": node.score
            })
        return chunks
        
    def execute(self, query_id: str, query_text: str) -> dict:
        import time
        start_time = time.time()
        
        chunks = self._retrieve(query_text)
        
        # Default decision trace
        trace = {
            "query_id": query_id,
            "retrieved_chunk_ids": [c['chunk_id'] for c in chunks],
            "gate_state": "SKIPPED",
            "gate_confidence": 0.0,
            "supporting_chunk_ids": [],
            "conflicting_chunk_ids": [],
            "answer": "",
            "verification_state": "SKIPPED",
            "verification_confidence": 0.0,
            "latency_ms": 0
        }
        
        # 1. Evidence / Conflict Gate
        if self.evidence_gate:
            gate_decision = self.evidence_gate.evaluate(query_text, chunks)
            trace["gate_state"] = gate_decision["state"]
            trace["gate_confidence"] = gate_decision["confidence"]
            trace["supporting_chunk_ids"] = gate_decision["supporting_chunks"]
            trace["conflicting_chunk_ids"] = gate_decision["conflicting_chunks"]
            
            # Ablation logic
            if gate_decision["state"] == "INSUFFICIENT":
                if self.ablation_mode in ['evidence', 'full']:
                    trace["answer"] = "I don't know. The retrieved evidence is insufficient to answer the query."
                    trace["latency_ms"] = int((time.time() - start_time) * 1000)
                    return trace
                    
            if gate_decision["state"] == "CONFLICT":
                if self.ablation_mode in ['conflict', 'full']:
                    # Explicit conflict constraint prompt
                    context_str = "\n".join([f"[{c['chunk_id']}] {c['text']}" for c in chunks])
                    prompt = f"Evidence contains conflicting claims. Do not reconcile them unless the evidence provides a basis for doing so. Identify the conflict and state what can and cannot be concluded.\n\nContext:\n{context_str}\n\nQuery: {query_text}\nAnswer:"
                    response = self.llm.complete(prompt)
                    trace["answer"] = str(response)
                    
                    # Verify?
                    if self.verifier:
                        v_dec = self.verifier.verify(trace["answer"], chunks)
                        trace["verification_state"] = v_dec["state"]
                        trace["verification_confidence"] = v_dec["confidence"]
                        if v_dec["state"] == "REJECT":
                            trace["answer"] = "I abstain. The generated answer contained unsupported claims."
                            
                    trace["latency_ms"] = int((time.time() - start_time) * 1000)
                    return trace
        
        # 2. Normal Generation
        context_str = "\n".join([f"[{c['chunk_id']}] {c['text']}" for c in chunks])
        if self.ablation_mode in ['evidence', 'full'] and trace["gate_state"] == "SUFFICIENT":
            # Constrained prompt
            prompt = f"Answer ONLY from the accepted evidence provided below. Do not include external knowledge.\n\nContext:\n{context_str}\n\nQuery: {query_text}\nAnswer:"
        else:
            # Baseline prompt
            prompt = f"Context information is below.\n---------------------\n{context_str}\n---------------------\nGiven the context information and not prior knowledge, answer the query.\nQuery: {query_text}\nAnswer: "
            
        response = self.llm.complete(prompt)
        trace["answer"] = str(response)
        
        # 3. Post-generation Verification
        if self.verifier:
            v_dec = self.verifier.verify(trace["answer"], chunks)
            trace["verification_state"] = v_dec["state"]
            trace["verification_confidence"] = v_dec["confidence"]
            
            if v_dec["state"] == "REJECT":
                trace["answer"] = "I abstain. The generated answer contained unsupported claims."
                
        trace["latency_ms"] = int((time.time() - start_time) * 1000)
        return trace
