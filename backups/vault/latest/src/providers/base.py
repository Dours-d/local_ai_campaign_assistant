from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class AIResponse(BaseModel):
    """Standardized response across all providers"""
    content: str
    model: str
    provider: str
    tokens_used: Optional[int] = None
    generation_time: Optional[float] = None
    raw_response: Optional[Dict[str, Any]] = None

class BaseProvider(ABC):
    """Abstract base for all AI providers"""
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> AIResponse:
        """Generate a response from the AI model"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is running and accessible"""
        pass
    
    @abstractmethod
    def list_models(self) -> List[str]:
        """List available models for this provider"""
        pass
