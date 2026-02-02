import requests
import time
from typing import List, Optional, Dict, Any
from .base import BaseProvider, AIResponse

class OllamaProvider(BaseProvider):
    """Implementation for Ollama AI backend"""
    
    def __init__(self, host: str = "localhost", port: int = 11434, default_model: str = "gemma3:4b"):
        self.base_url = f"http://{host}:{port}/api"
        self.default_model = default_model

    def generate(self, prompt: str, **kwargs) -> AIResponse:
        model = kwargs.get("model", self.default_model)
        system = kwargs.get("system", "")
        
        start_time = time.time()
        
        payload = {
            "model": model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", 0.7),
                "num_predict": kwargs.get("max_tokens", 2048)
            }
        }
        
        try:
            response = requests.post(f"{self.base_url}/generate", json=payload)
            response.raise_for_status()
            data = response.json()
            
            generation_time = time.time() - start_time
            
            return AIResponse(
                content=data.get("response", ""),
                model=model,
                provider="ollama",
                tokens_used=data.get("eval_count"),
                generation_time=generation_time,
                raw_response=data
            )
        except Exception as e:
            raise RuntimeError(f"Ollama generation failed: {str(e)}")

    def is_available(self) -> bool:
        try:
            response = requests.get(f"{self.base_url.replace('/api', '')}")
            return response.status_code == 200
        except:
            return False

    def list_models(self) -> List[str]:
        try:
            response = requests.get(f"{self.base_url}/tags")
            response.raise_for_status()
            models = response.json().get("models", [])
            return [m["name"] for m in models]
        except Exception as e:
            return []
