"""
Esempi di utilizzo della libreria LinkBay-AI
"""

import asyncio
from linkbay_ai import (
    AIOrchestrator,
    ProviderConfig,
    ProviderType,
    DeepSeekProvider,
    OpenAIProvider,
    BudgetConfig,
    ConversationConfig,
    PromptLibrary
)

# ============= SETUP BASE =============

async def example_basic_setup():
    """Esempio base: configurazione e utilizzo semplice"""
    
    # Crea orchestratore
    orchestrator = AIOrchestrator(
        budget_config=BudgetConfig(
            max_tokens_per_hour=50000,
            max_tokens_per_day=500000
        ),
        conversation_config=ConversationConfig(max_messages=15),
        enable_cache=True,
        enable_tools=True
    )
    
    # Registra provider DeepSeek
    deepseek_config = ProviderConfig(
        api_key="your-deepseek-api-key",
        base_url="https://api.deepseek.com",
        default_model="deepseek-chat",
        provider_type=ProviderType.DEEPSEEK,
        priority=1
    )
    deepseek = DeepSeekProvider(deepseek_config)
    orchestrator.register_provider(deepseek, priority=1)
    
    # Registra OpenAI come fallback
    openai_config = ProviderConfig(
        api_key="your-openai-api-key",
        base_url="https://api.openai.com/v1",
        default_model="gpt-3.5-turbo",
        provider_type=ProviderType.OPENAI,
        priority=99  
    )
    openai = OpenAIProvider(openai_config)
    orchestrator.register_provider(openai, priority=2)
    
    # Chat semplice con cache e conversation
    response = await orchestrator.chat(
        prompt="Ciao! Qual è la capitale della Francia?",
        use_conversation=True,
        use_cache=True
    )
    print(f"Response: {response.content}")
    print(f"Provider: {response.provider}, Tokens: {response.tokens_used}")


# ============= STREAMING =============

async def example_streaming():
    """Esempio: streaming di risposte"""
    orchestrator = AIOrchestrator(enable_cache=True)
    
    # Registra provider (setup omesso per brevità)
    
    print("Streaming response:")
    async for chunk in orchestrator.chat_stream(
        prompt="Scrivi una breve poesia sulla programmazione",
        use_conversation=False
    ):
        print(chunk, end="", flush=True)
    print()


# ============= TOOLS/FUNCTION CALLING =============

async def example_tools():
    """Esempio: uso di tools e function calling"""
    orchestrator = AIOrchestrator(enable_tools=True)
    
    # Registra provider...
    
    # Chiedi al modello di usare un tool
    response = await orchestrator.chat(
        prompt="Calcola 2 * 3 + 4, poi convertilo anche a temperatura in Celsius se rappresenta Fahrenheit",
        use_tools=True,
        model="deepseek-reasoning"
    )
    
    if response.tool_calls:
        print(f"Tool calls requested: {response.tool_calls}")
        # I tool call vengono già eseguiti automaticamente

    print(f"Final response: {response.content}")


# ============= CONVERSAZIONE MULTI-TURN =============

async def example_conversation():
    """Esempio: conversazione multi-turn con context"""
    orchestrator = AIOrchestrator(
        conversation_config=ConversationConfig(
            max_messages=20,
            context_window=4096,
            summarize_old_messages=True
        )
    )
    
    # Registra provider...
    
    # Prima domanda
    resp1 = await orchestrator.chat(
        prompt="Mi piace Python. Quale other linguaggio di programmazione mi consigli?",
        use_conversation=True
    )
    print(f"Q1: {resp1.content}\n")
    
    # Seconda domanda (ha accesso al context della prima)
    resp2 = await orchestrator.chat(
        prompt="Come imparo questo linguaggio nel modo migliore?",
        use_conversation=True
    )
    print(f"Q2: {resp2.content}\n")
    
    # Statistiche conversazione
    stats = orchestrator.conversation.get_stats()
    print(f"Conversation stats: {stats}")


# ============= PROMPT LIBRARY =============

async def example_prompt_library():
    """Esempio: uso della libreria di prompt templates"""
    orchestrator = AIOrchestrator()
    
    # Registra provider...
    
    # Riassumi testo
    prompt = PromptLibrary.summarize("""
    Machine learning è un campo dell'intelligenza artificiale che si concentra 
    nel far imparare ai computer a partire dai dati, senza essere esplicitamente 
    programmati. Viene utilizzato in molte applicazioni come riconoscimento 
    vocale, visione artificiale, elaborazione del linguaggio naturale e molto altro.
    """)
    
    response = await orchestrator.chat(prompt, use_conversation=False)
    print(f"Riassunto: {response.content}")


# ============= ERROR HANDLING =============

async def example_error_handling():
    """Esempio: gestione degli errori"""
    from linkbay_ai import BudgetExceededException, ProviderError
    
    orchestrator = AIOrchestrator(
        budget_config=BudgetConfig(max_tokens_per_hour=1000)  # Budget molto basso per test
    )
    
    # Registra provider...
    
    try:
        # Questo potrebbe superare il budget
        response = await orchestrator.chat(
            prompt="Scrivi un romanzo completo sulla storia dell'informatica"
        )
    except BudgetExceededException as e:
        print(f"❌ Budget exceeded: {e}")
    except ProviderError as e:
        print(f"❌ Provider error: {e}")


# ============= ANALYTICS =============

async def example_analytics():
    """Esempio: ottenere analytics e statistiche"""
    orchestrator = AIOrchestrator(enable_cache=True)
    
    # Registra provider e fai alcune chat...
    
    # Analytics dell'orchestratore
    analytics = orchestrator.get_analytics()
    print(f"Analytics: {analytics}")
    
    # Stats della cache
    cache_stats = orchestrator.semantic_cache.get_stats()
    print(f"Cache stats: {cache_stats}")
    
    # Stats conversazione
    conv_stats = orchestrator.conversation.get_stats()
    print(f"Conversation stats: {conv_stats}")


# ============= MAIN =============

async def main():
    """Esegui uno degli esempi"""
    print("=== LinkBay-AI Examples ===\n")
    
    # Scegli quale esempio eseguire:
    # await example_basic_setup()
    # await example_streaming()
    # await example_tools()
    # await example_conversation()
    # await example_prompt_library()
    # await example_error_handling()
    # await example_analytics()
    
    print("Seleziona un esempio per eseguirlo!")


if __name__ == "__main__":
    asyncio.run(main())
