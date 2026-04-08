# Тесты для проекта Gemma Hub

## Запуск тестов

```bash
python3 tests/test_auth.py -v
```

## Структура тестов

### TestPasswordHashing
Тесты функций хеширования паролей:
- `test_hash_password_returns_string` - проверка возврата строки
- `test_hash_password_different_hashes` - проверка детерминированности SHA-256
- `test_hash_password_consistent` - проверка стабильности хеширования
- `test_hash_password_same_password_verifies` - проверка верификации пароля
- `test_verify_password_wrong_password` - проверка отклонения неверного пароля
- `test_hash_password_empty_string` - работа с пустой строкой
- `test_hash_password_special_chars` - работа со спецсимволами

### TestDatabaseFunctions
Тесты функций работы с БД (с моками):
- `test_get_user_by_client_uuid_success` - успешное получение пользователя
- `test_get_user_by_client_uuid_not_found` - пользователь не найден
- `test_register_user_success` - успешная регистрация
- `test_register_user_duplicate_login` - дублирование логина
- `test_authenticate_user_success` - успешная аутентификация
- `test_authenticate_user_wrong_password` - неверный пароль
- `test_authenticate_user_not_found` - пользователь не найден

### TestAuthIntegration
Интеграционные тесты (требуют подключения к PostgreSQL):
- `test_full_auth_flow_skipped` - полный цикл аутентификации (пропускается без БД)

## Зависимости

Для запуска тестов требуется только стандартная библиотека Python 3.12+:
- unittest
- unittest.mock

Подключение к базе данных не требуется для модульных тестов (используются моки).

## Результаты

Все тесты проходят успешно:
```
Ran 15 tests in 0.040s

OK (skipped=1)
```
