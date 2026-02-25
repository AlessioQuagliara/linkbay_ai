from openai import OpenAI, APIError, APIConnectionError, APITimeoutError, RateLimitError
from .schemas import ProviderConfig, GenerationParams, AIResponse, Message, ProviderType
from typing import Dict, Any, List, AsyncIterator, Optional
from abc import ABC, abstractmethod
import logging
import asyncio

logger = logging.getLogger(__name__)

class ProviderError(Exception):
    """Errore generico del provider"""
    pass

class ProviderTimeoutError(ProviderError):
    """Errore di timeout del provider"""
    pass

class ProviderRateLimitError(ProviderError):
    """Limite di rate raggiunto"""
    pass

class ProviderConnectionError(ProviderError):
    """Errore di connessione con il provider"""
    pass

class BaseProvider(ABC):
    """Base class per tutti i provider AI"""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.name = config.provider_type.value
    
    @abstractmethod
    async def chat(self, messages: List[Message], params: GenerationParams = None) -> AIResponse:
        """Esegui una chat completion"""
        pass
    
    @abstractmethod
    async def stream(self, messages: List[Message], params: GenerationParams = None) -> AsyncIterator[str]:
        """Esegui una chat completion con streaming"""
        pass
    
    def is_available(self) -> bool:
        """Verifica se il provider è disponibile"""
        try:
            return self._health_check()
        except Exception as e:
            logger.warning(f"Health check fallito per {self.name}: {e}")
            return False
    
    def _health_check(self) -> bool:
        """Health check specifico del provider"""
        return True
    
    async def _execute_with_retry(self, func, max_retries: int = 3, backoff_factor: float = 1.5):
        """
        Esegui funzione con retry e exponential backoff
        
        Args:
            func: Funzione async da eseguire
            max_retries: Numero di tentativi
            backoff_factor: Fattore di backoff esponenziale
            
        Returns:
            Risultato della funzione
            
        Raises:
            ProviderError: Se tutti i tentativi falliscono
        """
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                self.request_count += 1
                result = await func() if asyncio.iscoroutinefunction(func) else func()
                return result
            except RateLimitError as e:
                last_exception = ProviderRateLimitError(f"Rate limit error: {e}")
                wait_time = (2 ** attempt) * backoff_factor
                logger.warning(f"⚠️ Rate limit colpito, retry in {wait_time}s...")
                await asyncio.sleep(wait_time)
            except APITimeoutError as e:
                last_exception = ProviderTimeoutError(f"Timeout: {e}")
                logger.warning(f"⏱️ Timeout, retry {attempt + 1}/{max_retries}...")
                await asyncio.sleep(2 ** attempt)
            except APIConnectionError as e:
                last_exception = ProviderConnectionError(f"Connection error: {e}")
                logger.warning(f"🔌 Errore connessione, retry {attempt + 1}/{max_retries}...")
                await asyncio.sleep(2 ** attempt)
            except APIError as e:
                # Non ritentare per errori di validazione (4xx)
                if hasattr(e, 'status_code') and 400 <= e.status_code < 500:
                    raise ProviderError(f"Client error: {e}")
                last_exception = ProviderError(f"API error: {e}")
                logger.warning(f"❌ Errore API, retry {attempt + 1}/{max_retries}...")
                await asyncio.sleep(2 ** attempt)
            except Exception as e:
                last_exception = ProviderError(f"Unexpected error: {e}")
                logger.error(f"❌ Errore inaspettato: {e}")
                break
        
        self.error_count += 1
        logger.error(f"❌ Provider {self.name} fallito dopo {max_retries} tentativi")
        raise last_exception or ProviderError(f"Provider {self.name} non disponibile")
    
    def get_stats(self) -> Dict[str, Any]:
        """Ottieni statistiche del provider"""
        return {"name": self.name}

