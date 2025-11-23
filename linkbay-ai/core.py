from .providers import DeepSeekProvider
from .schemas import ProviderConfig, GenerationParams, AIRequest
from typing import Dict, Any, List

class AIOrchestrator:
    def __init__(self):
        self.providers: Dict[str, DeepSeekProvider] = {}
        self.request_history: List[Dict] = []
    
    def register_provider(self, name: str, provider: DeepSeekProvider):
        self.providers[name] = provider
    
    def chat(self, prompt: str, model: str = "deepseek-chat") -> str:
        if not self.providers:
            raise ValueError("No AI providers configured")
        
        provider = list(self.providers.values())[0]
        params = GenerationParams(model=model)
        
        response = provider.chat(prompt, params)
        
        self.request_history.append({
            "prompt": prompt,
            "model": model,
            "response": response
        })
        
        return response
    
    def get_analytics(self) -> Dict[str, Any]:
        return {
            "total_requests": len(self.request_history),
            "models_used": {
                "deepseek-chat": len([r for r in self.request_history if r["model"] == "deepseek-chat"]),
                "deepseek-reasoning": len([r for r in self.request_history if r["model"] == "deepseek-reasoning"])
            }
        }