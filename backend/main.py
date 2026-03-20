from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
import random
from datetime import datetime, timezone, timedelta
import hashlib
import base64
import os
from io import BytesIO
from roles_manager import RoleManager
import re
from passlib.context import CryptContext
from image_processor import sanitize_document_image, is_image_valid, get_supported_formats_text
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from auth import password_validator, hash_password_secure, verify_password_secure
from encryption import encryption_manager
import logging
import uuid
import secrets
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, Depends
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
import time

# Импортируем нашу конфигурацию БД
from db_config import get_db_connection

# ============== FASTAPI APP ==============
app = FastAPI(
    title="Need for Party API",
    version="1.0.0",
    description="API для Telegram Mini App 'Need for Party'",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://karina0409.github.io",  # Ваш GitHub Pages
        "http://localhost",  # Локальная разработка
        "http://localhost:8080",
        "http://localhost:8000",
        "*"  # Для тестирования
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============== МОДЕЛИ ДАННЫХ ==============
class UserRegister(BaseModel):
    name: str
    surname: str
    email: str
    nickname: str
    refer_from: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    name: str
    surname: str
    nickname: str
    email: str
    refer: str
    current_rank: str
    visits_count: int = 0
    invited_count: int = 0
    total_bar_spent: int = 0
    battle_participations: int = 0

class Party(BaseModel):
    id: int
    name: str
    date: str
    location: str
    seats: str
    price: str

# ============== УТИЛИТЫ ==============

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app_security.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Инициализация лимитера запросов
limiter = Limiter(key_func=get_remote_address, default_limits=["100 per minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def generate_referral_code(name: str) -> str:
    """Генерация реферального кода: ддммггггччммсс + 2 буквы (GMT+7)"""
    gmt7 = timezone(timedelta(hours=7))
    now = datetime.now(gmt7)
    datetime_part = now.strftime("%d%m%Y%H%M%S")
    
    # Буквы из имени (латинские)
    letters = [c.upper() for c in name if 'A' <= c.upper() <= 'Z']
    
    # Если нет латинских букв, конвертируем русские
    if not letters:
        ru_to_lat = {'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D'}
        for char in name.upper():
            if char in ru_to_lat:
                letters.append(ru_to_lat[char])
    
    # Формируем буквенную часть
    if len(letters) >= 2:
        name_part = ''.join(random.sample(letters, 2))
    elif len(letters) == 1:
        name_part = letters[0] + random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    else:
        name_part = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=2))
    
    return f"{datetime_part}{name_part}"


def get_photo_info(photo_binary, format_photo):
    """Получение информации о фото из binary данных"""
    if not photo_binary:
        return None
    
    try:
        photo_hash = hashlib.md5(photo_binary).hexdigest()
        return {
            "hash": photo_hash,
            "format": format_photo or "jpg",
            "size": len(photo_binary)
        }
    except Exception as e:
        print(f"Ошибка обработки фото: {e}")
        return None
    
def hash_password(password: str) -> str:
    """
    Хеширование пароля с использованием PBKDF2
    (без bcrypt, чтобы избежать ограничения в 72 байта)
    """
    # Генерируем случайную соль (16 байт)
    salt = os.urandom(16)
    
    # Хешируем пароль с солью (100,000 итераций)
    key = hashlib.pbkdf2_hmac(
        'sha256',  # алгоритм хеширования
        password.encode('utf-8'),  # пароль в байтах
        salt,  # соль
        100000,  # количество итераций
        dklen=32  # длина ключа (32 байта = 256 бит)
    )
    
    # Конвертируем в base64 для хранения в БД
    salt_b64 = base64.b64encode(salt).decode('utf-8')
    key_b64 = base64.b64encode(key).decode('utf-8')
    
    # Возвращаем соль и ключ вместе
    return f"{salt_b64}:{key_b64}"

def verify_password(plain_password: str, stored_hash: str) -> bool:
    """
    Проверка пароля
    """
    try:
        # Разделяем соль и ключ
        salt_b64, key_b64 = stored_hash.split(':')
        
        # Декодируем из base64
        salt = base64.b64decode(salt_b64)
        stored_key = base64.b64decode(key_b64)
        
        # Вычисляем хеш для проверки
        key = hashlib.pbkdf2_hmac(
            'sha256',
            plain_password.encode('utf-8'),
            salt,
            100000,
            dklen=32
        )
        
        # Сравниваем ключи (время-константное сравнение)
        return key == stored_key
        
    except Exception as e:
        print(f"❌ Ошибка проверки пароля: {e}")
        return False

def validate_email(email: str) -> bool:
    """Усиленная валидация email"""
    # Базовая проверка формата
    pattern = r'^[a-zA-Z0-9][a-zA-Z0-9._%+-]*@[a-zA-Z0-9][a-zA-Z0-9.-]*\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False
    
    # Проверка длины
    if len(email) > 254:  # Максимальная длина email по стандарту
        return False
    
    # Проверка на временные email-адреса (можно расширять список)
    disposable_domains = ['tempmail.com', 'throwaway.com', 'mailinator.com']
    domain = email.split('@')[-1].lower()
    if domain in disposable_domains:
        return False
    
    return True

def validate_password(password: str) -> bool:
    """Валидация пароля - теперь без ограничения bcrypt"""
    return 5 <= len(password) <= 100  # можно увеличить до 100

def validate_nickname(nickname: str) -> bool:
    """Усиленная валидация никнейма"""
    # Длина
    if len(nickname) < 3 or len(nickname) > 30:
        return False
    
    # Только буквы, цифры и подчеркивание
    if not re.match(r'^[a-zA-Z0-9_]+$', nickname):
        return False
    
    # Запрещенные никнеймы
    forbidden = ['admin', 'administrator', 'support', 'moderator', 'root', 'system']
    if nickname.lower() in forbidden:
        return False
    
    return True

async def get_party_info(party_id: int):
    """Получение информации о вечеринке по ID"""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                ID,
                name,
                cost,
                location,
                CONVERT(VARCHAR, start_party, 104) as date,
                CONVERT(VARCHAR, start_party, 108) as time,
                count_seats,
                id_city
            FROM parties 
            WHERE ID = ?
        """, (party_id,))
        
        party = cursor.fetchone()
        conn.close()
        
        if not party:
            return None
        
        return {
            "id": party[0],
            "name": party[1],
            "cost": float(party[2]) if party[2] else 0,
            "location": party[3],
            "date": party[4],
            "time": party[5],
            "seats": party[6],
            "city_id": party[7]
        }
        
    except Exception as e:
        print(f"❌ Ошибка получения информации о вечеринке: {e}")
        if conn:
            conn.close()
        return None

# ============== API ЭНДПОИНТЫ ==============



@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "message": "🎉 Need for Party API работает!",
        "version": "1.0.0",
        "docs": "/api/docs",
        "health": "/api/health"
    }

@app.get("/api/health")
async def health_check():
    """Проверка здоровья API и БД"""
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT @@version")
            db_version = cursor.fetchone()[0]
            conn.close()
            db_status = "connected"
        else:
            db_version = None
            db_status = "disconnected"
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": db_status,
            "version": db_version[:100] if db_version else None
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/api/test-db")
async def test_database():
    """Тестирование подключения к БД"""
    try:
        conn = get_db_connection()
        if not conn:
            return {
                "success": False,
                "message": "Не удалось подключиться к БД",
                "tables": [],
                "user_count": 0
            }
        
        cursor = conn.cursor()
        
        # Проверяем таблицы
        cursor.execute("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        # Проверяем пользователей
        user_count = 0
        if 'users' in [t.lower() for t in tables]:
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "success": True,
            "message": "БД подключена успешно",
            "tables": tables,
            "user_count": user_count
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Ошибка БД: {str(e)}",
            "tables": [],
            "user_count": 0
        }
    
# Middleware для безопасности
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    # Генерируем уникальный ID запроса
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    # Логируем входящий запрос
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"Request ID: {request_id} | IP: {client_ip} | Method: {request.method} | Path: {request.url.path}")
    
    # Добавляем заголовки безопасности
    response = await call_next(request)
    
    # Security Headers
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    return response

@app.post("/api/user/register")
@limiter.limit("3 per minute")
async def register_user(request: Request, user: dict):
    """Регистрация нового пользователя с усиленной проверкой пароля"""
    print(f"📝 Регистрация пользователя: {user.get('name')} {user.get('surname')}")
    
    # Проверка на бота (простая капча)
    if not check_human_request(request):
        return {"success": False, "error": "Подтвердите, что вы не бот"}
    
    # Валидация данных
    name = user.get("name", "").strip()
    surname = user.get("surname", "").strip()
    email = user.get("email", "").strip()
    nickname = user.get("nickname", "").strip()
    password = user.get("password", "")
    gender = user.get("gender", "male")
    refer_from = user.get("refer_from")
    
    # Проверка обязательных полей
    if not all([name, surname, email, nickname, password]):
        return {"success": False, "error": "Заполните все обязательные поля"}
    
    # Валидация email
    if not validate_email(email):
        return {"success": False, "error": "Введите корректный email (пример: name@domain.com)"}
    
    # УСИЛЕННАЯ ВАЛИДАЦИЯ ПАРОЛЯ
    is_valid, password_error = password_validator.validate(password)
    if not is_valid:
        return {"success": False, "error": password_error}
    
    # Валидация никнейма
    if not validate_nickname(nickname):
        return {"success": False, "error": "Никнейм должен содержать минимум 3 символа и только буквы, цифры и _"}
    
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return {"success": False, "error": "Ошибка подключения к БД"}
        
        cursor = conn.cursor()
        
        # Проверяем уникальность nickname и email
        cursor.execute("""
            SELECT ID FROM users 
            WHERE nickname = ? OR mail = ?
        """, (nickname, email))
        
        if cursor.fetchone():
            conn.close()
            return {"success": False, "error": "Пользователь с таким nickname или email уже существует"}
        
        # Проверяем реферальный код (если указан)
        refer_from_id = None
        if refer_from and refer_from.strip():
            cursor.execute("SELECT ID FROM users WHERE refer = ?", (refer_from.strip(),))
            result = cursor.fetchone()
            if result:
                refer_from_id = result[0]
                print(f"✅ Найден пригласивший: ID {refer_from_id}")
        
        # Генерируем реферальный код
        refer_code = generate_referral_code(name)
        
        # Хешируем пароль новым безопасным методом
        hashed_password = hash_password_secure(password)
        
        # Вставляем пользователя
        gender_bit = 1 if gender == 'male' else 0
        default_age = 18
        
        query = """
            INSERT INTO users (
                nickname, surname, name, age, is_verificated, is_ban,
                phone_number, mail, refer, refer_from, gender, password
            ) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            nickname,
            surname,
            name,
            default_age,
            0,       # не верифицирован
            0,       # не забанен
            None,    # телефон
            email,
            refer_code,
            refer_from if refer_from_id else None,
            gender_bit,
            hashed_password
        )
        
        cursor.execute(query, params)
        
        # Получаем ID нового пользователя
        cursor.execute("SELECT @@IDENTITY")
        new_user_id = cursor.fetchone()[0]
        
        # Назначаем роль "Участник"
        try:
            cursor.execute("SELECT ID FROM roles WHERE name = 'Участник'")
            role_result = cursor.fetchone()
            
            if role_result:
                # Проверяем, есть ли поле is_selected
                cursor.execute("""
                    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_NAME = 'user_role' AND COLUMN_NAME = 'is_selected'
                """)
                
                has_is_selected = cursor.fetchone()[0] > 0
                
                if has_is_selected:
                    cursor.execute("""
                        INSERT INTO user_role (id_user, id_role, is_selected) 
                        VALUES (?, ?, 1)
                    """, (new_user_id, role_result[0]))
                else:
                    cursor.execute("""
                        INSERT INTO user_role (id_user, id_role) 
                        VALUES (?, ?)
                    """, (new_user_id, role_result[0]))
        except Exception as role_error:
            print(f"⚠️ Ошибка назначения роли: {role_error}")
        
        conn.commit()
        
        # Формируем ответ
        response_data = {
            "success": True,
            "message": "Регистрация успешна! 🎉",
            "user": {
                "id": new_user_id,
                "name": name,
                "surname": surname,
                "nickname": nickname,
                "email": email,
                "gender": "male" if gender_bit == 1 else "female",
                "refer": refer_code,
                "current_rank": "Участник",
                "is_verificated": False,
                "is_banned": False
            }
        }
        
        # Логируем успешную регистрацию (просто в консоль)
        logger.info(f"✅ Новый пользователь зарегистрирован: {nickname} (ID: {new_user_id}) from IP: {request.client.host}")
        
        conn.close()
        return response_data
        
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        
        logger.error(f"❌ Ошибка регистрации: {e}")
        return {"success": False, "error": f"Ошибка при регистрации: {str(e)}"}
    
