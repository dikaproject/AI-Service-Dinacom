import json
from .knowledge_base import KnowledgeBase, Diagnosis
from typing import Dict, List

class InteractiveDiagnosis:
    def __init__(self, initial_complaint: str, symptoms: List[str] = None, answers: Dict[str, str] = None):
        self.initial_complaint = initial_complaint
        self.symptoms = symptoms or []
        self.answers = answers or {}
        self.health_score = 0
        self.severity_level = ""
        self.urgency_level = ""
        self.risk_factors = []
        self.possible_conditions = []
        self.recommendations = []

class InferenceEngine:
    def __init__(self, knowledge_base: KnowledgeBase, llm_client):
        self.kb = knowledge_base
        self.llm = llm_client
        
        # Add standard questions to reduce API calls
        self.standard_questions = [
            "Sudah berapa lama Anda mengalami keluhan ini?",
            "Apakah keluhan ini mengganggu aktivitas sehari-hari?",
            "Apakah ada riwayat kondisi medis sebelumnya?",
            "Berapa usia kehamilan Anda saat ini?",
            "Apakah sudah berkonsultasi dengan dokter sebelumnya?"
        ]
    
    async def generate_questions(self, complaint: str) -> List[str]:
        # Use standard questions instead of generating new ones
        return {
            "questions": self.standard_questions,
            "total_questions": len(self.standard_questions),
            "severity_initial": "Sedang",
            "progress": 0
        }

    async def analyze_answers(self, diagnosis: InteractiveDiagnosis) -> InteractiveDiagnosis:
        context = f"Keluhan: {diagnosis.initial_complaint[:200]}. Jawaban: {str(diagnosis.answers)[:300]}"
        
        # Force strict JSON
        prompt = f"""\
Anda adalah asisten AI yang hanya membalas dalam format JSON.
Abaikan penjelasan, hanya beri JSON.
Teks input: "{context}"

Format JSON yang ketat, hanya balas dengan struktur ini:
{{
    "health_score": 80,
    "severity_level": "Ringan/Sedang/Berat",
    "urgency_level": "Rendah/Sedang/Tinggi",
    "possible_conditions": ["kondisi 1", "kondisi 2"],
    "recommendations": ["rekomendasi 1", "rekomendasi 2"]
}}
"""
        response = await self.llm.get_response(prompt, "")
        print("Raw LLM response:", response)

        # If response is empty
        if not response.strip():
            print("Warning: Empty response from LLM.")
            diagnosis.health_score = 50
            diagnosis.severity_level = "Ringan"
            diagnosis.urgency_level = "Rendah"
            diagnosis.possible_conditions = ["Data tidak cukup"]
            diagnosis.recommendations = ["Silakan periksa koneksi atau coba lagi"]
            return diagnosis

        # Try to parse as JSON
        try:
            analysis = json.loads(response)
            diagnosis.health_score = analysis["health_score"]
            diagnosis.severity_level = analysis["severity_level"]
            diagnosis.urgency_level = analysis["urgency_level"]
            diagnosis.risk_factors = analysis.get("risk_factors", [])
            diagnosis.possible_conditions = analysis["possible_conditions"]
            diagnosis.recommendations = analysis["recommendations"]
        except Exception as e:
            print(f"Error parsing analysis: {e}")

            # Attempt minimal text-based parsing (optional)
            # Example: parse lines for numeric health_score
            # or fallback to basic diagnosis
            diagnosis.health_score = 50
            diagnosis.severity_level = "Ringan"
            diagnosis.urgency_level = "Rendah"
            diagnosis.possible_conditions = ["Gagal memproses data"]
            diagnosis.recommendations = ["Silakan coba lagi atau konsultasi dengan dokter"]
        
        return diagnosis

    async def diagnose(self, complaint: str, answers: Dict[str, str] = None) -> InteractiveDiagnosis:
        diagnosis = InteractiveDiagnosis(complaint)
        
        if not answers:
            # If no answers provided, return questions for FE
            questions = await self.generate_questions(complaint)
            return {"questions": questions}
            
        diagnosis.answers = answers
        diagnosis = await self.analyze_answers(diagnosis)
        return diagnosis
