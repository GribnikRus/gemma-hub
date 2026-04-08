import requests
from config import OLLAMA_URL, OLLAMA_MODEL_VISION

def process_image(prompt: str, images_base64: list) -> str:
    """Отправляет промпт + изображения (base64) в Ollama."""
    try:
        payload = {
            "model": OLLAMA_MODEL_VISION,
            "prompt": prompt.strip(),
            "images": images_base64,
            "stream": False
        }
        resp = requests.post(OLLAMA_URL, json=payload, timeout=180)
        resp.raise_for_status()
        return resp.json().get("response", "Модель не вернула ответ.")
    except requests.exceptions.Timeout:
        return "⏱️ Таймаут: обработка изображения заняла много времени."
    except Exception as e:
        return f"❌ Ошибка: {str(e)}"