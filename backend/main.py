from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
import random
from datetime import datetime, timezone, timedelta
from contextlib import contextmanager

# Импортируем нашу конфигурацию БД
from db_config import DatabaseConfig, get_db_connection

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
            "user_count": user_count,
            "server": DatabaseConfig.SERVER,
            "database": DatabaseConfig.DATABASE
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Ошибка БД: {str(e)}",
            "tables": [],
            "user_count": 0
        }

@app.post("/api/user/register", response_model=dict)
async def register_user(user: UserRegister):
    """Регистрация нового пользователя"""
    print(f"📝 Регистрация пользователя: {user.name} {user.surname}")
    
    # Генерируем реферальный код
    refer_code = generate_referral_code(user.name)
    
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Ошибка подключения к БД")
        
        cursor = conn.cursor()
        
        # 1. Проверяем уникальность nickname и email
        cursor.execute("""
            SELECT ID FROM users 
            WHERE nickname = ? OR mail = ?
        """, (user.nickname, user.email))
        
        if cursor.fetchone():
            raise HTTPException(
                status_code=400,
                detail="Пользователь с таким nickname или email уже существует"
            )
        
        # 2. Проверяем реферальный код (если указан)
        refer_from_id = None
        if user.refer_from and user.refer_from.strip():
            cursor.execute("""
                SELECT ID FROM users WHERE refer = ?
            """, (user.refer_from.strip(),))
            result = cursor.fetchone()
            if result:
                refer_from_id = result[0]
        
        # 3. Вставляем пользователя
        query = """
            INSERT INTO users (
                nickname, surname, name, age, is_verificated, is_ban,
                phone_number, mail, refer, refer_from, gender, invited_count
            ) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            user.nickname,
            user.surname,
            user.name,
            18,      # возраст по умолчанию
            0,       # не верифицирован
            0,       # не забанен
            None,    # телефон
            user.email,
            refer_code,
            user.refer_from if refer_from_id else None,
            1,       # gender (1 - мужской)
            0        # invited_count по умолчанию
        )
        
        cursor.execute(query, params)
        
        # 4. Получаем ID нового пользователя
        cursor.execute("SELECT @@IDENTITY")
        new_user_id = cursor.fetchone()[0]
        
        # 5. Назначаем роль "Участник" если таблица user_role существует
        try:
            cursor.execute("SELECT ID FROM roles WHERE name = 'Участник'")
            role_result = cursor.fetchone()
            
            if role_result:
                # Проверяем существует ли таблица user_role
                cursor.execute("""
                    IF OBJECT_ID('user_role', 'U') IS NOT NULL
                    BEGIN
                        INSERT INTO user_role (id_user, id_role) 
                        VALUES (?, ?)
                    END
                """, (new_user_id, role_result[0]))
        except Exception as role_error:
            print(f"⚠️ Ошибка назначения роли: {role_error}. Продолжаем...")
        
        # 6. Увеличиваем счетчик пригласившего (если есть)
        if refer_from_id:
            cursor.execute("""
                UPDATE users 
                SET invited_count = ISNULL(invited_count, 0) + 1 
                WHERE ID = ?
            """, (refer_from_id,))
        
        conn.commit()
        
        # 7. Формируем ответ
        response_data = {
            "success": True,
            "message": "Регистрация успешна! 🎉",
            "user": {
                "id": new_user_id,
                "name": user.name,
                "surname": user.surname,
                "nickname": user.nickname,
                "email": user.email,
                "refer": refer_code,
                "current_rank": "Участник",
                "visits_count": 0,
                "invited_count": 0,
                "total_bar_spent": 0,
                "battle_participations": 0
            }
        }
        
        print(f"✅ Пользователь зарегистрирован: {user.nickname} (ID: {new_user_id})")
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ Ошибка регистрации: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Ошибка при регистрации: {str(e)}"
        )
    finally:
        if conn:
            conn.close()

# В функции get_users в main.py измените запрос:
@app.get("/api/users", response_model=List[dict])
async def get_users(limit: int = 10, offset: int = 0):
    """Получение списка пользователей"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Используем CAST для поля name в таблице roles
        cursor.execute("""
            SELECT 
                u.ID, u.nickname, u.name, u.surname, u.mail, u.refer,
                CAST(r.name AS NVARCHAR(255)) as current_rank,
                ISNULL(u.invited_count, 0) as invited_count
            FROM users u
            LEFT JOIN user_role ur ON u.ID = ur.id_user
            LEFT JOIN roles r ON ur.id_role = r.ID
            ORDER BY u.ID DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """, (offset, limit))
        
        columns = [column[0] for column in cursor.description]
        users = []
        for row in cursor.fetchall():
            user_dict = dict(zip(columns, row))
            user_dict['name'] = f"{user_dict['name']} {user_dict['surname']}"
            users.append(user_dict)
        
        conn.close()
        return users
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/parties", response_model=List[dict])
async def get_parties(upcoming: bool = True):
    """Получение списка вечеринок"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if upcoming:
            cursor.execute("""
                SELECT 
                    ID, name, cost, location, 
                    CONVERT(VARCHAR, start_party, 104) as date,
                    CONVERT(VARCHAR, start_party, 108) as time,
                    count_seats
                FROM parties 
                WHERE start_party > GETDATE()
                ORDER BY start_party ASC
            """)
        else:
            cursor.execute("""
                SELECT 
                    ID, name, cost, location, 
                    CONVERT(VARCHAR, start_party, 104) as date,
                    CONVERT(VARCHAR, start_party, 108) as time,
                    count_seats
                FROM parties 
                ORDER BY start_party DESC
            """)
        
        columns = [column[0] for column in cursor.description]
        parties = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return parties
        
    except Exception as e:
        # Возвращаем тестовые данные если БД недоступна
        return [
            {
                "id": 1,
                "name": "Новогодняя ночь 🎄",
                "cost": 2500.00,
                "location": "Клуб 'Ледниковый'",
                "date": "31.12.2023",
                "time": "22:00:00",
                "count_seats": 200
            }
        ]

# ============== ЗАПУСК ==============
if __name__ == "__main__":
    print("🚀 Запуск Need for Party API...")
    print(f"📡 Адрес: http://0.0.0.0:8000")
    print(f"📖 Документация: http://0.0.0.0:8000/api/docs")
    print(f"🔧 Тестирование БД: http://0.0.0.0:8000/api/test-db")
    
    uvicorn.run(
        "main:app",  # ← ИМЕННО ТАК ДОЛЖНО БЫТЬ
        host="0.0.0.0", 
        port=8000, 
        log_level="info",
        reload=False  # ← сначала отключите reload
    )