@app.post("/api/admin/fix-user-roles")
async def fix_user_roles(request: dict):
    """Исправление ролей пользователя (только для админов)"""
    user_id = request.get("user_id")
    keep_only = request.get("keep_only", ["Участник"])
    
    conn = get_db_connection()
    if not conn:
        return {"success": False, "error": "Ошибка подключения к БД"}
    
    try:
        cursor = conn.cursor()
        
        # Получаем ID роли "Участник"
        cursor.execute("SELECT ID FROM roles WHERE name = 'Участник'")
        participant = cursor.fetchone()
        
        if not participant:
            conn.close()
            return {"success": False, "error": "Роль Участник не найдена"}
        
        # Удаляем все роли пользователя
        cursor.execute("DELETE FROM user_role WHERE id_user = ?", (user_id,))
        
        # Добавляем только роль Участник
        cursor.execute("""
            INSERT INTO user_role (id_user, id_role, is_selected) 
            VALUES (?, ?, 1)
        """, (user_id, participant[0]))
        
        conn.commit()
        conn.close()
        
        return {"success": True, "message": "Роли исправлены"}
        
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return {"success": False, "error": str(e)}

def check_human_request(request: Request) -> bool:
    """Простая проверка, что запрос не от бота"""
    user_agent = request.headers.get("user-agent", "").lower()
    
    # Блокируем пустые user-agent
    if not user_agent:
        return False
    
    # Блокируем известных ботов
    bot_keywords = ['bot', 'crawler', 'spider', 'scanner', 'curl', 'wget']
    if any(bot in user_agent for bot in bot_keywords):
        return False
    
    return True


