"""
Тест работы с ролями при типе TEXT
"""

from db_config import get_db_connection

def test_text_column():
    """Тест работы с полем TEXT"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Тест 1: Простой SELECT с CAST
    cursor.execute("SELECT CAST(name AS NVARCHAR(MAX)) FROM roles WHERE ID = 1")
    result = cursor.fetchone()
    print(f"Тест 1 - Роль ID 1: {result[0] if result else 'Нет результата'}")
    
    # Тест 2: Поиск по имени
    cursor.execute("SELECT ID FROM roles WHERE CAST(name AS NVARCHAR(MAX)) = 'Участник'")
    result = cursor.fetchone()
    print(f"Тест 2 - ID роли 'Участник': {result[0] if result else 'Не найдена'}")
    
    # Тест 3: Все роли
    cursor.execute("SELECT ID, CAST(name AS NVARCHAR(MAX)) as name FROM roles ORDER BY name")
    roles = cursor.fetchall()
    print("\nТест 3 - Все роли в БД:")
    for role_id, role_name in roles:
        print(f"  {role_id}: {role_name}")
    
    conn.close()

if __name__ == "__main__":
    test_text_column()