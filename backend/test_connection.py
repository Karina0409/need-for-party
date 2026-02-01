#!/usr/bin/env python
"""
Скрипт для проверки подключения к SQL Server
Запуск: python test_connection.py
"""

import pyodbc
import sys
import os
from dotenv import load_dotenv

def test_windows_authentication():
    """Тест Windows Authentication"""
    print("\n🔐 Тестирование Windows Authentication...")
    
    # Варианты строк подключения для Windows Auth
    connection_strings = [
        # 1. Точка - локальный компьютер
        "DRIVER={ODBC Driver 17 for SQL Server};SERVER=.;DATABASE=master;Trusted_Connection=yes;",
        
        # 2. localhost
        "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=master;Trusted_Connection=yes;",
        
        # 3. С инстансом SQLEXPRESS
        "DRIVER={ODBC Driver 17 for SQL Server};SERVER=.\\SQLEXPRESS;DATABASE=master;Trusted_Connection=yes;",
        
        # 4. С конкретным инстансом
        "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost\\SQLEXPRESS;DATABASE=master;Trusted_Connection=yes;",
    ]
    
    for i, conn_str in enumerate(connection_strings, 1):
        print(f"\n{i}. Пробуем: {conn_str[:80]}...")
        try:
            conn = pyodbc.connect(conn_str, timeout=5)
            cursor = conn.cursor()
            cursor.execute("SELECT @@version")
            version = cursor.fetchone()[0]
            print(f"   ✅ Успешно! SQL Server версия: {version[:60]}...")
            
            # Проверяем нашу базу
            cursor.execute("SELECT name FROM sys.databases WHERE name = 'need_for_party'")
            if cursor.fetchone():
                print(f"   💾 База данных 'need_for_party' найдена")
            else:
                print(f"   ⚠️  База данных 'need_for_party' не найдена")
                
            conn.close()
            return conn_str.replace("DATABASE=master;", "DATABASE=need_for_party;")
            
        except pyodbc.Error as e:
            print(f"   ❌ Ошибка: {str(e)[:100]}...")
    
    return None

def test_sql_authentication():
    """Тест SQL Authentication (sa пользователь)"""
    print("\n🔑 Тестирование SQL Authentication...")
    
    # Попробуйте разные пароли
    passwords = [
        "YourStrong!Pass123",
        "NewPassword123!",
        "Password123!",
        "sql123",
        "sa",
        ""
    ]
    
    server = ".\\SQLEXPRESS"
    
    for password in passwords:
        conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE=master;UID=sa;PWD={password};"
        
        print(f"\nПароль: '{password}'")
        try:
            conn = pyodbc.connect(conn_str, timeout=5)
            cursor = conn.cursor()
            cursor.execute("SELECT @@version")
            version = cursor.fetchone()[0]
            print(f"   ✅ Успешно! Версия: {version[:50]}...")
            
            conn.close()
            return conn_str.replace("DATABASE=master;", "DATABASE=need_for_party;")
            
        except pyodbc.Error as e:
            if "Login failed" in str(e):
                print(f"   ❌ Неверный пароль")
            else:
                print(f"   ❌ Ошибка: {str(e)[:80]}...")
    
    return None

