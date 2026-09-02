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
            "proposition": text,
            "condition_spans": [],
            "conditions": {
                "version": None,
                "time": None,
                "scope": None,
                "role": None,
                "environment": None,
                "lifecycle": None,
                "explicit": False
            }
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
            result["condition_spans"].append(condition_span)
        elif suffix_match:
            condition_span = f"{suffix_match.group(2)} {suffix_match.group(3)}"
            prop_text = suffix_match.group(1)
            condition_text = condition_span
            result["condition_spans"].append(condition_span)
        elif text_lower.startswith("currently, "):
            condition_span = "Currently,"
            prop_text = text[len("Currently, "):]
            condition_text = condition_span
            result["condition_spans"].append(condition_span)
        elif text_lower.startswith("formerly, "):
            condition_span = "Formerly,"
            prop_text = text[len("Formerly, "):]
            condition_text = condition_span
            result["condition_spans"].append(condition_span)
            
        if condition_text:
            cond_lower = condition_text.lower()
            
            # Version
            ver_match = re.search(r'\b(v\d+|version \d+(?:\.\d+)?)\b', cond_lower)
            if ver_match:
                result["conditions"]["version"] = ver_match.group(1)
                result["conditions"]["explicit"] = True
                
            # Time
            time_match = re.search(r'\b(before \d{4}|after \d{4}|since \d{4}|\d+ am|\d+ pm|currently|formerly|presently)\b', cond_lower)
            if time_match:
                result["conditions"]["time"] = time_match.group(1)
                result["conditions"]["explicit"] = True
                
            # Scope / Lifecycle
            if "legacy" in cond_lower or "deprecated" in cond_lower:
                result["conditions"]["lifecycle"] = "legacy"
                result["conditions"]["explicit"] = True
                
            # Role
            role_match = re.search(r'\b(administrator|admin|guest|user)\b', cond_lower)
            if role_match:
                result["conditions"]["role"] = role_match.group(1)
                result["conditions"]["explicit"] = True
                
            # Environment
            env_match = re.search(r'\b(staging|production|prod|dev|test)\b', cond_lower)
            if env_match:
                result["conditions"]["environment"] = env_match.group(1)
                result["conditions"]["explicit"] = True

        result["proposition"] = prop_text.strip()
        
        # If no syntactic clause was found but keywords exist in the text, we fail closed (ambiguous)
        if not result["conditions"]["explicit"]:
            # Check if keywords exist anyway
            kw_match = re.search(r'\b(v\d+|version \d+|legacy|admin|guest|staging|prod|dev|currently|formerly)\b', text_lower)
            if kw_match:
                result["ambiguous"] = True # keyword found but no syntactic clause
            else:
                result["ambiguous"] = False
        else:
            result["ambiguous"] = False
            
        return result

    def _extract_e1(self, text: str) -> dict:
        if not self.llm:
            return self._extract_e0(text)
            
        prompt = f"""You are a strict Information Extraction system.
Extract any explicitly stated conditions from the text into the following JSON schema.
Do NOT infer conditions. Only extract what is explicitly written.
If a field is not explicitly present, set it to null.
If ANY condition is extracted, set "explicit" to true. Otherwise, false.

Schema:
{{
  "version": "string or null",
  "time": "string or null",
  "scope": "string or null",
  "role": "string or null",
  "environment": "string or null",
  "lifecycle": "string or null",
  "explicit": boolean
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
                "version": data.get("version"),
                "time": data.get("time"),
                "scope": data.get("scope"),
                "role": data.get("role"),
                "environment": data.get("environment"),
                "lifecycle": data.get("lifecycle"),
                "explicit": data.get("explicit", False)
            }
            
            # Ensure "explicit" is accurate based on extracted fields
            has_any = any(v is not None for k, v in validated.items() if k != "explicit")
            validated["explicit"] = has_any
            
            return validated
            
        except Exception as e:
            # Fallback to E0 if LLM fails (malformed JSON, etc)
            print(f"[E1 Extractor Error] Falling back to E0: {e}")
            return self._extract_e0(text)
