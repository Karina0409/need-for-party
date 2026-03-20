"""
КОНФИГУРАЦИЯ ПОДКЛЮЧЕНИЯ К БД SQL SERVER
Windows Authentication - РАБОТАЮЩАЯ ВЕРСИЯ
"""

import pyodbc

class DatabaseConfig:
    """Конфигурация подключения к БД"""
    
    # РАБОЧАЯ строка подключения (Windows Authentication)
    CONNECTION_STRING = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=.;DATABASE=need_for_party;Trusted_Connection=yes;"
    
    @classmethod
    def get_connection(cls):
        """Возвращает подключение к БД"""
        try:
            conn = pyodbc.connect(cls.CONNECTION_STRING)
            return conn
        except Exception as e:
            print(f"❌ Ошибка подключения: {e}")
            return None
    
    @classmethod
    def test_connection(cls):
        """Тестирование подключения"""
        try:
            conn = cls.get_connection()
            if not conn:
                return {"success": False, "message": "Не удалось подключиться"}
            
            cursor = conn.cursor()
            cursor.execute("SELECT @@version as version, DB_NAME() as db_name")
            result = cursor.fetchone()
            
            conn.close()
            
            return {
                "success": True,
                "message": "Подключение успешно",
                "version": result.version,
                "database": result.db_name
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

# ⭐ ВАЖНО: Эта функция должна быть доступна для импорта ⭐
def get_db_connection():
    """
    Функция для импорта из main.py
    Просто вызывает метод класса DatabaseConfig
    """
    return DatabaseConfig.get_connection()

# Тест при запуске файла
if __name__ == "__main__":
    print("🔧 Тестирование конфигурации...")
    result = DatabaseConfig.test_connection()
    
    if result["success"]:
        print(f"✅ Конфигурация работает!")
        print(f"   База данных: {result.get('database', 'unknown')}")
        print(f"   Метод: Windows Authentication")
    else:
        print(f"❌ Ошибка: {result['message']}")