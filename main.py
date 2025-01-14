from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
import os
from typing import List, Optional, Dict
from pathlib import Path
import PyPDF2
import docx
from dotenv import load_dotenv
from serpapi import GoogleSearch
import asyncio
from models import HealthQuery, HealthResponse, ModelVersion
from llm_clients import GroqClient, GPT4Client
from expert_system.knowledge_base import KnowledgeBase
from expert_system.inference_engine import InferenceEngine
from pydantic import BaseModel
import re  # Add this import at the top


load_dotenv()
print("Loaded API Keys:")
print(f"Required API Key: {os.getenv('API_KEY_REQUIRED')}")
print(f"Premium API Key: {os.getenv('PREMIUM_API_KEY')}")

app = FastAPI()

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SearchEngine:
    def __init__(self):
        self.max_results = 5
        self.api_keys = [
            os.getenv("SERPAPI_KEY_1", ""),
        ]
        self.current_key_index = 0
    
    def _get_next_api_key(self):
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        return self.api_keys[self.current_key_index]

    async def search(self, query: str) -> List[Dict[str, str]]:
        try:
            params = {
                "engine": "google",
                "q": query,
                "api_key": self._get_next_api_key(),
                "num": self.max_results,
                "gl": "id",  # Set region to Indonesia
                "hl": "id"   # Set language to Indonesian
            }
            
            loop = asyncio.get_event_loop()
            search = await loop.run_in_executor(None, lambda: GoogleSearch(params).get_dict())
            
            if "error" in search:
                print(f"Search error: {search['error']}")
                return []
            
            results = []
            for result in search.get("organic_results", [])[:self.max_results]:
                results.append({
                    "title": result.get("title", ""),
                    "body": result.get("snippet", ""),
                    "link": result.get("link", "")
                })
            return results
        except Exception as e:
            print(f"Search error: {e}")
            return []

    def format_results(self, results: List[Dict[str, str]]) -> str:
        formatted_results = "\n".join([f"{result['title']}\n{result['body']}\n{result['link']}" for result in results])
        return formatted_results

