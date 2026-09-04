import re
import json

class ConditionExtractor:
    def __init__(self, llm=None, mode="E0"):
        """
        mode: "E0" for Rule-based regex, "E1" for LLM-based JSON extraction
        """
        self.mode = mode
        self.llm = llm
        
    def extract(self, text: str) -> dict:
        if self.mode == "E0":
            return self._extract_e0(text)
        elif self.mode == "E1":
            return self._extract_e1(text)
        else:
            raise ValueError("Invalid mode. Use 'E0' or 'E1'.")

    def _extract_e0(self, text: str) -> dict:
        text_lower = text.lower().strip()
        result = {
            "status": "NONE",
            "proposition": text,
            "conditions": {
                "version": [],
                "role": [],
                "scope": [],
                "environment": [],
                "temporal": []
            },
            "spans": []
        }
        
        # Syntactic clause patterns
        # 1. Prefix condition: "In v1, " or "For legacy users, "
        # 2. Suffix condition: " ... in v1."
        prefix_pattern = re.compile(r'^(in|for|before|after|when|if|currently|formerly)\s+([^,]+),\s*(.*)', re.IGNORECASE)
        suffix_pattern = re.compile(r'^(.*?)\s+(in|for|before|after|when|if)\s+([^.]+)\.?$', re.IGNORECASE)
        
        prop_text = text
        condition_text = ""
        
        prefix_match = prefix_pattern.match(text)
        suffix_match = suffix_pattern.match(text)
        
        if prefix_match:
            condition_span = f"{prefix_match.group(1)} {prefix_match.group(2)},"
            prop_text = prefix_match.group(3)
            condition_text = condition_span
            result["spans"].append(condition_span)
        elif suffix_match:
            condition_span = f"{suffix_match.group(2)} {suffix_match.group(3)}"
            prop_text = suffix_match.group(1)
            condition_text = condition_span
            result["spans"].append(condition_span)
        elif text_lower.startswith("currently, "):
            condition_span = "Currently,"
            prop_text = text[len("Currently, "):]
            condition_text = condition_span
            result["spans"].append(condition_span)
        elif text_lower.startswith("formerly, "):
            condition_span = "Formerly,"
            prop_text = text[len("Formerly, "):]
            condition_text = condition_span
            result["spans"].append(condition_span)
            
        if condition_text:
            cond_lower = condition_text.lower()
            
            # Version
            ver_match = re.search(r'\b(v\d+|version \d+(?:\.\d+)?)\b', cond_lower)
            if ver_match:
                result["conditions"]["version"].append(ver_match.group(1))
                result["status"] = "EXPLICIT"
                
            # Temporal
            time_match = re.search(r'\b(before \d{4}|after \d{4}|since \d{4}|\d+ am|\d+ pm|currently|formerly|presently)\b', cond_lower)
            if time_match:
                result["conditions"]["temporal"].append(time_match.group(1))
                result["status"] = "EXPLICIT"
                
            # Scope
            if "legacy" in cond_lower or "deprecated" in cond_lower:
                result["conditions"]["scope"].append("legacy")
                result["status"] = "EXPLICIT"
                
            # Role
            role_match = re.search(r'\b(administrator|admin|guest|user)\b', cond_lower)
            if role_match:
                result["conditions"]["role"].append(role_match.group(1))
                result["status"] = "EXPLICIT"
                
            # Environment
            env_match = re.search(r'\b(staging|production|prod|dev|test)\b', cond_lower)
            if env_match:
                result["conditions"]["environment"].append(env_match.group(1))
                result["status"] = "EXPLICIT"

        result["proposition"] = prop_text.strip()
        
        # If no syntactic clause was found but keywords exist in the text, we fail closed (ambiguous)
        if result["status"] == "NONE":
            # Check if keywords exist anyway
            kw_match = re.search(r'\b(v\d+|version \d+|legacy|admin|guest|staging|prod|dev|currently|formerly)\b', text_lower)
            if kw_match:
                result["status"] = "AMBIGUOUS" # keyword found but no syntactic clause
            
        return result

    def _extract_e1(self, text: str) -> dict:
        if not self.llm:
            return self._extract_e0(text)
            
        prompt = f"""You are a strict Information Extraction system.
Extract any explicitly stated conditions from the text into the following JSON schema.
Do NOT infer conditions. Only extract what is explicitly written.
Extract values as arrays of strings. If a field is not explicitly present, set it to an empty array.
If ANY condition is extracted, set "status" to "EXPLICIT". Otherwise, set to "NONE". (Use "AMBIGUOUS" if unclear).

Schema:
{{
  "status": "EXPLICIT | NONE | AMBIGUOUS",
  "proposition": "string (the core statement without conditions)",
  "conditions": {{
      "version": ["string"],
      "temporal": ["string"],
      "scope": ["string"],
      "role": ["string"],
      "environment": ["string"]
  }},
  "spans": ["string (exact substrings representing conditions)"]
}}

Text: "{text}"

Output strictly valid JSON:"""
        try:
            # We assume self.llm has a complete method (LlamaIndex LLM)
            response = self.llm.complete(prompt).text
            
            # Clean JSON block
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
                
            data = json.loads(response)
            
            # Validation
            validated = {
                "status": data.get("status", "NONE"),
                "proposition": data.get("proposition", text),
                "conditions": {
                    "version": data.get("conditions", {}).get("version", []),
                    "temporal": data.get("conditions", {}).get("temporal", []),
                    "scope": data.get("conditions", {}).get("scope", []),
                    "role": data.get("conditions", {}).get("role", []),
                    "environment": data.get("conditions", {}).get("environment", [])
                },
                "spans": data.get("spans", [])
            }
            
            return validated
            
        except Exception as e:
            # Fallback to E0 if LLM fails (malformed JSON, etc)
            print(f"[E1 Extractor Error] Falling back to E0: {e}")
            return self._extract_e0(text)


class QueryExtractor:
    def __init__(self, llm=None):
        self.llm = llm
        
    def extract_ir(self, query: str) -> dict:
        if not self.llm:
            return {"raw_text": query, "status": "failed_extraction"}
            
        prompt = f"""You are a strict query constraint extractor.
Extract all structural, conditional, and comparative constraints from the query.
Output a JSON object with exactly two fields:
- "status": "EXPLICIT" if there are constraints, "NONE" if unconditional, or "AMBIGUOUS" if unclear.
- "constraints": a list of string statements that MUST be true for an answer to fully address the query's constraints. (e.g. ["The answer must specify if this applies ONLY when CPU hits 80%", "The answer must compare Version A and Version B"])

Query: "{query}"
JSON:"""
        try:
            response = self.llm.complete(prompt).text
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "{" in response:
                response = response[response.find("{"):response.rfind("}")+1]
            data = __import__('json').loads(response)
            if "status" not in data:
                data["status"] = "failed_extraction"
            return data
        except Exception:
            pass
        return {"raw_text": query, "status": "failed_extraction"}
