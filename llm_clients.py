from abc import ABC, abstractmethod
import os
import httpx
from fastapi import HTTPException

class BaseLLMClient(ABC):
    @abstractmethod
    async def get_response(self, query: str, context: str) -> str:
        pass

class GroqClient(BaseLLMClient):
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
    
    async def get_response(self, query: str, context: str) -> str:
        messages = [
            {
                "role": "system",
                "content": (
                    "Anda adalah PregnaAI, asisten ramah untuk ibu hamil. "
                    "Berikan respons yang hangat dan supportif. "
                    "Gunakan bahasa yang sederhana dan mudah dipahami. "
                    "Fokus pada memberikan informasi tentang fitur platform dan dukungan umum. "
                    "Jika ada pertanyaan medis spesifik, sarankan untuk mengaktifkan web search "
                    "atau berkonsultasi dengan dokter.\n\n"
                    f"Konteks Platform: {context}"
                )
            },
            {
                "role": "user",
                "content": query
            }
        ]
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url,
                headers=self.headers,
                json={
                    "model": "llama3-8b-8192",
                    "messages": messages,
                    "temperature": 0.3
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Error processing request")
                
            return response.json()["choices"][0]["message"]["content"]

class GPT4Client(BaseLLMClient):
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = "https://api.openai.com/v1/chat/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
    
    async def get_response(self, query: str, context: str) -> str:
        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "Anda adalah asisten kesehatan premium yang berfokus pada kesejahteraan fisik dan mental. "
                        "Spesialisasi anda mencakup:\n"
                        "1. Kesehatan mental dan manajemen stress\n"
                        "2. Pemantauan kesehatan real-time dan gaya hidup sehat\n"
                        "3. Pencegahan penyakit dan perawatan kesehatan preventif\n"
                        "4. Panduan aktivitas fisik dan nutrisi\n\n"
                        "Berikan jawaban komprehensif dalam Bahasa Indonesia yang mudah dipahami. "
                        "Gunakan konteks dokumen sebagai referensi utama dan tambahkan wawasan medis "
                        "terkini jika relevan.\n\n"
                        f"Konteks: {context}"
                    )
                },
                {
                    "role": "user",
                    "content": query
                }
            ]
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.base_url,
                    headers=self.headers,
                    json={
                        "model": "gpt-4-turbo-preview",
                        "messages": messages,
                        "temperature": 0.3
                    },
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    error_detail = response.json().get('error', {}).get('message', 'Unknown error')
                    print(f"OpenAI API Error: {error_detail}")
                    raise HTTPException(status_code=response.status_code, detail=f"OpenAI API Error: {error_detail}")
                    
                return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"GPT4Client Error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")
