import requests
import time
from typing import List, Optional, Dict, Any
from .base import BaseProvider, AIResponse

class GPT4AllProvider(BaseProvider):
    """Implementation for GPT4All AI backend (OpenAI-compatible)"""
    
    def __init__(self, host: str = "localhost", port: int = 4891, default_model: str = "mistral-7b-instruct"):
        self.base_url = f"http://{host}:{port}/v1"
        self.default_model = default_model

    def generate(self, prompt: str, **kwargs) -> AIResponse:
        model = kwargs.get("model", self.default_model)
        
        start_time = time.time()
        
        payload = {
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "model": model,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 2048),
            "stream": False
        }
        
        try:
            response = requests.post(f"{self.base_url}/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            
            generation_time = time.time() - start_time
            
            content = data["choices"][0]["message"]["content"]
            
            return AIResponse(
                content=content,
                model=model,
                provider="gpt4all",
                tokens_used=data.get("usage", {}).get("total_tokens"),
                generation_time=generation_time,
                raw_response=data
            )
        except Exception as e:
            raise RuntimeError(f"GPT4All generation failed: {str(e)}")

    def is_available(self) -> bool:
        try:
            # GPT4All /v1/models might be available if the server is up
            response = requests.get(f"{self.base_url}/models")
            return response.status_code == 200
        except:
            return False

    def list_models(self) -> List[str]:
        try:
            response = requests.get(f"{self.base_url}/models")
            response.raise_for_status()
            models_data = response.json().get("data", [])
            return [m["id"] for m in models_data]
        except Exception as e:
            return []
