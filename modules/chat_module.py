import requests

OLLAMA_URL = "http://192.168.0.166:11434/api/generate"
MODEL = "gemma4:e4b"

def process_chat(prompt: str) -> str:
    """Отправляет текстовый запрос в Ollama и возвращает ответ."""
    try:
        payload = {
            "model": MODEL,
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