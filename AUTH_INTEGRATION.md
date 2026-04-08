# Инструкция по внедрению авторизации логин/пароль

## 1. Миграция базы данных

Когда PostgreSQL станет доступен, выполните миграцию:

```bash
source venv/bin/activate
python3 migrate_auth.py
```

Это создаст:
- Таблицу `users` с полями: id, login, password_hash, name, client_uuid, created_at
- Колонку `client_uuid` в таблице `clients` (если её нет)

## 2. Изменения в backend (app.py)

В app.py уже добавлены маршруты:
- `/api/auth/register` - регистрация нового пользователя
- `/api/auth/login` - вход пользователя  
- `/api/auth/logout` - выход из системы
- `/api/auth/status` - проверка статуса аутентификации

## 3. Изменения в frontend (index.html)

### A. Добавьте стили для модального окна авторизации

В секцию `<style>` добавьте:

```css
/* Стили для модального окна авторизации */
.auth-modal {
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.5);
    justify-content: center;
    align-items: center;
    z-index: 1000;
}
.auth-modal-content {
    background: white;
    padding: 2rem;
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    max-width: 400px;
    width: 90%;
}
.auth-modal h2 { margin-bottom: 1rem; text-align: center; color: #111827; }
.auth-form input {
    width: 100%;
    padding: 0.8rem;
    border: 1px solid var(--border);
    border-radius: 8px;
    margin-bottom: 1rem;
    font-size: 1rem;
}
.auth-form button {
    width: 100%;
    padding: 0.8rem;
    background: var(--primary);
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    cursor: pointer;
    transition: 0.2s;
    margin-bottom: 0.5rem;
}
.auth-form button:hover { background: var(--primary-hover); }
.auth-toggle {
    text-align: center;
    margin-top: 1rem;
    font-size: 0.9rem;
}
.auth-toggle a {
    color: var(--primary);
    cursor: pointer;
    text-decoration: underline;
}
.auth-status {
    position: absolute;
    top: 1rem;
    right: 1rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
```

### B. Добавьте HTML модального окна

После закрывающего тега `</div>` контейнера и перед `<script>` добавьте:

```html
<!-- Модальное окно авторизации -->
<div id="auth-modal" class="auth-modal">
    <div class="auth-modal-content">
        <h2 id="auth-modal-title">🔑 Вход в систему</h2>
        
        <!-- Форма входа -->
        <div id="login-form-container" class="auth-form">
            <input type="text" id="login-username" placeholder="Логин" autocomplete="username">
            <input type="password" id="login-password" placeholder="Пароль" autocomplete="current-password">
            <button onclick="loginUser()">Войти</button>
            <div class="auth-toggle">
                Нет аккаунта? <a onclick="toggleAuthForm('register')">Зарегистрироваться</a>
            </div>
        </div>
        
        <!-- Форма регистрации -->
        <div id="register-form-container" class="auth-form" style="display: none;">
            <input type="text" id="register-username" placeholder="Придумайте логин" autocomplete="username">
            <input type="password" id="register-password" placeholder="Придумайте пароль" autocomplete="new-password">
            <input type="text" id="register-name" placeholder="Ваше имя (необязательно)">
            <button onclick="registerUser()">Зарегистрироваться</button>
            <div class="auth-toggle">
                Уже есть аккаунт? <a onclick="toggleAuthForm('login')">Войти</a>
            </div>
        </div>
    </div>
</div>

<!-- Контейнер статуса авторизации -->
<div id="auth-status-container" class="auth-status"></div>
```

### C. Добавьте JavaScript функции

В начало секции `<script>`, после объявления переменных, добавьте:

