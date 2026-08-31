class IntegrationError(Exception):
    """Raised when a target RAG fails the integration contract."""
    pass

def validate_target_contract(response: dict) -> None:
    """
    Validates that a target RAG's response meets the Aegis-Eval integration contract.
    The contract requires that the target returns 'retrieved_chunk_ids' in its response.
    """
    if not response.get("retrieved_chunk_ids"):
        raise IntegrationError(
            "Target RAG did not return retrieved_chunk_ids. "
            "Aegis-Eval cannot evaluate a black-box system with no retrieval evidence."
        )