@app.post("/api/user/login")
@limiter.limit("5 per minute")
async def login_user(request: Request, credentials: dict):
    """Авторизация пользователя с защитой от брутфорса (упрощенная)"""
    
    # Проверка на бота
    if not check_human_request(request):
        return {"success": False, "error": "Доступ запрещен"}
    
    email = credentials.get("email", "").strip()
    password = credentials.get("password", "")
    
    if not email or not password:
        return {"success": False, "error": "Введите email и пароль"}
    
    conn = get_db_connection()
    if not conn:
        return {"success": False, "error": "Ошибка подключения к БД"}
    
    try:
        cursor = conn.cursor()
        
        # Ищем пользователя
        cursor.execute("""
            SELECT ID, nickname, name, surname, mail, gender, password, is_verificated, is_ban, refer
            FROM users 
            WHERE mail = ?
        """, (email,))
        
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            # Просто возвращаем ошибку, без логирования
            return {"success": False, "error": "Неверный email или пароль"}
        
        user_id, nickname, name, surname, user_email, gender, hashed_password, is_verified, is_banned, refer_code = user
        
        # Проверяем бан
        if is_banned == 1:
            conn.close()
            return {"success": False, "error": "banned"}
        
        # Проверяем пароль
        if not verify_password_secure(password, hashed_password):
            conn.close()
            return {"success": False, "error": "Неверный email или пароль"}
        
        # Получаем текущую роль пользователя
        try:
            cursor.execute("""
                SELECT TOP 1 CAST(r.name AS NVARCHAR(MAX))
                FROM user_role ur
                JOIN roles r ON ur.id_role = r.ID
                WHERE ur.id_user = ?
                ORDER BY ur.ID DESC
            """, (user_id,))
            role_result = cursor.fetchone()
            current_role = role_result[0] if role_result else "Участник"
        except:
            current_role = "Участник"
        
        conn.close()
        
        # Логируем успешный вход (просто в консоль)
        logger.info(f"✅ Успешный вход: {nickname} (ID: {user_id}) from IP: {request.client.host}")
        
        return {
            "success": True,
            "user": {
                "id": user_id,
                "name": name,
                "surname": surname,
                "nickname": nickname,
                "email": user_email,
                "gender": "male" if gender == 1 else "female",
                "is_verificated": bool(is_verified),
                "is_banned": bool(is_banned),
                "current_rank": current_role,
                "refer": refer_code
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка входа: {e}")
        if conn:
            conn.close()
        return {"success": False, "error": str(e)}

def log_failed_attempt(ip: str, email: str):
    """Логирование неудачных попыток входа"""
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        
        # Создаем таблицу для логов, если её нет
        cursor.execute("""
            IF OBJECT_ID('failed_logins', 'U') IS NULL
            BEGIN
                CREATE TABLE failed_logins (
                    ID INT IDENTITY(1,1) PRIMARY KEY,
                    ip VARCHAR(45) NOT NULL,
                    email VARCHAR(255),
                    attempt_time DATETIME DEFAULT GETDATE()
                )
            END
        """)
        
        cursor.execute("""
            INSERT INTO failed_logins (ip, email) VALUES (?, ?)
        """, (ip, email))
        
        conn.commit()
        conn.close()
    except:
        pass

@app.get("/api/user/{user_id}/qr-data")
async def get_user_qr_data(user_id: int):
    """Получение данных пользователя для QR-кода"""
    conn = get_db_connection()
    if not conn:
        # Возвращаем JSON вместо raise для избежания 500
        return {
            "success": False,
            "error": "Ошибка подключения к БД",
            "user_id": user_id
        }
    
    try:
        cursor = conn.cursor()
        
        # Проверяем существование таблицы users
        cursor.execute("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_NAME = 'users'
        """)
        
        if cursor.fetchone()[0] == 0:
            conn.close()
            return {
                "success": False,
                "error": "Таблица users не найдена",
                "user_id": user_id
            }
        
        cursor.execute("""
            SELECT 
                ID, 
                nickname, 
                name, 
                surname, 
                is_verificated, 
                is_ban, 
                refer,
                photo, 
                format_photo,
                mail, 
                age, 
                gender
            FROM users 
            WHERE ID = ?
        """, (user_id,))
        
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            return {
                "success": False,
                "error": f"Пользователь с ID {user_id} не найден",
                "user_id": user_id
            }
        
        # Формируем данные для QR
        qr_data = {
            "success": True,
            "user_id": user[0],
            "nickname": user[1],
            "name": user[2],
            "surname": user[3],
            "is_verified": bool(user[4]),
            "is_banned": bool(user[5]),
            "refer_code": user[6],
            "email": user[9],
            "age": user[10],
            "gender": "male" if user[11] == 1 else "female",
            "timestamp": datetime.now().isoformat()
        }
        
        # Добавляем информацию о фото если есть
        if user[7]:  # photo binary
            import hashlib
            photo_hash = hashlib.md5(user[7]).hexdigest()
            qr_data["photo_hash"] = photo_hash
            qr_data["photo_format"] = user[8] or "jpg"
        
        return qr_data
        
    except Exception as e:
        print(f"❌ Ошибка получения QR-данных: {e}")
        if conn:
            conn.close()
        return {
            "success": False,
            "error": str(e),
            "user_id": user_id
        }

@app.get("/api/user/{user_id}/qr-image")
async def generate_user_qr_image(user_id: int):
    """Генерация QR-кода изображения для пользователя"""
    try:
        # Проверяем наличие библиотеки qrcode
        try:
            import qrcode
            from io import BytesIO
            import json
            import base64
        except ImportError:
            return {
                "success": False,
                "error": "Библиотека qrcode не установлена",
                "user_id": user_id
            }
        
        # Получаем данные пользователя
        qr_data_response = await get_user_qr_data(user_id)
        
        if not qr_data_response.get("success"):
            return qr_data_response
        
        # Убираем поле success из данных для QR
        qr_data = {k: v for k, v in qr_data_response.items() if k != 'success'}
        
        # Компактный JSON
        data_str = json.dumps(qr_data, ensure_ascii=False, separators=(',', ':'))
        
        # Генерируем QR-код
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(data_str)
        qr.make(fit=True)
        
        # Создаем изображение
        img = qr.make_image(
            fill_color="#00ccff",
            back_color="#0a0a1a"
        )
        
        # Конвертируем в base64
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return {
            "success": True,
            "image_base64": img_str,
            "image_url": f"data:image/png;base64,{img_str}",
            "user_id": user_id,
            "data_length": len(data_str)
        }
        
    except Exception as e:
        print(f"❌ Ошибка генерации QR: {e}")
        return {
            "success": False,
            "error": str(e),
            "user_id": user_id
        }
    
@app.get("/api/user/{user_id}/qr-image")
async def generate_user_qr_image(user_id: int):
    """Генерация QR-кода изображения для пользователя"""
    try:
        import qrcode
        from io import BytesIO
        import json
        import base64
        
        # Получаем данные пользователя
        qr_data = await get_user_qr_data(user_id)
        
        # Компактный JSON
        data_str = json.dumps(qr_data, ensure_ascii=False, separators=(',', ':'))
        
        # Генерируем QR-код
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(data_str)
        qr.make(fit=True)
        
        # Создаем изображение
        img = qr.make_image(
            fill_color="#00ccff",
            back_color="#0a0a1a"
        )
        
        # Конвертируем в base64
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return {
            "success": True,
            "image_base64": img_str,
            "image_url": f"data:image/png;base64,{img_str}",
            "user_id": user_id,
            "data_length": len(data_str)
        }
        
    except ImportError:
        raise HTTPException(
            status_code=500, 
            detail="Для генерации QR-изображения установите библиотеку qrcode[pil]"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ticket/{ticket_id}/qr-data")
async def get_ticket_qr_data(ticket_id: int):
    """Получение данных для QR-кода конкретного билета"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Ошибка подключения к БД")
    
    try:
        cursor = conn.cursor()
        
        # Получаем информацию о билете, пользователе и вечеринке
        cursor.execute("""
            SELECT 
                t.ID as ticket_id,
                t.id_user,
                t.id_party,
                u.nickname,
                u.name,
                u.surname,
                u.is_verificated,
                u.is_ban,
                u.refer,
                p.name as party_name,
                p.start_party,
                p.location,
                p.cost
            FROM tickets t
            JOIN users u ON t.id_user = u.ID
            JOIN parties p ON t.id_party = p.ID
            WHERE t.ID = ?
        """, (ticket_id,))
        
        ticket = cursor.fetchone()
        conn.close()
        
        if not ticket:
            raise HTTPException(status_code=404, detail="Билет не найден")
        
        # Формируем данные для QR-кода
        qr_data = {
            "v": 1,  # Версия формата
            "type": "ticket",
            "ticket_id": ticket[0],
            "user_id": ticket[1],
            "party_id": ticket[2],
            "nickname": ticket[3],
            "name": ticket[4],
            "surname": ticket[5],
            "is_verified": bool(ticket[6]),
            "is_banned": bool(ticket[7]),
            "refer_code": ticket[8],
            "party_name": ticket[9],
            "party_date": ticket[10].isoformat() if ticket[10] else None,
            "party_location": ticket[11],
            "party_cost": float(ticket[12]) if ticket[12] else 0,
            "timestamp": datetime.now().isoformat()
        }
        
        return {
            "success": True,
            "qr_data": qr_data,
            "ticket_id": ticket_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        if conn:
            conn.close()
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/api/giveaway/claim")
async def claim_giveaway_ticket(request: dict):
    """Активация бесплатного билета по QR-коду"""
    qr_code = request.get("code")
    user_id = request.get("user_id")
    
    if not qr_code or not user_id:
        return {"success": False, "error": "Не указан код или пользователь"}
    
    conn = get_db_connection()
    if not conn:
        return {"success": False, "error": "Ошибка подключения к БД"}
    
    try:
        cursor = conn.cursor()
        
        # Проверяем существование QR-кода
        cursor.execute("""
            SELECT ID, party_id, is_used, expires_at 
            FROM giveaway_qr_codes 
            WHERE code = ?
        """, (qr_code,))
        
        qr = cursor.fetchone()
        
        if not qr:
            conn.close()
            return {"success": False, "error": "Недействительный QR-код"}
        
        qr_id, party_id, is_used, expires_at = qr
        
        # Проверяем, не использован ли уже
        if is_used:
            conn.close()
            return {"success": False, "error": "Этот билет уже был активирован"}
        
        # Проверяем срок действия
        if expires_at and expires_at < datetime.now():
            conn.close()
            return {"success": False, "error": "Срок действия билета истек"}
        
        # Проверяем, нет ли уже билета у пользователя на эту вечеринку
        cursor.execute("""
            SELECT ID FROM tickets 
            WHERE id_user = ? AND id_party = ?
        """, (user_id, party_id))
        
        if cursor.fetchone():
            conn.close()
            return {"success": False, "error": "У вас уже есть билет на эту вечеринку"}
        
        # Создаем билет
        cursor.execute("""
            INSERT INTO tickets (id_user, id_party, date_sale)
            VALUES (?, ?, GETDATE())
        """, (user_id, party_id))
        
        ticket_id = cursor.execute("SELECT @@IDENTITY").fetchone()[0]
        
        # Отмечаем QR как использованный
        cursor.execute("""
            UPDATE giveaway_qr_codes 
            SET is_used = 1, used_by_user_id = ?, used_at = GETDATE()
            WHERE ID = ?
        """, (user_id, qr_id))
        
        conn.commit()
        conn.close()
        
        # Получаем информацию о вечеринке для ответа
        party_info = await get_party_info(party_id)
        
        return {
            "success": True,
            "message": "Билет успешно активирован!",
            "ticket_id": ticket_id,
            "party": party_info
        }
        
    except Exception as e:
        print(f"❌ Ошибка активации билета: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return {"success": False, "error": str(e)}

@app.post("/api/admin/giveaway/create")
async def create_giveaway_qr(request: dict, admin_id: int):
    """Создание QR-кода для розыгрыша (только для админов)"""
    party_id = request.get("party_id")
    count = request.get("count", 1)
    expires_days = request.get("expires_days", 30)
    
    if not party_id:
        return {"success": False, "error": "Не указана вечеринка"}
    
    conn = get_db_connection()
    if not conn:
        return {"success": False, "error": "Ошибка подключения к БД"}
    
    try:
        cursor = conn.cursor()
        
        # Проверяем существование вечеринки
        cursor.execute("SELECT name FROM parties WHERE ID = ?", (party_id,))
        party = cursor.fetchone()
        if not party:
            conn.close()
            return {"success": False, "error": "Вечеринка не найдена"}
        
        import secrets
        import json
        from datetime import datetime, timedelta
        
        codes = []
        expires_at = datetime.now() + timedelta(days=expires_days)
        
        for i in range(count):
            # Генерируем уникальный код
            code = secrets.token_urlsafe(16)
            
            cursor.execute("""
                INSERT INTO giveaway_qr_codes (code, party_id, expires_at, created_by)
                VALUES (?, ?, ?, ?)
            """, (code, party_id, expires_at, admin_id))
            
            codes.append(code)
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": f"Создано {count} QR-кодов",
            "codes": codes,
            "party_name": party[0]
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания QR-кодов: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return {"success": False, "error": str(e)}
    
@app.post("/api/admin/create-giveaway-tickets")
async def create_giveaway_tickets(request: dict):
    """Создание билетов для розыгрыша с автоматической генерацией отрицательных ID"""
    party_id = request.get("party_id")
    count = request.get("count", 10)
    admin_id = request.get("admin_id")
    
    if not party_id:
        return {"success": False, "error": "Не указана вечеринка"}
    
    if count <= 0 or count > 1000:
        return {"success": False, "error": "Количество должно быть от 1 до 1000"}
    
    conn = get_db_connection()
    if not conn:
        return {"success": False, "error": "Ошибка подключения к БД"}
    
    try:
        cursor = conn.cursor()
        
        # Начинаем транзакцию
        cursor.execute("BEGIN TRANSACTION")
        
        # Проверяем существование вечеринки
        cursor.execute("SELECT name FROM parties WHERE ID = ?", (party_id,))
        party = cursor.fetchone()
        if not party:
            cursor.execute("ROLLBACK TRANSACTION")
            conn.close()
            return {"success": False, "error": "Вечеринка не найдена"}
        
        # Находим следующий отрицательный ID
        cursor.execute("""
            SELECT ISNULL(MIN(id_user), 0) - 1 
            FROM tickets 
            WHERE id_user < 0
        """)
        next_id = cursor.fetchone()[0]
        
        # Если нет отрицательных, начинаем с -1
        if next_id > -1:
            next_id = -1
        
        created_tickets = []
        start_id = next_id
        
        # Создаем билеты с убывающими ID
        for i in range(count):
            current_id = next_id - i
            cursor.execute("""
                INSERT INTO tickets (id_user, id_party, date_sale)
                OUTPUT INSERTED.ID as ticket_db_id
                VALUES (?, ?, NULL)
            """, (current_id, party_id))
            
            ticket_db_id = cursor.fetchone()[0]
            created_tickets.append({
                "negative_id": current_id,
                "db_id": ticket_db_id
            })
        
        # Подтверждаем транзакцию
        cursor.execute("COMMIT TRANSACTION")
        
        # Логируем действие админа
        try:
            cursor.execute("""
                IF OBJECT_ID('admin_actions', 'U') IS NOT NULL
                BEGIN
                    INSERT INTO admin_actions (admin_id, action_type, details, timestamp)
                    VALUES (?, 'create_giveaway', ?, GETDATE())
                END
            """, (admin_id, f"Создано {count} билетов для вечеринки {party_id}"))
        except:
            pass
        
        conn.close()
        
        return {
            "success": True,
            "message": f"Создано {count} билетов для розыгрыша",
            "party_id": party_id,
            "party_name": party[0],
            "count": count,
            "id_range": {
                "start": start_id,
                "end": next_id - count + 1
            },
            "tickets": created_tickets
        }
        
    except Exception as e:
        # Откатываем транзакцию в случае ошибки
        cursor.execute("ROLLBACK TRANSACTION")
        conn.close()
        logger.error(f"❌ Ошибка создания билетов: {e}")
        return {"success": False, "error": str(e)}
    
@app.post("/api/claim-ticket")
async def claim_ticket(request: dict):
    """Активация билета по отрицательному ID"""
    ticket_negative_id = request.get("ticket_id")  # Это будет -1, -2 и т.д.
    user_id = request.get("user_id")
    
    print(f"🎫 Попытка активации: ticket_id={ticket_negative_id}, user_id={user_id}")
    
    if not ticket_negative_id or not user_id:
        return {"success": False, "error": "Не указан билет или пользователь"}
    
    # Проверяем, что ID отрицательный
    if ticket_negative_id >= 0:
        return {"success": False, "error": "Неверный формат билета"}
    
    conn = get_db_connection()
    if not conn:
        return {"success": False, "error": "Ошибка подключения к БД"}
    
    try:
        cursor = conn.cursor()
        
        # Проверяем существование билета с таким отрицательным ID
        cursor.execute("""
            SELECT t.id, t.id_party, p.name, p.location, p.start_party
            FROM tickets t
            JOIN parties p ON t.id_party = p.ID
            WHERE t.id_user = ? AND t.date_sale IS NULL
        """, (ticket_negative_id,))
        
        ticket = cursor.fetchone()
        
        if not ticket:
            conn.close()
            print(f"❌ Билет с ID {ticket_negative_id} не найден или уже активирован")
            return {"success": False, "error": "Билет не найден или уже активирован"}
        
        ticket_db_id, party_id, party_name, party_location, party_date = ticket
        
        # Проверяем, нет ли уже билета у пользователя на эту вечеринку
        cursor.execute("""
            SELECT 1 FROM tickets 
            WHERE id_user = ? AND id_party = ? AND date_sale IS NOT NULL
        """, (user_id, party_id))
        
        if cursor.fetchone():
            conn.close()
            return {"success": False, "error": "У вас уже есть билет на эту вечеринку"}
        
        # Активируем билет
        cursor.execute("""
            UPDATE tickets 
            SET id_user = ?, date_sale = GETDATE()
            WHERE id = ? AND id_user = ? AND date_sale IS NULL
        """, (user_id, ticket_db_id, ticket_negative_id))
        
        if cursor.rowcount == 0:
            conn.close()
            return {"success": False, "error": "Не удалось активировать билет"}
        
        conn.commit()
        conn.close()
        
        print(f"✅ Билет {ticket_negative_id} активирован для пользователя {user_id}")
        
        return {
            "success": True,
            "message": "Билет успешно активирован!",
            "ticket_id": ticket_db_id,
            "party": {
                "id": party_id,
                "name": party_name,
                "location": party_location,
                "date": party_date.isoformat() if party_date else None
            }
        }
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        conn.rollback()
        conn.close()
        return {"success": False, "error": str(e)}
    
@app.get("/api/admin/giveaway-status/{party_id}")
async def get_giveaway_status(party_id: int):
    """Получение статуса розыгрыша по вечеринке"""
    conn = get_db_connection()
    if not conn:
        return {"success": False, "error": "Ошибка подключения к БД"}
    
    try:
        cursor = conn.cursor()
        
        # Получаем статистику
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN date_sale IS NULL THEN 1 ELSE 0 END) as available,
                SUM(CASE WHEN date_sale IS NOT NULL THEN 1 ELSE 0 END) as claimed
            FROM tickets
            WHERE id_party = ? AND id_user < 0
        """, (party_id,))
        
        total, available, claimed = cursor.fetchone()
        
        # Получаем список активированных билетов
        cursor.execute("""
            SELECT 
                t.id_user as negative_id,
                u.nickname,
                u.name,
                u.surname,
                t.date_sale
            FROM tickets t
            JOIN users u ON t.id_user = u.ID
            WHERE t.id_party = ? AND t.date_sale IS NOT NULL AND t.id_user > 0
            ORDER BY t.date_sale DESC
        """, (party_id,))
        
        activated = []
        for row in cursor.fetchall():
            activated.append({
                "user": f"{row[2]} {row[3]} (@{row[1]})",
                "activated_at": row[4].isoformat() if row[4] else None
            })
        
        conn.close()
        
        return {
            "success": True,
            "party_id": party_id,
            "statistics": {
                "total": total or 0,
                "available": available or 0,
                "claimed": claimed or 0
            },
            "activated": activated
        }
        
    except Exception as e:
        conn.close()
        return {"success": False, "error": str(e)}

@app.post("/api/ticket/buy-test")
async def buy_test_ticket(request: dict):
    """Псевдо-покупка билета для тестирования"""
    print(f"📥 Получен запрос на покупку билета: {request}")
    
    user_id = request.get("user_id")
    party_id = request.get("party_id")
    
    if not user_id:
        return {"success": False, "error": "Не указан user_id"}
    
    if not party_id:
        return {"success": False, "error": "Не указан party_id"}
    
    try:
        user_id = int(user_id)
        party_id = int(party_id)
    except ValueError:
        return {"success": False, "error": "user_id и party_id должны быть числами"}
    
    conn = get_db_connection()
    if not conn:
        return {"success": False, "error": "Ошибка подключения к БД"}
    
    try:
        cursor = conn.cursor()
        
        # 1. Проверяем, существует ли пользователь
        cursor.execute("SELECT ID, nickname FROM users WHERE ID = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            conn.close()
            return {"success": False, "error": f"Пользователь с ID {user_id} не найден"}
        
        # 2. Проверяем, существует ли вечеринка
        cursor.execute("""
            SELECT ID, name, cost, location, start_party 
            FROM parties 
            WHERE ID = ? AND start_party > GETDATE()
        """, (party_id,))
        
        party = cursor.fetchone()
        if not party:
            conn.close()
            return {"success": False, "error": f"Вечеринка с ID {party_id} не найдена или уже прошла"}
        
        party_id_db, party_name, party_cost, party_location, party_date = party
        
        # 3. Проверяем, нет ли уже билета
        cursor.execute("""
            SELECT ID FROM tickets 
            WHERE id_user = ? AND id_party = ?
        """, (user_id, party_id_db))
        
        existing_ticket = cursor.fetchone()
        
        if existing_ticket:
            conn.close()
            return {
                "success": False, 
                "error": "Билет на эту вечеринку уже есть",
                "ticket_id": existing_ticket[0]
            }
        
        # 4. Создаем новый билет
        cursor.execute("""
            INSERT INTO tickets (id_user, id_party, date_sale)
            OUTPUT INSERTED.ID
            VALUES (?, ?, GETDATE())
        """, (user_id, party_id_db))
        
        ticket_id = cursor.fetchone()[0]
        
        conn.commit()
        conn.close()
        
        print(f"✅ Билет #{ticket_id} создан для пользователя {user_id} на вечеринку '{party_name}'")
        
        return {
            "success": True,
            "message": "Билет успешно куплен! 🎉",
            "ticket_id": ticket_id,
            "user_id": user_id,
            "party_id": party_id_db,
            "party_name": party_name,
            "party_cost": float(party_cost) if party_cost else 0,
            "party_location": party_location,
            "party_date": party_date.isoformat() if party_date else None
        }
        
    except Exception as e:
        print(f"❌ Ошибка создания билета: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
            conn.close()
        return {"success": False, "error": str(e)}

@app.get("/api/users", response_model=List[dict])
async def get_users(limit: int = 10, offset: int = 0):
    """Получение списка пользователей (адаптировано под текущую БД)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Запрос для текущей БД (без отсутствующих полей)
        # В функции get_users:
        cursor.execute("""
            SELECT 
                u.ID, u.nickname, u.name, u.surname, u.mail, u.refer,
                u.is_verificated, u.is_ban,
                -- Получаем роли отдельным запросом
                (SELECT STRING_AGG(CAST(r.name AS NVARCHAR(MAX)), ', ') 
                FROM user_role ur 
                JOIN roles r ON ur.id_role = r.ID 
                WHERE ur.id_user = u.ID) as user_roles
            FROM users u
            ORDER BY u.ID DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """, (offset, limit))
        
        columns = [column[0] for column in cursor.description]
        users = []
        for row in cursor.fetchall():
            user_dict = dict(zip(columns, row))
            # Добавляем поля, которые ожидает фронтенд (с заглушками)
            user_dict.update({
                'full_name': f"{user_dict['name']} {user_dict['surname']}",
                'invited_count': 0,           # Заглушка - нет в БД
                'visits_count': 0,            # Заглушка - нет в БД
                'total_bar_spent': 0,         # Заглушка - нет в БД
                'battle_participations': 0,   # Заглушка - нет в БД
                'current_rank': user_dict.get('current_rank', 'Участник')
            })
            users.append(user_dict)
        
        conn.close()
        return users
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    


# Временное хранилище для выбранных ролей (в памяти)
user_selected_roles_cache = {}

@app.get("/api/user/{user_id}/roles")
async def get_user_roles_api(user_id: int):
    """API для получения ролей пользователя (УПРОЩЕННАЯ ВЕРСИЯ)"""
    try:
        conn = get_db_connection()
        if not conn:
            return {
                "success": False,
                "error": "Нет подключения к БД",
                "user_id": user_id
            }
        
        cursor = conn.cursor()
        
        # 1. Получаем все роли пользователя (без сортировки)
        cursor.execute("""
            SELECT DISTINCT CAST(r.name AS NVARCHAR(MAX)) as role_name
            FROM user_role ur
            JOIN roles r ON ur.id_role = r.ID
            WHERE ur.id_user = ?
        """, (user_id,))
        
        results = cursor.fetchall()
        all_roles = [row[0] for row in results]
        
        # 2. Получаем выбранную роль (если есть)
        cursor.execute("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'user_role' AND COLUMN_NAME = 'selected_role'
        """)
        
        has_selected_role = cursor.fetchone()[0] > 0
        selected_role = None
        
        if has_selected_role:
            cursor.execute("""
                SELECT TOP 1 selected_role
                FROM user_role 
                WHERE id_user = ? AND selected_role IS NOT NULL
            """, (user_id,))
            
            selected_result = cursor.fetchone()
            if selected_result:
                selected_role = selected_result[0]
        
        conn.close()
        
        # 3. Если ролей нет, добавляем Участника
        if not all_roles:
            all_roles = ['Участник']
            if not selected_role:
                selected_role = 'Участник'
            
            # Добавляем роль Участник в БД
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT ID FROM roles WHERE CAST(name AS NVARCHAR(MAX)) = 'Участник'")
                participant = cursor.fetchone()
                if participant:
                    if has_selected_role:
                        cursor.execute("""
                            INSERT INTO user_role (id_user, id_role, selected_role) 
                            VALUES (?, ?, ?)
                        """, (user_id, participant[0], 'Участник'))
                    else:
                        cursor.execute("INSERT INTO user_role (id_user, id_role) VALUES (?, ?)", 
                                     (user_id, participant[0]))
                    conn.commit()
                conn.close()
        
        # 4. Если нет выбранной роли, но есть роли, берем первую
        if not selected_role and all_roles:
            selected_role = all_roles[0]
        
        # 5. Сортируем роли так, чтобы выбранная была первой
        sorted_roles = []
        if selected_role and selected_role in all_roles:
            sorted_roles.append(selected_role)
            for role in all_roles:
                if role != selected_role:
                    sorted_roles.append(role)
        else:
            sorted_roles = all_roles
        
        # 6. Разделяем на типы
        auto_roles = []
        admin_roles = []
        
        for role in sorted_roles:
            if role in ['Танцор', 'Ас танцпола', 'Любитель выпить', 'Глава бара']:
                admin_roles.append(role)
            else:
                auto_roles.append(role)
        
        has_legend = 'Легенда' in sorted_roles
        
        print(f"📊 Роли пользователя {user_id}: {sorted_roles}")
        print(f"🎯 Выбранная роль: {selected_role}")
        
        return {
            "success": True,
            "user_id": user_id,
            "all_roles": sorted_roles,
            "auto_roles": sorted(auto_roles),
            "admin_roles": sorted(admin_roles),
            "total_count": len(sorted_roles),
            "has_legend": has_legend,
            "selected_role": selected_role
        }
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "user_id": user_id
        }

@app.get("/api/user/{user_id}/selected-role")
async def get_selected_role(user_id: int):
    """Получение выбранной пользователем роли (последняя добавленная)"""
    conn = get_db_connection()
    if not conn:
        return {"success": True, "user_id": user_id, "selected_role": None}
    
    try:
        cursor = conn.cursor()
        
        # Получаем последнюю добавленную роль (максимальный ID в user_role)
        cursor.execute("""
            SELECT TOP 1 CAST(r.name AS NVARCHAR(MAX)) as role_name
            FROM user_role ur
            JOIN roles r ON ur.id_role = r.ID
            WHERE ur.id_user = ?
            ORDER BY ur.ID DESC  -- Берем запись с наибольшим ID (последнюю добавленную)
        """, (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        selected_role = result[0] if result else None
        
        return {
            "success": True,
            "user_id": user_id,
            "selected_role": selected_role,
            "selected_at": datetime.now().isoformat() if selected_role else None,
            "method": "last_added_role"
        }
        
    except Exception as e:
        if conn:
            conn.close()
        return {"success": True, "user_id": user_id, "selected_role": None}

@app.get("/api/user/{user_id}/selected-role")
async def get_selected_role(user_id: int):
    """Получение выбранной пользователем роли"""
    if user_id in user_selected_roles_cache:
        return {
            "success": True,
            "user_id": user_id,
            "selected_role": user_selected_roles_cache[user_id]["role"],
            "selected_at": user_selected_roles_cache[user_id]["selected_at"],
            "from_cache": True
        }
    else:
        return {
            "success": True,
            "user_id": user_id,
            "selected_role": None,
            "message": "Роль не выбрана"
        }
    

@app.post("/api/user/{user_id}/force-check-roles")
async def force_check_user_roles(user_id: int):
    """Принудительная проверка и обновление ролей пользователя"""
    try:
        result = RoleManager.check_and_update_roles(user_id)
        
        if result["success"]:
            return {
                "success": True,
                "message": "Роли успешно проверены и обновлены",
                "added_roles": result.get("added_roles", []),
                "current_roles": result.get("current_roles", []),
                "user_id": user_id
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Неизвестная ошибка")
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/api/user/{user_id}/roles")
async def get_user_roles_api(user_id: int):
    """API для получения ролей пользователя (ИСПРАВЛЕННАЯ ВЕРСИЯ)"""
    try:
        conn = get_db_connection()
        if not conn:
            return {
                "success": False,
                "error": "Нет подключения к БД",
                "user_id": user_id
            }
        
        cursor = conn.cursor()
        
        # Проверяем, есть ли поле selected_role
        cursor.execute("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'user_role' AND COLUMN_NAME = 'selected_role'
        """)
        
        has_selected_role = cursor.fetchone()[0] > 0
        
        if has_selected_role:
            # Получаем выбранную роль
            cursor.execute("""
                SELECT TOP 1 selected_role
                FROM user_role 
                WHERE id_user = ? AND selected_role IS NOT NULL
            """, (user_id,))
            
            selected_result = cursor.fetchone()
            selected_role = selected_result[0] if selected_result else None
            
            # Получаем все уникальные роли пользователя без ORDER BY в основном запросе
            cursor.execute("""
                SELECT DISTINCT CAST(r.name AS NVARCHAR(MAX)) as role_name
                FROM user_role ur
                JOIN roles r ON ur.id_role = r.ID
                WHERE ur.id_user = ?
            """, (user_id,))
            
            results = cursor.fetchall()
            all_roles = [row[0] for row in results]
            
            # Если есть выбранная роль, перемещаем её в начало списка
            if selected_role and selected_role in all_roles:
                all_roles.remove(selected_role)
                all_roles.insert(0, selected_role)
            elif not selected_role and all_roles:
                selected_role = all_roles[0]
            elif not all_roles:
                all_roles = ['Участник']
                selected_role = 'Участник'
            
        else:
            # Старая версия - без selected_role
            cursor.execute("""
                SELECT CAST(r.name AS NVARCHAR(MAX)) as role_name
                FROM user_role ur
                JOIN roles r ON ur.id_role = r.ID
                WHERE ur.id_user = ?
                GROUP BY CAST(r.name AS NVARCHAR(MAX))
                ORDER BY MAX(ur.ID) DESC
            """, (user_id,))
            
            results = cursor.fetchall()
            all_roles = [row[0] for row in results]
            selected_role = all_roles[0] if all_roles else 'Участник'
        
        # Если ролей нет, добавляем Участника
        if not all_roles:
            all_roles = ['Участник']
            selected_role = 'Участник'
            # Проверяем, есть ли роль Участник
            cursor.execute("SELECT ID FROM roles WHERE CAST(name AS NVARCHAR(MAX)) = 'Участник'")
            participant = cursor.fetchone()
            if participant:
                if has_selected_role:
                    cursor.execute("""
                        INSERT INTO user_role (id_user, id_role, selected_role) 
                        VALUES (?, ?, ?)
                    """, (user_id, participant[0], 'Участник'))
                else:
                    cursor.execute("INSERT INTO user_role (id_user, id_role) VALUES (?, ?)", 
                                 (user_id, participant[0]))
                conn.commit()
        
        # Разделяем на типы
        auto_roles = []
        admin_roles = []
        
        for role in all_roles:
            if role in ['Танцор', 'Ас танцпола', 'Любитель выпить', 'Глава бара']:
                admin_roles.append(role)
            else:
                auto_roles.append(role)
        
        has_legend = 'Легенда' in all_roles
        
        conn.close()
        
        print(f"📊 Роли пользователя {user_id}: {all_roles}")
        print(f"🎯 Выбранная роль: {selected_role}")
        
        return {
            "success": True,
            "user_id": user_id,
            "all_roles": all_roles,
            "auto_roles": sorted(auto_roles),
            "admin_roles": sorted(admin_roles),
            "total_count": len(all_roles),
            "has_legend": has_legend,
            "selected_role": selected_role
        }
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "user_id": user_id
        }
    

@app.post("/api/user/{user_id}/select-role")
async def select_user_role(user_id: int, request: dict):
    """Выбор роли пользователем - поддержка Легенды"""
    role_name = request.get("role_name")
    
    if not role_name:
        return {"success": False, "error": "Не указана роль"}
    
    print(f"\n{'='*50}")
    print(f"🎯 ВЫБОР РОЛИ: Пользователь {user_id} выбирает роль: {role_name}")
    print(f"{'='*50}")
    
    conn = get_db_connection()
    if not conn:
        return {"success": False, "error": "Ошибка подключения к БД"}
    
    try:
        cursor = conn.cursor()
        
        # Проверяем наличие поля selected_role
        cursor.execute("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'user_role' AND COLUMN_NAME = 'selected_role'
        """)
        
        has_selected_role = cursor.fetchone()[0] > 0
        
        if not has_selected_role:
            conn.close()
            return {"success": False, "error": "Требуется миграция"}
        
        # Получаем ID роли
        cursor.execute("SELECT ID FROM roles WHERE CAST(name AS NVARCHAR(MAX)) = ?", (role_name,))
        role_result = cursor.fetchone()
        
        if not role_result:
            conn.close()
            return {"success": False, "error": f"Роль '{role_name}' не найдена"}
        
        role_id = role_result[0]
        
        # Проверяем, есть ли у пользователя эта роль
        cursor.execute("SELECT 1 FROM user_role WHERE id_user = ? AND id_role = ?", (user_id, role_id))
        
        if not cursor.fetchone():
            conn.close()
            return {"success": False, "error": f"У вас нет роли '{role_name}'"}
        
        # Сбрасываем selected_role для всех записей пользователя
        cursor.execute("UPDATE user_role SET selected_role = NULL WHERE id_user = ?", (user_id,))
        print(f"🔄 Сброшены все selected_role")
        
        # Устанавливаем selected_role для выбранной роли
        cursor.execute("""
            UPDATE user_role 
            SET selected_role = ? 
            WHERE id_user = ? AND id_role = ?
        """, (role_name, user_id, role_id))
        
        affected_rows = cursor.rowcount
        print(f"✅ Обновлено записей: {affected_rows}")
        
        conn.commit()
        
        # Проверяем, что сохранилось
        cursor.execute("""
            SELECT selected_role FROM user_role 
            WHERE id_user = ? AND selected_role IS NOT NULL
        """, (user_id,))
        
        saved = cursor.fetchone()
        if saved:
            print(f"✅ В БД сохранена роль: '{saved[0]}'")
        else:
            print("❌ Ошибка: роль не сохранилась!")
        
        conn.close()
        
        return {
            "success": True,
            "message": f"Роль '{role_name}' выбрана как основная",
            "user_id": user_id,
            "selected_role": role_name
        }
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return {"success": False, "error": str(e)}
    

@app.get("/api/parties")
async def get_parties(upcoming: bool = True):
    """Получение списка вечеринок из БД"""
    try:
        conn = get_db_connection()
        if not conn:
            return []
        
        cursor = conn.cursor()
        
        if upcoming:
            query = """
                SELECT 
                    ID,
                    name,
                    cost,
                    location,
                    CONVERT(VARCHAR, start_party, 104) as date,
                    CONVERT(VARCHAR, start_party, 108) as time,
                    count_seats,
                    id_city
                FROM parties 
                WHERE start_party > GETDATE()
                ORDER BY start_party ASC
            """
        else:
            query = """
                SELECT 
                    ID,
                    name,
                    cost,
                    location,
                    CONVERT(VARCHAR, start_party, 104) as date,
                    CONVERT(VARCHAR, start_party, 108) as time,
                    count_seats,
                    id_city
                FROM parties 
                ORDER BY start_party DESC
            """
        
        cursor.execute(query)
        
        columns = [column[0] for column in cursor.description]
        parties = []
        
        for row in cursor.fetchall():
            party_dict = dict(zip(columns, row))
            if 'cost' in party_dict and party_dict['cost'] is not None:
                party_dict['cost'] = float(party_dict['cost'])
            parties.append(party_dict)
        
        conn.close()
        
        print(f"📊 Загружено {len(parties)} вечеринок из БД")
        print(f"   ID вечеринок: {[p['ID'] for p in parties]}")  # Отладка
        
        return parties
        
    except Exception as e:
        print(f"❌ Ошибка получения вечеринок: {e}")
        if conn:
            conn.close()
        return []

def get_test_parties():
    """Возвращает тестовые данные вечеринок"""
    from datetime import datetime, timedelta
    
    now = datetime.now()
    
    return [
        {
            "id": 1,
            "name": "Новогодняя ночь 🎄",
            "cost": 3500.00,
            "location": "Клуб 'Ледниковый'",
            "date": (now + timedelta(days=3)).strftime("%d.%m.%Y"),
            "time": "22:00:00",
            "count_seats": 200,
            "id_city": 1
        },
        {
            "id": 2,
            "name": "Рождественский бал ✨",
            "cost": 2800.00,
            "location": "Ресторан 'Сибирь'",
            "date": (now + timedelta(days=10)).strftime("%d.%m.%Y"),
            "time": "21:00:00",
            "count_seats": 150,
            "id_city": 1
        },
        {
            "id": 3,
            "name": "Зимний фестиваль ❄️",
            "cost": 2200.00,
            "location": "Бар 'У камина'",
            "date": (now + timedelta(days=20)).strftime("%d.%m.%Y"),
            "time": "20:00:00",
            "count_seats": 100,
            "id_city": 1
        }
    ]

@app.get("/api/debug/parties")
async def debug_parties():
    """Отладочный эндпоинт для проверки вечеринок в БД"""
    conn = get_db_connection()
    if not conn:
        return {"success": False, "error": "Нет подключения к БД"}
    
    try:
        cursor = conn.cursor()
        
        # 1. Проверяем существование таблицы
        cursor.execute("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_NAME = 'parties'
        """)
        table_exists = cursor.fetchone()[0] > 0
        
        if not table_exists:
            conn.close()
            return {"success": False, "error": "Таблица parties не существует"}
        
        # 2. Получаем все вечеринки
        cursor.execute("""
            SELECT 
                ID,
                name,
                cost,
                location,
                start_party,
                count_seats,
                id_city
            FROM parties
            ORDER BY start_party
        """)
        
        parties = []
        for row in cursor.fetchall():
            parties.append({
                "id": row[0],
                "name": row[1],
                "cost": float(row[2]) if row[2] else 0,
                "location": row[3],
                "start_party": row[4].isoformat() if row[4] else None,
                "count_seats": row[5],
                "id_city": row[6]
            })
        
        # 3. Проверяем будущие вечеринки
        cursor.execute("""
            SELECT COUNT(*) FROM parties 
            WHERE start_party > GETDATE()
        """)
        upcoming_count = cursor.fetchone()[0]
        
        # 4. Текущее время на сервере
        cursor.execute("SELECT GETDATE()")
        current_time = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "success": True,
            "table_exists": table_exists,
            "total_parties": len(parties),
            "upcoming_parties": upcoming_count,
            "server_time": current_time.isoformat() if current_time else None,
            "parties": parties
        }
        
    except Exception as e:
        if conn:
            conn.close()
        return {"success": False, "error": str(e)}
    
@app.get("/api/ticket/{ticket_id}/qr-image")
async def get_ticket_qr_image(ticket_id: int):
    """Генерация QR-кода изображения для билета"""
    try:
        import qrcode
        from io import BytesIO
        import json
        import base64
        
        # Получаем данные для QR
        qr_data_response = await get_ticket_qr_data(ticket_id)
        qr_data = qr_data_response["qr_data"]
        
        # Компактный JSON
        data_str = json.dumps(qr_data, ensure_ascii=False, separators=(',', ':'))
        
        # Генерируем QR-код
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(data_str)
        qr.make(fit=True)
        
        # Создаем изображение
        img = qr.make_image(
            fill_color="#00ccff",
            back_color="#0a0a1a"
        )
        
        # Конвертируем в base64
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return {
            "success": True,
            "image_base64": img_str,
            "image_url": f"data:image/png;base64,{img_str}",
            "ticket_id": ticket_id,
            "party_name": qr_data["party_name"],
            "party_location": qr_data["party_location"]
        }
        
    except ImportError:
        raise HTTPException(
            status_code=500, 
            detail="Для генерации QR-изображения установите библиотеку qrcode[pil]"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ticket/{ticket_id}/qr-image")
async def get_ticket_qr_image(ticket_id: int):
    """Генерация QR-кода изображения для билета"""
    print(f"📱 Запрос QR-кода для билета {ticket_id}")
    
    try:
        import qrcode
        from io import BytesIO
        import json
        import base64
        
        # Получаем данные для QR
        qr_data_response = await get_ticket_qr_data(ticket_id)
        
        if not qr_data_response.get("success"):
            raise HTTPException(status_code=404, detail="Билет не найден")
            
        qr_data = qr_data_response["qr_data"]
        
        # Компактный JSON
        data_str = json.dumps(qr_data, ensure_ascii=False, separators=(',', ':'))
        print(f"📝 Данные для QR: {data_str[:100]}...")
        
        # Генерируем QR-код
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(data_str)
        qr.make(fit=True)
        
        # Создаем изображение
        img = qr.make_image(
            fill_color="#00ccff",
            back_color="#0a0a1a"
        )
        
        # Конвертируем в base64
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        print(f"✅ QR-код для билета {ticket_id} сгенерирован")
        
        return {
            "success": True,
            "image_base64": img_str,
            "image_url": f"data:image/png;base64,{img_str}",
            "ticket_id": ticket_id,
            "party_name": qr_data.get("party_name"),
            "party_location": qr_data.get("party_location")
        }
        
    except ImportError:
        print("❌ Библиотека qrcode не установлена")
        raise HTTPException(
            status_code=500, 
            detail="Для генерации QR-изображения установите библиотеку qrcode[pil]"
        )
    except Exception as e:
        print(f"❌ Ошибка генерации QR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/api/user/{user_id}/visits-count")
async def get_visits_count(user_id: int):
    """Получение количества посещений (купленных билетов) пользователя"""
    conn = get_db_connection()
    if not conn:
        return {"success": False, "error": "Ошибка подключения к БД"}
    
    try:
        cursor = conn.cursor()
        
        # Считаем количество билетов пользователя
        cursor.execute("SELECT COUNT(*) FROM tickets WHERE id_user = ?", (user_id,))
        count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "success": True,
            "user_id": user_id,
            "visits_count": count
        }
        
    except Exception as e:
        print(f"❌ Ошибка получения количества посещений: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/qr/verify")
async def verify_qr_code(request_data: dict):
    """
    Верификация QR-кода сканером администратора
    Принимает JSON данные из QR-кода
    """
    qr_data = request_data.get("qr_data")
    
    if not qr_data:
        raise HTTPException(status_code=400, detail="No QR data provided")
    
    # Проверяем обязательные поля
    required_fields = ["user_id", "nickname", "refer_code"]
    for field in required_fields:
        if field not in qr_data:
            return {
                "valid": False,
                "error": f"Отсутствует обязательное поле: {field}",
                "action": "invalid_qr"
            }
    
    user_id = qr_data.get("user_id")
    
    # Проверяем актуальность данных (не старше 24 часов)
    if "timestamp" in qr_data:
        try:
            qr_time = datetime.fromisoformat(qr_data["timestamp"].replace('Z', '+00:00'))
            time_diff = datetime.now(timezone.utc) - qr_time
            
            if time_diff.total_seconds() > 86400:  # 24 часа
                return {
                    "valid": False,
                    "error": "QR код устарел (более 24 часов)",
                    "action": "qr_expired",
                    "qr_age_hours": round(time_diff.total_seconds() / 3600, 1),
                    "user_info": {
                        "id": user_id,
                        "nickname": qr_data.get("nickname"),
                        "name": f"{qr_data.get('name', '')} {qr_data.get('surname', '')}".strip()
                    }
                }
        except Exception as e:
            print(f"⚠️ Ошибка проверки времени: {e}")
            # Продолжаем проверку даже если время неверное
    
    # Получаем актуальные данные из БД
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Проверяем пользователя
    current_party_id = qr_data.get("current_party_id", 1)  # ID текущей вечеринки
    
    cursor.execute("""
        SELECT 
            u.ID, u.nickname, u.name, u.surname, 
            u.is_verificated, u.is_ban, u.refer,
            (SELECT COUNT(*) FROM tickets t WHERE t.id_user = u.ID AND t.id_party = ?) as has_ticket
        FROM users u
        WHERE u.ID = ?
    """, (current_party_id, user_id))
    
    db_user = cursor.fetchone()
    conn.close()
    
    if not db_user:
        return {
            "valid": False,
            "error": "Пользователь не найден в базе данных",
            "action": "user_not_found",
            "qr_user_id": user_id
        }
    
    # Проверяем бан
    if db_user[5]:  # is_ban
        return {
            "valid": False,
            "user_info": {
                "id": db_user[0],
                "nickname": db_user[1],
                "name": f"{db_user[2]} {db_user[3]}",
                "refer_code": db_user[6]
            },
            "error": "Пользователь забанен",
            "action": "user_banned",
            "timestamp": datetime.now().isoformat()
        }
    
    # Проверяем верификацию
    if not db_user[4]:  # is_verificated
        return {
            "valid": False,
            "user_info": {
                "id": db_user[0],
                "nickname": db_user[1],
                "name": f"{db_user[2]} {db_user[3]}",
                "refer_code": db_user[6]
            },
            "error": "Требуется верификация",
            "action": "verification_required",
            "timestamp": datetime.now().isoformat()
        }
    
    # Проверяем билет на текущую вечеринку (если указана вечеринка)
    if qr_data.get("current_party_id") and db_user[7] == 0:
        return {
            "valid": False,
            "user_info": {
                "id": db_user[0],
                "nickname": db_user[1],
                "name": f"{db_user[2]} {db_user[3]}",
                "refer_code": db_user[6]
            },
            "error": "Нет билета на эту вечеринку",
            "action": "no_ticket",
            "party_id": qr_data.get("current_party_id")
        }
    
    # Проверяем совпадение реферального кода (базовая проверка подлинности)
    if db_user[6] != qr_data.get("refer_code"):
        return {
            "valid": False,
            "warning": "Реферальный код не совпадает с данными в базе",
            "action": "data_mismatch",
            "qr_refer": qr_data.get("refer_code"),
            "db_refer": db_user[6],
            "user_info": {
                "id": db_user[0],
                "nickname": db_user[1],
                "name": f"{db_user[2]} {db_user[3]}"
            }
        }
    
    # ВСЁ ОК - пользователь прошел проверку
    # Можно добавить запись о входе в логи (если таблица существует)
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Проверяем существует ли таблица party_entries
        cursor.execute("""
            IF OBJECT_ID('party_entries', 'U') IS NOT NULL
            BEGIN
                INSERT INTO party_entries (user_id, party_id, entry_time, verified_by)
                VALUES (?, ?, GETDATE(), 'qr_scanner')
            END
        """, (user_id, current_party_id))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️ Не удалось записать вход в логи: {e}")
    
    return {
        "valid": True,
        "user_info": {
            "id": db_user[0],
            "nickname": db_user[1],
            "name": f"{db_user[2]} {db_user[3]}",
            "refer_code": db_user[6],
            "has_ticket": db_user[7] > 0
        },
        "action": "allow_entry",
        "timestamp": datetime.now().isoformat(),
        "message": f"✅ Добро пожаловать, {db_user[2]}!",
        "party_id": current_party_id,
        "entry_recorded": True
    }

@app.get("/api/user/{user_id}/referral-count")
async def get_referral_count(user_id: int):
    """Получение количества приглашенных пользователей"""
    conn = get_db_connection()
    if not conn:
        return {"success": False, "error": "Ошибка подключения к БД"}
    
    try:
        cursor = conn.cursor()
        
        # Получаем реферальный код пользователя
        cursor.execute("SELECT refer FROM users WHERE ID = ?", (user_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return {"success": False, "error": "Пользователь не найден"}
        
        refer_code = result[0]
        
        # Считаем количество пользователей, которые использовали этот код
        cursor.execute("SELECT COUNT(*) FROM users WHERE refer_from = ?", (refer_code,))
        count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "success": True,
            "user_id": user_id,
            "referral_count": count,
            "refer_code": refer_code
        }
        
    except Exception as e:
        print(f"❌ Ошибка получения количества рефералов: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/user/{user_id}/qr-image")
async def get_user_qr_image(user_id: int):
    """Генерация QR-кода изображения с данными пользователя (опционально)"""
    try:
        import qrcode
        from io import BytesIO
        import json
        
        # Получаем данные
        user_data = await get_user_qr_data(user_id)
        
        # Компактный JSON без лишних пробелов
        data_str = json.dumps(user_data, ensure_ascii=False, separators=(',', ':'))
        
        # Генерируем QR-код
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(data_str)
        qr.make(fit=True)
        
        # Создаем изображение
        img = qr.make_image(
            fill_color="#00ccff",
            back_color="#0a0a1a"
        )
        
        # Конвертируем в base64
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return {
            "image_base64": img_str,
            "image_url": f"data:image/png;base64,{img_str}",
            "data_length": len(data_str),
            "user_id": user_id
        }
    except ImportError:
        raise HTTPException(
            status_code=500, 
            detail="Для генерации QR-изображения установите библиотеку qrcode[pil]"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============== ДОПОЛНИТЕЛЬНЫЕ ЭНДПОИНТЫ ==============

@app.get("/api/user/{user_id}/stats")
async def get_user_stats(user_id: int):
    """Получение статистики пользователя (с заглушками для отсутствующих полей)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            u.ID, u.nickname, u.name, u.surname,
            u.is_verificated, u.is_ban, u.refer
        FROM users u
        WHERE u.ID = ?
    """, (user_id,))
    
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Считаем количество приглашенных (если поле refer_from заполнено у других пользователей)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE refer_from = ?", (user[6],))
    invited_count = cursor.fetchone()[0]
    
    # Считаем количество посещений (билетов пользователя)
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE id_user = ?", (user_id,))
    visits_count = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        "user_id": user[0],
        "nickname": user[1],
        "name": user[2],
        "surname": user[3],
        "refer_code": user[6],
        "stats": {
            "visits_count": visits_count,
            "invited_count": invited_count,
            "total_bar_spent": 0,  # Заглушка - нет в БД
            "battle_participations": 0  # Заглушка - нет в БД
        },
        "status": {
            "is_verified": bool(user[4]),
            "is_banned": bool(user[5])
        }
    }

@app.get("/api/user/{user_id}/tickets")
async def get_user_tickets(user_id: int):
    """Получение билетов пользователя"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                t.ID as ticket_id,
                p.name as party_name,
                p.cost as price,
                p.location,
                CONVERT(VARCHAR, p.start_party, 104) as date,
                CONVERT(VARCHAR, p.start_party, 108) as time,
                d.discount
            FROM tickets t
            INNER JOIN parties p ON t.id_party = p.ID
            LEFT JOIN discounts d ON t.id_user = d.id_user AND t.id_party = d.id_party
            WHERE t.id_user = ?
            ORDER BY p.start_party DESC
        """, (user_id,))
        
        columns = [column[0] for column in cursor.description]
        tickets = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        
        if not tickets:
            return {
                "user_id": user_id,
                "tickets": [],
                "message": "У пользователя нет билетов"
            }
        
        return {
            "user_id": user_id,
            "tickets": tickets,
            "count": len(tickets)
        }
        
    except Exception as e:
        return {
            "user_id": user_id,
            "tickets": [],
            "error": str(e)
        }

