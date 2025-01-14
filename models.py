from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class ModelVersion(str, Enum):
    ITHAI_1 = "ITHAI-1.0"  # Free version (Groq)
    ITHAI_2 = "ITHAI-2.0"  # Premium version (GPT-4)

class HealthQuery(BaseModel):
    question: str
    version: ModelVersion = Field(default=ModelVersion.ITHAI_1, description="Model version to use")
    useWebSearch: bool = Field(default=False, description="Whether to enable web search for responses")
    context: Optional[str] = None

class HealthResponse(BaseModel):
    answer: str
    sources: List[str] = []
    is_document_based: bool = False
    version: ModelVersion