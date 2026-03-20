# check_tables.py
from db_config import get_db_connection

def check_all_tables():
    """Проверка всех таблиц в базе данных"""
    conn = get_db_connection()
    if not conn:
        print("❌ Нет подключения к БД")
        return
    
    try:
        cursor = conn.cursor()
        
        # Получаем список всех таблиц
        cursor.execute("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
        """)
        
        tables = cursor.fetchall()
        
        print("\n📋 ТАБЛИЦЫ В БАЗЕ ДАННЫХ:")
        print("="*50)
        
        if not tables:
            print("❌ В базе данных нет таблиц!")
        else:
            for table in tables:
                table_name = table[0]
                # Проверяем количество записей в каждой таблице
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    print(f"   ✅ {table_name}: {count} записей")
                except:
                    print(f"   ⚠️ {table_name}: (не удалось получить количество)")
        
        # Особо проверяем нужные таблицы
        print("\n🔍 ПРОВЕРКА КЛЮЧЕВЫХ ТАБЛИЦ:")
        print("="*50)
        
        required_tables = ['users', 'roles', 'user_role', 'parties', 'tickets']
        
        for table in required_tables:
            cursor.execute("""
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_NAME = ?
            """, (table,))
            
            exists = cursor.fetchone()[0] > 0
            status = "✅ Есть" if exists else "❌ ОТСУТСТВУЕТ"
            print(f"   {table}: {status}")
            
            if exists:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    print(f"      Записей: {count}")
                except:
                    pass
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        conn.close()

if __name__ == "__main__":
    check_all_tables()