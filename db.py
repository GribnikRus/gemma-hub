# db.py
import psycopg2
from config import DATABASE_URL
from psycopg2.extras import RealDictCursor
import logging
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def hash_password(password):
    """Хеширует пароль с помощью SHA-256."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def verify_password(password, password_hash):
    """Проверяет соответствие пароля хешу."""
    return hash_password(password) == password_hash

def get_db_connection():
    """Создаёт подключение к БД."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        # logger.info("✅ Успешное подключение к PostgreSQL") # Закомментим, чтобы не засорять лог
        return conn
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к БД: {e}")
        raise

def create_or_get_client_id_db(client_uuid):
    """
    Проверяет, есть ли клиент с client_uuid в таблице clients.
    Если нет - создаёт новую запись.
    Возвращает DB ID клиента.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Попробуем получить id
        cur.execute("SELECT id FROM clients WHERE client_uuid = %s;", (client_uuid,))
        result = cur.fetchone()
        if result:
            client_db_id = result[0]
            logger.debug(f"🔍 Клиент {client_uuid} уже существует, DB ID: {client_db_id}")
        else:
            # Вставим новую запись
            cur.execute("""
                INSERT INTO clients (client_uuid, name)
                VALUES (%s, %s)
                RETURNING id;
            """, (client_uuid, f"User_{client_uuid[:8]}")) # Простое имя по умолчанию
            client_db_id = cur.fetchone()[0]
            conn.commit()
            logger.info(f"🆕 Клиент {client_uuid} добавлен в таблицу clients, DB ID: {client_db_id}")

        cur.close()
        conn.close()
        return client_db_id

    except Exception as e:
        logger.error(f"❌ Ошибка при создании/получении клиента в БД: {e}")
        raise

def register_user(login, password, name=None):
    """Регистрирует нового пользователя с логином и паролем. Возвращает client_uuid."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Проверка, существует ли уже пользователь с таким логином
        cur.execute("SELECT id FROM users WHERE login = %s;", (login,))
        if cur.fetchone():
            cur.close()
            conn.close()
            raise ValueError(f"Пользователь с логином '{login}' уже существует")
        
        # Хешируем пароль
        password_hash = hash_password(password)
        
        # Создаём запись в таблице users
        cur.execute("""
            INSERT INTO users (login, password_hash, name)
            VALUES (%s, %s, %s)
            RETURNING id, client_uuid;
        """, (login, password_hash, name or f"User_{login}"))
        
        result = cur.fetchone()
        user_db_id, client_uuid = result
        conn.commit()
        
        cur.close()
        conn.close()
        
        logger.info(f"🆕 Пользователь '{login}' зарегистрирован, DB ID: {user_db_id}, Client UUID: {client_uuid}")
        return client_uuid
        
    except Exception as e:
        logger.error(f"❌ Ошибка регистрации пользователя: {e}")
        raise

def authenticate_user(login, password):
    """Аутентифицирует пользователя по логину и паролю. Возвращает client_uuid или None."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Получаем хеш пароля
        cur.execute("SELECT id, password_hash, client_uuid FROM users WHERE login = %s;", (login,))
        result = cur.fetchone()
        
        if not result:
            cur.close()
            conn.close()
            logger.warning(f"⚠️ Пользователь '{login}' не найден")
            return None
        
        user_db_id, stored_password_hash, client_uuid = result
        
        # Проверяем пароль
        if verify_password(password, stored_password_hash):
            cur.close()
            conn.close()
            logger.info(f"✅ Пользователь '{login}' успешно аутентифицирован, Client UUID: {client_uuid}")
            return client_uuid
        else:
            cur.close()
            conn.close()
            logger.warning(f"⚠️ Неверный пароль для пользователя '{login}'")
            return None
        
    except Exception as e:
        logger.error(f"❌ Ошибка аутентификации пользователя: {e}")
        raise

def get_user_by_client_uuid(client_uuid):
    """Получает информацию о пользователе по client_uuid. Возвращает dict с login, name или None."""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT u.id, u.login, u.name, u.client_uuid
            FROM users u
            WHERE u.client_uuid = %s;
        """, (client_uuid,))
        
        result = cur.fetchone()
        cur.close()
        conn.close()
        
        if result:
            return {
                "id": result["id"],
                "login": result["login"],
                "name": result["name"],
                "client_uuid": result["client_uuid"]
            }
        return None
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения пользователя: {e}")
        return None

