import uuid
from typing import List, Dict, Any

# Intentionally inconsistent and ambiguous corpus for testing Aegis-Eval
CORPUS = {
    "chunk-001": "The default timeout for the v1 API is 30 seconds.",
    "chunk-002": "API requests will time out after 60 seconds by default in the new configuration.",
    "chunk-003": "Service A connects to the messaging queue.",
    "chunk-004": "The messaging queue is hosted on redis-01.",
    "chunk-005": "The user profile can be updated via the PUT /user endpoint.",
    "chunk-006": "The PUT /user endpoint is deprecated in v2, use POST /user/update.",
    "chunk-007": "All database passwords must be rotated every 90 days."
}

class ReferenceTarget:
    """
    A purpose-built reference RAG target over a corpus chosen to exercise
    all four attack types (contradiction, out-of_domain, multi_hop, ambiguous).
    """

    def __init__(self):
        self.corpus = CORPUS
        self.call_counts = {
            "ambiguous": 0,
            "contradiction": 0,
            "out_of_domain": 0,
            "multi_hop": 0,
            "safe_infrastructure": 0,
            "mixed": 0
        }

    def retrieve(self, query: str, attack_type: str = None) -> List[str]:
        """
        Mock retrieval logic. In a real RAG, this would use embeddings.
        For the reference target, we return hardcoded chunks based on keywords
        to ensure the specific adversarial conditions are met for testing.
        """
        if attack_type == "contradiction":
            return ["chunk-001", "chunk-002"]
        if attack_type == "multi_hop":
            return ["chunk-003", "chunk-004"]
        if attack_type == "ambiguous":
            return ["chunk-005", "chunk-006"]
        if attack_type == "out_of_domain":
            return ["chunk-007"]
            
        return ["chunk-001"]

    def generate_answer(self, query: str, retrieved_chunk_ids: List[str], attack_type: str = None) -> str:
        """
        Mock generation logic. We return a string that intentionally fails 
        certain evaluation checks if not properly handled.
        """
        if attack_type is not None:
            self.call_counts[attack_type] += 1
            count = self.call_counts[attack_type]
        else:
            count = 1
        
        if attack_type == "contradiction":
            if count <= 9:
                return "The API timeout is exactly 30 seconds." # Contradiction (Fail)
            return "The timeout is 30 seconds for v1 and 60 seconds for the new configuration." # Good (Pass)
            
        elif attack_type == "ambiguous":
            if count <= 5:
                return "You can update the user profile via the PUT /user endpoint." # Commits (Fail)
            return "It depends on the version. Use PUT for v1 or POST for v2." # Acknowledges (Pass)
            
        elif attack_type == "multi_hop":
            if count <= 5:
                return "Service A connects to the API." # Uses 1 chunk (Fail)
            return "Service A connects to the messaging queue hosted on redis-01." # Synthesizes (Pass)
            
        elif attack_type == "out_of_domain":
            if count <= 5:
                return "The UI uses a dark mode." # Ungrounded (Fail)
            return "I am not sure." # Hedging (Pass)
            
        return "I am not sure."

    def query(self, query: str, attack_type: str = None) -> Dict[str, Any]:
        """
        The main endpoint for the RAG target.
        Satisfies the Integration Contract by returning retrieved_chunk_ids.
        """
        chunks = self.retrieve(query, attack_type)
        answer = self.generate_answer(query, chunks, attack_type)
        
        return {
            "answer_text": answer,
            "retrieved_chunk_ids": chunks
        }
