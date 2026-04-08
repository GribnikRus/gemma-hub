import requests
from config import OLLAMA_URL, OLLAMA_MODEL_CHAT

def process_chat(prompt: str) -> str:
    """Отправляет текстовый запрос в Ollama и возвращает ответ."""
    try:
        payload = {
            "model": OLLAMA_MODEL_CHAT,
            "prompt": prompt.strip(),
            "stream": False
        }
        resp = requests.post(OLLAMA_URL, json=payload, timeout=120)
        resp.raise_for_status()
        return resp.json().get("response", "Модель не вернула ответ.")
    except requests.exceptions.Timeout:
        return "⏱️ Таймаут: модель думает слишком долго."
    except Exception as e:
        return f"❌ Ошибка соединения: {str(e)}"