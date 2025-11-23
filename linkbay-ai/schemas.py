from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class ProviderConfig(BaseModel):
    api_key: str
    base_url: str
    default_model: str = "deepseek-chat"

class GenerationParams(BaseModel):
    model: str
    max_tokens: int = 1000
    stream: bool = False
    temperature: float = 0.7

class AIRequest(BaseModel):
    prompt: str
    params: Optional[GenerationParams] = None
    context: Optional[Dict[str, Any]] = None