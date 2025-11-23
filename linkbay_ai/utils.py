from .core import AIOrchestrator
from .schemas import GenerationParams
from typing import Dict, Any, List

def generate_html_tailwind(ai: AIOrchestrator, description: str) -> str:
    prompt = f"""
    Genera codice HTML con Tailwind CSS per: {description}
    Restituisci SOLO il codice HTML, senza commenti o spiegazioni.
    Usa classi Tailwind per lo styling.
    """
    return ai.chat(prompt, model="deepseek-chat")

def fill_form_fields(ai: AIOrchestrator, user_input: str, fields: List[str]) -> Dict[str, str]:
    prompt = f"""
    Dall'input utente: "{user_input}"
    Estrai i valori per questi campi: {', '.join(fields)}
    Restituisci SOLO un JSON con chiavi: {', '.join(fields)}
    Per campi non trovati, usa null.
    """
    response = ai.chat(prompt, model="deepseek-chat")
    return _parse_json_response(response)

def analyze_sales_data(ai: AIOrchestrator, csv_data: str) -> str:
    prompt = f"""
    Analizza questi dati di vendita e fornisci insights:
    {csv_data}
    
    Cerca:
    - Andamento vendite
    - Prodotti top
    - Suggerimenti miglioramento
    """
    return ai.chat(prompt, model="deepseek-reasoning")

def analyze_traffic_data(ai: AIOrchestrator, log_data: str) -> str:
    prompt = f"""
    Analizza questi dati di traffico:
    {log_data}
    
    Cerca:
    - Picchi di traffico
    - Pagine più visitate
    - Problemi prestazioni
    """
    return ai.chat(prompt, model="deepseek-reasoning")

def _parse_json_response(response: str) -> Dict[str, str]:
    import json
    try:
        return json.loads(response.strip())
    except:
        return {"error": "Failed to parse AI response as JSON"}