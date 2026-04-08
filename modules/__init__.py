# modules/__init__.py
"""
Модули для обработки задач:
- chat_module: текстовый чат с Ollama
- vision_module: обработка изображений через Ollama
- transcribe_module: транскрибация аудио (заглушка)
"""

from .chat_module import process_chat
from .vision_module import process_image
from .transcribe_module import transcribe_audio

__all__ = ['process_chat', 'process_image', 'transcribe_audio']
