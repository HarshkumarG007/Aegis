from sentence_transformers import CrossEncoder

class NLIContradictionEvaluator:
    def __init__(self):
        # cross-encoder/nli-deberta-v3-small outputs: 0: contradiction, 1: entailment, 2: neutral
        self.model = CrossEncoder('cross-encoder/nli-deberta-v3-small')
        
    def evaluate(self, query: str, answer: str, retrieved_chunks: list[str]) -> tuple[bool, str]:
        if not retrieved_chunks:
            return False, "No chunks provided"
            
        # We check if the chunk contradicts the answer.
        # For each chunk, pair = (chunk, answer)
        pairs = [[chunk, answer] for chunk in retrieved_chunks]
        scores = self.model.predict(pairs)
        
        for i, score in enumerate(scores):
            # score is array of 3 probabilities (or logits)
            # Find the max label
            pred_label = score.argmax()
            if pred_label == 0: # Contradiction
                return False, f"Contradicts chunk {i+1}"
                
        return True, "No contradictions found"
