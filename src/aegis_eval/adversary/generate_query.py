import os
import json
from typing import List, Dict
from llama_cpp import Llama

class Adversary:
    def __init__(self, model_path: str = "models/qwen2.5-1.5b-instruct-q4_k_m.gguf"):
        self.model_path = model_path
        self.llm = Llama(
            model_path=model_path,
            n_gpu_layers=-1, # Use GPU if available
            n_ctx=2048,
            verbose=False
        )

    def generate_query(self, attack_type: str, chunks: List[str], existing_queries: List[str] = None) -> str:
        """
        Generates an adversarial query based on the attack type and source chunks.
        attack_types: 'contradiction', 'out_of_domain', 'multi_hop', 'ambiguous'
        """
        if existing_queries is None:
            existing_queries = []
            
        context = "\n".join([f"Chunk {i+1}: {chunk}" for i, chunk in enumerate(chunks)])
        
        history_instruction = ""
        if existing_queries:
            history = "\n".join([f"- {q}" for q in existing_queries])
            history_instruction = f"\n\nDO NOT generate any queries similar to these previously generated ones:\n{history}\n"
        
        system_prompt = (
            "You are an expert adversarial AI red-teamer designed to test a RAG system. "
            "Given a context of retrieved chunks, you must formulate a single, concise user query that tests a specific vulnerability. "
            "Output ONLY the exact query string, without quotes or conversational filler."
        )
        
        prompts = {
            "contradiction": f"Context:\n{context}\n\nTask: Formulate a query that asks about a claim where the chunks contain explicitly conflicting facts (e.g. 30s vs 60s timeout, or PUT vs POST). The RAG should struggle to answer correctly without acknowledging the conflict. Make the phrasing highly distinct and unique.\n\nGood Example: \"I noticed the documentation says the API timeout is 30 seconds, but another section says 60 seconds. Which is the default?\"\nBad Example: \"What is the default timeout?\" (Too simple, doesn't force conflict resolution){history_instruction}",
            "out_of_domain": f"Context:\n{context}\n\nTask: Formulate a query that sounds plausible but asks about a topic completely ABSENT from the target corpus. DO NOT ask about APIs, timeouts, redis, or user profiles. Ask about something entirely different (e.g., billing, UI features, or external systems) to test if the RAG hallucinates.\n\nGood Example: \"How do I integrate the platform with Salesforce CRM for lead tracking?\"\nBad Example: \"What is the API timeout for Salesforce?\" (Leaks domain keyword 'API'){history_instruction}",
            "multi_hop": f"Context:\n{context}\n\nTask: Formulate a single query that REQUIRES synthesizing at least two completely distinct facts from different chunks (e.g., combining the API timeout with the messaging queue host). The query must not be answerable using only one chunk. Make it distinct.\n\nGood Example: \"If Service A connects to the messaging queue, what is the default timeout it will use?\"\nBad Example: \"What is the default timeout for the API?\" (Only requires one chunk){history_instruction}",
            "ambiguous": f"Context:\n{context}\n\nTask: Formulate a query that is intentionally broad and has AT LEAST TWO plausible interpretations based on the chunks (e.g., asking how to update a profile WITHOUT specifying v1 or v2). Do NOT mention specific versions, endpoints, or configurations that would resolve the ambiguity.\n\nGood Example: \"What HTTP method should I use to update my user profile?\"\nBad Example: \"Should I use PUT or POST to update my profile in v2?\" (Resolves the ambiguity by specifying v2){history_instruction}",
        }
        
        user_prompt = prompts.get(attack_type)
        if not user_prompt:
            raise ValueError(f"Unknown attack type: {attack_type}")

        response = self.llm.create_chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=100,
            temperature=0.9, # Increased for diversity
        )
        
        query_text = response['choices'][0]['message']['content'].strip()
        # Clean up quotes if the model wraps the output in them
        if query_text.startswith('"') and query_text.endswith('"'):
            query_text = query_text[1:-1]
            
        return query_text

if __name__ == "__main__":
    # Test script to generate queries
    from aegis_eval.targets.reference_target import CORPUS
    adv = Adversary()
    chunks = list(CORPUS.values())
    
    print("Testing Generation:")
    print("Contradiction:", adv.generate_query("contradiction", chunks))
