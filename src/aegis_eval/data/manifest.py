import hashlib
import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class BenchmarkManifest(BaseModel):
    benchmark_version: str = "2.0"
    query_set: str
    query_set_sha256: str
    corpus_sha256: str
    models: str
    embedding_model: str
    evaluator_version: str
    code_revision: str
    random_seed: int
    retrieval_config: Dict[str, Any]
    thresholds: Dict[str, Any]

    def get_canonical_json(self) -> str:
        """Returns a deterministic JSON representation of the manifest."""
        # Dump model to dict, then to json with sorted keys for determinism
        data = self.model_dump()
        return json.dumps(data, sort_keys=True, separators=(",", ":"))

    def compute_sha256(self) -> str:
        """Computes the SHA-256 hash of the canonical manifest."""
        canonical_json = self.get_canonical_json()
        return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
