# app.py
from flask import Flask, request, jsonify, Response, make_response
from tasks import process_chat_task, process_vision_task, celery_app
from db import get_task_history_by_client, get_task_history, create_or_get_client_id_db, register_user, authenticate_user, get_user_by_client_uuid # Исправлен импорт
import logging
import os
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STATIC_FOLDER = os.path.join(os.path.dirname(__file__), 'static')
logger.info(f"📁 Папка статики: {STATIC_FOLDER}")
logger.info(f"📁 Файл index.html существует: {os.path.exists(os.path.join(STATIC_FOLDER, 'index.html'))}")

app = Flask(__name__)#, static_folder=STATIC_FOLDER__)

def get_or_create_client_id():
    """Получает client_id из cookie или создает новый."""
    client_id = request.cookies.get('client_id')
    if not client_id:
        client_id = str(uuid.uuid4()) # Генерируем новый UUID4
        logger.info(f"🆕 Новый client_id сгенерирован для сессии: {client_id}")
        return client_id, True # True означает, что cookie нужно установить
    else:
        logger.info(f"👤 Используем существующий client_id из cookie: {client_id}")
        return client_id, False # False означает, что cookie НЕ нужно устанавливать

def ensure_client_in_db(client_uuid):
    """Убедиться, что запись о клиенте есть в таблице clients."""
    # Вызовем функцию из db.py, которая создаст запись, если её нет
    db_client_id = create_or_get_client_id_db(client_uuid)
    logger.info(f"✅ Запись в clients подтверждена для UUID {client_uuid}, DB ID: {db_client_id}")
    return db_client_id

@app.route('/')
def index():
    logger.info("🌐 Запрос главной страницы")
    try:
        html_content = get_index_html()
        if isinstance(html_content, tuple): # Если вернулась ошибка (строка, код)
            return html_content

        client_id, needs_cookie = get_or_create_client_id()
        # Убедимся, что запись в БД есть
        ensure_client_in_db(client_id)

        response = Response(html_content, mimetype='text/html; charset=utf-8')
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        # Устанавливаем cookie client_id, если его не было
        if needs_cookie:
            logger.info(f"🍪 Устанавливаю cookie client_id: {client_id}")
            response.set_cookie('client_id', client_id, httponly=True, samesite='Lax', max_age=30*24*60*60) # 30 дней
        return response
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке index.html: {e}")
        return f"Ошибка сервера: {e}", 500

# --- Маршруты для аутентификации ---
@app.route('/api/auth/register', methods=['POST'])
def api_register():
    """Регистрация нового пользователя."""
    try:
        data = request.json
        login = data.get('login')
        password = data.get('password')
        name = data.get('name')
        
        if not login or not password:
            return jsonify({"success": False, "error": "Логин и пароль обязательны"}), 400
        
        logger.info(f"📝 Попытка регистрации пользователя: {login}")
        
        # Регистрируем пользователя
        client_uuid = register_user(login, password, name)
        
        # Создаём ответ с cookie
        response = make_response(jsonify({
            "success": True,
            "message": f"Пользователь '{login}' успешно зарегистрирован",
            "client_uuid": client_uuid,
            "user": get_user_by_client_uuid(client_uuid)
        }))
        
        # Устанавливаем cookie с client_uuid
        response.set_cookie('client_id', client_uuid, httponly=True, samesite='Lax', max_age=30*24*60*60)
        
        return response
        
    except ValueError as ve:
        logger.error(f"❌ Ошибка валидации при регистрации: {ve}")
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        logger.error(f"❌ Ошибка при регистрации: {e}")
        return jsonify({"success": False, "error": f"Внутренняя ошибка сервера: {str(e)}"}), 500

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    """Вход пользователя."""
    try:
        data = request.json
        login = data.get('login')
        password = data.get('password')
        
        if not login or not password:
            return jsonify({"success": False, "error": "Логин и пароль обязательны"}), 400
        
        logger.info(f"🔑 Попытка входа пользователя: {login}")
        
        # Аутентифицируем пользователя
        client_uuid = authenticate_user(login, password)
        
        if not client_uuid:
            return jsonify({"success": False, "error": "Неверный логин или пароль"}), 401
        
        # Убедимся, что запись в clients есть
        ensure_client_in_db(client_uuid)
        
        # Создаём ответ с cookie
        response = make_response(jsonify({
            "success": True,
            "message": f"Пользователь '{login}' успешно вошёл в систему",
            "client_uuid": client_uuid,
            "user": get_user_by_client_uuid(client_uuid)
        }))
        
        # Устанавливаем cookie с client_uuid
        response.set_cookie('client_id', client_uuid, httponly=True, samesite='Lax', max_age=30*24*60*60)
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Ошибка при входе: {e}")
        return jsonify({"success": False, "error": f"Внутренняя ошибка сервера: {str(e)}"}), 500