class HealthKnowledgeBase:
    def __init__(self):
        self.knowledge = []
        self.sources = {}
        self.search_engine = SearchEngine()
        self.groq_client = GroqClient()
        self.gpt4_client = GPT4Client()
        
    def load_pdf(self, pdf_path: str):
        pdf_name = Path(pdf_path).name
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            
            chunks = self._chunk_text(text)
            for chunk in chunks:
                self.knowledge.append(chunk)
                self.sources[chunk] = f"Document: {pdf_name}"
    
    def load_docx(self, docx_path: str):
        doc_name = Path(docx_path).name
        doc = docx.Document(docx_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        
        chunks = self._chunk_text(text)
        for chunk in chunks:
            self.knowledge.append(chunk)
            self.sources[chunk] = f"Document: {doc_name}"
    
    def _chunk_text(self, text: str, chunk_size: int = 1000):
        words = text.split()
        chunks = []
        current_chunk = []
        current_size = 0
        
        for word in words:
            if current_size + len(word) > chunk_size:
                chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_size = len(word)
            else:
                current_chunk.append(word)
                current_size += len(word) + 1
                
        if current_chunk:
            chunks.append(" ".join(current_chunk))
            
        return chunks
    
    def find_relevant_context(self, query: str, max_chunks: int = 2) -> tuple[str, List[str]]:
        relevant_chunks = []
        sources = []
        
        query_words = set(query.lower().split())
        scored_chunks = []
        
        for chunk in self.knowledge:
            chunk_words = set(chunk.lower().split())
            score = len(query_words.intersection(chunk_words))
            if score > 0:
                scored_chunks.append((score, chunk))
        
        scored_chunks.sort(reverse=True)
        
        for _, chunk in scored_chunks[:max_chunks]:
            relevant_chunks.append(chunk)
            sources.append(self.sources[chunk])
            
        return "\n".join(relevant_chunks), list(set(sources))

    async def get_answer(self, query: str, model_version: ModelVersion, use_web_search: bool) -> tuple[str, List[str], bool]:
        # If web search is disabled, use conversational mode
        if not use_web_search:
            return await self.get_conversational_response(query)
            
        # Otherwise, proceed with normal search-enabled response
        # Get document context first
        doc_context, doc_sources = self.find_relevant_context(query)
        
        # Determine if using premium model
        is_premium = model_version == ModelVersion.ITHAI_2
        client = self.gpt4_client if is_premium else self.groq_client
        
        # If we have relevant document context, use only that
        if doc_context.strip():
            response = await client.get_response(query, doc_context)
            return response, doc_sources, True
        
        # If no document context, try search engine for all users
        search_results = await self.search_engine.search(query + " kesehatan ibu hamil indonesia")
        if search_results:
            search_context = self.search_engine.format_results(search_results)
            response = await client.get_response(query, search_context)
            sources = [f"Web: {result['link']}" for result in search_results]
            return response, sources, False
        
        # If no context available from either source
        return "Maaf, informasi yang Anda tanyakan tidak tersedia dalam dokumen referensi kami maupun sumber online.", [], False

    # Add this new method
    async def get_basic_response(self, query: str, context: str) -> str:
        """Handle basic conversations without web search"""
        is_greeting = bool(re.search(r'^hi\b|^hello\b|^hay\b|^halo\b', query.lower()))
        is_thanks = bool(re.search(r'thank|thanks|terima kasih', query.lower()))
        is_goodbye = bool(re.search(r'bye|goodbye|sampai jumpa', query.lower()))
        
        if is_greeting:
            return ("Halo! Saya PregnaAI, asisten AI yang siap membantu Anda seputar kehamilan. "
                   "Saya dapat memberikan informasi tentang kesehatan ibu hamil, memberikan saran nutrisi, "
                   "dan menjawab pertanyaan umum seputar kehamilan. Apa yang ingin Anda ketahui?")
        elif is_thanks:
            return ("Sama-sama! Senang bisa membantu Anda. Jangan ragu untuk bertanya lagi jika "
                   "Anda memiliki pertanyaan lain seputar kehamilan.")
        elif is_goodbye:
            return ("Sampai jumpa! Jaga kesehatan Anda dan bayi. Jangan lupa untuk rutin "
                   "melakukan pemeriksaan dan mengisi DailyCheckup Anda.")
        else:
            # Use the LLM for other basic responses
            client = self.groq_client  # Using Groq for basic responses
            return await client.get_response(query, context)

    async def get_conversational_response(self, query: str) -> tuple[str, List[str], bool]:
        """Handle platform-focused conversations without web search"""
        # Use base Groq model for consistent responses
        response = await self.groq_client.get_response(
            query,
            WEBSITE_CONTEXT
        )
        return response, [], False

# Initialize knowledge base
kb = HealthKnowledgeBase()
pregnancy_kb = KnowledgeBase(lang='id', serpapi_key=os.getenv("SERPAPI_KEY_1"))
expert_system = InferenceEngine(pregnancy_kb, kb.groq_client)  # Pass the LLM client

# Initialize pregnancy knowledge base
def initialize_pregnancy_kb():
    # Add pregnancy-related symptoms
    pregnancy_kb.add_symptom('nausea', {
        'name': {'id': 'Mual', 'en': 'Nausea'},
        'weight': 1.2,
        'questions': {
            'id': [
                'Seberapa sering Anda merasa mual?',
                'Apakah mual disertai muntah?'
            ],
            'en': [
                'How often do you feel nauseous?',
                'Is the nausea accompanied by vomiting?'
            ]
        }
    })
    # ...add other symptoms and conditions...

# Initialize expert system on startup
initialize_pregnancy_kb()

WEBSITE_CONTEXT = """
You are PregnaAI, a friendly and helpful AI assistant for pregnant mothers. You are part of a comprehensive pregnancy care platform that includes:

1. PregnaAI Chat (your current feature):
   - 24/7 pregnancy companion
   - Friendly conversation and support
   - Can answer medical questions when web search is enabled

2. AI-Powered Features:
   - AI Diagnosis: Smart analysis of pregnancy symptoms and concerns
   - AI Analytics: Comprehensive analysis of daily health data
   - Smart Exercise Recommendations based on pregnancy stage

3. Daily Health Tracking:
   - DailyCheckup: Track vital signs, mood, and symptoms
   - Nutrition Logging: Monitor diet and get personalized advice
   - Exercise Tracking: Safe workout monitoring for pregnant mothers

4. Professional Care:
   - Direct Doctor Consultation
   - Certified healthcare providers
   - Expert medical advice

5. Smart Reminders & Integration:
   - WhatsApp notifications for checkups
   - Appointment reminders
   - Quick data entry via WhatsApp chatbot
   - Daily health tracking reminders

Conversation Guidelines:
- Be warm, friendly, and supportive
- Use simple, clear language
- Refer to platform features when relevant
- Express empathy and understanding
- For medical questions, recommend enabling web search or consulting doctors
- Focus on being a helpful companion rather than a medical advisor
"""

@app.post("/v1/health/chat", response_model=HealthResponse)
async def health_chat(query: HealthQuery, x_api_key: str = Header(None)):
    print(f"Received API Key: {x_api_key}")  # Debug log
    
    required_key = os.getenv("API_KEY_REQUIRED")
    premium_key = os.getenv("PREMIUM_API_KEY")
    
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing API key")
    
    if x_api_key != required_key and x_api_key != premium_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Check if premium model is requested but user doesn't have premium access
    if query.version == ModelVersion.ITHAI_2 and x_api_key != premium_key:
        raise HTTPException(
            status_code=403, 
            detail="Access to ITHAI-2.0 requires a premium API key. Please upgrade or use ITHAI-1.0."
        )
    
    try:
        print(f"Processing query with version: {query.version}")  # Debug log
        
        # Check if it's a basic conversation
        basic_patterns = [
            r'^hi\b|^hello\b|^hay\b|^halo\b',
            r'thank|thanks|terima kasih',
            r'bye|goodbye|sampai jumpa',
        ]
        
        is_basic = any(re.search(pattern, query.question.lower()) for pattern in basic_patterns)
        
        if is_basic and not query.useWebSearch:
            # Use direct response without web search
            response = await kb.get_basic_response(query.question, WEBSITE_CONTEXT)
            return HealthResponse(
                answer=response,
                sources=[],
                is_document_based=False,
                version=query.version
            )
        
        # Otherwise, proceed with normal search-enabled response
        response, sources, is_document_based = await kb.get_answer(
            query.question, 
            query.version,
            query.useWebSearch
        )
        
        return HealthResponse(
            answer=response,
            sources=sources if query.useWebSearch else [],
            is_document_based=is_document_based,
            version=query.version
        )
    except Exception as e:
        print(f"Error in health_chat: {str(e)}")  # Debug log
        raise HTTPException(status_code=500, detail=str(e))

class DiagnosisRequest(BaseModel):
    complaint: str
    answers: Optional[Dict[str, str]] = None

@app.post("/v1/health/diagnose")
async def diagnose_symptoms(request: DiagnosisRequest, x_api_key: str = Header(None)):
    premium_key = os.getenv("PREMIUM_API_KEY")
    if not x_api_key or x_api_key != premium_key:
        raise HTTPException(
            status_code=401, 
            detail="This endpoint requires a premium API key"
        )
        
    try:
        diagnosis = await expert_system.diagnose(request.complaint, request.answers)
        return diagnosis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/docs/usage")
def usage_docs():
    return {
        "description": "Use the /v1/health/chat endpoint by including 'x-api-key' with a valid key in the header."
    }

if __name__ == "__main__":
    import uvicorn
    # Initialize expert system
    initialize_pregnancy_kb()
    uvicorn.run(app, host="0.0.0.0", port=8000)