# LinkBay-AI 

[![License](https://img.shields.io/badge/license-MIT-blue)]()

**AI per CMS LinkBay - analizza dati, orchestra lavoro, completa form e genera HTML**

## Indice

- [Installazione](#installazione)
- [Configurazione](#configurazione)
- [Utilizzo Rapido](#utilizzo-rapido)
- [Funzionalità](#funzionalità)
- [Esempi](#esempi)
- [Licenza](#licenza)

## Installazione

```bash
pip install git+https://github.com/AlessioQuagliara/linkbay-ai.git
```

## Configurazione

from linkbay_ai import DeepSeekProvider, ProviderConfig

# Configura il provider DeepSeek

```bash
config = ProviderConfig(
    api_key="tuo-api-key-deepseek",
    base_url="https://api.deepseek.com"
)

provider = DeepSeekProvider(config)
```
## utilizzo-rapido

```bash
from linkbay_ai import AIOrchestrator, DeepSeekProvider, ProviderConfig

# Setup
config = ProviderConfig(api_key="tuo-key", base_url="https://api.deepseek.com")
provider = DeepSeekProvider(config)

ai = AIOrchestrator()
ai.register_provider("deepseek", provider)

# Chat semplice
risposta = ai.chat("Ciao, come stai?")
print(risposta)
```

## Funzionalità
```bash
risposta = ai.chat("Spiega il machine learning")
```

# Compila il form 
```bash
campi = ["nome", "email", "telefono"]
dati = fill_form_fields(ai, "Mi chiamo Mario, cell 123456", campi)
# {'nome': 'Mario', 'email': None, 'telefono': '123456'}
```

# Genera HTML Tailwind
```bash
html = generate_html_tailwind(ai, "bottone rosso con testo bianco")
```
# Analisi Vendite
```bash
report = analyze_sales_data(ai, "vendite.csv content...")
```

# Analisi Traffico
```bash
insights = analyze_traffic_data(ai, "log traffico...")
```

## esempi

# Modello Reasoning (pensante)
```bash
analisi = ai.chat("Analizza questi dati...", model="deepseek-reasoning")
```

# Modello Chat (veloce)
```bash
risposta = ai.chat("Traduci questo testo", model="deepseek-chat")
```

# Esempio d'uso dentro al programma
```bash
from linkbay_ai import AIOrchestrator, DeepSeekProvider, ProviderConfig

config = ProviderConfig(
    api_key="sk-tua-chiave",
    base_url="https://api.deepseek.com"
)

ai = AIOrchestrator()
ai.register_provider("deepseek", DeepSeekProvider(config))

# Usa tutte le funzionalità!
html = generate_html_tailwind(ai, "navbar responsive")
```