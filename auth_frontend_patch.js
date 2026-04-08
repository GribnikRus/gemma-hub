// Этот скрипт нужно вставить в начало <script> в index.html
// Переменные аутентификации
let currentUser = null;
let isLoggedIn = false;

// Проверка статуса аутентификации при загрузке
async function checkAuthStatus() {
    try {
        const res = await fetch('/api/auth/status');
        const data = await res.json();
        
        if (data.authenticated) {
            isLoggedIn = true;
            currentUser = { client_id: data.client_id };
            updateAuthUI();
        } else {
            showAuthModal();
        }
    } catch (e) {
        console.error('Ошибка проверки статуса:', e);
    }
}

// Показать модальное окно аутентификации
function showAuthModal() {
    const modal = document.getElementById('auth-modal');
    if (modal) {
        modal.style.display = 'flex';
    }
}

// Скрыть модальное окно аутентификации
function hideAuthModal() {
    const modal = document.getElementById('auth-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// Переключение между входом и регистрацией
function toggleAuthForm(formType) {
    const loginForm = document.getElementById('login-form-container');
    const registerForm = document.getElementById('register-form-container');
    
    if (formType === 'login') {
        loginForm.style.display = 'block';
        registerForm.style.display = 'none';
    } else {
        loginForm.style.display = 'none';
        registerForm.style.display = 'block';
    }
}

// Вход пользователя
async function loginUser() {
    const loginInput = document.getElementById('login-username').value;
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
        console.error(e);
    }
}

// Регистрация пользователя
async function registerUser() {
    const loginInput = document.getElementById('register-username').value;
    const passwordInput = document.getElementById('register-password').value;
    const nameInput = document.getElementById('register-name').value;
    
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
        console.error(e);
    }
}

// Выход пользователя
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

// Обновление UI в зависимости от статуса аутентификации
function updateAuthUI() {
    const authContainer = document.getElementById('auth-status-container');
    if (!authContainer) return;
    
    if (isLoggedIn && currentUser) {
        authContainer.innerHTML = `
            <span style="margin-right: 10px;">👤 ${currentUser.login || 'Пользователь'}</span>
            <button onclick="logoutUser()" class="small" style="padding: 0.4rem 0.8rem; font-size: 0.85rem;">🚪 Выйти</button>
        `;
    } else {
        authContainer.innerHTML = `
            <button onclick="showAuthModal()" class="small" style="padding: 0.4rem 0.8rem; font-size: 0.85rem;">🔑 Войти</button>
        `;
    }
}

// Вызываем проверку при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    checkAuthStatus();
});