@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    """Выход пользователя."""
    try:
        logger.info("🚪 Пользователь выходит из системы")
        
        response = make_response(jsonify({
            "success": True,
            "message": "Вы успешно вышли из системы"
        }))
        
        # Удаляем cookie
        response.delete_cookie('client_id')
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Ошибка при выходе: {e}")
        return jsonify({"success": False, "error": f"Внутренняя ошибка сервера: {str(e)}"}), 500

@app.route('/api/auth/status', methods=['GET'])
def api_auth_status():
    """Проверка статуса аутентификации."""
    try:
        client_id = request.cookies.get('client_id')
        
        if client_id:
            ensure_client_in_db(client_id)
            # Получаем информацию о пользователе
            user_info = get_user_by_client_uuid(client_id)
            return jsonify({
                "authenticated": True,
                "client_id": client_id,
                "user": user_info
            })
        else:
            return jsonify({
                "authenticated": False,
                "client_id": None
            })
            
    except Exception as e:
        logger.error(f"❌ Ошибка проверки статуса: {e}")
        return jsonify({
            "authenticated": False,
            "error": str(e)
        }), 500

def get_index_html():
    """Читает index.html как строку и удаляет BOM, если есть."""
    try:
        with open(os.path.join(STATIC_FOLDER, 'index.html'), 'r', encoding='utf-8-sig') as f:
            content = f.read()
        stripped_content = content.lstrip()
        if not stripped_content.startswith('<!DOCTYPE html>'):
            idx = stripped_content.find('<!DOCTYPE html>')
            if idx != -1:
                stripped_content = stripped_content[idx:]
            else:
                logger.warning("⚠️ <!DOCTYPE html> не найден в начале файла.")
        return stripped_content
    except FileNotFoundError:
        logger.error("❌ Файл index.html не найден!")
        return "Файл index.html не найден.", 404
    except Exception as e:
        logger.error(f"❌ Ошибка при чтении index.html: {e}")
        return f"Ошибка сервера при чтении index.html: {e}", 500