class DeepSeekProvider(BaseProvider):
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout
        )
    
    async def chat(self, messages: List[Message], params: GenerationParams = None) -> AIResponse:
        if params is None:
            params = GenerationParams(model=self.config.default_model)
        
        async def _call():
            # Converti i messaggi nel formato OpenAI
            api_messages = [{"role": msg.role, "content": msg.content} for msg in messages]
            
            response = self.client.chat.completions.create(
                model=params.model,
                messages=api_messages,
                max_tokens=params.max_tokens,
                temperature=params.temperature,
                stream=False,
                tools=params.tools
            )
            
            # Gestisci tool calls se presenti
            tool_calls = None
            if hasattr(response.choices[0].message, 'tool_calls') and response.choices[0].message.tool_calls:
                tool_calls = [
                    {"name": tc.function.name, "arguments": tc.function.arguments}
                    for tc in response.choices[0].message.tool_calls
                ]
            
            return AIResponse(
                content=response.choices[0].message.content or "",
                model=params.model,
                provider=self.name,
                tokens_used=response.usage.total_tokens if response.usage else 0,
                tool_calls=tool_calls
            )
        
        try:
            return await self._execute_with_retry(_call)
        except ProviderError as e:
            logger.error(f"DeepSeek API error: {str(e)}")
            raise
    
    async def stream(self, messages: List[Message], params: GenerationParams = None) -> AsyncIterator[str]:
        if params is None:
            params = GenerationParams(model=self.config.default_model)
        
        async def _call():
            api_messages = [{"role": msg.role, "content": msg.content} for msg in messages]
            
            response = self.client.chat.completions.create(
                model=params.model,
                messages=api_messages,
                max_tokens=params.max_tokens,
                temperature=params.temperature,
                stream=True
            )
            
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        
        try:
            async for chunk in _call():
                yield chunk
        except ProviderError as e:
            logger.error(f"DeepSeek streaming error: {str(e)}")
            raise

class OpenAIProvider(BaseProvider):
    """OpenAI provider come fallback"""
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.client = OpenAI(
            api_key=config.api_key,
            timeout=config.timeout
        )
    
    async def chat(self, messages: List[Message], params: GenerationParams = None) -> AIResponse:
        if params is None:
            params = GenerationParams(model="gpt-3.5-turbo")
        
        async def _call():
            api_messages = [{"role": msg.role, "content": msg.content} for msg in messages]
            
            response = self.client.chat.completions.create(
                model=params.model,
                messages=api_messages,
                max_tokens=params.max_tokens,
                temperature=params.temperature,
                stream=False,
                tools=params.tools
            )
            
            return AIResponse(
                content=response.choices[0].message.content or "",
                model=params.model,
                provider=self.name,
                tokens_used=response.usage.total_tokens if response.usage else 0
            )
        
        try:
            return await self._execute_with_retry(_call)
        except ProviderError as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise
    
    async def stream(self, messages: List[Message], params: GenerationParams = None) -> AsyncIterator[str]:
        if params is None:
            params = GenerationParams(model="gpt-3.5-turbo")
        
        async def _call():
            api_messages = [{"role": msg.role, "content": msg.content} for msg in messages]
            
            response = self.client.chat.completions.create(
                model=params.model,
                messages=api_messages,
                max_tokens=params.max_tokens,
                temperature=params.temperature,
                stream=True
            )
            
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        
        try:
            async for chunk in _call():
                yield chunk
        except ProviderError as e:
            logger.error(f"OpenAI streaming error: {str(e)}")
            raise

class LocalProvider(BaseProvider):
    """Local provider fallback (mock per ora)"""
    
    async def chat(self, messages: List[Message], params: GenerationParams = None) -> AIResponse:
        # Implementazione mock - potrebbe usare Ollama o modello locale
        return AIResponse(
            content="Local provider non ancora implementato. Tutti i provider remoti sono down.",
            model="local",
            provider=self.name,
            tokens_used=0
        )
    
    async def stream(self, messages: List[Message], params: GenerationParams = None) -> AsyncIterator[str]:
        yield "Local provider non ancora implementato."