def test_need_for_party_database(connection_string):
    """Тестирование подключения к конкретной базе need_for_party"""
    print(f"\n📊 Тестирование базы данных 'need_for_party'...")
    
    try:
        conn_str = connection_string
        if "DATABASE=master;" in conn_str:
            conn_str = conn_str.replace("DATABASE=master;", "DATABASE=need_for_party;")
        
        print(f"Строка подключения: {conn_str[:100]}...")
        
        conn = pyodbc.connect(conn_str, timeout=5)
        cursor = conn.cursor()
        
        # 1. Проверяем таблицы БЕЗ сортировки по имени таблицы
        cursor.execute("""
            SELECT TABLE_NAME, TABLE_TYPE 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE = 'BASE TABLE'
        """)
        
        tables = cursor.fetchall()
        print(f"\n📋 Найдено таблиц: {len(tables)}")
        
        for table in tables:
            table_name = table[0]
            
            # Считаем записи в таблице (избегаем проблем с TEXT)
            try:
                if table_name == 'roles':
                    # Для таблицы roles используем CAST
                    cursor.execute("SELECT COUNT(*) as cnt FROM roles WHERE name IS NOT NULL")
                else:
                    cursor.execute(f"SELECT COUNT(*) as cnt FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"   • {table_name}: {count} записей")
            except:
                print(f"   • {table_name}: не удалось посчитать")
        
        # 2. Проверяем пользователей
        if 'users' in [t[0].lower() for t in tables]:
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            print(f"\n👥 Пользователей в системе: {user_count}")
            
            # Показываем несколько пользователей
            if user_count > 0:
                cursor.execute("SELECT TOP 3 nickname, name, surname, mail FROM users")
                for row in cursor.fetchall():
                    print(f"   • {row[0]} ({row[1]} {row[2]}) - {row[3]}")
        
        # 3. Проверяем роли (используем CAST)
        if 'roles' in [t[0].lower() for t in tables]:
            try:
                cursor.execute("SELECT CAST(name AS NVARCHAR(255)) as name FROM roles")
                roles = [row[0] for row in cursor.fetchall() if row[0]]
                print(f"\n🏆 Роли в системе: {', '.join(roles[:5])}...")
            except:
                print(f"\n🏆 Роли в системе: (ошибка чтения, требуется обновление типа данных)")
        
        conn.close()
        print(f"\n🎉 База данных 'need_for_party' доступна!")
        return True
        
    except pyodbc.Error as e:
        print(f"\n❌ Ошибка подключения к need_for_party: {e}")
        return False

def create_config_file(connection_string, auth_method):
    """Создание db_config.py на основе найденной конфигурации"""
    config_content = f'''"""
АВТОМАТИЧЕСКИ СОЗДАННЫЙ КОНФИГ ФАЙЛ
На основе успешного тестирования подключения
Метод аутентификации: {auth_method}
"""

import pyodbc

class DatabaseConfig:
    """Конфигурация подключения к БД"""
    
    # Используйте эту строку подключения - она РАБОТАЕТ!
    CONNECTION_STRING = "{connection_string}"
    
    @classmethod
    def get_connection(cls):
        """Возвращает подключение к БД"""
        try:
            conn = pyodbc.connect(cls.CONNECTION_STRING)
            return conn
        except Exception as e:
            print(f"❌ Ошибка подключения: {{e}}")
            return None
    
    @classmethod
    def test_connection(cls):
        """Тестирование подключения"""
        try:
            conn = cls.get_connection()
            if not conn:
                return {{"success": False, "message": "Не удалось подключиться"}}
            
            cursor = conn.cursor()
            cursor.execute("SELECT @@version as version, DB_NAME() as db_name")
            result = cursor.fetchone()
            
            conn.close()
            
            return {{
                "success": True,
                "message": "Подключение успешно",
                "version": result.version,
                "database": result.db_name
            }}
        except Exception as e:
            return {{"success": False, "message": str(e)}}

# Тест при запуске файла
if __name__ == "__main__":
    print("🔧 Тестирование конфигурации...")
    result = DatabaseConfig.test_connection()
    
    if result["success"]:
        print(f"✅ Конфигурация работает!")
        print(f"   База данных: {{result.get('database', 'unknown')}}")
        print(f"   Метод: {auth_method}")
    else:
        print(f"❌ Ошибка: {{result['message']}}")
'''
    
    with open("db_config.py", "w", encoding="utf-8") as f:
        f.write(config_content)
    
    print(f"\n📁 Конфигурационный файл создан: db_config.py")
    print(f"   Метод аутентификации: {auth_method}")

def main():
    """Основная функция"""
    print("=" * 60)
    print("🔧 ТЕСТИРОВАНИЕ ПОДКЛЮЧЕНИЯ К SQL SERVER")
    print("=" * 60)
    
    # 1. Сначала пробуем Windows Authentication
    conn_str = test_windows_authentication()
    auth_method = "Windows Authentication"
    
    # 2. Если не сработало, пробуем SQL Authentication
    if not conn_str:
        conn_str = test_sql_authentication()
        auth_method = "SQL Authentication"
    
    # 3. Если нашлась рабочая конфигурация
    if conn_str:
        print(f"\n{'='*60}")
        print(f"✅ НАЙДЕНА РАБОЧАЯ КОНФИГУРАЦИЯ!")
        print(f"   Метод: {auth_method}")
        print(f"   Строка подключения: {conn_str[:100]}...")
        
        # 4. Тестируем подключение к need_for_party
        if test_need_for_party_database(conn_str):
            # 5. Создаем конфигурационный файл
            create_config_file(conn_str, auth_method)
            
            print(f"\n{'='*60}")
            print("🎉 ВСЁ ГОТОВО! Следующие шаги:")
            print("   1. Переместите db_config.py в папку backend/")
            print("   2. Запустите бэкенд: python backend/main.py")
            print("   3. Проверьте API: http://localhost:8000/api/test-db")
        else:
            print(f"\n{'='*60}")
            print("⚠️  База данных need_for_party недоступна")
            print("\n🔧 Создайте базу данных:")
            print("   1. Откройте SSMS")
            print("   2. Выполните: CREATE DATABASE need_for_party;")
            print("   3. Или запустите database/init.sql")
    else:
        print(f"\n{'='*60}")
        print("❌ НЕ УДАЛОСЬ ПОДКЛЮЧИТЬСЯ К SQL SERVER")
        print("\n🔧 Решение проблем:")
        print("   1. Убедитесь, что SQL Server запущен")
        print("   2. Проверьте, включен ли Mixed Mode аутентификации")
        print("   3. Установите ODBC Driver 17 for SQL Server")
        print("   4. Проверьте пароль для учетной записи sa")
        print("\n💡 Альтернатива: используйте SQLite для разработки")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Тестирование прервано пользователем")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        sys.exit(1)