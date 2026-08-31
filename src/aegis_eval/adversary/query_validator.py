import re
from typing import List, Dict, Set
from sentence_transformers import SentenceTransformer, util

class QueryValidator:
    def __init__(self):
        # We can use the same small embedding model used for NLI, or a generic one
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.domain_keywords = {"api", "timeout", "update", "profile", "put", "post", "redis-01", "service a", "messaging queue", "database", "password"}
        
    def check_exact_duplicates(self, queries: List[str]) -> bool:
        return len(queries) != len(set(queries))
        
    def get_max_similarity(self, new_query: str, existing_queries: List[str]) -> float:
        if not existing_queries:
            return 0.0
        
        embeddings1 = self.model.encode([new_query])
        embeddings2 = self.model.encode(existing_queries)
        cosine_scores = util.cos_sim(embeddings1, embeddings2)
        return float(cosine_scores.max())

    def validate_out_of_domain(self, query: str) -> bool:
        """Returns True if valid OOD (i.e. does NOT contain domain keywords)."""
        query_lower = query.lower()
        # If it has too many domain keywords, it's not truly out of domain.
        match_count = sum(1 for kw in self.domain_keywords if kw in query_lower)
        return match_count <= 1  # Tolerate at most 1 generic keyword like "api"

    def validate_multi_hop(self, query: str) -> bool:
        """Returns True if query contains keywords from at least two distinct topics."""
        query_lower = query.lower()
        topics_hit = 0
        if "timeout" in query_lower or "seconds" in query_lower:
            topics_hit += 1
        if "service a" in query_lower or "messaging" in query_lower or "redis" in query_lower:
            topics_hit += 1
        if "profile" in query_lower or "update" in query_lower or "put" in query_lower:
            topics_hit += 1
        if "password" in query_lower or "database" in query_lower:
            topics_hit += 1
            
        return topics_hit >= 2

    def validate_ambiguous(self, query: str) -> bool:
        """Returns True if the query is ambiguous (doesn't specify the version)."""
        query_lower = query.lower()
        if "v1" in query_lower or "v2" in query_lower or "new configuration" in query_lower or "current configuration" in query_lower:
            return False # Specifying version removes ambiguity
        return True
