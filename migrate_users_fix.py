#!/usr/bin/env python3
"""
Скрипт миграции для создания/исправления таблицы пользователей.
Запускается один раз для настройки БД под авторизацию.
"""
import os
import sys
from db import get_db_connection

def migrate_users_table():
    """Создает таблицу users, если она не существует, или исправляет её структуру."""
    conn = get_db_connection()
    if not conn:
        print("❌ Не удалось подключиться к базе данных")
        return False
    
    try:
        cursor = conn.cursor()
        
        # Проверяем существование таблицы
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'users'
            );
        """)
        table_exists = cursor.fetchone()[0]
        
        if table_exists:
            print("⚠️ Таблица users уже существует. Проверяем структуру...")
            # Проверяем наличие колонки id
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name = 'id'
                );
            """)
            has_id = cursor.fetchone()[0]
            
            if not has_id:
                print("❌ В таблице users отсутствует колонка id. Пересоздаем таблицу...")
                cursor.execute("DROP TABLE IF EXISTS users CASCADE;")
                conn.commit()
                table_exists = False
            else:
                print("✅ Таблица users существует и имеет корректную структуру.")
                return True

        if not table_exists:
            print("🔨 Создаем таблицу users...")
            cursor.execute("""
                CREATE TABLE users (
                    id SERIAL PRIMARY KEY,
                    login VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    name VARCHAR(255),
                    client_uuid VARCHAR(255) UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()
            print("✅ Таблица users успешно создана!")
            
            # Проверяем наличие client_uuid в таблице clients
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'clients' AND column_name = 'client_uuid'
                );
            """)
            has_client_uuid = cursor.fetchone()[0]
            
            if not has_client_uuid:
                print("🔨 Добавляем колонку client_uuid в таблицу clients...")
                cursor.execute("ALTER TABLE clients ADD COLUMN client_uuid VARCHAR(255);")
                conn.commit()
                print("✅ Колонка client_uuid добавлена в таблицу clients!")
            else:
                print("✅ Колонка client_uuid уже существует в таблице clients.")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка миграции: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    print("🚀 Запуск миграции базы данных для авторизации...")
    success = migrate_users_table()
    if success:
        print("🎉 Миграция завершена успешно!")
        sys.exit(0)
    else:
        print("💥 Миграция завершилась с ошибкой!")
        sys.exit(1)
