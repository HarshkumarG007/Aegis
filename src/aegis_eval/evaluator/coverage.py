from sentence_transformers import SentenceTransformer, util

class CoverageEvaluator:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
    def evaluate(self, query: str, answer: str, retrieved_chunks: list[str]) -> tuple[bool, str]:
        if not retrieved_chunks:
            return False, "No chunks provided"
            
        ans_emb = self.model.encode([answer])
        chunk_embs = self.model.encode(retrieved_chunks)
        scores = util.cos_sim(ans_emb, chunk_embs)[0]
        
        # Count chunks that have meaningful similarity to the answer
        # Raised threshold to 0.5 to avoid false positives on loosely related sentences
        supported_chunks = sum(1 for s in scores if float(s) > 0.5)
        
        if supported_chunks >= 2:
            return True, f"Synthesized {supported_chunks} chunks"
        
        return False, f"Failed to synthesize multiple chunks (only {supported_chunks} hit threshold)"
