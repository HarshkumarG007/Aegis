import re
from sentence_transformers import SentenceTransformer, util

class GroundednessEvaluator:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.abstain_phrases = [
            "i don't know", "not mentioned", "cannot answer", 
            "no information", "does not contain", "is not provided",
            "i am sorry", "i cannot", "not sure"
        ]
        
    def evaluate(self, query: str, answer: str, retrieved_chunks: list[str]) -> tuple[bool, str]:
        ans_lower = answer.lower()
        for p in self.abstain_phrases:
            if p in ans_lower:
                return True, "Passed via abstention"
                
        if not retrieved_chunks:
            return False, "Ungrounded (no chunks)"
            
        # Split answer into sentences
        sentences = [s.strip() for s in re.split(r'[.!?]', answer) if len(s.strip()) > 10]
        if not sentences:
            sentences = [answer]
            
        chunk_embeddings = self.model.encode(retrieved_chunks)
        
        for sent in sentences:
            sent_emb = self.model.encode([sent])
            scores = util.cos_sim(sent_emb, chunk_embeddings)
            max_score = float(scores.max())
            
            # If the sentence has very low similarity to all chunks, it is ungrounded
            if max_score < 0.35: 
                return False, f"Ungrounded claim: '{sent}' (max sim: {max_score:.2f})"
                
        return True, "All claims grounded"
