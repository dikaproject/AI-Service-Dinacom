from dataclasses import dataclass
from typing import Dict, List
import json

@dataclass
class Diagnosis:
    symptoms: List[str]
    possible_conditions: List[str]
    severity: int
    recommendations: List[str]

class KnowledgeBase:
    def __init__(self, lang: str = 'en', serpapi_key: str = None):
        self.lang = lang
        self.serpapi_key = serpapi_key
        self.symptoms = {}
        self.conditions = {}
    
    def add_symptom(self, id: str, data: Dict):
        self.symptoms[id] = data

    def add_condition(self, id: str, data: Dict):
        self.conditions[id] = data
        
    async def get_medical_info(self, query: str) -> Dict:
        """Get medical information from SerpAPI"""
        if not self.serpapi_key:
            print("Warning: No SERPAPI key provided")
            return {}
            
        try:
            from serpapi import GoogleSearch
            search = GoogleSearch({
                "q": f"{query} kehamilan gejala",
                "api_key": self.serpapi_key,
                "gl": "id",
                "hl": "id",
                "num": 5  # Limit results
            })
            
            results = search.get_dict()
            if "error" in results:
                print(f"SERPAPI error: {results['error']}")
                return {}
                
            return results
        except Exception as e:
            print(f"Search error: {e}")
            return {}
