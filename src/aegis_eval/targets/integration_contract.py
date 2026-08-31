from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, ValidationError

class IntegrationError(Exception):
    """Raised when a target RAG fails the integration contract."""
    pass

class TargetStatus(str, Enum):
    SUCCESS = "SUCCESS"
    TIMEOUT = "TIMEOUT"
    HTTP_ERROR = "HTTP_ERROR"
    DAEMON_CRASH = "DAEMON_CRASH"
    MALFORMED = "MALFORMED"

class RetrievedChunk(BaseModel):
    chunk_id: str
    rank: int
    score: Optional[float] = None
    text_hash: Optional[str] = None

class AegisTargetResponse(BaseModel):
    status: TargetStatus
    answer: Optional[str] = None
    query_id: str
    target_id: str
    retrieved_chunks: List[RetrievedChunk] = Field(default_factory=list)
    latency_ms: Optional[int] = None
    model: Optional[str] = None
    embedding_model: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

def validate_target_contract(response: dict) -> AegisTargetResponse:
    """
    Validates that a target RAG's response meets the Aegis-Eval V2 integration contract.
    Returns the parsed AegisTargetResponse model if valid.
    """
    try:
        parsed_response = AegisTargetResponse(**response)
        
        if parsed_response.status == TargetStatus.SUCCESS:
            if not parsed_response.retrieved_chunks:
                raise IntegrationError("Target RAG returned SUCCESS but no retrieved_chunks.")
                
        return parsed_response
        
    except ValidationError as e:
        # If it completely fails structural validation, it's malformed
        raise IntegrationError(f"Target RAG returned malformed response: {e}")