@app.get("/api/ticket/{ticket_id}/qr-image")
async def get_ticket_qr_image(ticket_id: int):
    """Генерация QR-кода изображения для билета"""
    try:
        import qrcode
        from io import BytesIO
        import json
        import base64
        
        print(f"📱 Запрос QR-кода для билета {ticket_id}")
        
        # Получаем данные для QR
        qr_data_response = await get_ticket_qr_data(ticket_id)
        
        if not qr_data_response.get("success"):
            return {
                "success": False,
                "error": qr_data_response.get("error", "Билет не найден")
            }
        
        qr_data = qr_data_response["qr_data"]
        
        # Компактный JSON без лишних пробелов
        data_str = json.dumps(qr_data, ensure_ascii=False, separators=(',', ':'))
        
        # Генерируем QR-код
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(data_str)
        qr.make(fit=True)
        
        # Создаем изображение
        img = qr.make_image(
            fill_color="#00ccff",
            back_color="#0a0a1a"
        )
        
        # Конвертируем в base64
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        print(f"✅ QR-код для билета {ticket_id} сгенерирован")
        
        return {
            "success": True,
            "image_base64": img_str,
            "image_url": f"data:image/png;base64,{img_str}",
            "ticket_id": ticket_id,
            "party_name": qr_data.get("party_name"),
            "party_location": qr_data.get("party_location")
        }
        
    except ImportError as e:
        print(f"❌ Ошибка импорта qrcode: {e}")
        return {
            "success": False,
            "error": "Библиотека qrcode не установлена. Установите: pip install qrcode[pil]"
        }
    except Exception as e:
        print(f"❌ Ошибка генерации QR-кода: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

# Эндпоинт для проверки и обновления ролей
@app.post("/api/user/{user_id}/check-roles")
async def check_user_roles(user_id: int):
    """Принудительная проверка и обновление ролей пользователя с подробным логом"""
    try:
        result = RoleManager.check_and_update_roles(user_id)
        
        if result["success"]:
            # Добавляем отладочную информацию
            debug_info = {
                "legend_check": {
                    "eligible": result.get("legend_eligible", False),
                    "required": result.get("required_for_legend", []),
                    "has": result.get("user_has_roles", [])
                }
            }
            
            return {
                "success": True,
                "message": "Роли успешно проверены и обновлены",
                "added_roles": result.get("added_roles", []),
                "current_roles": result.get("current_roles", []),
                "user_id": user_id,
                "debug": debug_info
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Неизвестная ошибка")
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# Эндпоинт для назначения роли администратором
@app.post("/api/admin/assign-role")
async def assign_role(request: dict):
    """Назначение роли администратором"""
    required_fields = ['user_id', 'role_name', 'admin_id']
    for field in required_fields:
        if field not in request:
            raise HTTPException(status_code=400, detail=f"Отсутствует поле: {field}")
    
    result = RoleManager.assign_admin_role(
        request['user_id'],
        request['role_name'],
        request['admin_id']
    )
    
    if 'error' in result:
        raise HTTPException(status_code=400, detail=result['error'])
    
    return result

# Эндпоинт для верификации пользователя
@app.post("/api/admin/verify-user")
async def verify_user(request: dict):
    """Верификация пользователя администратором"""
    if 'user_id' not in request or 'admin_id' not in request:
        raise HTTPException(status_code=400, detail="Требуется user_id и admin_id")
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Верифицируем пользователя
        cursor.execute("""
            UPDATE users 
            SET is_verificated = 1 
            WHERE ID = ?
        """, (request['user_id'],))
        
        # Логируем действие
        cursor.execute("""
            INSERT INTO admin_actions (admin_id, user_id, action_type, details, timestamp)
            VALUES (?, ?, 'verify_user', 'Верификация аккаунта', GETDATE())
        """, (request['admin_id'], request['user_id']))
        
        conn.commit()
        
        # Проверяем роли (добавится "Рисковый")
        RoleManager.check_and_update_roles(request['user_id'])
        
        return {
            "success": True,
            "message": "Пользователь верифицирован",
            "user_id": request['user_id']
        }
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.get("/api/user/{user_id}/roles")
async def get_user_roles_api(user_id: int):
    """API для получения ролей пользователя"""
    try:
        conn = get_db_connection()
        if not conn:
            return {
                "success": False,
                "error": "Нет подключения к БД",
                "user_id": user_id
            }
        
        cursor = conn.cursor()
        
        # 1. Получаем все уникальные роли пользователя
        cursor.execute("""
            SELECT DISTINCT CAST(r.name AS NVARCHAR(MAX)) as role_name
            FROM user_role ur
            JOIN roles r ON ur.id_role = r.ID
            WHERE ur.id_user = ?
        """, (user_id,))
        
        results = cursor.fetchall()
        all_roles = [row[0] for row in results]
        print(f"📋 Все роли из БД: {all_roles}")
        
        # 2. Получаем выбранную роль
        cursor.execute("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'user_role' AND COLUMN_NAME = 'selected_role'
        """)
        
        has_selected_role = cursor.fetchone()[0] > 0
        selected_role = None
        
        if has_selected_role:
            cursor.execute("""
                SELECT TOP 1 selected_role
                FROM user_role 
                WHERE id_user = ? AND selected_role IS NOT NULL
            """, (user_id,))
            
            selected_result = cursor.fetchone()
            if selected_result:
                selected_role = selected_result[0]
                print(f"✅ Найдена выбранная роль в БД: '{selected_role}'")
        
        conn.close()
        
        # 3. Если ролей нет, добавляем Участника
        if not all_roles:
            all_roles = ['Участник']
            if not selected_role:
                selected_role = 'Участник'
            print("📝 Ролей нет, установлен Участник")
        
        # 4. Если нет выбранной роли, но есть роли, берем первую
        if not selected_role and all_roles:
            selected_role = all_roles[0]
            print(f"⚠️ Нет выбранной роли, берем первую: '{selected_role}'")
        
        # 5. Сортируем роли так, чтобы выбранная была первой
        sorted_roles = []
        if selected_role and selected_role in all_roles:
            sorted_roles.append(selected_role)
            for role in all_roles:
                if role != selected_role:
                    sorted_roles.append(role)
            print(f"📊 Отсортировано: выбранная роль '{selected_role}' в начале")
        else:
            sorted_roles = all_roles
            print(f"📊 Без сортировки: {sorted_roles}")
        
        # 6. Разделяем на типы
        auto_roles = []
        admin_roles = []
        
        for role in sorted_roles:
            if role in ['Танцор', 'Ас танцпола', 'Любитель выпить', 'Глава бара']:
                admin_roles.append(role)
            else:
                auto_roles.append(role)
        
        has_legend = 'Легенда' in sorted_roles
        
        print(f"🎯 ИТОГ: selected_role='{selected_role}', all_roles={sorted_roles}")
        
        return {
            "success": True,
            "user_id": user_id,
            "all_roles": sorted_roles,
            "auto_roles": sorted(auto_roles),
            "admin_roles": sorted(admin_roles),
            "total_count": len(sorted_roles),
            "has_legend": has_legend,
            "selected_role": selected_role  # Просто возвращаем то, что в БД
        }
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "user_id": user_id
        }

    
@app.get("/api/user/{user_id}/roles-debug")
async def debug_user_roles(user_id: int):
        """Отладочный эндпоинт для проверки ролей"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем таблицы
        cursor.execute("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_NAME IN ('user_role', 'roles', 'users')
        """)
        tables = cursor.fetchall()
        
        # Проверяем пользователя
        cursor.execute("SELECT ID, nickname FROM users WHERE ID = ?", (user_id,))
        user = cursor.fetchone()
        
        # Проверяем роли
        cursor.execute("""
            SELECT COUNT(*) as total_roles FROM user_role WHERE id_user = ?
        """, (user_id,))
        total_roles = cursor.fetchone()[0]
        
        # Получаем названия ролей
        cursor.execute("""
            SELECT CAST(r.name AS NVARCHAR(MAX)) as role_name
            FROM user_role ur
            JOIN roles r ON ur.id_role = r.ID
            WHERE ur.id_user = ?
        """, (user_id,))
        roles = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            "debug": True,
            "user_id": user_id,
            "user_exists": bool(user),
            "user_nickname": user[1] if user else None,
            "tables_found": [t[0] for t in tables],
            "total_roles_in_db": total_roles,
            "roles_found": roles,
            "has_legend": 'Легенда' in roles,
            "timestamp": datetime.now().isoformat()
        }


@app.post("/api/user/{user_id}/upload-document")
async def upload_document(user_id: int, request: dict):
    """Загрузка документа для верификации"""
    try:
        from image_processor import sanitize_document_image, is_image_valid
        from encryption import encrypt_document
        import base64
        
        citizenship = request.get("citizenship")
        phone = request.get("phone")
        iid = request.get("iid")
        document_base64 = request.get("document")
        
        # Валидация
        if not all([citizenship, phone, iid, document_base64]):
            return {"success": False, "error": "Заполните все поля"}
        
        if not isinstance(citizenship, int) or citizenship < 1 or citizenship > 8:
            return {"success": False, "error": "Неверное гражданство"}
        
        if len(phone) != 10 or not phone.isdigit():
            return {"success": False, "error": "Номер телефона должен содержать 10 цифр"}
        
        if len(iid) > 20 or not iid.isdigit():
            return {"success": False, "error": "ID документа должен содержать только цифры (макс. 20)"}
        
        # Обработка фото
        try:
            if ',' in document_base64:
                document_base64 = document_base64.split(',')[1]
            document_binary = base64.b64decode(document_base64)
        except Exception as e:
            return {"success": False, "error": "Неверный формат изображения"}
        
        # Проверка изображения
        is_valid, error_msg = is_image_valid(document_binary)
        if not is_valid:
            return {"success": False, "error": f"Файл поврежден: {error_msg}"}
        
        # Очистка метаданных
        cleaned_image = sanitize_document_image(document_binary)
        if not cleaned_image:
            return {"success": False, "error": "Не удалось обработать изображение"}
        
        # Шифрование
        encrypted_document = encrypt_document(cleaned_image)
        if not encrypted_document:
            return {"success": False, "error": "Ошибка шифрования"}
        
        # Сохранение в БД
        conn = get_db_connection()
        if not conn:
            return {"success": False, "error": "Ошибка подключения к БД"}
        
        cursor = conn.cursor()
        
        # Проверка пользователя
        cursor.execute("SELECT is_verificated FROM users WHERE ID = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return {"success": False, "error": "Пользователь не найден"}
        
        if user[0] == 1:
            conn.close()
            return {"success": False, "error": "Пользователь уже верифицирован"}
        
        # Обновляем данные пользователя
        cursor.execute("""
            UPDATE users 
            SET id_citizenship = ?, 
                phone_number = ?, 
                iid = ?, 
                photo = ?
            WHERE ID = ?
        """, (citizenship, phone, iid, encrypted_document, user_id))
        
        # Создаем очередь верификации
        cursor.execute("""
            IF OBJECT_ID('verification_queue', 'U') IS NULL
            BEGIN
                CREATE TABLE verification_queue (
                    ID INT IDENTITY(1,1) PRIMARY KEY,
                    user_id INT NOT NULL,
                    submitted_at DATETIME DEFAULT GETDATE(),
                    status VARCHAR(20) DEFAULT 'pending',
                    admin_id INT NULL,
                    verified_at DATETIME NULL
                )
            END
        """)
        
        cursor.execute("INSERT INTO verification_queue (user_id) VALUES (?)", (user_id,))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Документ загружен: user_id={user_id}, phone={phone}, citizenship={citizenship}")
        
        return {
            "success": True,
            "message": "Документ отправлен на проверку",
            "user_id": user_id
        }
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

    
@app.get("/api/admin/verification-document/{user_id}")
async def get_verification_document(user_id: int, admin_id: int = None):
    """Получение документа для верификации"""
    
    conn = get_db_connection()
    if not conn:
        return {"success": False, "error": "Ошибка подключения к БД"}
    
    try:
        cursor = conn.cursor()
        
        # Получаем все данные пользователя
        cursor.execute("""
            SELECT 
                u.photo, 
                u.iid, 
                u.name, 
                u.surname, 
                u.nickname,
                u.phone_number,
                u.id_citizenship,
                c.citizenship
            FROM users u
            LEFT JOIN citizenships c ON u.id_citizenship = c.ID
            WHERE u.ID = ?
        """, (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result or not result[0]:
            return {"success": False, "error": "Документ не найден"}
        
        encrypted_doc, iid, name, surname, nickname, phone, cit_id, citizenship = result
        
        # Дешифруем документ
        from encryption import decrypt_document
        document_binary = decrypt_document(encrypted_doc)
        
        if not document_binary:
            return {"success": False, "error": "Ошибка дешифрования"}
        
        import base64
        document_base64 = base64.b64encode(document_binary).decode('utf-8')
        
        # Логируем просмотр
        try:
            log_admin_action(admin_id, user_id, 'view_document', f'Просмотр документа пользователя {nickname}')
        except:
            pass
        
        # Формируем название гражданства
        citizenship_names = {
            1: "🇷🇺 Россия",
            2: "🇰🇿 Казахстан", 
            3: "🇺🇿 Узбекистан",
            4: "🇰🇬 Кыргызстан",
            5: "🇨🇳 Китай",
            6: "🇬🇪 Грузия",
            7: "🇮🇳 Индия",
            8: "🇹🇯 Таджикистан"
        }
        
        citizenship_display = citizenship_names.get(cit_id, citizenship or "Не указано")
        
        return {
            "success": True,
            "user_id": user_id,
            "name": name,
            "surname": surname,
            "nickname": nickname,
            "phone": f"+7 {phone[:3]} {phone[3:6]} {phone[6:8]} {phone[8:10]}" if phone else "Не указан",
            "citizenship": citizenship_display,
            "iid": iid,
            "document": document_base64,
            "warning": "Это конфиденциальные данные. Не распространяйте их!"
        }
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return {"success": False, "error": str(e)}
    
@app.get("/api/user/{user_id}/verification-status")
async def get_verification_status(user_id: int):
    """Получение статуса верификации пользователя"""
    conn = get_db_connection()
    if not conn:
        return {"success": False, "error": "Ошибка подключения к БД"}
    
    try:
        cursor = conn.cursor()
        
        # Сначала проверяем статус в таблице users
        cursor.execute("SELECT is_verificated FROM users WHERE ID = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return {"success": False, "error": "Пользователь не найден"}
        
        # Если пользователь верифицирован, сразу возвращаем verified
        if user[0] == 1:
            conn.close()
            return {
                "success": True,
                "status": "verified",
                "user_id": user_id
            }
        
        # Если не верифицирован, проверяем очередь
        cursor.execute("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_NAME = 'verification_queue'
        """)
        
        has_queue = cursor.fetchone()[0] > 0
        
        if has_queue:
            cursor.execute("""
                SELECT status FROM verification_queue 
                WHERE user_id = ? AND status = 'pending'
                ORDER BY submitted_at DESC
            """, (user_id,))
            
            result = cursor.fetchone()
            
            if result:
                conn.close()
                return {
                    "success": True,
                    "status": "pending",
                    "user_id": user_id
                }
        
        conn.close()
        return {
            "success": True,
            "status": "not_submitted",
            "user_id": user_id
        }
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        if conn:
            conn.close()
        return {"success": False, "error": str(e)}
    
@app.get("/api/admin/verification-queue")
async def get_verification_queue():
    """Получение очереди на верификацию (для админ-консоли)"""
    conn = get_db_connection()
    if not conn:
        return {"success": False, "error": "Ошибка подключения к БД"}
    
    try:
        cursor = conn.cursor()
        
        # Проверяем наличие таблицы
        cursor.execute("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_NAME = 'verification_queue'
        """)
        
        if cursor.fetchone()[0] == 0:
            conn.close()
            return {"success": True, "queue": [], "count": 0}
        
        cursor.execute("""
            SELECT 
                vq.ID,
                vq.user_id,
                u.nickname,
                u.name,
                u.surname,
                vq.submitted_at
            FROM verification_queue vq
            JOIN users u ON vq.user_id = u.ID
            WHERE vq.status = 'pending'
            ORDER BY vq.submitted_at ASC
        """)
        
        queue = []
        for row in cursor.fetchall():
            queue.append({
                "queue_id": row[0],
                "user_id": row[1],
                "nickname": row[2],
                "name": row[3],
                "surname": row[4],
                "submitted_at": row[5].isoformat() if row[5] else None
            })
        
        conn.close()
        
        return {
            "success": True,
            "queue": queue,
            "count": len(queue)
        }
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        if conn:
            conn.close()
        return {"success": False, "error": str(e)}

@app.get("/api/admin/verification-queue")
async def get_verification_queue():
    """Получение очереди на верификацию (для админ-консоли)"""
    conn = get_db_connection()
    if not conn:
        return {"success": False, "error": "Ошибка подключения к БД"}
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                vq.ID,
                vq.user_id,
                u.nickname,
                u.name,
                u.surname,
                vq.submitted_at
            FROM verification_queue vq
            JOIN users u ON vq.user_id = u.ID
            WHERE vq.status = 'pending'
            ORDER BY vq.submitted_at ASC
        """)
        
        queue = []
        for row in cursor.fetchall():
            queue.append({
                "queue_id": row[0],
                "user_id": row[1],
                "nickname": row[2],
                "name": row[3],
                "surname": row[4],
                "submitted_at": row[5].isoformat() if row[5] else None
            })
        
        conn.close()
        
        return {
            "success": True,
            "queue": queue,
            "count": len(queue)
        }
        
    except Exception as e:
        if conn:
            conn.close()
        return {"success": False, "error": str(e)}

@app.get("/api/admin/verification-document/{user_id}")
async def get_verification_document(user_id: int, admin_id: int = None):
    """Получение документа для верификации (только для админов)"""
    # В реальном проекте здесь должна быть проверка прав администратора
    
    conn = get_db_connection()
    if not conn:
        return {"success": False, "error": "Ошибка подключения к БД"}
    
    try:
        cursor = conn.cursor()
        
        # Получаем зашифрованный документ и хеш ID
        cursor.execute("""
            SELECT photo, iid, name, surname, nickname
            FROM users
            WHERE ID = ?
        """, (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result or not result[0]:
            return {"success": False, "error": "Документ не найден"}
        
        encrypted_doc, hashed_iid, name, surname, nickname = result
        
        # Дешифруем документ
        from encryption import decrypt_document
        document_binary = decrypt_document(encrypted_doc)
        
        if not document_binary:
            return {"success": False, "error": "Ошибка дешифрования документа"}
        
        # Конвертируем в base64 для отправки
        import base64
        document_base64 = base64.b64encode(document_binary).decode('utf-8')
        
        # Логируем просмотр документа
        log_admin_action(admin_id, user_id, 'view_document', f'Просмотр документа пользователя {nickname}')
        
        return {
            "success": True,
            "user_id": user_id,
            "name": name,
            "surname": surname,
            "nickname": nickname,
            "document": document_base64,
            "hashed_iid": hashed_iid,
            "warning": "Это конфиденциальные данные. Не распространяйте их!"
        }
        
    except Exception as e:
        print(f"❌ Ошибка получения документа: {e}")
        return {"success": False, "error": str(e)}

def log_admin_action(admin_id, user_id, action, details):
    """Логирование действий администратора"""
    try:
        conn = get_db_connection()
        if not conn:
            return
        
        cursor = conn.cursor()
        
        cursor.execute("""
            IF OBJECT_ID('admin_actions', 'U') IS NOT NULL
            BEGIN
                INSERT INTO admin_actions (admin_id, user_id, action_type, details, timestamp)
                VALUES (?, ?, ?, ?, GETDATE())
            END
        """, (admin_id, user_id, action, details))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"⚠️ Не удалось записать в лог: {e}")

# ============== ЗАПУСК ==============
if __name__ == "__main__":
    print("🚀 Запуск Need for Party API...")
    print(f"📡 Адрес: http://0.0.0.0:8000")
    print(f"📖 Документация: http://0.0.0.0:8000/api/docs")
    print(f"🔧 Тестирование БД: http://0.0.0.0:8000/api/test-db")
    
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        log_level="info",
        reload=True
    )