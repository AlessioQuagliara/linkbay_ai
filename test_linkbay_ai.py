"""
Tests base per LinkBay-AI - No external dependencies
"""

import asyncio
import pytest
from linkbay_ai import (
    AIOrchestrator,
    ProviderConfig,
    ProviderType,
    BudgetConfig,
    ConversationConfig,
    PromptLibrary,
    SemanticCache,
    ConversationContext,
    CostController,
    BudgetExceededException,
    LocalProvider
)
from linkbay_ai.tools import CommonTools, ToolExecutionError
from linkbay_ai.providers import ProviderError


# ============= UNIT TESTS =============

class TestBudgetController:
    """Test del budget controller"""
    
    @pytest.mark.asyncio
    async def test_budget_exceeds_hourly(self):
        """Test: superamento budget orario"""
        config = BudgetConfig(max_tokens_per_hour=1000)
        controller = CostController(config)
        
        # Primo check OK
        assert await controller.check_budget(500) is True
        controller.record_usage(500)
        
        # Secondo check OK
        assert await controller.check_budget(400) is True
        controller.record_usage(400)
        
        # Terzo check fallisce
        with pytest.raises(BudgetExceededException):
            await controller.check_budget(200)  # 500+400+200 > 1000
    
    @pytest.mark.asyncio
    async def test_budget_invalid_tokens(self):
        """Test: parametri non validi"""
        config = BudgetConfig(max_tokens_per_hour=1000)
        controller = CostController(config)
        
        with pytest.raises(ValueError):
            await controller.check_budget(-100)
    
    def test_budget_stats(self):
        """Test: statistiche budget"""
        config = BudgetConfig(max_tokens_per_hour=1000)
        controller = CostController(config)
        
        controller.record_usage(100)
        controller.record_usage(200)
        
        stats = controller.get_current_usage()
        assert stats["hourly"]["tokens"] == 300
        assert stats["hourly"]["percent"] == 30.0


class TestConversationContext:
    """Test del context conversazione"""
    
    def test_add_message(self):
        """Test: aggiungere messaggi"""
        conv = ConversationContext()
        
        conv.add_message("user", "Ciao", tokens=2)
        conv.add_message("assistant", "Ciao a te!", tokens=3)
        
        assert len(conv.history) == 2
        assert conv.total_tokens == 5
    
    def test_context_window_overflow(self):
        """Test: gestione overflow context window"""
        config = ConversationConfig(max_messages=3)
        conv = ConversationContext(config)
        
        for i in range(5):
            conv.add_message("user", f"Messaggio {i}", tokens=10)
        
        assert len(conv.history) <= 3
    
    def test_get_messages(self):
        """Test: ottenere messaggi"""
        conv = ConversationContext()
        
        for i in range(5):
            conv.add_message("user", f"Messaggio {i}")
        
        last_3 = conv.get_messages(last_n=3)
        assert len(last_3) == 3


class TestSemanticCache:
    """Test della semantic cache"""
    
    @pytest.mark.asyncio
    async def test_cache_hit_miss(self):
        """Test: cache hit e miss"""
        cache = SemanticCache(similarity_threshold=0.95)
        
        if not cache._embeddings_available:
            pytest.skip("sentence-transformers non disponibile")
        
        # Cache miss
        result = await cache.get_cached_response("Ciao")
        assert result is None
        
        # Salva in cache
        await cache.cache_response("Ciao", "Ciao a te!")
        
        # Cache hit con query simile
        result = await cache.get_cached_response("Ciao")
        assert result == "Ciao a te!"
    
    def test_cache_stats(self):
        """Test: statistiche cache"""
        cache = SemanticCache()
        stats = cache.get_stats()
        
        assert "size" in stats
        assert "enabled" in stats


class TestPromptLibrary:
    """Test della libreria prompt"""
    
    def test_summarize_template(self):
        """Test: template riassunto"""
        prompt = PromptLibrary.summarize("Testo lungo da riassumere")
        
        assert "Testo lungo da riassumere" in prompt
        assert "Riassunto" in prompt
    
    def test_translate_template(self):
        """Test: template traduzione"""
        prompt = PromptLibrary.translate("Hello", "italiano")
        
        assert "Hello" in prompt
        assert "italiano" in prompt
    
    def test_missing_parameter(self):
        """Test: parametro mancante"""
        with pytest.raises(ValueError):
            PromptLibrary.render(PromptLibrary.SUMMARIZE)  # Manca $text


