import re

class AmbiguityEvaluator:
    def __init__(self):
        self.markers = [
            r"it depends", r"could refer to", r"multiple", r"\beither\b", r"\bor\b", 
            r"\bboth\b", r"clarify", r"specify", r"which version", r"\bv1\b", r"\bv2\b", 
            r"however", r"on the other hand", r"\balternatively\b", r"two methods",
            r"\bversus\b", r"\bvs\b"
        ]
        
    def evaluate(self, query: str, answer: str, retrieved_chunks: list[str]) -> tuple[bool, str]:
        ans_lower = answer.lower()
        
        if "?" in answer:
            return True, "Passed (asked clarifying question)"
            
        matches = [m for m in self.markers if re.search(m, ans_lower)]
        if matches:
            return True, f"Passed (acknowledged ambiguity via markers: {matches})"
            
        return False, "Failed to acknowledge ambiguity (committed to single interpretation)"