def is_group_owner(group_id, owner_client_uuid):
    """
    Проверяет, является ли клиент owner_client_uuid владельцем группы group_id.
    Возвращает True/False.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Получим UUID владельца из таблицы groups
        cur.execute("""
            SELECT c.client_uuid
            FROM groups g
            JOIN clients c ON g.owner_client_id = c.id
            WHERE g.id = %s;
        """, (group_id,))
        result = cur.fetchone()
        cur.close()
        conn.close()

        if result:
            stored_owner_uuid = result[0]
            return stored_owner_uuid == owner_client_uuid
        else:
            # Группа не найдена
            return False
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке владельца группы {group_id}: {e}")
        raise

def save_task_history(user_ip, module, prompt, response, images_count=0, audio_duration=0, status="completed", client_id=None):
    """Сохраняет историю задачи в БД. Теперь принимает client_id."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO task_history (user_ip, module, prompt, response, images_count, audio_duration_sec, status, client_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (user_ip, module, prompt, response, images_count, audio_duration, status, client_id))
        conn.commit()
        cur.close()
        conn.close()
        logger.info(f"✅ Задача сохранена в БД: {module}, status: {status}, client_id: {client_id}")
    except Exception as e:
        logger.error(f"❌ О БД: {e}")

def get_task_history(limit=50):
    """Получает последние задачи из БД (для администратора/общего просмотра)."""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT module, prompt, response, created_at, status, user_ip, client_id
            FROM task_history
            ORDER BY created_at DESC
            LIMIT %s
        """, (limit,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        logger.info(f"✅ Получена общая история задач: {len(rows)} записей")
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"❌ Ошибка получения общей истории: {e}")
        return []

def get_task_history_by_client(client_uuid, limit=20):
    """Получает историю задач для конкретного клиента по его UUID."""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        # Сначала получим DB ID клиента
        cur.execute("SELECT id FROM clients WHERE client_uuid = %s;", (client_uuid,))
        result = cur.fetchone()
        if not result:
            logger.warning(f"⚠️ Клиент с UUID {client_uuid} не найден в таблице clients при запросе истории.")
            return []

        client_db_id = result[0]

        cur.execute("""
            SELECT module, prompt, response, created_at, status
            FROM task_history
            WHERE client_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (client_db_id, limit)) # Используем DB ID клиента, а не UUID
        rows = cur.fetchall()
        cur.close()
        conn.close()
        logger.info(f"✅ Получена история для клиента {client_uuid} (DB ID {client_db_id}): {len(rows)} записей")
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"❌ Ошибка получения истории для клиента {client_uuid}: {e}")
        return []

# --- Функции для работы с группами (заготовки) ---

def create_group(name, owner_client_uuid):
    """Создаёт новую группу. Возвращает ID группы."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Получим DB ID владельца
        cur.execute("SELECT id FROM clients WHERE client_uuid = %s;", (owner_client_uuid,))
        result = cur.fetchone()
        if not result:
            raise ValueError(f"Владелец с UUID {owner_client_uuid} не найден.")
        owner_db_id = result[0]

        # --- ИСПРАВЛЕНО: Добавлен правильный отступ ---
        cur.execute("""
            INSERT INTO groups (name, owner_client_id)
            VALUES (%s, %s)
            RETURNING id;
        """, (name, owner_db_id))
        group_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        logger.info(f"🆕 Группа '{name}' создана, ID: {group_id}, владелец DB ID: {owner_db_id}")
        return group_id
    except Exception as e:
        logger.error(f"❌ Ошибка создания группы: {e}")
        raise

def invite_client_to_group(group_id, target_client_uuid):
    """Отправляет приглашение в группу. Возвращает ID членства."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Проверим, существует ли группа
        cur.execute("SELECT id FROM groups WHERE id = %s;", (group_id,))
        if not cur.fetchone():
            raise ValueError(f"Группа с ID {group_id} не существует.")

        # Получим DB ID приглашаемого
        cur.execute("SELECT id FROM clients WHERE client_uuid = %s;", (target_client_uuid,))
        result = cur.fetchone()
        if not result:
            raise ValueError(f"Приглашаемый клиент с UUID {target_client_uuid} не найден.")
        target_db_id = result[0]

        # Создадим запись о членстве (статус pending)
        cur.execute("""
            INSERT INTO group_memberships (group_id, client_id, status)
            VALUES (%s, %s, %s)
            RETURNING id;
        """, (group_id, target_db_id, 'pending'))
        membership_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        logger.info(f"📧 Приглашение в группу {group_id} отправлено клиенту {target_client_uuid} (DB ID {target_db_id}), Membership ID: {membership_id}")
        return membership_id
    except Exception as e:
        logger.error(f"❌ Ошибка приглашения в группу: {e}")
        raise

