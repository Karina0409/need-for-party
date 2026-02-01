"""
КОНФИГУРАЦИЯ ПОДКЛЮЧЕНИЯ К БАЗЕ ДАННЫХ
Работает с Windows Authentication
"""

import pyodbc

class DatabaseConfig:
    """Конфигурация подключения к SQL Server"""
    
    # Добавляем атрибуты для test-db эндпоинта
    DRIVER = "ODBC Driver 17 for SQL Server"
    SERVER = "."  # Точка = локальный компьютер
    DATABASE = "need_for_party"
    
    # Используйте эту строку подключения - она РАБОТАЕТ!
    CONNECTION_STRING = f"DRIVER={{{DRIVER}}};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;"
    
    @classmethod
    def get_connection(cls):
        """Возвращает подключение к БД"""
        try:
            conn = pyodbc.connect(cls.CONNECTION_STRING)
            return conn
        except Exception as e:
            print(f"❌ Ошибка подключения: {e}")
            return None

def get_db_connection():
    """
    Функция для импорта из main.py
    Просто вызывает метод класса DatabaseConfig
    """
    return DatabaseConfig.get_connection()

# Тест при запуске файла
if __name__ == "__main__":
    print("🔧 Тестирование конфигурации...")
    
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT @@version as version, DB_NAME() as db_name")
            result = cursor.fetchone()
            conn.close()
            
            print(f"✅ Конфигурация работает!")
            print(f"   База данных: {result.db_name}")
            print(f"   Метод: Windows Authentication")
            print(f"   Сервер: {DatabaseConfig.SERVER}")
        else:
            print("❌ Не удалось подключиться к БД")
    except Exception as e:
        print(f"❌ Ошибка: {e}")