@app.route('/api/chat', methods=['POST'])
def api_chat():
    try:
        data = request.json
        prompt = data.get('prompt', '')
        user_ip = request.remote_addr
        client_id, _ = get_or_create_client_id() # Получаем client_id
        ensure_client_in_db(client_id) # Убедимся, что запись в БД есть

        logger.info(f"💬 Получен чат-запрос от {user_ip} (client_id: {client_id}): {prompt[:30]}...")
        
        # --- ИСПРАВЛЕНО: Передаём client_id в задачу ---
        task = process_chat_task.delay(prompt, user_ip, client_id)
        logger.info(f"💬 Задача в очереди: {task.id}")
        return jsonify({"task_id": task.id, "status": "queued"})
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/vision', methods=['POST'])
def api_vision():
    try:
        data = request.json
        prompt = data.get('prompt', '')
        images = data.get('images', [])
        user_ip = request.remote_addr
        client_id, _ = get_or_create_client_id() # Получаем client_id
        ensure_client_in_db(client_id) # Убедимся, что запись в БД есть

        logger.info(f"🖼️ Получен вижн-запрос от {user_ip} (client_id: {client_id}), изображений: {len(images)}")
        
        if not images:
            return jsonify({"error": "No images provided"}), 400

        # --- ИСПРАВЛЕНО: Передаём client_id в задачу ---
        task = process_vision_task.delay(prompt, images, user_ip, client_id)
        logger.info(f"🖼️ Задача в очереди: {task.id}")
        return jsonify({"task_id": task.id, "status": "queued"})
    except Exception as e:
        logger.error(f"❌ Ошибка в /api/vision: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/task-status/<task_id>', methods=['GET'])
def api_task_status(task_id):
    try:
        logger.info(f"📋 Запрос статуса задачи: {task_id}")
        task_result = celery_app.AsyncResult(task_id)
        
        state = task_result.state
        response_data = {"task_id": task_id, "status": state.lower()}
        
        if state == 'PENDING':
            response_data["result"] = "Задача ожидает в очереди..."
        elif state == 'STARTED':
            response_data["result"] = "Задача выполняется..."
        elif state == 'SUCCESS':
            response_data["result"] = task_result.result
        elif state == 'FAILURE':
            response_data["result"] = f"Ошибка: {str(task_result.info)}"
        elif state in ('RETRY', 'REVOKED'):
            response_data["result"] = f"Статус: {state.lower()}"

        logger.info(f"📋 Статус задачи {task_id}: {state}")
        return jsonify(response_data)
    except Exception as e:
        logger.error(f"❌ Ошибка в /api/task-status: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/history', methods=['GET'])
def api_history():
    try:
        limit = int(request.args.get('limit', 20))
        client_id, _ = get_or_create_client_id() # Получаем client_id текущего пользователя
        ensure_client_in_db(client_id) # Убедимся, что запись в БД есть
        logger.info(f"📋 Запрос истории для client_id: {client_id}, limit={limit}")
        
        # Получаем историю для конкретного клиента
        records = get_task_history_by_client(client_id, limit)
        return jsonify(records)
    except Exception as e:
        logger.error(f"❌ Ошибка в /api/history: {e}")
        return jsonify({"error": str(e)}), 500

# --- НОВЫЙ маршрут: получить общую историю (для администратора или отладки) ---
@app.route('/api/history-all', methods=['GET'])
def api_history_all():
    try:
        limit = int(request.args.get('limit', 50))
        logger.info(f"📋 Запрос ОБЩЕЙ истории, limit={limit}")
        records = get_task_history(limit)
        return jsonify(records)
    except Exception as e:
        logger.error(f"❌ Ошибка в /api/history-all: {e}")
        return jsonify({"error": str(e)}), 500

# --- НОВЫЙ маршрут: Создание группы ---
@app.route('/api/group/create', methods=['POST'])
def api_group_create():
    try:
        data = request.json
        group_name = data.get('name')
        if not group_name:
            return jsonify({"success": False, "error": "Поле 'name' обязательно"}), 400

        # Получаем client_id текущего пользователя
        client_id, _ = get_or_create_client_id()
        # Убедимся, что запись в БД есть
        ensure_client_in_db(client_id)

        logger.info(f"👥 Пользователь {client_id} пытается создать группу '{group_name}'")

        # Вызываем функцию из db.py
        from db import create_group
        group_id = create_group(group_name, client_id)

        return jsonify({
            "success": True,
            "group_id": group_id,
            "message": f"Группа '{group_name}' успешно создана с ID {group_id}."
        })

    except ValueError as ve:
        # Ошибка валидации (например, владелец не найден)
        logger.error(f"❌ Ошибка валидации при создании группы: {ve}")
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        logger.error(f"❌ Ошибка при создании группы: {e}")
        return jsonify({"success": False, "error": f"Внутренняя ошибка сервера: {str(e)}"}), 500
@app.route('/api/group/invite', methods=['POST'])
def api_group_invite():
    try:
        data = request.json
        group_id = data.get('group_id')
        target_client_uuid = data.get('target_client_uuid')

        if not group_id or not target_client_uuid:
            return jsonify({"success": False, "error": "Поля 'group_id' и 'target_client_uuid' обязательны"}), 400

        # Получаем client_id текущего пользователя
        client_id, _ = get_or_create_client_id()
        # Убедимся, что запись в БД есть
        ensure_client_in_db(client_id)

        logger.info(f"✉️ Пользователь {client_id} пытается пригласить {target_client_uuid} в группу {group_id}")

        # Проверим, является ли текущий пользователь владельцем группы
        # Нужно добавить функцию в db.py для проверки
        from db import is_group_owner
        if not is_group_owner(group_id, client_id):
            logger.warning(f"⚠️ Пользователь {client_id} не является владельцем группы {group_id}")
            return jsonify({"success": False, "error": "У вас нет прав на приглашение в эту группу"}), 403

        # Вызываем функцию из db.py
        from db import invite_client_to_group
        membership_id = invite_client_to_group(group_id, target_client_uuid)

        return jsonify({
            "success": True,
            "membership_id": membership_id,
            "message": f"Приглашение в группу {group_id} отправлено пользователю {target_client_uuid}."
        })

    except ValueError as ve:
        # Ошибка валидации (например, группа или клиент не найден)
        logger.error(f"❌ Ошибка валидации при приглашении: {ve}")
        return jsonify({"success": False, "error": str(ve)}), 400
    except PermissionError as pe:
        logger.error(f"❌ Ошибка доступа при приглашении: {pe}")
        return jsonify({"success": False, "error": str(pe)}), 403
    except Exception as e:
        logger.error(f"❌ Ошибка при приглашении: {e}")
        return jsonify({"success": False, "error": f"Внутренняя ошибка сервера: {str(e)}"}), 500


@app.route('/api/group/respond-invite', methods=['POST'])
def api_group_respond_invite():
    try:
        data = request.json
        membership_id = data.get('membership_id')
        action = data.get('action')

        if not membership_id or action not in ['accept', 'reject']:
            return jsonify({"success": False, "error": "Поля 'membership_id' и 'action' ('accept' или 'reject') обязательны"}), 400

        # Получаем client_id текущего пользователя
        client_id, _ = get_or_create_client_id()
        # Убедимся, что запись в БД есть
        ensure_client_in_db(client_id)

        logger.info(f"🤝 Пользователь {client_id} пытается {action} приглашение с ID {membership_id}")

        # Вызываем функцию из db.py
        # Она сама проверит, принадлежит ли приглашение пользователю
        from db import respond_to_invite
        respond_to_invite(membership_id, client_id, action)

        message_action = "принято" if action == 'accept' else "отклонено"
        return jsonify({
            "success": True,
            "message": f"Приглашение с ID {membership_id} {message_action}."
        })

    except ValueError as ve:
        # Приглашение не найдено
        logger.error(f"❌ Ошибка валидации при ответе на приглашение: {ve}")
        return jsonify({"success": False, "error": str(ve)}), 400
    except PermissionError as pe:
        # Приглашение не принадлежит пользователю
        logger.error(f"❌ Ошибка доступа при ответе на приглашение: {pe}")
        return jsonify({"success": False, "error": str(pe)}), 403
    except Exception as e:
        logger.error(f"❌ Ошибка при ответе на приглашение: {e}")
        return jsonify({"success": False, "error": f"Внутренняя ошибка сервера: {str(e)}"}), 500
@app.route('/api/group/<int:group_id>/history', methods=['GET'])
def api_group_history(group_id):
    try:
        # Получаем client_id текущего пользователя
        client_id, _ = get_or_create_client_id()
        # Убедимся, что запись в БД есть
        ensure_client_in_db(client_id)

        logger.info(f"📚 Пользователь {client_id} запрашивает историю для группы {group_id}")

        # Проверим, состоит ли пользователь в группе
        from db import is_client_member_of_group
        if not is_client_member_of_group(client_id, group_id):
            logger.warning(f"⚠️ Пользователь {client_id} не является участником группы {group_id} или статус не 'accepted'")
            return jsonify({"success": False, "error": "У вас нет доступа к истории этой группы"}), 403

        # Получим лимит, если передан
        limit = int(request.args.get('limit', 50))

        # Вызываем функцию из db.py
        from db import get_group_history
        history = get_group_history(group_id, limit)

        return jsonify({
            "success": True,
            "history": history
        })

    except Exception as e:
        logger.error(f"❌ Ошибка при получении истории группы {group_id}: {e}")
        return jsonify({"success": False, "error": f"Внутренняя ошибка сервера: {str(e)}"}), 500
    
@app.route('/api/client/groups', methods=['GET'])
def api_client_groups():
    try:
        # Получаем client_id текущего пользователя
        client_id, _ = get_or_create_client_id()
        # Убедимся, что запись в БД есть
        ensure_client_in_db(client_id)

        logger.info(f"👥 Запрос списка групп для клиента {client_id}")

        # Вызываем функцию из db.py
        from db import get_client_groups
        groups = get_client_groups(client_id)

        return jsonify({
            "success": True,
            "groups": groups
        })

    except Exception as e:
        logger.error(f"❌ Ошибка при получении списка групп для клиента {client_id}: {e}")
        return jsonify({"success": False, "error": f"Внутренняя ошибка сервера: {str(e)}"}), 500
@app.route('/api/clients/list', methods=['GET'])
def api_clients_list():
    try:
        logger.info(f"🌐 Запрос списка всех клиентов")

        # Вызываем функцию из db.py
        from db import get_all_clients
        clients = get_all_clients()

        return jsonify({
            "success": True,
            "clients": clients
        })

    except Exception as e:
        logger.error(f"❌ Ошибка при получении списка клиентов: {e}")
        return jsonify({"success": False, "error": f"Внутренняя ошибка сервера: {str(e)}"}), 500
    
@app.route('/api/client/invitations/pending', methods=['GET'])
def api_client_invitations_pending():
    try:
        # Получаем client_id текущего пользователя
        client_id, _ = get_or_create_client_id()
        # Убедимся, что запись в БД есть
        ensure_client_in_db(client_id)

        logger.info(f"📨 Запрос ожидающих приглашений для клиента {client_id}")

        # Вызываем функцию из db.py
        from db import get_pending_invitations_for_client
        invitations = get_pending_invitations_for_client(client_id)

        return jsonify({
            "success": True,
            "invitations": invitations
        })

    except Exception as e:
        logger.error(f"❌ Ошибка при получении ожидающих приглашений для клиента {client_id}: {e}")
        return jsonify({"success": False, "error": f"Внутренняя ошибка сервера: {str(e)}"}), 500

@app.route('/api/client/owned-groups', methods=['GET'])
def api_client_owned_groups():
    try:
        # Получаем client_id текущего пользователя
        client_id, _ = get_or_create_client_id()
        # Убедимся, что запись в БД есть
        ensure_client_in_db(client_id)

        logger.info(f"👑 Запрос списка групп, которыми владеет клиент {client_id}")

        # Вызываем функцию из db.py
        from db import get_owned_groups_by_client
        groups = get_owned_groups_by_client(client_id)

        return jsonify({
            "success": True,
            "groups": groups
        })

    except Exception as e:
        logger.error(f"❌ Ошибка при получении списка групп-владений для клиента {client_id}: {e}")
        return jsonify({"success": False, "error": f"Внутренняя ошибка сервера: {str(e)}"}), 500

    

# --- НОВЫЙ маршрут: Отмена задачи по ID с подтверждением паролем ---
@app.route('/api/task/cancel', methods=['POST'])
def api_task_cancel():
    try:
        data = request.json
        task_id = data.get('task_id')
        password = data.get('password')

        if not task_id:
            return jsonify({"success": False, "error": "Поле 'task_id' обязательно"}), 400

        # Проверка пароля (постоянный пароль "20021977")
        if password != "20021977":
            logger.warning(f"⚠️ Неверный пароль при попытке отмены задачи {task_id}")
            return jsonify({"success": False, "error": "Неверный пароль"}), 403

        logger.info(f"🛑 Попытка отмены задачи {task_id} с подтверждением паролем")

        # Отменяем задачу через Celery
        from celery.result import AsyncResult
        task_result = AsyncResult(task_id, app=celery_app)
        
        # Проверяем текущий статус задачи
        if task_result.state in ['SUCCESS', 'FAILURE', 'REVOKED']:
            return jsonify({
                "success": False, 
                "error": f"Задача уже завершена со статусом: {task_result.state}"
            }), 400

        # Отменяем задачу
        celery_app.control.revoke(task_id, terminate=True)
        
        logger.info(f"✅ Задача {task_id} успешно отменена")

        return jsonify({
            "success": True,
            "message": f"Задача {task_id} успешно отменена"
        })

    except Exception as e:
        logger.error(f"❌ Ошибка при отмене задачи {task_id}: {e}")
        return jsonify({"success": False, "error": f"Внутренняя ошибка сервера: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=False)