def respond_to_invite(membership_id, client_uuid, action):
    """Принимает или отклоняет приглашение. action: 'accept', 'reject'."""
    if action not in ['accept', 'reject']:
        raise ValueError("Action must be 'accept' or 'reject'")

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Проверим, принадлежит ли приглашение клиенту
        cur.execute("""
            SELECT gm.client_id, c.client_uuid
            FROM group_memberships gm
            JOIN clients c ON gm.client_id = c.id
            WHERE gm.id = %s;
        """, (membership_id,))
        result = cur.fetchone()
        if not result:
            raise ValueError(f"Приглашение с ID {membership_id} не найдено.")

        invited_client_db_id, invited_client_uuid = result
        if invited_client_uuid != client_uuid:
            raise PermissionError("Приглашение не принадлежит текущему пользователю.")

        new_status = 'accepted' if action == 'accept' else 'rejected'
        cur.execute("""
            UPDATE group_memberships
            SET status = %s
            WHERE id = %s;
        """, (new_status, membership_id))
        conn.commit()
        cur.close()
        conn.close()
        logger.info(f"✅ Приглашение {membership_id} от клиента {client_uuid} {action}ed, new status: {new_status}")
    except Exception as e:
        logger.error(f"❌ Ошибка при ответе на приглашение: {e}")
        raise

def get_client_groups(client_uuid):
    """Получает список групп, в которых состоит клиент (с accepted статусом)."""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT g.id, g.name, g.owner_client_id, gm.joined_at
            FROM groups g
            JOIN group_memberships gm ON g.id = gm.group_id
            JOIN clients c ON gm.client_id = c.id
            WHERE c.client_uuid = %s AND gm.status = 'accepted';
        """, (client_uuid,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        logger.info(f"✅ Получены группы для клиента {client_uuid}: {len(rows)}")
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"❌ Ошибка получения групп клиента {client_uuid}: {e}")
        return []
def get_all_clients():
    """
    Возвращает список всех клиентов (id, name, created_at) из таблицы clients.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT client_uuid, name, created_at
            FROM clients
            ORDER BY created_at ASC;
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        logger.info(f"✅ Получен список всех клиентов: {len(rows)} записей")
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"❌ Ошибка получения списка всех клиентов: {e}")
        return []


def get_pending_invitations_for_client(client_uuid):
    """
    Возвращает список ожидающих приглашений для клиента client_uuid.
    Включает ID членства, ID группы, имя группы, имя отправителя.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT
                gm.id AS membership_id,
                gm.group_id,
                g.name AS group_name,
                c.name AS inviter_name
            FROM group_memberships gm
            JOIN groups g ON gm.group_id = g.id
            JOIN clients c ON g.owner_client_id = c.id
            JOIN clients target_c ON gm.client_id = target_c.id
            WHERE target_c.client_uuid = %s AND gm.status = 'pending';
        """, (client_uuid,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        logger.info(f"✅ Получены ожидающие приглашения для {client_uuid}: {len(rows)} шт.")
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"❌ Ошибка получения ожидающих приглашений для {client_uuid}: {e}")
        return []

def is_client_member_of_group(client_uuid, group_id):
    """
    Проверяет, состоит ли клиент client_uuid в группе group_id со статусом 'accepted'.
    Возвращает True/False.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Проверим, есть ли запись в group_memberships с accepted статусом
        cur.execute("""
            SELECT 1
            FROM group_memberships gm
            JOIN clients c ON gm.client_id = c.id
            WHERE c.client_uuid = %s AND gm.group_id = %s AND gm.status = 'accepted';
        """, (client_uuid, group_id))
        result = cur.fetchone()
        cur.close()
        conn.close()

        # Если вернулась строка (1), значит, пользователь участник
        return result is not None

    except Exception as e:
        logger.error(f"❌ Ошибка при проверке участия в группе {group_id} для клиента {client_uuid}: {e}")
        raise

def get_group_history(group_id, limit=50):
    """Получает историю задач для всех участников группы."""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT th.module, th.prompt, th.response, th.created_at, th.status, c.name as client_name
            FROM task_history th
            JOIN clients c ON th.client_id = c.id  -- Исправлено: client_id это INTEGER (DB ID)
            JOIN group_memberships gm ON c.id = gm.client_id
            WHERE gm.group_id = %s AND gm.status = 'accepted'
            ORDER BY th.created_at DESC
            LIMIT %s;
        """, (group_id, limit))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        logger.info(f"✅ Получена история для группы {group_id}: {len(rows)} записей")
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"❌ Ошибка получения истории группы {group_id}: {e}")
        return []
    
def get_owned_groups_by_client(owner_client_uuid):
    """
    Возвращает список групп, владельцем которых является клиент owner_client_uuid.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT g.id, g.name, g.created_at
            FROM groups g
            JOIN clients c ON g.owner_client_id = c.id
            WHERE c.client_uuid = %s;
        """, (owner_client_uuid,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        logger.info(f"✅ Получены группы, которыми владеет {owner_client_uuid}: {len(rows)} шт.")
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"❌ Ошибка получения групп-владений для {owner_client_uuid}: {e}")
        return []