class TestTools:
    """Test dei tools comuni"""
    
    @pytest.mark.asyncio
    async def test_calculate(self):
        """Test: calcolatore"""
        result = await CommonTools.calculate("2 + 2 * 3")
        assert result == 8.0
    
    @pytest.mark.asyncio
    async def test_calculate_invalid(self):
        """Test: calcolatore con espressione invalida"""
        with pytest.raises(ValueError):
            await CommonTools.calculate("import os; os.system('rm -rf /')")  # Security check
    
    @pytest.mark.asyncio
    async def test_search_products(self):
        """Test: ricerca prodotti"""
        result = await CommonTools.search_products("laptop", category="Informatica", max_results=5)
        
        assert isinstance(result, list)
        assert len(result) > 0
        assert result[0]["name"]
    
    @pytest.mark.asyncio
    async def test_search_products_invalid(self):
        """Test: ricerca prodotti con input invalido"""
        with pytest.raises(ValueError):
            await CommonTools.search_products("")  # Query vuota
    
    @pytest.mark.asyncio
    async def test_get_weather(self):
        """Test: meteo"""
        result = await CommonTools.get_weather("Roma")
        
        assert result["location"] == "Roma"
        assert "temperature" in result
    
    @pytest.mark.asyncio
    async def test_get_user_info(self):
        """Test: info utente"""
        result = await CommonTools.get_user_info("user123")
        
        assert result["user_id"] == "user123"
        assert "email" in result
    
    @pytest.mark.asyncio
    async def test_send_notification(self):
        """Test: invio notifica"""
        result = await CommonTools.send_notification(
            "user123",
            "Ciao!",
            channel="email"
        )
        
        assert result is True


class TestAIOrchestrator:
    """Test dell'orchestratore AI"""
    
    def test_orchestrator_init(self):
        """Test: inizializzazione"""
        orchestrator = AIOrchestrator(
            budget_config=BudgetConfig(),
            conversation_config=ConversationConfig(),
            enable_cache=True,
            enable_tools=True
        )
        
        assert orchestrator.cost_controller is not None
        assert orchestrator.semantic_cache is not None
        assert orchestrator.conversation is not None
        assert orchestrator.tools_manager is not None
    
    def test_register_provider(self):
        """Test: registrazione provider"""
        orchestrator = AIOrchestrator()
        
        config = ProviderConfig(
            api_key="test",
            base_url="http://localhost",
            provider_type=ProviderType.LOCAL
        )
        provider = LocalProvider(config)
        
        orchestrator.register_provider(provider, priority=1)
        
        assert len(orchestrator.providers) > 0
        assert orchestrator.providers[0].name == "local"
    
    async def test_reset_conversation(self):
        """Test: reset conversazione"""
        orchestrator = AIOrchestrator()
        
        orchestrator.conversation.add_message("user", "Test")
        assert len(orchestrator.conversation.history) == 1
        
        orchestrator.reset_conversation()
        assert len(orchestrator.conversation.history) == 0


# ============= INTEGRATION TESTS =============

class TestIntegration:
    """Test di integrazione"""
    
    @pytest.mark.asyncio
    async def test_full_conversation_flow(self):
        """Test: flusso conversazione completo"""
        orchestrator = AIOrchestrator(enable_cache=True)
        
        config = ProviderConfig(
            api_key="test",
            base_url="http://localhost",
            provider_type=ProviderType.LOCAL
        )
        provider = LocalProvider(config)
        orchestrator.register_provider(provider)
        
        # Per LocalProvider, funzionerà (mock)
        response = await orchestrator.chat(
            prompt="Ciao",
            use_conversation=True,
            use_cache=True
        )
        
        assert response is not None
        assert isinstance(response.content, str)
    
    @pytest.mark.asyncio
    async def test_budget_workflow(self):
        """Test: workflow budget"""
        config = BudgetConfig(max_tokens_per_hour=10000)
        controller = CostController(config)
        
        # Simula varie richieste
        for i in range(3):
            await controller.check_budget(1000)
            controller.record_usage(1000)
        
        stats = controller.get_current_usage()
        assert stats["hourly"]["tokens"] == 3000
        assert stats["hourly"]["percent"] == 30.0


# ============= RUN TESTS =============

if __name__ == "__main__":
    # Esegui con: pytest test_linkbay_ai.py -v
    print("Esegui con: pytest test_linkbay_ai.py -v")
