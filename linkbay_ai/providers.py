from openai import OpenAI
from .schemas import ProviderConfig, GenerationParams
from typing import Dict, Any

class DeepSeekProvider:
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url
        )
    
    def chat(self, prompt: str, params: GenerationParams = None) -> str:
        if params is None:
            params = GenerationParams(model=self.config.default_model)
        
        try:
            response = self.client.chat.completions.create(
                model=params.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=params.max_tokens,
                temperature=params.temperature,
                stream=params.stream
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"DeepSeek API error: {str(e)}")