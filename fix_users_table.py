#!/usr/bin/env python3
"""
Скрипт для проверки и исправления структуры таблицы users.
"""
import psycopg2

DATABASE_URL = "postgresql://bot_user:YesNo1977@192.168.0.34:5432/sleep_data_db"

def check_and_fix_users_table():
    try:
        # Подключаемся с таймаутом
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        cursor = conn.cursor()
        
        print("🔍 Проверяем таблицу users...")
        
        # Проверяем существование таблицы
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'users'
            );
        """)
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            print("⚠️ Таблица users не существует. Создаем...")
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
            print("✅ Таблица users создана!")
        else:
            print("ℹ️ Таблица users существует. Проверяем колонки...")
            
            # Получаем список колонок
            cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'users'
                ORDER BY ordinal_position;
            """)
            columns = cursor.fetchall()
            
            print(f"📋 Текущие колонки: {[col[0] for col in columns]}")
            
            # Проверяем наличие id
            has_id = any(col[0] == 'id' for col in columns)
            
            if not has_id:
                print("❌ Колонка 'id' отсутствует! Пересоздаем таблицу...")
                cursor.execute("DROP TABLE IF EXISTS users CASCADE;")
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
                print("✅ Таблица users пересоздана с правильной структурой!")
            else:
                print("✅ Таблица users имеет корректную структуру!")
        
        # Проверяем clients
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'clients' AND column_name = 'client_uuid'
            );
        """)
        has_client_uuid = cursor.fetchone()[0]
        
        if not has_client_uuid:
            print("🔨 Добавляем client_uuid в таблицу clients...")
            cursor.execute("ALTER TABLE clients ADD COLUMN client_uuid VARCHAR(255);")
            conn.commit()
            print("✅ Колонка client_uuid добавлена!")
        else:
            print("✅ client_uuid уже есть в таблице clients.")
        
        cursor.close()
        conn.close()
        print("\n🎉 Миграция завершена успешно!")
        return True
        
    except psycopg2.OperationalError as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        print("Проверьте, что сервер PostgreSQL доступен по адресу 192.168.0.34:5432")
        return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

if __name__ == "__main__":
    check_and_fix_users_table()
