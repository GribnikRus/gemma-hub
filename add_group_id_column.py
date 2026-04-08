#!/usr/bin/env python3
"""Скрипт для добавления колонки group_id в таблицу task_history."""

import psycopg2
from config import DATABASE_URL
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_group_id_column():
    """Добавляет колонку group_id в таблицу task_history."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True  # Важно для ALTER TABLE
        cur = conn.cursor()

        logger.info("🔍 Проверка наличия колонки group_id в таблице task_history...")
        
        # Проверяем, существует ли уже колонка group_id
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'task_history' AND column_name = 'group_id';
        """)
        
        if cur.fetchone():
            logger.info("✅ Колонка group_id уже существует в таблице task_history")
        else:
            logger.info("➕ Добавление колонки group_id в таблицу task_history...")
            cur.execute("""
                ALTER TABLE task_history
                ADD COLUMN group_id INTEGER REFERENCES groups(id) ON DELETE SET NULL;
            """)
            logger.info("✅ Колонка group_id успешно добавлена")
            
        cur.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Ошибка при добавлении колонки group_id: {e}")
        raise

if __name__ == "__main__":
    add_group_id_column()
    logger.info("🎉 Миграция завершена успешно!")
