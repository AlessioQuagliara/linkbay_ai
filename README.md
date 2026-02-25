# LinkBay-AI

**Un orchestratore AI async-first per integrare più LLM in modo semplice, senza architetture pesanti.**  
L’obiettivo è essere pragmatici: feature utili, API coerenti, esempi pronti da copiare.

> **Enterprise-ready AI orchestration library** con multi‑provider fallback, budget control, semantic caching, streaming, conversation management, e function calling.

---

## Indice

- [Caratteristiche Principali](#caratteristiche-principali)
- [Installazione](#installazione)
- [Quick Start](#quick-start)
- [Panoramica Componenti](#panoramica-componenti)
- [Utilizzo Dettagliato](#utilizzo-dettagliato)
  - [Multi‑provider fallback](#1-multi-provider-fallback)
  - [Budget control](#2-budget-control)
  - [Cache semantica](#3-cache-semantica)
  - [Conversazioni multi‑turn](#4-conversazioni-multi-turn)
  - [Streaming token‑by‑token](#5-streaming-token-by-token)
  - [Prompt Library](#6-prompt-library)
  - [Tool / Function Calling](#7-tool--function-calling)
  - [Helper leggeri](#8-helper-leggeri)
- [Configurazione](#configurazione)
- [API Reference](#api-reference)
- [Error Handling](#error-handling)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
- [FAQ – performance e sicurezza](#faq--performance-e-sicurezza)
- [Licenza](#licenza)
- [Supporto e Roadmap](#supporto-e-roadmap)

---

## Caratteristiche Principali

| Funzionalità | Descrizione |
|--------------|-------------|
| **Multi‑Provider Orchestration** | Fallback automatico tra provider (DeepSeek → OpenAI → Local), smart routing basato sulla complessità della richiesta, retry con exponential backoff, rate limit handling, health checks. |
| **Budget Management** | Token budgeting orario/giornaliero, cost control in tempo reale, alert system quando ci si avvicina ai limiti, flexible pricing per modello. |
| **Smart Caching** | Cache semantica con embeddings (sentence‑transformers), similarity matching per evitare duplicati, TTL‑based cleanup automatico, statistiche hit/miss. |
| **Conversation Context** | Multi‑turn conversations con memory, gestione intelligente della context window, tracciamento token, auto‑summarization di messaggi vecchi. |
| **Function Calling** | Registrazione semplice di tool, CommonTools predefiniti (calcolo, ricerca, notifiche), esecuzione asincrona, error handling specifico. |
| **Prompt Library** | 20+ template `string.Template` per task comuni (HTML, analytics, business, reasoning), parametrizzazione semplice, best practices integrate. |
| **Streaming & Analytics** | Streaming token‑by‑token, request history, statistiche per provider (request count, error rate), cache analytics con hit rate. |

---

## Installazione

```bash
# Dipendenze core
pip install linkbay-ai
```
```bash
# Con cache semantica (scarica sentence-transformers, ~500 MB)
pip install "linkbay-ai[cache]"
```
```bash
# Tutto incluso (cache + eventuali extra futuri)
pip install "linkbay-ai[all]"
```
```bash
# Per sviluppo
pip install "linkbay-ai[dev]"
```

| Requisito | Versione | Note |
|-----------|----------|------|
| Python    | 3.8 – 3.12 | testato in CI |
| openai    | >= 1.0.0   | SDK usato anche per DeepSeek |
| sentence‑transformers *(opz.)* | >= 2.0.0 | richiesto solo se `enable_cache=True` |

---

## Quick Start

```python
import asyncio
from linkbay_ai import (
    AIOrchestrator,
    DeepSeekProvider,
    OpenAIProvider,
    ProviderConfig,
    BudgetConfig,
)

async def main() -> None:
    # Crea orchestratore con budget e cache
    ai = AIOrchestrator(
        budget_config=BudgetConfig(max_tokens_per_hour=100_000),
        enable_cache=True,
        enable_tools=False,
    )

    # Configura provider
    deepseek_cfg = ProviderConfig(
        api_key="DEEPSEEK_KEY",
        base_url="https://api.deepseek.com",
        priority=1,
    )
    openai_cfg = ProviderConfig(
        api_key="OPENAI_KEY",
        base_url="https://api.openai.com/v1",
        priority=2,
    )

    # Registra provider (ordine di priorità)
    ai.register_provider(DeepSeekProvider(deepseek_cfg), priority=1)
    ai.register_provider(OpenAIProvider(openai_cfg), priority=2)

    # Fai una richiesta
    response = await ai.chat("Traduci 'Hello world' in italiano")
    print(response.content)  # → "Ciao mondo"

    # Visualizza statistiche
    print(ai.get_analytics())

asyncio.run(main())
```

> **Importante:** l’API è completamente **async**. In ambienti sync usa `asyncio.run()` oppure integra direttamente le coroutine in FastAPI, Quart, ecc.

---

## Panoramica Componenti

| Componente | Ruolo | Default / Note |
|------------|-------|----------------|
| `AIOrchestrator` | Coordina provider, budget, cache, conversazioni, tools | — |
| `BaseProvider` + `DeepSeekProvider`, `OpenAIProvider`, `LocalProvider` | Adapter verso LLM esterni | DeepSeek + OpenAI come esempi |
| `CostController` | Tracking token/costo e alert soglia | 100 k token/h, $10/h, alert 80% |
| `SemanticCache` | Cache in‑memory con embedding `all-MiniLM-L6-v2` | TTL 24h, max 1000 entry, soglia 0.95 |
| `ConversationContext` | History multi‑turn con trimming intelligente | 10 messaggi, context window 4096, auto‑summarization opzionale |
| `ToolsManager` | Function calling (5 tool predefiniti + custom) | tools: search, calculate, weather, user info, notifications |
| `PromptLibrary` | 20+ template `string.Template` | HTML, analytics, business, reasoning, ecc. |

---

## Utilizzo Dettagliato

### 1. Multi‑provider fallback

```python
async def resilient_chat(prompt: str):
    orchestrator = AIOrchestrator()
    orchestrator.register_provider(DeepSeekProvider(primary_cfg), priority=1)
    orchestrator.register_provider(OpenAIProvider(backup_cfg), priority=2)

    return await orchestrator.chat(prompt)
```

- Provider provati in ordine di priorità (numero più basso = più importante).
- `max_retries` (default 3) gestisce i retry per singolo provider.
- Se tutti falliscono viene sollevata `AllProvidersFailedException`.

### 2. Budget control

```python
from linkbay_ai import BudgetConfig, BudgetExceededException

ai = AIOrchestrator(
    budget_config=BudgetConfig(
        max_tokens_per_hour=50_000,
        max_tokens_per_day=500_000,
        max_cost_per_hour=5.0,
    )
)

try:
    response = await ai.chat("Genera un business plan di 5 pagine")
except BudgetExceededException as exc:
    logger.warning("Budget superato: %s", exc)

print(ai.get_analytics()["budget"])  # Statistiche correnti
```

### 3. Cache semantica

```python
ai = AIOrchestrator(enable_cache=True)

first = await ai.chat("Cos'è l'e-commerce?")
second = await ai.chat("Che cosa si intende per commercio elettronico?")

print(first.cached, second.cached)  # False, True
```

Dettagli rapidi:
- Embedding model: `SentenceTransformer('all-MiniLM-L6-v2')`
- Soglia hit: `0.95` (configurabile)
- TTL: 24h, max 1000 entry, eviction per hit count
- Se `sentence-transformers` manca, la cache si disattiva automaticamente

### 4. Conversazioni multi‑turn

```python
from linkbay_ai import ConversationConfig

ai = AIOrchestrator(conversation_config=ConversationConfig(max_messages=6))
ai.add_system_prompt("Sei un assistente e-commerce positivo")

await ai.chat("Che scarpe avete?", use_conversation=True)
reply = await ai.chat("Quali taglie sono disponibili?", use_conversation=True)

print(reply.content)
```

`get_analytics()["conversation"]` mostra conteggio messaggi e token utilizzati.

### 5. Streaming token‑by‑token

```python
async for chunk in ai.chat_stream(
    "Scrivi un pitch di 100 parole",
    use_conversation=False
):
    print(chunk, end="", flush=True)
```

### 6. Prompt Library

```python
from linkbay_ai import PromptLibrary

prompt = PromptLibrary.generate_html("Card prodotto responsive con CTA")
html_response = await ai.chat(prompt, use_conversation=False)

prompt = PromptLibrary.analyze_sales("Prodotto A,100\nProdotto B,250")
analysis_response = await ai.chat(prompt, model="deepseek-reasoner")
```

Template principali:
- **Generici:** `SUMMARIZE`, `TRANSLATE`, `EXTRACT_KEYWORDS`
- **UI:** `GENERATE_HTML`, `GENERATE_COMPONENT`
- **Dati:** `ANALYZE_DATA`, `ANALYZE_SALES`, `ANALYZE_TRAFFIC`
- **Business:** `WRITE_EMAIL`, `GENERATE_DESCRIPTION`
- **Reasoning:** `DEEP_REASONING`, `DEBUG_CODE`

### 7. Tool / Function Calling

```python
from linkbay_ai import ToolCall

response = await ai.chat("Che meteo fa a Milano?", use_tools=True)
if response.tool_calls:
    meteo = await ai.tools_manager.execute_tool(ToolCall(**response.tool_calls[0]))
    print(meteo)
```

Registrare un tool custom:

```python
async def get_exchange_rate(base: str, quote: str) -> dict:
    return {"pair": f"{base}/{quote}", "rate": 1.08}

ai.tools_manager.register_tool(
    name="fx_rate",
    function=get_exchange_rate,
    description="Restituisce il tasso di cambio",
    parameters={
        "type": "object",
        "properties": {
            "base": {"type": "string"},
            "quote": {"type": "string"},
        },
        "required": ["base", "quote"],
    },
)
```

### 8. Helper leggeri

```python
from linkbay_ai.utils import generate_html_tailwind, fill_form_fields

html = await generate_html_tailwind(ai, "Navbar minimal con CTA")
form = await fill_form_fields(
    ai,
    "Mi chiamo Alessio, email alessio@example.com",
    ["nome", "email"],
)

print(form)  # {"nome": "Alessio", "email": "alessio@example.com"}
```

---

## Configurazione

### ProviderConfig

```python
ProviderConfig(
    api_key: str,                     # Chiave API
    base_url: str,                     # Endpoint del provider
    default_model: str = "deepseek-chat",
    provider_type: Literal["deepseek", "openai", "local"],
    priority: int = 1,                  # Priorità (1 = più alta)
    timeout: int = 30,                   # Timeout in secondi
)
```

### BudgetConfig

```python
BudgetConfig(
    max_tokens_per_hour=100_000,
    max_tokens_per_day=1_000_000,
    max_cost_per_hour=10.0,             # Costo massimo in dollari
    alert_threshold=0.8,                 # 80% dei limiti → alert
)
```

### ConversationConfig

```python
ConversationConfig(
    max_messages=10,
    context_window=4096,                 # Token massimi per la finestra di contesto
    summarize_old_messages=True,          # Riassumi messaggi vecchi per risparmiare token
)
```

### GenerationParams

Per override puntuali dei parametri di generazione, passa un oggetto `GenerationParams` a `chat()`:

```python
from linkbay_ai import GenerationParams

params = GenerationParams(
    model="deepseek-reasoner",
    max_tokens=500,
    temperature=0.7,
    top_p=0.9
)

response = await ai.chat("Spiega la relatività", params=params)
```

---

## API Reference

### AIOrchestrator

```python
orchestrator = AIOrchestrator(
    budget_config: Optional[BudgetConfig] = None,
    conversation_config: Optional[ConversationConfig] = None,
    enable_cache: bool = True,
    enable_tools: bool = True
)

# Metodi principali
await orchestrator.chat(
    prompt: str,
    model: Optional[str] = None,
    use_conversation: bool = True,
    use_cache: bool = True,
    use_tools: bool = False,
    max_retries: int = 3,
    params: Optional[GenerationParams] = None
) -> AIResponse

async for chunk in orchestrator.chat_stream(
    prompt: str,
    model: Optional[str] = None,
    use_conversation: bool = True,
    params: Optional[GenerationParams] = None
) -> AsyncIterator[str]

orchestrator.register_provider(provider: BaseProvider, priority: int = 99)
orchestrator.get_analytics() -> Dict[str, Any]
orchestrator.reset_conversation()
orchestrator.add_system_prompt(prompt: str)
```

### Providers

```python
# Provider supportati
- DeepSeekProvider(config: ProviderConfig)
- OpenAIProvider(config: ProviderConfig)
- LocalProvider(config: ProviderConfig)   # mock per test/fallback

# Metodi comuni
await provider.chat(messages: List[Dict], params: GenerationParams) -> AIResponse
async for chunk in provider.stream(messages: List[Dict], params: GenerationParams) -> AsyncIterator[str]
provider.get_stats() -> Dict[str, Any]   # richieste, errori, uptime
provider.is_available() -> bool
```

### CostController

```python
controller = CostController(config: BudgetConfig)
await controller.check_budget(tokens: int, model: str) -> bool   # True se ok
controller.record_usage(tokens: int, model: str)
controller.get_current_usage() -> Dict   # token usati, costo stimato
controller.reset_budgets()
```

### SemanticCache

```python
cache = SemanticCache(similarity_threshold=0.95, max_entries=1000, ttl=86400)
await cache.get_cached_response(query: str) -> Optional[str]
await cache.cache_response(query: str, response: str)
cache.get_stats() -> Dict   # hit, miss, size
cache.clear_cache()
```

---

## Error Handling

La libreria definisce eccezioni specifiche per una gestione granulare:

```python
from linkbay_ai import (
    BudgetExceededException,
    ProviderError,
    ProviderTimeoutError,
    ProviderRateLimitError,
    ProviderUnavailableError,
    AllProvidersFailedException,
    ToolExecutionError,
    ToolValidationError,
    ToolNotFoundError,
    CacheError,
)

try:
    response = await ai.chat("Prompt difficile")
except BudgetExceededException:
    print("⚠️ Budget superato – ferma le richieste o aumenta i limiti.")
except ProviderRateLimitError:
    print("⏳ Rate limit – riprovo con backoff esponenziale (gestito automaticamente).")
except ProviderTimeoutError:
    print("⌛ Timeout – il provider è lento, passo al fallback.")
except ProviderUnavailableError:
    print("🔌 Provider non disponibile.")
except AllProvidersFailedException:
    print("❌ Nessun provider ha risposto correttamente.")
except ToolExecutionError as e:
    print(f"🔧 Errore durante esecuzione tool: {e}")
```

---

## Best Practices

1. **Imposta sempre i budget** – Previeni costi a sorpresa.
2. **Usa il contesto di conversazione** – Mantieni lo stato tra i turni.
3. **Abilita la cache** – Evita richieste duplicate e risparmia token.
4. **Usa lo streaming** – Migliore UX per risposte lunghe.
5. **Monitora le analytics** – Tieni traccia di performance e costi.
6. **Gestisci gli errori dei provider** – Implementa graceful degradation.
7. **Registra i provider in ordine di priorità** – Il più importante (e.g., più economico/veloce) per primo.

---

## Troubleshooting

| Problema | Causa | Soluzione |
|----------|-------|-----------|
| `Client.__init__() got an unexpected keyword argument 'proxies'` | L'SDK OpenAI ≥1.0 non accetta `proxies` | Configura proxy via variabili d'ambiente (`HTTP_PROXY`, `HTTPS_PROXY`) e rimuovi il parametro. |
| `sentence-transformers` non trovato | Cache attivata senza dipendenza opzionale | Installa `linkbay-ai[cache]` oppure imposta `enable_cache=False`. |
| `RuntimeError: Event loop is closed` | `asyncio.run` dentro un loop già attivo | Usa `await ai.chat` diretto (es. in FastAPI) invece di `asyncio.run()`. |
| `BudgetExceededException` frequente | Limiti troppo bassi | Alza le soglie o abilita la cache per ridurre i token. |
| Rate limit errors | Troppe richieste in poco tempo | Sono gestiti automaticamente con retry e backoff; se persistono, aumenta il delay tra le richieste o usa provider alternativi. |
| Timeout errors | Richiesta troppo complessa o provider lento | Aumenta `timeout` in `ProviderConfig` o usa streaming per risposte lunghe. |

---

## FAQ – performance e sicurezza

- **Cache & memoria:** 1000 entry con `MiniLM` occupano circa 70 MB. Riduci `max_entries` se hai bisogno di un footprint minore.
- **Overhead embedding:** ~3–5 ms su CPU moderna. Per workload non ripetitivi disabilita la cache.
- **Persistenza cache:** al momento in‑memory. Puoi derivare `SemanticCache` per usare Redis o un database.
- **Logging / metriche:** `AIOrchestrator` usa il modulo `logging` di Python. Collega handler strutturati o esponi `get_analytics()` come endpoint.
- **Sicurezza input:** nessuna sanitizzazione automatica. Filtra i prompt e gestisci i dati personali (PII) a livello di applicazione.
- **Gestione chiavi:** conserva le API key in un secret manager (Vault, AWS Secrets Manager). LinkBay-AI non salva né ruota le credenziali.

---

## Licenza

MIT © Alessio Quagliara

---

## Supporto e Roadmap

- **Issues:** [https://github.com/AlessioQuagliara/linkbay_ai/issues](https://github.com/AlessioQuagliara/linkbay_ai/issues)
- **Email:** quagliara.alessio@gmail.com
- **Docs:** [https://linkbay.io/docs](https://linkbay-cms.com/docs) *(in costruzione)*

Contribuisci, apri una issue o raccontaci come stai usando la libreria 🧡

****

*Documentazione generata unendo le versioni 0.2.1 e successive.*