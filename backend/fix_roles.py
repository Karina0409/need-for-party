# fix_roles.py
import pyodbc

# Подключение к БД
conn_str = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=.;DATABASE=need_for_party;Trusted_Connection=yes;"

try:
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    user_id = 6
    print(f"🔧 Исправление ролей для пользователя ID {user_id}")
    
    # 1. Удаляем все текущие роли пользователя
    cursor.execute("DELETE FROM user_role WHERE id_user = ?", (user_id,))
    print(f"✅ Удалены старые роли")
    
    # 2. Получаем ID всех нужных ролей
    roles_to_add = [
        ('Участник', 'Участник'),
        ('Рисковый', 'Рисковый'),
        ('Душа компании', 'Душа компании'),
        ('Весельчак', 'Весельчак'),
        ('Тусовщик', 'Тусовщик'),
        ('Ас тусовок', 'Ас тусовок'),
        ('Танцор', 'Танцор'),
        ('Ас танцпола', 'Ас танспола'),  # Обратите внимание: в БД "Ас танспола"
        ('Любитель выпить', 'Любитель выпить'),
        ('Глава бара', 'Глава бара'),
        ('Легенда', 'Легенда')
    ]
    
    # 3. Добавляем каждую роль
    for display_name, db_name in roles_to_add:
        cursor.execute("SELECT ID FROM roles WHERE CAST(name AS NVARCHAR(MAX)) = ?", (db_name,))
        role = cursor.fetchone()
        
        if role:
            role_id = role[0]
            cursor.execute("INSERT INTO user_role (id_user, id_role) VALUES (?, ?)", (user_id, role_id))
            print(f"   ✅ Добавлена роль: {display_name}")
        else:
            print(f"   ❌ Роль не найдена: {db_name}")
    
    conn.commit()
    print(f"\n🎉 Все роли успешно добавлены пользователю {user_id}!")
    
except Exception as e:
    print(f"❌ Ошибка: {e}")
finally:
    if conn:
        conn.close()