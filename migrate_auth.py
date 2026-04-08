#!/usr/bin/env python3
"""Скрипт миграции БД для добавления таблицы пользователей."""

import psycopg2
from config import DATABASE_URL
import logging
import uuid
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def hash_password(password):
    """Хеширует пароль с помощью SHA-256."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def migrate():
    """Создаёт таблицу users и генерирует client_uuid для существующих записей."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Создаём таблицу users
        logger.info("📝 Создание таблицы users...")
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
        logger.info("📊 Таблица users создана")
        logger.info("📊 Колонка client_uuid добавлена в таблицу clients")
        
    except Exception as e:
        logger.error(f"❌ Ошибка миграции: {e}")
        raise

if __name__ == '__main__':
    migrate()
