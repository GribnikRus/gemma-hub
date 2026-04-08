# tasks.py
from celery import Celery
from config import OLLAMA_URL, CELERY_BROKER_URL, CELERY_RESULT_BACKEND, OLLAMA_MODEL_CHAT, OLLAMA_MODEL_VISION
import requests
from db import save_task_history
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

celery_app = Celery('gemma_tasks', broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)

@celery_app.task(bind=True, max_retries=3)
def process_chat_task(self, prompt, user_ip, client_id, group_id=None):
    try:
        logger.info(f"💬 Начинаю обработку чата (client_id: {client_id}, group_id: {group_id}): {prompt[:30]}...")
        payload = {
            "model": OLLAMA_MODEL_CHAT,
            "prompt": prompt,
            "stream": False
        }
        response = requests.post(OLLAMA_URL, json=payload, timeout=600)
        response.raise_for_status()
        result = response.json().get("response", "Модель не вернула ответ.")

        # Сохраняем в БД с client_id и group_id
        save_task_history(user_ip, "chat", prompt, result, client_id=client_id, group_id=group_id)
        logger.info("✅ Задача чата завершена")
        return result

    except requests.exceptions.Timeout:
        error_msg = f"⏰ Таймаут при запросе к Ollama при обработке чата."
        logger.error(error_msg)
        save_task_history(user_ip, "chat", prompt, error_msg, status="failed", client_id=client_id, group_id=group_id)
        raise self.retry(exc=Exception(error_msg), countdown=60)

    except requests.exceptions.RequestException as e:
        error_msg = f"❌ Ошибка соединения с Ollama при обработке чата: {e}"
        logger.error(error_msg)
        save_task_history(user_ip, "chat", prompt, error_msg, status="failed", client_id=client_id, group_id=group_id)
        raise self.retry(exc=e, countdown=60)

    except Exception as exc:
        error_msg = f"❌ Непредвиденная ошибка при обработке чата: {exc}"
        logger.error(error_msg)
        save_task_history(user_ip, "chat", prompt, error_msg, status="failed", client_id=client_id, group_id=group_id)
        raise self.retry(exc=exc, countdown=60)

@celery_app.task(bind=True, max_retries=3)
def process_vision_task(self, prompt, images_b64, user_ip, client_id): # Добавили client_id
    try:
        logger.info(f"🖼️ Начинаю обработку изображения (client_id: {client_id}): {prompt[:30]}..., images: {len(images_b64)}")
        payload = {
            "model": OLLAMA_MODEL_VISION,
            "prompt": prompt,
            "images": images_b64,
            "stream": False
        }
        response = requests.post(OLLAMA_URL, json=payload, timeout=900)
        response.raise_for_status()
        result = response.json().get("response", "Модель не вернула ответ.")

        # Сохраняем в БД с client_id
        save_task_history(user_ip, "vision", prompt, result, images_count=len(images_b64), client_id=client_id)
        logger.info("✅ Задача изображения завершена")
        return result

    except requests.exceptions.Timeout:
        error_msg = f"⏰ Таймаут при запросе к Ollama (изображение). Попробуйте ещё раз или используйте изображение меньшего размера."
        logger.error(error_msg)
        save_task_history(user_ip, "vision", prompt, error_msg, images_count=len(images_b64), status="failed", client_id=client_id)
        # Не делаем retry при таймауте, так как это может занять много времени
        return error_msg

    except requests.exceptions.RequestException as e:
        error_msg = f"❌ Ошибка соединения с Ollama при обработке изображения: {e}"
        logger.error(error_msg)
        save_task_history(user_ip, "vision", prompt, error_msg, images_count=len(images_b64), status="failed", client_id=client_id)
        raise self.retry(exc=e, countdown=60)

    except Exception as exc:
        error_msg = f"❌ Непредвиденная ошибка при обработке изображения: {exc}"
        logger.error(error_msg)
        save_task_history(user_ip, "vision", prompt, error_msg, images_count=len(images_b64), status="failed", client_id=client_id)
        raise self.retry(exc=exc, countdown=60)

@celery_app.task(bind=True, max_retries=3)
def transcribe_audio_task(self, audio_file_path, user_ip, client_id): # Добавили client_id
    # Пока заглушка
    result = f"[Транскрибация файла {audio_file_path}]"
    save_task_history(user_ip, "transcribe", f"Audio: {audio_file_path}", result, client_id=client_id)
    logger.info("✅ Задача транскрибации завершена")
    return result