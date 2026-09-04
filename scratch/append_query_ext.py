import os

with open('src/aegis_eval/hardened_rag/condition_extractor.py', 'a') as f:
    f.write('''

class QueryExtractor:
    def __init__(self, llm=None):
        self.llm = llm
        
    def extract_ir(self, query: str) -> dict:
        if not self.llm:
            return {"raw_text": query, "status": "failed_extraction"}
            
        prompt = f"""Extract the structural constraints of the following query into JSON.
Identify the subject, predicate, object, conditions, and type (boolean, comparative_attribute, conjunction_demand, etc).
Query: "{query}"
JSON:"""
        try:
            response = self.llm.complete(prompt).text
            if "{" in response:
                j_str = response[response.find("{"):response.rfind("}")+1]
                return __import__('json').loads(j_str)
        except Exception:
            pass
        return {"raw_text": query, "status": "failed_extraction"}
''')
