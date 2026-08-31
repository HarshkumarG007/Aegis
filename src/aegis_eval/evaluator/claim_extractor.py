import json
from typing import List
from llama_cpp import Llama

class ClaimExtractor:
    def __init__(self, model_path: str = "models/qwen2.5-1.5b-instruct-q4_k_m.gguf"):
        self.llm = Llama(
            model_path=model_path,
            n_gpu_layers=0,  # 0 for CPU inference on standard environment, or -1 if GPU
            n_ctx=2048,
            verbose=False
        )

    def extract_claims(self, text: str) -> List[str]:
        if not text or not text.strip():
            return []
            
        system_prompt = (
            "You are an expert fact-extractor. Given an answer text, extract all distinct, verifiable atomic factual claims. "
            "Split complex sentences into multiple simple claims. Resolve pronouns to their referents. "
            "Output ONLY a valid JSON array of strings, with no other text, commentary, or markdown blocks."
        )
        
        user_prompt = f"Text to extract claims from:\n{text}"
        
        response = self.llm.create_chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=500,
            temperature=0.1,
            # Force JSON array output format structure if possible
            response_format={"type": "json_object"} if hasattr(self.llm, "create_chat_completion") else None
        )
        
        raw_output = response['choices'][0]['message']['content'].strip()
        
        # Clean up in case model wrapped it in markdown json block
        if raw_output.startswith("```json"):
            raw_output = raw_output[7:]
        if raw_output.endswith("```"):
            raw_output = raw_output[:-3]
        raw_output = raw_output.strip()
        
        try:
            claims = json.loads(raw_output)
            if isinstance(claims, list):
                return [str(c) for c in claims]
            elif isinstance(claims, dict) and "claims" in claims:
                return [str(c) for c in claims["claims"]]
            return []
        except json.JSONDecodeError:
            # Fallback parsing if JSON fails (split by newline if it returned a list)
            lines = raw_output.split("\n")
            cleaned = []
            for line in lines:
                line = line.strip()
                if line.startswith("-") or line.startswith("*"):
                    cleaned.append(line[1:].strip())
                elif line:
                    cleaned.append(line)
            return cleaned
