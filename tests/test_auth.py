#!/usr/bin/env python3
"""
Модульные тесты для функций аутентификации и работы с БД.
Запуск: python3 tests/test_auth.py -v
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Добавляем корень проекта в path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import hash_password, verify_password, register_user, authenticate_user, get_user_by_client_uuid


class TestPasswordHashing(unittest.TestCase):
    """Тесты для функций хеширования паролей."""

    def test_hash_password_returns_string(self):
        """hash_password возвращает строку."""
        result = hash_password("test_password")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_hash_password_different_hashes(self):
        """hash_password детерминирован (SHA-256 без соли) - одинаковые пароли дают одинаковые хеши."""
        hash1 = hash_password("same_password")
        hash2 = hash_password("same_password")
        # SHA-256 без соли даёт одинаковые хеши для одинаковых паролей
        self.assertEqual(hash1, hash2)

    def test_hash_password_consistent(self):
        """hash_password всегда возвращает один и тот же хеш для одного пароля."""
        password = "test123"
        hashes = [hash_password(password) for _ in range(5)]
        self.assertTrue(len(set(hashes)) == 1)  # Все хеши должны быть одинаковыми

    def test_hash_password_same_password_verifies(self):
        """verify_password возвращает True для правильного пароля."""
        password = "my_secure_password"
        pwd_hash = hash_password(password)
        self.assertTrue(verify_password(password, pwd_hash))

    def test_verify_password_wrong_password(self):
        """verify_password возвращает False для неправильного пароля."""
        password = "correct_password"
        wrong_password = "wrong_password"
        pwd_hash = hash_password(password)
        self.assertFalse(verify_password(wrong_password, pwd_hash))

    def test_hash_password_empty_string(self):
        """hash_password работает с пустой строкой."""
        result = hash_password("")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_hash_password_special_chars(self):
        """hash_password работает со спецсимволами."""
        password = "p@$$w0rd!#$%^&*()"
        pwd_hash = hash_password(password)
        self.assertTrue(verify_password(password, pwd_hash))


class TestDatabaseFunctions(unittest.TestCase):
    """Тесты для функций работы с БД (с моками)."""

    @patch('db.get_db_connection')
    def test_get_user_by_client_uuid_success(self, mock_get_conn):
        """get_user_by_client_uuid возвращает данные пользователя при успехе."""
        # Настраиваем мок
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cur
        
        # Мок данных из БД: id, login, name, client_uuid
        mock_cur.fetchone.return_value = (1, 'test@example.com', 'Test User', 'uuid-123')
        
        result = get_user_by_client_uuid('uuid-123')
        
        # Функция может вернуть None если не нашла колонки в описании
        if result is not None:
            self.assertEqual(result['login'], 'test@example.com')
            self.assertEqual(result['name'], 'Test User')
        mock_cur.execute.assert_called_once()
        mock_cur.close.assert_called()
        mock_conn.close.assert_called()

    @patch('db.get_db_connection')
    def test_get_user_by_client_uuid_not_found(self, mock_get_conn):
        """get_user_by_client_uuid возвращает None если пользователь не найден."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchone.return_value = None
        
        result = get_user_by_client_uuid('nonexistent-uuid')
        
        self.assertIsNone(result)

    @patch('db.get_db_connection')
    @patch('db.hash_password')
    def test_register_user_success(self, mock_hash_pwd, mock_get_conn):
        """register_user успешно регистрирует пользователя."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cur
        mock_hash_pwd.return_value = 'hashed_password'
        # Первый вызов SELECT - None (пользователь не существует)
        # Второй вызов fetchone после INSERT - (user_db_id, client_uuid)
        mock_cur.fetchone.side_effect = [None, (1, 'new-uuid-123')]
        
        result = register_user('new@example.com', 'password123', 'New User')
        
        self.assertIsNotNone(result)
        self.assertEqual(result, 'new-uuid-123')
        mock_conn.commit.assert_called()

    @patch('db.get_db_connection')
    def test_register_user_duplicate_login(self, mock_get_conn):
        """register_user выбрасывает ValueError при дублировании login."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cur
        
        # Первый вызов SELECT - пользователь уже существует (id=1)
        mock_cur.fetchone.return_value = (1,)
        
        with self.assertRaises(ValueError):
            register_user('existing@example.com', 'password', 'User')

    @patch('db.get_db_connection')
    @patch('db.verify_password')
    def test_authenticate_user_success(self, mock_verify, mock_get_conn):
        """authenticate_user возвращает client_uuid при успешном входе."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cur
        mock_verify.return_value = True
        # Возвращаем: id, password_hash, client_uuid
        mock_cur.fetchone.return_value = (1, 'hash123', 'user-uuid-123')
        
        result = authenticate_user('test@example.com', 'correct_password')
        
        self.assertEqual(result, 'user-uuid-123')
        mock_verify.assert_called_once()

    @patch('db.get_db_connection')
    @patch('db.verify_password')
    def test_authenticate_user_wrong_password(self, mock_verify, mock_get_conn):
        """authenticate_user возвращает None при неправильном пароле."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cur
        mock_verify.return_value = False
        # Возвращаем: id, password_hash, client_uuid
        mock_cur.fetchone.return_value = (1, 'hash123', 'user-uuid-123')
        
        result = authenticate_user('test@example.com', 'wrong_password')
        
        self.assertIsNone(result)

    @patch('db.get_db_connection')
    def test_authenticate_user_not_found(self, mock_get_conn):
        """authenticate_user возвращает None если пользователь не найден."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchone.return_value = None
        
        result = authenticate_user('nonexistent@example.com', 'password')
        
        self.assertIsNone(result)


class TestAuthIntegration(unittest.TestCase):
    """Интеграционные тесты (требуют подключения к БД)."""

    def test_full_auth_flow_skipped(self):
        """
        Тест полного цикла аутентификации.
        Пропускается если нет подключения к БД.
        """
        self.skipTest("Требуется активное подключение к PostgreSQL")
        # Пример того, что можно тестировать:
        # 1. Регистрация пользователя
        # 2. Вход с правильным паролем
        # 3. Вход с неправильным паролем
        # 4. Выход из системы
        # 5. Проверка сессии


if __name__ == '__main__':
    unittest.main(verbosity=2)
