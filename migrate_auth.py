#!/usr/bin/env python3
"""Скрипт миграции БД для добавления таблицы пользователей."""

import psycopg2
from config import DATABASE_URL
import logging
import uuid

# Импортируем функцию хеширования из db.py вместо дублирования
from db import hash_password

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate():
    """Создаёт таблицу users и генерирует client_uuid для существующих записей."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Создаём таблицу users с проверкой всех колонок
        logger.info("📝 Создание/проверка таблицы users...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                login VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(64) NOT NULL,
                name VARCHAR(255),
                client_uuid VARCHAR(36) UNIQUE NOT NULL DEFAULT gen_random_uuid(),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Проверяем наличие всех необходимых колонок
        logger.info("🔍 Проверка колонок таблицы users...")
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' 
            ORDER BY ordinal_position;
        """)
        existing_columns = [row[0] for row in cur.fetchall()]
        logger.info(f"📊 Существующие колонки в users: {existing_columns}")
        
        # Добавляем отсутствующие колонки
        required_columns = {
            'id': 'ALTER TABLE users ADD COLUMN IF NOT EXISTS id SERIAL PRIMARY KEY;',
            'login': 'ALTER TABLE users ADD COLUMN IF NOT EXISTS login VARCHAR(255) UNIQUE NOT NULL;',
            'password_hash': 'ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(64) NOT NULL;',
            'name': 'ALTER TABLE users ADD COLUMN IF NOT EXISTS name VARCHAR(255);',
            'client_uuid': 'ALTER TABLE users ADD COLUMN IF NOT EXISTS client_uuid VARCHAR(36) UNIQUE NOT NULL DEFAULT gen_random_uuid();',
            'created_at': 'ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;'
        }
        
        for col_name, alter_query in required_columns.items():
            if col_name not in existing_columns:
                logger.info(f"➕ Добавление колонки '{col_name}' в таблицу users...")
                try:
                    cur.execute(alter_query)
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось добавить колонку {col_name}: {e}")
        
        # Проверяем, есть ли колонка client_uuid в таблице clients
        logger.info("🔍 Проверка таблицы clients...")
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'clients' AND column_name = 'client_uuid';
        """)
        
        if not cur.fetchone():
            logger.info("➕ Добавление колонки client_uuid в таблицу clients...")
            cur.execute("""
                ALTER TABLE clients
                ADD COLUMN client_uuid VARCHAR(36) DEFAULT gen_random_uuid();
            """)
            
            # Обновляем существующие записи
            cur.execute("""
                UPDATE clients
                SET client_uuid = gen_random_uuid()
                WHERE client_uuid IS NULL;
            """)
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info("✅ Миграция успешно завершена!")
        logger.info("📊 Таблица users создана/проверена")
        logger.info("📊 Колонка client_uuid добавлена в таблицу clients")
        
    except Exception as e:
        logger.error(f"❌ Ошибка миграции: {e}")
        raise

if __name__ == '__main__':
    migrate()