```javascript
// === АУТЕНТИФИКАЦИЯ ===
let currentUser = null;
let isLoggedIn = false;

async function checkAuthStatus() {
    try {
        const res = await fetch('/api/auth/status');
        const data = await res.json();
        if (data.authenticated) {
            isLoggedIn = true;
            currentUser = { client_id: data.client_id };
            updateAuthUI();
            hideAuthModal();
        } else {
            showAuthModal();
        }
    } catch (e) {
        console.error('Ошибка проверки статуса:', e);
        showAuthModal();
    }
}

function showAuthModal() {
    const modal = document.getElementById('auth-modal');
    if (modal) modal.style.display = 'flex';
}

function hideAuthModal() {
    const modal = document.getElementById('auth-modal');
    if (modal) modal.style.display = 'none';
}

function toggleAuthForm(formType) {
    const loginForm = document.getElementById('login-form-container');
    const registerForm = document.getElementById('register-form-container');
    const modalTitle = document.getElementById('auth-modal-title');
    
    if (formType === 'login') {
        loginForm.style.display = 'block';
        registerForm.style.display = 'none';
        modalTitle.textContent = '🔑 Вход в систему';
    } else {
        loginForm.style.display = 'none';
        registerForm.style.display = 'block';
        modalTitle.textContent = '📝 Регистрация';
    }
}

async function loginUser() {
    const loginInput = document.getElementById('login-username').value.trim();
    const passwordInput = document.getElementById('login-password').value;
    
    if (!loginInput || !passwordInput) {
        alert('Введите логин и пароль');
        return;
    }
    
    try {
        const res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ login: loginInput, password: passwordInput })
        });
        const data = await res.json();
        if (data.success) {
            isLoggedIn = true;
            currentUser = { client_id: data.client_uuid, login: loginInput };
            hideAuthModal();
            updateAuthUI();
            alert('Вы успешно вошли в систему!');
        } else {
            alert('Ошибка: ' + data.error);
        }
    } catch (e) {
        alert('Ошибка соединения с сервером');
    }
}

async function registerUser() {
    const loginInput = document.getElementById('register-username').value.trim();
    const passwordInput = document.getElementById('register-password').value;
    const nameInput = document.getElementById('register-name').value.trim();
    
    if (!loginInput || !passwordInput) {
        alert('Логин и пароль обязательны');
        return;
    }
    if (passwordInput.length < 4) {
        alert('Пароль должен быть не менее 4 символов');
        return;
    }
    
    try {
        const res = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ login: loginInput, password: passwordInput, name: nameInput || undefined })
        });
        const data = await res.json();
        if (data.success) {
            isLoggedIn = true;
            currentUser = { client_id: data.client_uuid, login: loginInput };
            hideAuthModal();
            updateAuthUI();
            alert('Регистрация успешна! Добро пожаловать!');
        } else {
            alert('Ошибка: ' + data.error);
        }
    } catch (e) {
        alert('Ошибка соединения с сервером');
    }
}

async function logoutUser() {
    try {
        await fetch('/api/auth/logout', { method: 'POST' });
        isLoggedIn = false;
        currentUser = null;
        updateAuthUI();
        showAuthModal();
        alert('Вы вышли из системы');
    } catch (e) {
        console.error('Ошибка выхода:', e);
    }
}

function updateAuthUI() {
    const authContainer = document.getElementById('auth-status-container');
    if (!authContainer) return;
    
    if (isLoggedIn && currentUser) {
        authContainer.innerHTML = `
            <span style="margin-right: 10px; font-weight: 500;">👤 ${currentUser.login || 'Пользователь'}</span>
            <button onclick="logoutUser()" style="padding: 0.4rem 0.8rem; font-size: 0.85rem; background: #ef4444; color: white; border: none; border-radius: 6px; cursor: pointer;">🚪 Выйти</button>
        `;
    } else {
        authContainer.innerHTML = `
            <button onclick="showAuthModal()" style="padding: 0.4rem 0.8rem; font-size: 0.85rem; background: #3b82f6; color: white; border: none; border-radius: 6px; cursor: pointer;">🔑 Войти</button>
        `;
    }
}

// Вызываем проверку при загрузке
document.addEventListener('DOMContentLoaded', function() {
    checkAuthStatus();
});
// === КОНЕЦ БЛОКА АУТЕНТИФИКАЦИИ ===
```

## 4. Проверка работы

1. Запустите сервер: `python3 app.py`
2. Откройте браузер
3. Должно появиться модальное окно входа
4. Зарегистрируйте нового пользователя
5. После входа в правом верхнем углу появится кнопка "Выйти" и имя пользователя

## 5. Важные замечания

- Пароли хешируются через SHA-256 перед сохранением в БД
- Client UUID автоматически генерируется при регистрации
- Все существующие функции (чаты, группы, изображения) продолжают работать
- Авторизация привязана к cookie сессии (30 дней)
