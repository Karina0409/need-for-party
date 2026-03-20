"""
Консоль администратора для управления пользователями Need for Party
Использует RoleManager для работы с ролями
"""

import sys
import os
import json
import requests
from typing import Dict, List, Any
from datetime import datetime

# Добавляем путь к backend
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from roles_manager import RoleManager
from db_config import get_db_connection

API_URL = "http://localhost:8000"

# Маппинг названий ролей для отображения и БД
ROLE_NAME_MAPPING = {
    'Ас танцпола': 'Ас танспола',  # Опечатка в БД
    'Ас танцпол': 'Ас танспола',
}

def print_menu():
    """Отображение меню"""
    print("\n" + "="*60)
    print("🛠️  КОНСОЛЬ АДМИНИСТРАТОРА Need for Party")
    print("="*60)
    print("1. 📋 Просмотреть информацию о пользователе")
    print("2. ✅ Верифицировать пользователя")
    print("3. 🎭 Назначить роль администратора")
    print("4. 🔄 Проверить/обновить автоматические роли")
    print("5. 🏆 Просмотреть все роли пользователя")
    print("6. ➕ Добавить конкретную роль пользователю")
    print("7. ❌ Удалить конкретную роль у пользователя")
    print("8. 🎯 Выбрать роль для пользователя")
    print("9. 🧪 Выдать все роли (тестовый режим)")
    print("10. 📊 Просмотреть статистику пользователя")
    print("11. 🗂️  Просмотреть все роли в системе")
    print("12. 🧹 Исправить роли пользователя (сбросить)")
    print("13. 🧹 Очистить дубликаты ролей у пользователя")
    print("14. 🧹 Очистить ВСЕ дубликаты ролей в системе")
    print("15. 🏆 Принудительная выдача Легенды")
    print("16. 🔍 Полная отладка ролей пользователя")
    print("17. 🔄 Сбросить выбранную роль пользователя")
    print("18. 🔧 Исправить порядок ролей")
    print("19. 🎪 Проверить вечеринки в БД")
    print("20. 🔍 Проверить точные названия ролей")
    print("21. 🔍 Просмотреть очередь верификации")
    print("22. 📄 Просмотреть документ пользователя")
    print("23. 🎭 Добавить все недостающие роли пользователю")
    print("24. 🔍 Быстрая проверка ролей пользователя")
    print("25. 🔧 ПРИНУДИТЕЛЬНО добавить все роли")
    print("26. 🧹 Очистить дубликаты ролей у всех пользователей")
    print("27. 🔄 Миграция: добавить is_selected")
    print("28. 🔨 Забанить пользователя")
    print("29. 🔓 Снять бан с пользователя")
    print("30. 📋 Список забаненных")
    print("31. 🎫 Создать билеты для розыгрыша")
    print("32. 📊 Статус розыгрыша")
    print("0. 🚪 Выход")
    print("="*60)

def get_db_role_name(display_name: str) -> str:
    """Получить имя роли в БД из отображаемого имени"""
    return ROLE_NAME_MAPPING.get(display_name, display_name)

def get_display_role_name(db_name: str) -> str:
    """Получить отображаемое имя роли из имени в БД"""
    for display, db in ROLE_NAME_MAPPING.items():
        if db == db_name:
            return display
    return db_name

def get_user_info_db(user_id: int) -> Dict:
    """Получение информации о пользователе напрямую из БД"""
    conn = get_db_connection()
    if not conn:
        return {"error": "Нет подключения к БД"}
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT ID, nickname, name, surname, age, is_verificated, is_ban,
                   phone_number, mail, refer, refer_from, gender
            FROM users 
            WHERE ID = ?
        """, (user_id,))
        
        user = cursor.fetchone()
        if not user:
            conn.close()
            return {"error": f"Пользователь с ID {user_id} не найден"}
        
        cursor.execute("""
            SELECT COUNT(*) FROM users WHERE refer_from = ?
        """, (user[9],))
        refer_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM tickets WHERE id_user = ?", (user_id,))
        tickets_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "success": True,
            "user_id": user[0],
            "nickname": user[1],
            "name": user[2],
            "surname": user[3],
            "full_name": f"{user[2]} {user[3]}",
            "age": user[4],
            "is_verified": bool(user[5]),
            "is_banned": bool(user[6]),
            "phone": user[7],
            "email": user[8],
            "refer_code": user[9],
            "refer_from": user[10],
            "gender": "Мужской" if user[11] == 1 else "Женский",
            "stats": {
                "referrals": refer_count,
                "tickets": tickets_count
            }
        }
        
    except Exception as e:
        if conn:
            conn.close()
        return {"error": str(e)}

def verify_user_console(user_id: int, admin_id: int = 1) -> Dict:
    """Верификация пользователя через консоль (с обновлением очереди)"""
    print(f"\n🔍 Верификация пользователя ID {user_id}...")
    
    user_info = get_user_info_db(user_id)
    if "error" in user_info:
        return user_info
    
    print(f"   Пользователь: {user_info['full_name']} (@{user_info['nickname']})")
    print(f"   Текущий статус: {'✅ Верифицирован' if user_info['is_verified'] else '❌ Не верифицирован'}")
    
    if user_info['is_verified']:
        confirm = input("\n⚠️  Пользователь уже верифицирован. Переверифицировать? (y/n): ").strip().lower()
        if confirm != 'y':
            return {"success": False, "message": "Отменено пользователем"}
    
    confirm = input(f"\n✅ Вы уверены, что хотите верифицировать {user_info['full_name']}? (y/n): ").strip().lower()
    if confirm != 'y':
        return {"success": False, "message": "Отменено"}
    
    # Выполняем верификацию
    result = RoleManager.verify_user(user_id, admin_id)
    
    if result["success"]:
        # Обновляем статус в очереди верификации
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE verification_queue 
                    SET status = 'verified', admin_id = ?, verified_at = GETDATE()
                    WHERE user_id = ? AND status = 'pending'
                """, (admin_id, user_id))
                conn.commit()
                conn.close()
                print(f"   ✅ Статус в очереди обновлен")
            except Exception as e:
                print(f"   ⚠️ Не удалось обновить очередь: {e}")
        
        print(f"\n🎉 Пользователь успешно верифицирован!")
        if "role_update" in result and result["role_update"]["success"]:
            added = result["role_update"].get("added_roles", [])
            if added:
                print(f"   Автоматически добавлены роли: {', '.join(added)}")
    else:
        print(f"\n❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}")
    
    return result

def assign_role_console(user_id: int, admin_id: int = 1) -> Dict:
    """Назначение роли администратором через консоль"""
    print(f"\n🎭 Назначение роли пользователю ID {user_id}")
    
    admin_roles = RoleManager.ADMIN_ROLES
    print(f"\n📋 Роли, которые может выдать администратор:")
    for i, role in enumerate(admin_roles, 1):
        print(f"   {i}. {role}")
    
    try:
        choice = int(input(f"\nВыберите роль (1-{len(admin_roles)}): ").strip())
        if choice < 1 or choice > len(admin_roles):
            return {"success": False, "error": "Неверный выбор"}
        
        role_name = admin_roles[choice - 1]
    except ValueError:
        return {"success": False, "error": "Введите число"}
    
    user_info = get_user_info_db(user_id)
    if "error" in user_info:
        return user_info
    
    print(f"\n🔍 Информация о назначении:")
    print(f"   Пользователь: {user_info['full_name']} (ID: {user_id})")
    print(f"   Роль: {role_name}")
    print(f"   Выдаёт: Администратор ID {admin_id}")
    
    confirm = input(f"\n✅ Подтвердить назначение роли '{role_name}'? (y/n): ").strip().lower()
    if confirm != 'y':
        return {"success": False, "message": "Отменено"}
    
    result = RoleManager.assign_admin_role(user_id, role_name, admin_id)
    
    if result["success"]:
        print(f"\n🎉 Роль '{role_name}' успешно назначена!")
    else:
        print(f"\n❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}")
    
    return result

def check_roles_console(user_id: int) -> Dict:
    """Проверка и обновление автоматических ролей"""
    print(f"\n🔄 Проверка автоматических ролей пользователя ID {user_id}...")
    
    user_info = get_user_info_db(user_id)
    if "error" in user_info:
        return user_info
    
    print(f"   Пользователь: {user_info['full_name']}")
    print(f"   Верифицирован: {'✅ Да' if user_info['is_verified'] else '❌ Нет'}")
    print(f"   Рефералов: {user_info['stats']['referrals']}")
    print(f"   Билетов: {user_info['stats']['tickets']}")
    
    result = RoleManager.check_and_update_roles(user_id)
    
    if result["success"]:
        print(f"\n✅ Проверка завершена!")
        print(f"   Добавлены роли: {result.get('added_roles', []) or 'Нет новых ролей'}")
        print(f"   Всего ролей: {len(result.get('current_roles', []))}")
        print(f"   Роли: {', '.join(result.get('current_roles', []))}")
        
        if result.get('legend_eligible'):
            print(f"\n🏆 Пользователь имеет все необходимые роли для Легенды!")
            if 'Легенда' in result.get('current_roles', []):
                print("   ✅ Роль 'Легенда' уже присвоена")
            else:
                print("   ⏳ Роль 'Легенда' будет присвоена при следующей проверке")
    else:
        print(f"\n❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}")
    
    return result

def get_user_roles_console(user_id: int) -> Dict:
    """Просмотр всех ролей пользователя"""
    print(f"\n🏆 Роли пользователя ID {user_id}")
    
    try:
        result = RoleManager.get_user_roles(user_id)
        
        if result["success"]:
            print(f"\n✅ Успешно получены роли:")
            print(f"   Всего ролей: {result['total_count']}")
            
            if result['auto_roles']:
                print(f"   Автоматические роли: {', '.join(result['auto_roles'])}")
            
            if result['admin_roles']:
                print(f"   Роли от администратора: {', '.join(result['admin_roles'])}")
            
            if result['has_legend']:
                print(f"\n   🏆 ПОЗДРАВЛЯЕМ! Пользователь - ЛЕГЕНДА!")
            
            if not result['has_legend']:
                all_roles_info = RoleManager.get_all_roles_info()
                if all_roles_info["success"]:
                    auto_role_names = [r['display_name'] for r in all_roles_info['roles'] 
                                     if r['type'] == 'auto' and r['display_name'] != 'Легенда']
                    
                    missing = [role for role in auto_role_names 
                              if role not in result['all_roles'] and role != 'Легенда']
                    
                    if missing:
                        print(f"\n   📊 До Легенды не хватает ролей: {', '.join(missing)}")
        else:
            print(f"\n❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}")
        
        return result
        
    except Exception as e:
        print(f"\n❌ Ошибка получения ролей: {e}")
        return {"success": False, "error": str(e)}

def add_specific_role_console(user_id: int, admin_id: int = 1) -> Dict:
    """Добавление конкретной роли пользователю (исправленная версия)"""
    print(f"\n➕ Добавление конкретной роли пользователю ID {user_id}")
    
    conn = get_db_connection()
    if not conn:
        return {"success": False, "error": "Нет подключения к БД"}
    
    try:
        cursor = conn.cursor()
        
        # Получаем все роли из БД
        cursor.execute("SELECT ID, CAST(name AS NVARCHAR(MAX)) as name FROM roles ORDER BY CAST(name AS NVARCHAR(MAX))")
        db_roles = cursor.fetchall()
        
        # Создаем словарь для быстрого поиска
        role_dict = {name: role_id for role_id, name in db_roles}
        
        # Получаем текущие роли пользователя
        cursor.execute("""
            SELECT CAST(r.name AS NVARCHAR(MAX)) as role_name
            FROM user_role ur
            JOIN roles r ON ur.id_role = r.ID
            WHERE ur.id_user = ?
        """, (user_id,))
        
        current_db_roles = [row[0] for row in cursor.fetchall()]
        
        # Преобразуем в отображаемые имена
        current_display_roles = []
        for db_role in current_db_roles:
            display_role = get_display_role_name(db_role)
            if display_role not in current_display_roles:
                current_display_roles.append(display_role)
        
        print(f"\n📋 Текущие роли пользователя ({len(current_display_roles)}):")
        if current_display_roles:
            for i, role in enumerate(sorted(current_display_roles), 1):
                print(f"   {i}. {role}")
        else:
            print("   ❌ У пользователя нет ролей")
        
        # Создаем список всех доступных ролей для отображения
        all_display_roles = []
        for db_name in role_dict.keys():
            display_name = get_display_role_name(db_name)
            if display_name not in all_display_roles:
                all_display_roles.append(display_name)
        
        # Доступные для добавления роли
        available_roles = [role for role in sorted(all_display_roles) if role not in current_display_roles]
        
        if not available_roles:
            print("\n⚠️  Все возможные роли уже назначены пользователю!")
            conn.close()
            return {"success": False, "error": "Все роли уже назначены"}
        
        print(f"\n📋 Доступные для добавления роли ({len(available_roles)}):")
        for i, role in enumerate(available_roles, 1):
            print(f"   {i}. {role}")
        
        try:
            choice = int(input(f"\nВыберите роль для добавления (1-{len(available_roles)}): ").strip())
            if choice < 1 or choice > len(available_roles):
                conn.close()
                return {"success": False, "error": "Неверный выбор"}
            
            selected_display_role = available_roles[choice - 1]
            db_role_name = get_db_role_name(selected_display_role)
            
        except ValueError:
            conn.close()
            return {"success": False, "error": "Введите число"}
        
        user_info = get_user_info_db(user_id)
        if "error" in user_info:
            conn.close()
            return user_info
        
        print(f"\n🔍 Информация о добавлении:")
        print(f"   Пользователь: {user_info['full_name']} (ID: {user_id})")
        print(f"   Роль для добавления: {selected_display_role}")
        print(f"   (в БД: {db_role_name})")
        print(f"   Выдаёт: Администратор ID {admin_id}")
        
        confirm = input(f"\n✅ Подтвердить добавление роли '{selected_display_role}'? (y/n): ").strip().lower()
        if confirm != 'y':
            conn.close()
            return {"success": False, "message": "Отменено"}
        
        # Получаем ID роли
        role_id = role_dict.get(db_role_name)
        
        if not role_id:
            # Если не нашли, пробуем поиск без учета регистра
            for db_name, rid in role_dict.items():
                if db_name.lower() == db_role_name.lower():
                    role_id = rid
                    break
        
        if not role_id:
            conn.close()
            return {"success": False, "error": f"Роль '{selected_display_role}' (БД: '{db_role_name}') не найдена в БД"}
        
        # Проверяем, есть ли уже эта роль
        cursor.execute("SELECT 1 FROM user_role WHERE id_user = ? AND id_role = ?", (user_id, role_id))
        if cursor.fetchone():
            conn.close()
            return {"success": False, "error": f"Роль '{selected_display_role}' уже есть у пользователя"}
        
        # Добавляем роль
        cursor.execute("INSERT INTO user_role (id_user, id_role) VALUES (?, ?)", (user_id, role_id))
        conn.commit()
        conn.close()
        
        print(f"\n✅ Роль '{selected_display_role}' успешно добавлена!")
        
        # Проверяем автоматические роли
        print(f"\n🔄 Проверяем автоматические роли...")
        RoleManager.check_and_update_roles(user_id)
        
        return {
            "success": True,
            "message": f"Роль '{selected_display_role}' добавлена пользователю {user_id}",
            "user_id": user_id,
            "role": selected_display_role
        }
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

def remove_specific_role_console(user_id: int, admin_id: int = 1) -> Dict:
    """Удаление конкретной роли у пользователя"""
    print(f"\n❌ Удаление конкретной роли у пользователя ID {user_id}")
    
    current_roles = RoleManager.get_user_roles(user_id)
    if not current_roles["success"]:
        return current_roles
    
    if not current_roles['all_roles']:
        print("\n⚠️  У пользователя нет ролей для удаления!")
        return {"success": False, "error": "Нет ролей для удаления"}
    
    print(f"\n📋 Текущие роли пользователя:")
    for i, role in enumerate(current_roles['all_roles'], 1):
        print(f"   {i}. {role}")
    
    try:
        choice = int(input(f"\nВыберите роль для удаления (1-{len(current_roles['all_roles'])}): ").strip())
        if choice < 1 or choice > len(current_roles['all_roles']):
            return {"success": False, "error": "Неверный выбор"}
        
        role_name = current_roles['all_roles'][choice - 1]
    except ValueError:
        return {"success": False, "error": "Введите число"}
    
    if role_name == 'Участник':
        print(f"\n⚠️  Роль '{role_name}' является базовой и не может быть удалена!")
        return {"success": False, "error": "Базовую роль 'Участник' нельзя удалить"}
    
    user_info = get_user_info_db(user_id)
    if "error" in user_info:
        return user_info
    
    print(f"\n🔍 Информация об удалении:")
    print(f"   Пользователь: {user_info['full_name']} (ID: {user_id})")
    print(f"   Роль для удаления: {role_name}")
    print(f"   Удаляет: Администратор ID {admin_id}")
    
    confirm = input(f"\n❌ ВНИМАНИЕ: Это действие нельзя отменить! Удалить роль '{role_name}'? (y/n): ").strip().lower()
    if confirm != 'y':
        return {"success": False, "message": "Отменено"}
    
    result = remove_role_directly(user_id, role_name, admin_id)
    
    if result["success"]:
        print(f"\n✅ Роль '{role_name}' успешно удалена!")
        
        updated_roles = RoleManager.get_user_roles(user_id)
        if updated_roles["success"]:
            print(f"\n📋 Обновлённый список ролей:")
            if updated_roles['all_roles']:
                for role in updated_roles['all_roles']:
                    print(f"   • {role}")
            else:
                print("   ❌ У пользователя больше нет ролей")
    else:
        print(f"\n❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}")
    
    return result

def remove_role_directly(user_id: int, role_name: str, admin_id: int) -> Dict:
    """Прямое удаление роли через БД"""
    conn = get_db_connection()
    if not conn:
        return {"success": False, "error": "Нет подключения к БД"}
    
    try:
        cursor = conn.cursor()
        
        db_role_name = get_db_role_name(role_name)
        
        cursor.execute("SELECT ID FROM roles WHERE CAST(name AS NVARCHAR(MAX)) = ?", (db_role_name,))
        role_result = cursor.fetchone()
        
        if not role_result:
            conn.close()
            return {"success": False, "error": f"Роль '{role_name}' не найдена в БД"}
        
        role_id = role_result[0]
        
        cursor.execute("SELECT 1 FROM user_role WHERE id_user = ? AND id_role = ?", (user_id, role_id))
        if not cursor.fetchone():
            conn.close()
            return {"success": False, "error": f"Роли '{role_name}' нет у пользователя"}
        
        cursor.execute("DELETE FROM user_role WHERE id_user = ? AND id_role = ?", (user_id, role_id))
        rows_deleted = cursor.rowcount
        
        if rows_deleted == 0:
            conn.close()
            return {"success": False, "error": "Не удалось удалить роль"}
        
        try:
            cursor.execute("""
                IF OBJECT_ID('admin_actions', 'U') IS NOT NULL
                BEGIN
                    INSERT INTO admin_actions (admin_id, user_id, action_type, details, timestamp)
                    VALUES (?, ?, 'remove_role', ?, GETDATE())
                END
            """, (admin_id, user_id, f"Удалена роль: {role_name}"))
        except Exception as log_error:
            print(f"⚠️ Не удалось записать в логи: {log_error}")
        
        conn.commit()
        conn.close()
        
        if role_name != 'Легенда':
            RoleManager.check_and_update_roles(user_id)
        elif role_name == 'Легенда':
            print(f"\n⚠️  Роль 'Легенда' удалена. Пользователь больше не считается Легендой!")
        
        return {
            "success": True,
            "message": f"Роль '{role_name}' успешно удалена",
            "user_id": user_id,
            "role": role_name,
            "removed_by": admin_id,
            "rows_deleted": rows_deleted
        }
        
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return {"success": False, "error": str(e)}

def select_role_for_user_console(user_id: int) -> Dict:
    """Выбор основной роли для пользователя через консоль администратора"""
    print(f"\n🎯 ВЫБОР ОСНОВНОЙ РОЛИ ДЛЯ ПОЛЬЗОВАТЕЛЯ")
    print(f"   ID пользователя: {user_id}")
    print("-" * 50)
    
    user_info = get_user_info_db(user_id)
    if "error" in user_info:
        print(f"❌ Ошибка: {user_info['error']}")
        return user_info
    
    print(f"👤 Пользователь: {user_info['full_name']} (@{user_info['nickname']})")
    
    print("\n🔄 Получение текущих ролей пользователя...")
    roles_result = RoleManager.get_user_roles(user_id)
    
    if not roles_result["success"]:
        print(f"❌ Ошибка получения ролей: {roles_result.get('error')}")
        return roles_result
    
    if not roles_result['all_roles']:
        print("⚠️  У пользователя нет ролей для выбора!")
        print("   Сначала добавьте пользователю роли через меню (пункт 6)")
        return {"success": False, "error": "Нет ролей для выбора"}
    
    current_selected = roles_result.get('selected_role', 'Не выбрана')
    print(f"\n📊 Текущая выбранная роль: {current_selected}")
    
    print(f"\n📋 Доступные роли пользователя ({len(roles_result['all_roles'])}):")
    print("-" * 30)
    
    for i, role in enumerate(roles_result['all_roles'], 1):
        role_type = ""
        if role in RoleManager.AUTO_ROLES:
            role_type = " [авто]"
        elif role in RoleManager.ADMIN_ROLES:
            role_type = " [админ]"
        
        current_marker = " ← ТЕКУЩАЯ" if role == current_selected else ""
        print(f"   {i:2d}. {role}{role_type}{current_marker}")
    
    print("-" * 30)
    
    try:
        choice = int(input(f"\n🎯 Выберите роль (1-{len(roles_result['all_roles'])}): ").strip())
        if choice < 1 or choice > len(roles_result['all_roles']):
            return {"success": False, "error": f"Неверный выбор. Введите число от 1 до {len(roles_result['all_roles'])}"}
        
        selected_role = roles_result['all_roles'][choice - 1]
        
        if selected_role == current_selected:
            print(f"\n⚠️  Роль '{selected_role}' уже выбрана как основная!")
            confirm = input("   Вы уверены, что хотите подтвердить её снова? (y/n): ").strip().lower()
            if confirm != 'y':
                return {"success": False, "message": "Отменено пользователем"}
    except ValueError:
        return {"success": False, "error": "Введите число"}
    
    print(f"\n🔍 ПОДТВЕРЖДЕНИЕ ВЫБОРА:")
    print(f"   Пользователь: {user_info['full_name']} (ID: {user_id})")
    print(f"   Выбранная роль: {selected_role}")
    print(f"   Выдаёт: Администратор (через консоль)")
    
    confirm = input(f"\n✅ Подтвердить выбор роли '{selected_role}'? (y/n): ").strip().lower()
    if confirm != 'y':
        return {"success": False, "message": "Отменено"}
    
    return update_user_role_order(user_id, selected_role)

def update_user_role_order(user_id: int, role_name: str) -> Dict:
    """Обновление порядка ролей (делает выбранную роль последней)"""
    print(f"\n🔄 Обновление порядка ролей для пользователя {user_id}")
    
    conn = get_db_connection()
    if not conn:
        return {"success": False, "error": "Нет подключения к БД"}
    
    try:
        cursor = conn.cursor()
        
        db_role_name = get_db_role_name(role_name)
        
        cursor.execute("SELECT ID FROM roles WHERE CAST(name AS NVARCHAR(MAX)) = ?", (db_role_name,))
        role_result = cursor.fetchone()
        
        if not role_result:
            conn.close()
            return {"success": False, "error": f"Роль '{role_name}' не найдена в БД"}
        
        role_id = role_result[0]
        
        # Получаем все роли пользователя
        cursor.execute("""
            SELECT id_role FROM user_role 
            WHERE id_user = ?
            GROUP BY id_role
        """, (user_id,))
        
        all_roles = [row[0] for row in cursor.fetchall()]
        
        if role_id not in all_roles:
            conn.close()
            return {"success": False, "error": f"У пользователя нет роли '{role_name}'"}
        
        # Удаляем все записи пользователя
        cursor.execute("DELETE FROM user_role WHERE id_user = ?", (user_id,))
        
        # Добавляем все роли, кроме выбранной
        for rid in all_roles:
            if rid != role_id:
                cursor.execute("INSERT INTO user_role (id_user, id_role) VALUES (?, ?)", (user_id, rid))
        
        # Добавляем выбранную роль последней
        cursor.execute("INSERT INTO user_role (id_user, id_role) VALUES (?, ?)", (user_id, role_id))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Роль '{role_name}' теперь основная (последняя в списке)")
        
        return {
            "success": True,
            "message": f"Роль '{role_name}' теперь основная",
            "user_id": user_id,
            "role": role_name
        }
        
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return {"success": False, "error": str(e)}

def assign_all_roles_console(user_id: int, admin_id: int = 1) -> Dict:
    """Выдача всех ролей (тестовый режим) - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    print(f"\n⚠️  ТЕСТОВЫЙ РЕЖИМ: Выдача ВСЕХ ролей пользователю ID {user_id}")
    print("   Это действие выдаст пользователю все возможные роли!")
    
    user_info = get_user_info_db(user_id)
    if "error" in user_info:
        return user_info
    
    print(f"\n🔍 Информация о пользователе:")
    print(f"   ID: {user_id}")
    print(f"   Имя: {user_info['full_name']}")
    print(f"   Ник: @{user_info['nickname']}")
    
    confirm = input(f"\n❌ ВНИМАНИЕ: Это действие нельзя отменить! Продолжить? (y/n): ").strip().lower()
    if confirm != 'y':
        return {"success": False, "message": "Отменено"}
    
    conn = get_db_connection()
    if not conn:
        return {"success": False, "error": "Нет подключения к БД"}
    
    try:
        cursor = conn.cursor()
        results = []
        
        # 1. Сначала верифицируем пользователя
        print(f"\n1. Верификация...")
        if not user_info['is_verified']:
            verify_result = RoleManager.verify_user(user_id, admin_id)
            results.append(("Верификация", verify_result))
        else:
            print("   ✅ Пользователь уже верифицирован")
            results.append(("Верификация", {"success": True, "message": "Уже верифицирован"}))
        
        # 2. Получаем все роли из системы
        cursor.execute("SELECT ID, CAST(name AS NVARCHAR(MAX)) as name FROM roles")
        all_roles = cursor.fetchall()
        
        # 3. Получаем текущие роли пользователя
        cursor.execute("SELECT id_role FROM user_role WHERE id_user = ?", (user_id,))
        current_role_ids = [row[0] for row in cursor.fetchall()]
        
        print(f"\n2. Выдача всех ролей...")
        added_count = 0
        
        for role_id, role_name in all_roles:
            # Пропускаем служебные роли
            if role_name in ['Админ', 'Бармен', 'Диджей', 'Охрана', 'Организатор', 'Ведущий']:
                continue
                
            if role_id not in current_role_ids:
                display_name = get_display_role_name(role_name)
                print(f"   Добавляем '{display_name}'...")
                
                try:
                    cursor.execute("INSERT INTO user_role (id_user, id_role) VALUES (?, ?)", 
                                 (user_id, role_id))
                    added_count += 1
                    results.append((display_name, {"success": True}))
                except Exception as e:
                    print(f"      ❌ Ошибка: {e}")
                    results.append((display_name, {"success": False, "error": str(e)}))
            else:
                display_name = get_display_role_name(role_name)
                print(f"   ✓ '{display_name}' уже есть")
        
        conn.commit()
        
        # 4. Проверяем автоматические роли
        print(f"\n3. Проверка автоматических ролей...")
        auto_result = RoleManager.check_and_update_roles(user_id)
        results.append(("Автоматические роли", auto_result))
        
        # 5. Выводим результаты
        print(f"\n📊 РЕЗУЛЬТАТЫ:")
        success_count = 0
        total_count = len(results)
        
        for role_name, result in results:
            if result.get("success"):
                status = "✅ Успешно"
                success_count += 1
            else:
                status = f"❌ Ошибка: {result.get('error', 'Неизвестно')}"
            
            print(f"   {role_name}: {status}")
        
        print(f"\n🎯 ИТОГО: Добавлено {added_count} новых ролей, всего операций: {success_count}/{total_count}")
        
        if added_count > 0:
            print(f"✨ Роли успешно добавлены!")
        
        conn.close()
        
        return {
            "success": True,
            "user_id": user_id,
            "added_count": added_count,
            "results": results,
            "total_operations": total_count,
            "successful_operations": success_count
        }
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
            conn.close()
        return {"success": False, "error": str(e)}
    
def add_all_missing_roles(user_id: int, admin_id: int = 1):
    """Добавление всех недостающих ролей пользователю"""
    print(f"\n🎭 Добавление ВСЕХ недостающих ролей пользователю ID {user_id}")
    
    conn = get_db_connection()
    if not conn:
        print("❌ Нет подключения к БД")
        return {"success": False, "error": "Нет подключения к БД"}
    
    try:
        cursor = conn.cursor()
        
        # Получаем информацию о пользователе
        cursor.execute("SELECT name, surname, nickname FROM users WHERE ID = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            conn.close()
            print("❌ Пользователь не найден")
            return {"success": False, "error": "Пользователь не найден"}
        
        print(f"👤 Пользователь: {user[0]} {user[1]} (@{user[2]})")
        
        # Получаем все роли из системы
        cursor.execute("SELECT ID, CAST(name AS NVARCHAR(MAX)) as name FROM roles")
        all_roles = cursor.fetchall()
        
        # Создаем словарь ролей
        role_dict = {}
        for role_id, role_name in all_roles:
            display_name = get_display_role_name(role_name)
            role_dict[display_name] = {"id": role_id, "db_name": role_name}
        
        # Получаем текущие роли пользователя
        cursor.execute("""
            SELECT CAST(r.name AS NVARCHAR(MAX)) as role_name
            FROM user_role ur
            JOIN roles r ON ur.id_role = r.ID
            WHERE ur.id_user = ?
        """, (user_id,))
        
        current_db_roles = [row[0] for row in cursor.fetchall()]
        current_roles = [get_display_role_name(role) for role in current_db_roles]
        
        print(f"\n📋 Текущие роли пользователя ({len(current_roles)}):")
        for role in sorted(current_roles):
            print(f"   • {role}")
        
        # Список всех нужных ролей (исключая служебные)
        required_roles = [
            'Участник', 'Рисковый', 'Душа компании', 'Весельчак', 
            'Тусовщик', 'Ас тусовок', 'Танцор', 'Ас танцпола', 
            'Любитель выпить', 'Глава бара', 'Легенда'
        ]
        
        missing_roles = []
        for role in required_roles:
            if role not in current_roles:
                missing_roles.append(role)
        
        if not missing_roles:
            print(f"\n✅ У пользователя уже есть все необходимые роли!")
            conn.close()
            return {"success": True, "message": "Все роли уже есть"}
        
        print(f"\n📋 Недостающие роли ({len(missing_roles)}):")
        for role in missing_roles:
            print(f"   • {role}")
        
        confirm = input(f"\n✅ Добавить все недостающие роли? (y/n): ").strip().lower()
        if confirm != 'y':
            conn.close()
            return {"success": False, "message": "Отменено"}
        
        # Добавляем недостающие роли
        added_count = 0
        for role in missing_roles:
            role_info = role_dict.get(role)
            if role_info:
                try:
                    cursor.execute("INSERT INTO user_role (id_user, id_role) VALUES (?, ?)", 
                                 (user_id, role_info["id"]))
                    print(f"   ✅ Добавлена роль: {role}")
                    added_count += 1
                except Exception as e:
                    print(f"   ❌ Ошибка при добавлении {role}: {e}")
            else:
                print(f"   ⚠️ Роль '{role}' не найдена в БД")
        
        conn.commit()
        
        # Проверяем, появилась ли Легенда
        cursor.execute("""
            SELECT ID FROM roles WHERE CAST(name AS NVARCHAR(MAX)) = 'Легенда'
        """)
        legend_result = cursor.fetchone()
        
        if legend_result:
            legend_id = legend_result[0]
            cursor.execute("SELECT 1 FROM user_role WHERE id_user = ? AND id_role = ?", (user_id, legend_id))
            if not cursor.fetchone() and all(role in current_roles + missing_roles for role in required_roles[:-1]):
                print(f"\n🏆 У пользователя теперь есть все роли для Легенды!")
                cursor.execute("INSERT INTO user_role (id_user, id_role) VALUES (?, ?)", (user_id, legend_id))
                print(f"   ✅ Добавлена роль: Легенда")
                added_count += 1
                conn.commit()
        
        conn.close()
        
        print(f"\n🎉 Добавлено {added_count} новых ролей!")
        
        return {
            "success": True,
            "message": f"Добавлено {added_count} ролей",
            "user_id": user_id,
            "added_count": added_count
        }
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
            conn.close()
        return {"success": False, "error": str(e)}
    
def check_user_roles_simple(user_id: int):
    """Простая проверка ролей пользователя"""
    conn = get_db_connection()
    if not conn:
        print("❌ Нет подключения к БД")
        return
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("SELECT name, surname, nickname FROM users WHERE ID = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            print("❌ Пользователь не найден")
            conn.close()
            return
        
        print(f"\n👤 Пользователь: {user[0]} {user[1]} (@{user[2]})")
        
        cursor.execute("""
            SELECT CAST(r.name AS NVARCHAR(MAX)) as role_name
            FROM user_role ur
            JOIN roles r ON ur.id_role = r.ID
            WHERE ur.id_user = ?
        """, (user_id,))
        
        roles = [get_display_role_name(row[0]) for row in cursor.fetchall()]
        
        print(f"\n📋 Роли пользователя ({len(roles)}):")
        for role in sorted(roles):
            print(f"   • {role}")
        
        required_roles = [
            'Участник', 'Рисковый', 'Душа компании', 'Весельчак', 
            'Тусовщик', 'Ас тусовок', 'Танцор', 'Ас танцпола', 
            'Любитель выпить', 'Глава бара'
        ]
        
        missing = [role for role in required_roles if role not in roles]
        
        if missing:
            print(f"\n❌ Не хватает ролей для Легенды: {', '.join(missing)}")
        else:
            print(f"\n✅ Есть ВСЕ роли для Легенды!")
            if 'Легенда' in roles:
                print(f"🏆 У пользователя уже есть роль Легенда!")
            else:
                print(f"🎯 Можно выдать роль Легенда!")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        conn.close()

def get_user_stats(user_id: int) -> Dict:
    """Получение статистики пользователя"""
    print(f"\n📊 Статистика пользователя ID {user_id}")
    
    user_info = get_user_info_db(user_id)
    if "error" in user_info:
        return user_info
    
    roles_result = RoleManager.get_user_roles(user_id)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE refer_from = ?", (user_info['refer_code'],))
    referral_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE id_user = ?", (user_id,))
    ticket_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM discounts WHERE id_user = ?", (user_id,))
    discount_count = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"\n👤 ОСНОВНАЯ ИНФОРМАЦИЯ:")
    print(f"   ID: {user_info['user_id']}")
    print(f"   Имя: {user_info['full_name']}")
    print(f"   Никнейм: @{user_info['nickname']}")
    print(f"   Email: {user_info['email']}")
    print(f"   Возраст: {user_info['age']}")
    print(f"   Пол: {user_info['gender']}")
    print(f"   Статус: {'✅ Активен' if not user_info['is_banned'] else '❌ Забанен'}")
    print(f"   Верификация: {'✅ Пройдена' if user_info['is_verified'] else '❌ Не пройдена'}")
    print(f"   Реферальный код: {user_info['refer_code']}")
    
    print(f"\n📈 СТАТИСТИКА:")
    print(f"   Рефералов приглашено: {referral_count}")
    print(f"   Билетов куплено: {ticket_count}")
    print(f"   Скидок получено: {discount_count}")
    
    if roles_result["success"]:
        print(f"\n🏆 РОЛИ ({roles_result['total_count']}):")
        if roles_result['auto_roles']:
            print(f"   Автоматические: {', '.join(roles_result['auto_roles'])}")
        if roles_result['admin_roles']:
            print(f"   От администратора: {', '.join(roles_result['admin_roles'])}")
        
        if roles_result['has_legend']:
            print(f"\n   🎉 ПОЗДРАВЛЯЕМ! ПОЛЬЗОВАТЕЛЬ - ЛЕГЕНДА! 🏆")
    
    return {
        "success": True,
        "user_info": user_info,
        "stats": {
            "referrals": referral_count,
            "tickets": ticket_count,
            "discounts": discount_count
        },
        "roles": roles_result if roles_result["success"] else None
    }

def view_all_system_roles():
    """Просмотр всех ролей в системе"""
    print(f"\n🗂️  Все роли в системе Need for Party")
    
    result = RoleManager.get_all_roles_info()
    
    if result["success"]:
        print(f"\n📊 Всего ролей в системе: {result['total_roles']}")
        
        print(f"\n🎭 АВТОМАТИЧЕСКИЕ РОЛИ:")
        auto_roles = [r for r in result['roles'] if r['type'] == 'auto']
        for role in auto_roles:
            legend_note = " (Легенда)" if role['display_name'] == 'Легенда' else ""
            print(f"   • {role['display_name']}{legend_note}")
        
        print(f"\n🛠️  РОЛИ АДМИНИСТРАТОРА:")
        admin_roles = [r for r in result['roles'] if r['type'] == 'admin']
        for role in admin_roles:
            print(f"   • {role['display_name']}")
        
        print(f"\n👔 СЛУЖЕБНЫЕ РОЛИ:")
        service_roles = [r for r in result['roles'] if r['type'] not in ['auto', 'admin']]
        for role in service_roles:
            print(f"   • {role['display_name']} ({role['db_name']})")
        
        print(f"\n📝 ПРИМЕЧАНИЯ:")
        print(f"   • Автоматические роли выдаются системой по условиям")
        print(f"   • Роли администратора выдаются вручную через эту консоль")
        print(f"   • Роль 'Легенда' выдаётся автоматически при получении всех ролей")
        print(f"   • Служебные роли предназначены для администраторов и сотрудников")
    else:
        print(f"\n❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}")
    
    return result

def fix_user_roles(user_id: int):
    """Исправление ролей пользователя (сброс и установка базовой)"""
    print(f"\n🧹 Исправление ролей пользователя ID {user_id}")
    print("   Это действие удалит все текущие роли и установит только 'Участник'")
    
    confirm = input("⚠️  Вы уверены? Это действие нельзя отменить! (y/n): ").strip().lower()
    if confirm != 'y':
        return {"success": False, "message": "Отменено"}
    
    conn = get_db_connection()
    if not conn:
        return {"success": False, "error": "Нет подключения к БД"}
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM user_role WHERE id_user = ?", (user_id,))
        deleted_count = cursor.rowcount
        print(f"   Удалено ролей: {deleted_count}")
        
        cursor.execute("SELECT ID FROM roles WHERE CAST(name AS NVARCHAR(MAX)) = 'Участник'")
        participant_id = cursor.fetchone()
        
        if not participant_id:
            conn.rollback()
            conn.close()
            return {"success": False, "error": "Роль 'Участник' не найдена"}
        
        cursor.execute("INSERT INTO user_role (id_user, id_role) VALUES (?, ?)", 
                      (user_id, participant_id[0]))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Роли исправлены. Теперь только 'Участник'")
        
        return RoleManager.check_and_update_roles(user_id)
        
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return {"success": False, "error": str(e)}

def clean_user_duplicate_roles(user_id: int):
    """Очистка дублирующихся ролей у конкретного пользователя"""
    print(f"\n🧹 Очистка дубликатов ролей для пользователя {user_id}")
    
    conn = get_db_connection()
    if not conn:
        return {"success": False, "error": "Нет подключения к БД"}
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT ur.ID, ur.id_role, CAST(r.name AS NVARCHAR(MAX)) as role_name
            FROM user_role ur
            JOIN roles r ON ur.id_role = r.ID
            WHERE ur.id_user = ?
            ORDER BY ur.ID
        """, (user_id,))
        
        all_records = cursor.fetchall()
        
        if not all_records:
            conn.close()
            return {"success": True, "message": "У пользователя нет ролей"}
        
        print(f"📊 Найдено записей: {len(all_records)}")
        
        role_groups = {}
        for record_id, role_id, role_name in all_records:
            if role_id not in role_groups:
                role_groups[role_id] = []
            role_groups[role_id].append((record_id, role_name))
        
        to_delete = []
        for role_id, records in role_groups.items():
            if len(records) > 1:
                display_name = get_display_role_name(records[0][1])
                print(f"   Роль '{display_name}' имеет {len(records)} записей")
                records.sort(key=lambda x: x[0])
                for record_id, role_name in records[:-1]:
                    to_delete.append(record_id)
        
        if not to_delete:
            conn.close()
            return {"success": True, "message": "Дубликатов не найдено"}
        
        print(f"🗑️  Удаляю {len(to_delete)} дубликатов...")
        
        deleted_count = 0
        for record_id in to_delete:
            cursor.execute("DELETE FROM user_role WHERE ID = ?", (record_id,))
            deleted_count += 1
        
        conn.commit()
        conn.close()
        
        print(f"✅ Удалено {deleted_count} дубликатов")
        
        return {
            "success": True,
            "message": f"Удалено {deleted_count} дубликатов ролей",
            "user_id": user_id,
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return {"success": False, "error": str(e)}

def clean_all_duplicate_roles():
    """Очистка дубликатов ролей во всей системе"""
    print(f"\n🧹 ГЛОБАЛЬНАЯ ОЧИСТКА ДУБЛИКАТОВ РОЛЕЙ")
    print("="*60)
    
    conn = get_db_connection()
    if not conn:
        return {"success": False, "error": "Нет подключения к БД"}
    
    try:
        cursor = conn.cursor()
        
        # Очистка дубликатов в таблице roles
        print("\n🔍 Проверка дубликатов в таблице roles...")
        
        cursor.execute("""
            SELECT CAST(name AS NVARCHAR(MAX)) as name, COUNT(*) as count
            FROM roles
            GROUP BY CAST(name AS NVARCHAR(MAX))
            HAVING COUNT(*) > 1
        """)
        
        role_duplicates = cursor.fetchall()
        
        if role_duplicates:
            print(f"\n📊 Найдены дубликаты ролей:")
            for name, count in role_duplicates:
                print(f"   • '{name}': {count} копий")
                
                cursor.execute("SELECT ID FROM roles WHERE CAST(name AS NVARCHAR(MAX)) = ? ORDER BY ID", (name,))
                ids = [row[0] for row in cursor.fetchall()]
                keep_id = ids[0]
                delete_ids = ids[1:]
                
                print(f"      Оставляем ID {keep_id}, удаляем {delete_ids}")
                
                for delete_id in delete_ids:
                    cursor.execute("UPDATE user_role SET id_role = ? WHERE id_role = ?", (keep_id, delete_id))
                    cursor.execute("DELETE FROM roles WHERE ID = ?", (delete_id,))
        else:
            print("✅ Дубликатов в таблице roles не найдено")
        
        # Очистка дубликатов в user_role
        print("\n🔍 Проверка дубликатов в таблице user_role...")
        
        cursor.execute("""
            SELECT id_user, id_role, COUNT(*) as count
            FROM user_role
            GROUP BY id_user, id_role
            HAVING COUNT(*) > 1
        """)
        
        user_role_duplicates = cursor.fetchall()
        
        if user_role_duplicates:
            print(f"\n📊 Найдены дубликаты в user_role:")
            total_deleted = 0
            
            for user_id, role_id, count in user_role_duplicates:
                cursor.execute("""
                    SELECT ID FROM user_role 
                    WHERE id_user = ? AND id_role = ?
                    ORDER BY ID
                """, (user_id, role_id))
                
                records = [row[0] for row in cursor.fetchall()]
                keep_id = records[-1]
                delete_ids = records[:-1]
                
                cursor.execute("SELECT CAST(name AS NVARCHAR(MAX)) FROM roles WHERE ID = ?", (role_id,))
                role_name = cursor.fetchone()[0]
                display_name = get_display_role_name(role_name)
                
                print(f"   Пользователь {user_id}, роль '{display_name}': {len(records)} записей")
                print(f"      Оставляем ID {keep_id}, удаляем {delete_ids}")
                
                for delete_id in delete_ids:
                    cursor.execute("DELETE FROM user_role WHERE ID = ?", (delete_id,))
                    total_deleted += 1
            
            print(f"\n✅ Удалено {total_deleted} дубликатов в user_role")
        else:
            print("✅ Дубликатов в таблице user_role не найдено")
        
        conn.commit()
        conn.close()
        
        print("\n🎉 Глобальная очистка завершена!")
        
        return {"success": True, "message": "Очистка завершена"}
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        conn.rollback()
        conn.close()
        return {"success": False, "error": str(e)}
    

def force_add_all_roles(user_id: int):
    """ПРИНУДИТЕЛЬНОЕ добавление всех ролей пользователю (максимально просто)"""
    print(f"\n🔧 ПРИНУДИТЕЛЬНОЕ добавление ВСЕХ ролей пользователю ID {user_id}")
    print("="*60)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Нет подключения к БД")
        return
    
    try:
        cursor = conn.cursor()
        
        # Получаем информацию о пользователе
        cursor.execute("SELECT name, surname FROM users WHERE ID = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            print("❌ Пользователь не найден")
            conn.close()
            return
        
        print(f"👤 Пользователь: {user[0]} {user[1]}")
        
        # Получаем ВСЕ роли из БД с их ID
        cursor.execute("SELECT ID, CAST(name AS NVARCHAR(MAX)) as name FROM roles")
        all_roles = cursor.fetchall()
        
        print(f"\n📋 Найдено ролей в системе: {len(all_roles)}")
        
        # Список ID ролей, которые нужно добавить (исключая служебные)
        role_ids_to_add = []
        role_names_to_add = []
        
        for role_id, role_name in all_roles:
            # Пропускаем служебные роли
            if role_name in ['Админ', 'Бармен', 'Диджей', 'Охрана', 'Организатор', 'Ведущий']:
                continue
            
            # Исправляем отображение
            display_name = role_name
            if role_name == 'Ас танспола':
                display_name = 'Ас танцпола'
            
            role_ids_to_add.append(role_id)
            role_names_to_add.append(display_name)
        
        print(f"\n🎯 Будет добавлено ролей: {len(role_ids_to_add)}")
        print("   " + ", ".join(role_names_to_add))
        
        confirm = input("\n✅ Продолжить? (y/n): ").strip().lower()
        if confirm != 'y':
            print("❌ Отменено")
            conn.close()
            return
        
        # Удаляем ВСЕ текущие роли пользователя
        cursor.execute("DELETE FROM user_role WHERE id_user = ?", (user_id,))
        print(f"   🗑️ Удалены все старые роли")
        
        # Добавляем ВСЕ роли по одной
        added = 0
        for role_id, display_name in zip(role_ids_to_add, role_names_to_add):
            try:
                cursor.execute("INSERT INTO user_role (id_user, id_role) VALUES (?, ?)", (user_id, role_id))
                print(f"   ✅ Добавлена: {display_name}")
                added += 1
            except Exception as e:
                print(f"   ❌ Ошибка при добавлении {display_name}: {e}")
        
        conn.commit()
        conn.close()
        
        print(f"\n🎉 УСПЕХ! Добавлено {added} ролей пользователю {user_id}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
            conn.close()

def force_legend_check(user_id: int):
    """Принудительная проверка и выдача роли Легенда"""
    print(f"\n🏆 Принудительная проверка Легенды для пользователя {user_id}")
    
    conn = get_db_connection()
    if not conn:
        return {"success": False, "error": "Нет подключения к БД"}
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT CAST(r.name AS NVARCHAR(MAX)) as role_name
            FROM user_role ur
            JOIN roles r ON ur.id_role = r.ID
            WHERE ur.id_user = ?
        """, (user_id,))
        
        user_roles = [row[0] for row in cursor.fetchall()]
        print(f"📋 Роли пользователя: {user_roles}")
        
        required_roles = ['Участник', 'Рисковый', 'Душа компании', 'Весельчак', 
                          'Тусовщик', 'Ас тусовок', 'Танцор', 'Ас танцпола', 
                          'Любитель выпить', 'Глава бара']
        
        user_roles_corrected = []
        for role in user_roles:
            user_roles_corrected.append(get_display_role_name(role))
        
        missing_roles = []
        for role in required_roles:
            if role not in user_roles_corrected:
                missing_roles.append(role)
        
        print(f"🎯 Требуется для Легенды: {required_roles}")
        print(f"❌ Не хватает: {missing_roles}")
        
        if not missing_roles:
            print(f"✅ У пользователя ВСЕ 10 ролей! Можно выдавать Легенду!")
            
            cursor.execute("SELECT ID FROM roles WHERE CAST(name AS NVARCHAR(MAX)) = 'Легенда'")
            legend_id = cursor.fetchone()
            
            if legend_id:
                legend_id = legend_id[0]
                
                cursor.execute("SELECT 1 FROM user_role WHERE id_user = ? AND id_role = ?", 
                             (user_id, legend_id))
                if not cursor.fetchone():
                    cursor.execute("INSERT INTO user_role (id_user, id_role) VALUES (?, ?)", 
                                 (user_id, legend_id))
                    conn.commit()
                    print(f"✅ Роль 'Легенда' успешно добавлена пользователю {user_id}!")
                    return {"success": True, "message": "Легенда выдана!", "user_id": user_id}
                else:
                    print(f"ℹ️ Роль 'Легенда' уже есть у пользователя")
                    return {"success": True, "message": "Легенда уже есть", "user_id": user_id}
            else:
                print(f"❌ Роль 'Легенда' не найдена в БД!")
                return {"success": False, "error": "Роль Легенда не найдена"}
        else:
            print(f"❌ Не хватает ролей: {missing_roles}")
            return {"success": False, "error": f"Не хватает ролей: {missing_roles}"}
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return {"success": False, "error": str(e)}

def debug_user_roles_full(user_id: int):
    """Полная отладка ролей пользователя"""
    print(f"\n🔍 ПОЛНАЯ ОТЛАДКА РОЛЕЙ ПОЛЬЗОВАТЕЛЯ {user_id}")
    print("="*60)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Нет подключения к БД")
        return
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("SELECT ID, nickname, name, surname FROM users WHERE ID = ?", (user_id,))
        user = cursor.fetchone()
        if user:
            print(f"👤 Пользователь: {user[2]} {user[3]} (@{user[1]})")
        else:
            print(f"❌ Пользователь {user_id} не найден!")
            return
        
        cursor.execute("SELECT ID, CAST(name AS NVARCHAR(MAX)) FROM roles ORDER BY ID")
        all_roles = cursor.fetchall()
        print(f"\n📋 Все роли в системе ({len(all_roles)}):")
        for role_id, role_name in all_roles:
            display_name = get_display_role_name(role_name)
            print(f"   ID {role_id}: '{role_name}' -> '{display_name}'")
        
        cursor.execute("""
            SELECT ur.ID, ur.id_role, CAST(r.name AS NVARCHAR(MAX)) as role_name
            FROM user_role ur
            JOIN roles r ON ur.id_role = r.ID
            WHERE ur.id_user = ?
            ORDER BY ur.ID
        """, (user_id,))
        
        user_roles = cursor.fetchall()
        print(f"\n🎭 Роли пользователя в user_role ({len(user_roles)} записей):")
        
        role_counts = {}
        for record_id, role_id, role_name in user_roles:
            display_name = get_display_role_name(role_name)
            print(f"   Запись ID {record_id}: Роль ID {role_id} = '{role_name}' -> '{display_name}'")
            if display_name in role_counts:
                role_counts[display_name] += 1
            else:
                role_counts[display_name] = 1
        
        print(f"\n✨ Уникальные роли пользователя:")
        unique_roles = set()
        for _, _, role_name in user_roles:
            unique_roles.add(get_display_role_name(role_name))
        
        for role in sorted(unique_roles):
            count = role_counts.get(role, 0)
            print(f"   • {role} ({count} записей)")
        
        required_roles = ['Участник', 'Рисковый', 'Душа компании', 'Весельчак', 
                         'Тусовщик', 'Ас тусовок', 'Танцор', 'Ас танцпола', 
                         'Любитель выпить', 'Глава бара']
        
        print(f"\n🎯 Проверка ролей для Легенды:")
        missing = []
        for role in required_roles:
            if role in unique_roles:
                print(f"   ✅ {role}")
            else:
                print(f"   ❌ {role}")
                missing.append(role)
        
        print(f"\n📊 ИТОГО: {len(unique_roles)}/10 ролей")
        if missing:
            print(f"❌ Не хватает: {missing}")
        else:
            print(f"✅ ЕСТЬ ВСЕ 10 РОЛЕЙ! МОЖНО ВЫДАВАТЬ ЛЕГЕНДУ!")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        conn.close()

def reset_selected_role(user_id: int, role_name: str = None):
    """Сброс выбранной роли пользователя"""
    print(f"\n🔄 Сброс выбранной роли для пользователя {user_id}")
    
    conn = get_db_connection()
    if not conn:
        return {"success": False, "error": "Нет подключения к БД"}
    
    try:
        cursor = conn.cursor()
        
        if role_name:
            db_role_name = get_db_role_name(role_name)
                
            cursor.execute("SELECT ID FROM roles WHERE CAST(name AS NVARCHAR(MAX)) = ?", (db_role_name,))
            role_result = cursor.fetchone()
            
            if role_result:
                role_id = role_result[0]
                
                cursor.execute("DELETE FROM user_role WHERE id_user = ? AND id_role = ?", 
                             (user_id, role_id))
                cursor.execute("INSERT INTO user_role (id_user, id_role) VALUES (?, ?)", 
                             (user_id, role_id))
                
                print(f"✅ Роль '{role_name}' сброшена")
        else:
            cursor.execute("""
                SELECT id_role, MIN(ID) as min_id
                FROM user_role
                WHERE id_user = ?
                GROUP BY id_role
            """, (user_id,))
            
            roles_to_keep = cursor.fetchall()
            
            cursor.execute("DELETE FROM user_role WHERE id_user = ?", (user_id,))
            
            for role_id, _ in roles_to_keep:
                cursor.execute("INSERT INTO user_role (id_user, id_role) VALUES (?, ?)", 
                             (user_id, role_id))
            
            print(f"✅ Все роли пользователя {user_id} сброшены")
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": "Роли успешно сброшены",
            "user_id": user_id
        }
        
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return {"success": False, "error": str(e)}

def fix_role_order(user_id: int, preferred_role: str = None):
    """Исправляет порядок ролей - делает выбранную роль последней"""
    print(f"\n🔄 ИСПРАВЛЕНИЕ ПОРЯДКА РОЛЕЙ для пользователя {user_id}")
    
    conn = get_db_connection()
    if not conn:
        return {"success": False, "error": "Нет подключения к БД"}
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id_role, CAST(r.name AS NVARCHAR(MAX)) as role_name
            FROM user_role ur
            JOIN roles r ON ur.id_role = r.ID
            WHERE ur.id_user = ?
            GROUP BY ur.id_role, CAST(r.name AS NVARCHAR(MAX))
        """, (user_id,))
        
        user_roles = cursor.fetchall()
        
        cursor.execute("DELETE FROM user_role WHERE id_user = ?", (user_id,))
        
        for role_id, role_name in user_roles:
            display_name = get_display_role_name(role_name)
            
            if preferred_role and display_name != preferred_role:
                cursor.execute("INSERT INTO user_role (id_user, id_role) VALUES (?, ?)", 
                             (user_id, role_id))
                print(f"   ✅ Добавлена роль: {display_name}")
        
        if preferred_role:
            db_role_name = get_db_role_name(preferred_role)
                
            cursor.execute("SELECT ID FROM roles WHERE CAST(name AS NVARCHAR(MAX)) = ?", (db_role_name,))
            role_result = cursor.fetchone()
            
            if role_result:
                role_id = role_result[0]
                cursor.execute("INSERT INTO user_role (id_user, id_role) VALUES (?, ?)", 
                             (user_id, role_id))
                print(f"   🎯 Добавлена ПРЕДПОЧТИТЕЛЬНАЯ роль: {preferred_role} (последней)")
        
        conn.commit()
        conn.close()
        
        print(f"\n✅ Порядок ролей исправлен!")
        print(f"   Предпочтительная роль: {preferred_role}")
        
        return {
            "success": True,
            "message": f"Порядок ролей исправлен",
            "user_id": user_id,
            "preferred_role": preferred_role
        }
        
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return {"success": False, "error": str(e)}

def check_parties_in_db():
    """Проверка вечеринок в БД"""
    print("\n🔍 ПРОВЕРКА ВЕЧЕРИНОК В БД")
    print("="*50)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Нет подключения к БД")
        return
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM parties")
        total = cursor.fetchone()[0]
        print(f"\n📊 Всего записей в parties: {total}")
        
        if total > 0:
            cursor.execute("""
                SELECT ID, name, cost, location, start_party, count_seats
                FROM parties
                ORDER BY start_party
            """)
            
            parties = cursor.fetchall()
            print(f"\n🎉 Список вечеринок:")
            for party in parties:
                print(f"\n   ID: {party[0]}")
                print(f"   Название: {party[1]}")
                print(f"   Цена: {party[2]}₽")
                print(f"   Локация: {party[3]}")
                print(f"   Дата: {party[4]}")
                print(f"   Мест: {party[5]}")
        else:
            print("\n❌ В таблице parties нет записей!")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        conn.close()

def check_exact_role_names():
    """Проверка точных названий ролей"""
    conn = get_db_connection()
    if not conn:
        print("❌ Нет подключения к БД")
        return
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("SELECT ID, CAST(name AS NVARCHAR(MAX)) as name FROM roles ORDER BY ID")
        results = cursor.fetchall()
        
        print("\n🔍 ТОЧНЫЕ НАЗВАНИЯ РОЛЕЙ В БД:")
        print("="*60)
        for role_id, role_name in results:
            print(f"   ID {role_id}: '{role_name}'")
            print(f"      Коды символов: {[ord(c) for c in role_name]}")
            print(f"      Отображаемое: '{get_display_role_name(role_name)}'")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        conn.close()

def view_verification_queue():
    """Просмотр очереди на верификацию"""
    print("\n🔍 ОЧЕРЕДЬ НА ВЕРИФИКАЦИЮ")
    print("="*50)
    
    try:
        response = requests.get(f"{API_URL}/api/admin/verification-queue")
        result = response.json()
        
        if result["success"]:
            queue = result["queue"]
            if not queue:
                print("📭 Нет ожидающих верификации")
                return
            
            print(f"\n📋 Ожидают проверки: {result['count']}")
            print("-" * 50)
            
            for item in queue:
                print(f"   ID: {item['user_id']}")
                print(f"   Пользователь: {item['name']} {item['surname']} (@{item['nickname']})")
                print(f"   Отправлено: {item['submitted_at']}")
                print("-" * 30)
        else:
            print(f"❌ Ошибка: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")

def view_user_document(user_id: int, admin_id: int = 1):
    """Просмотр документа пользователя"""
    print(f"\n📄 ПРОСМОТР ДОКУМЕНТА ПОЛЬЗОВАТЕЛЯ {user_id}")
    print("="*50)
    print("⚠️  ВНИМАНИЕ: Это конфиденциальные данные!")
    print("⚠️  Не распространяйте и не сохраняйте их!")
    print("="*50)
    
    confirm = input("\n✅ Подтвердите доступ (y/n): ").strip().lower()
    if confirm != 'y':
        print("❌ Отменено")
        return
    
    import requests
    import base64
    from datetime import datetime
    import os
    
    try:
        response = requests.get(
            f"{API_URL}/api/admin/verification-document/{user_id}",
            params={"admin_id": admin_id}
        )
        result = response.json()
        
        if result["success"]:
            print(f"\n👤 Пользователь: {result['name']} {result['surname']}")
            print(f"   Никнейм: @{result['nickname']}")
            print(f"   📞 Телефон: {result.get('phone', 'Не указан')}")
            print(f"   🌍 Гражданство: {result.get('citizenship', 'Не указано')}")
            print(f"   🆔 ID документа: {result.get('iid', 'Не указан')}")
            
            # Сохраняем документ
            doc_data = base64.b64decode(result['document'])
            
            temp_dir = "temp_docs"
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
            
            filename = f"{temp_dir}/doc_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            
            with open(filename, 'wb') as f:
                f.write(doc_data)
            
            print(f"\n✅ Документ сохранен: {filename}")
            print("\n📌 После просмотра файл будет удален")
            
            try:
                os.startfile(filename)
            except:
                print(f"📁 Откройте файл вручную: {filename}")
            
            # Верификация
            print("\n✅ Верифицировать пользователя? (y/n)")
            verify_choice = input().strip().lower()
            
            if verify_choice == 'y':
                verify_user_console(user_id, admin_id)
            
            input("\n⏎ Нажмите Enter для удаления файла...")
            os.remove(filename)
            print("✅ Временный файл удален")
            
        else:
            print(f"❌ Ошибка: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")

def clean_all_user_roles():
    """Очистка дубликатов ролей для всех пользователей"""
    print("\n🧹 ОЧИСТКА ДУБЛИКАТОВ РОЛЕЙ ДЛЯ ВСЕХ ПОЛЬЗОВАТЕЛЕЙ")
    print("="*60)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Нет подключения к БД")
        return
    
    try:
        cursor = conn.cursor()
        
        # Получаем всех пользователей, у которых есть роли
        cursor.execute("SELECT DISTINCT id_user FROM user_role")
        users = cursor.fetchall()
        
        total_deleted = 0
        
        for user_row in users:
            user_id = user_row[0]
            
            # Получаем все роли пользователя с их ID
            cursor.execute("""
                SELECT ur.ID, ur.id_role, CAST(r.name AS NVARCHAR(MAX)) as role_name
                FROM user_role ur
                JOIN roles r ON ur.id_role = r.ID
                WHERE ur.id_user = ?
                ORDER BY ur.ID
            """, (user_id,))
            
            records = cursor.fetchall()
            
            # Группируем по id_role
            role_groups = {}
            for record_id, role_id, role_name in records:
                if role_id not in role_groups:
                    role_groups[role_id] = []
                role_groups[role_id].append((record_id, role_name))
            
            # Для каждой роли оставляем только последнюю запись
            for role_id, role_records in role_groups.items():
                if len(role_records) > 1:
                    # Оставляем запись с максимальным ID
                    keep_id = max(r[0] for r in role_records)
                    for record_id, _ in role_records:
                        if record_id != keep_id:
                            cursor.execute("DELETE FROM user_role WHERE ID = ?", (record_id,))
                            total_deleted += 1
                            print(f"   Пользователь {user_id}: удален дубликат роли {role_records[0][1]}")
        
        conn.commit()
        conn.close()
        
        print(f"\n✅ Удалено {total_deleted} дубликатов")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        conn.rollback()
        conn.close()

def migrate_add_is_selected():
    """Добавление поля is_selected и установка для последних ролей"""
    print("\n🔄 МИГРАЦИЯ: Добавление поля is_selected")
    print("="*60)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Нет подключения к БД")
        return
    
    try:
        cursor = conn.cursor()
        
        # Проверяем, есть ли уже поле
        cursor.execute("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'user_role' AND COLUMN_NAME = 'is_selected'
        """)
        
        if cursor.fetchone()[0] == 0:
            print("📝 Добавляем поле is_selected...")
            cursor.execute("ALTER TABLE user_role ADD is_selected BIT DEFAULT 0 NOT NULL")
            print("✅ Поле добавлено")
        else:
            print("✅ Поле is_selected уже существует")
        
        # Сбрасываем все is_selected
        cursor.execute("UPDATE user_role SET is_selected = 0")
        
        # Для каждого пользователя выбираем последнюю роль и помечаем её
        cursor.execute("""
            SELECT id_user, MAX(ID) as last_id
            FROM user_role
            GROUP BY id_user
        """)
        
        users = cursor.fetchall()
        
        for user_id, last_id in users:
            cursor.execute("UPDATE user_role SET is_selected = 1 WHERE ID = ?", (last_id,))
            print(f"   Пользователь {user_id}: отмечена последняя роль (ID записи {last_id})")
        
        conn.commit()
        
        # Проверяем результат
        cursor.execute("SELECT COUNT(*) FROM user_role WHERE is_selected = 1")
        selected_count = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"\n✅ Миграция завершена. Отмечено ролей: {selected_count}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        conn.rollback()
        conn.close()

def migrate_add_selected_role():
    """Добавление поля selected_role и установка для последних ролей"""
    print("\n🔄 МИГРАЦИЯ: Добавление поля selected_role")
    print("="*60)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Нет подключения к БД")
        return
    
    try:
        cursor = conn.cursor()
        
        # Проверяем, есть ли уже поле selected_role
        cursor.execute("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'user_role' AND COLUMN_NAME = 'selected_role'
        """)
        
        if cursor.fetchone()[0] == 0:
            print("📝 Добавляем поле selected_role...")
            cursor.execute("ALTER TABLE user_role ADD selected_role VARCHAR(50) NULL")
            print("✅ Поле добавлено")
        else:
            print("✅ Поле selected_role уже существует")
        
        # Сбрасываем все selected_role
        cursor.execute("UPDATE user_role SET selected_role = NULL")
        
        # Для каждого пользователя выбираем последнюю роль и помечаем её
        cursor.execute("""
            SELECT ur.id_user, MAX(ur.ID) as last_id, CAST(r.name AS NVARCHAR(MAX)) as role_name
            FROM user_role ur
            JOIN roles r ON ur.id_role = r.ID
            GROUP BY ur.id_user, CAST(r.name AS NVARCHAR(MAX))
        """)
        
        users = cursor.fetchall()
        
        for user_id, last_id, role_name in users:
            cursor.execute("""
                UPDATE user_role 
                SET selected_role = ? 
                WHERE ID = ?
            """, (role_name, last_id))
            print(f"   Пользователь {user_id}: отмечена роль '{role_name}' (ID записи {last_id})")
        
        conn.commit()
        
        # Проверяем результат
        cursor.execute("SELECT COUNT(*) FROM user_role WHERE selected_role IS NOT NULL")
        selected_count = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"\n✅ Миграция завершена. Отмечено ролей: {selected_count}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        conn.rollback()
        conn.close()

def check_selected_roles():
    """Проверка выбранных ролей пользователей"""
    conn = get_db_connection()
    if not conn:
        print("❌ Нет подключения к БД")
        return
    
    try:
        cursor = conn.cursor()
        
        print("\n🔍 ПРОВЕРКА ВЫБРАННЫХ РОЛЕЙ")
        print("="*60)
        
        # Проверяем наличие поля
        cursor.execute("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'user_role' AND COLUMN_NAME = 'selected_role'
        """)
        
        if cursor.fetchone()[0] == 0:
            print("❌ Поле selected_role отсутствует!")
            conn.close()
            return
        
        # Получаем всех пользователей
        cursor.execute("SELECT ID, nickname, name, surname FROM users")
        users = cursor.fetchall()
        
        print(f"\n📋 Проверка пользователей:")
        for user_id, nickname, name, surname in users:
            # Получаем все роли пользователя
            cursor.execute("""
                SELECT DISTINCT CAST(r.name AS NVARCHAR(MAX)) as role_name
                FROM user_role ur
                JOIN roles r ON ur.id_role = r.ID
                WHERE ur.id_user = ?
            """, (user_id,))
            
            roles = [row[0] for row in cursor.fetchall()]
            
            # Получаем выбранную роль
            cursor.execute("""
                SELECT TOP 1 selected_role
                FROM user_role
                WHERE id_user = ? AND selected_role IS NOT NULL
            """, (user_id,))
            
            selected = cursor.fetchone()
            selected_role = selected[0] if selected else "НЕ ВЫБРАНА"
            
            print(f"\n   👤 {name} {surname} (@{nickname}) ID: {user_id}")
            print(f"      Все роли: {', '.join(roles) if roles else 'нет'}")
            print(f"      Выбранная роль: {selected_role}")
            
            # Проверяем, есть ли выбранная роль в списке ролей
            if selected_role != "НЕ ВЫБРАНА" and selected_role not in roles:
                print(f"      ⚠️ ВНИМАНИЕ: Выбранная роль '{selected_role}' отсутствует в списке ролей!")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        conn.close()

def ban_user_console(user_id: int, admin_id: int = 1):
    """Бан пользователя через консоль"""
    print(f"\n🔨 БАН ПОЛЬЗОВАТЕЛЯ ID {user_id}")
    print("="*50)
    
    # Получаем информацию о пользователе
    user_info = get_user_info_db(user_id)
    if "error" in user_info:
        print(f"❌ Ошибка: {user_info['error']}")
        return user_info
    
    print(f"👤 Пользователь: {user_info['full_name']} (@{user_info['nickname']})")
    print(f"📊 Статус: {'✅ Активен' if not user_info['is_banned'] else '❌ УЖЕ ЗАБАНЕН'}")
    
    if user_info['is_banned']:
        print("\n⚠️  Пользователь уже забанен!")
        confirm = input("Снять бан? (y/n): ").strip().lower()
        if confirm == 'y':
            return unban_user_console(user_id, admin_id)
        return {"success": False, "message": "Операция отменена"}
    
    print(f"\n⚠️  ВНИМАНИЕ: Пользователь будет заблокирован!")
    print("   Он не сможет войти в систему и покупать билеты.")
    
    confirm = input(f"\n✅ Подтвердите бан (y/n): ").strip().lower()
    if confirm != 'y':
        return {"success": False, "message": "Отменено"}
    
    # Выполняем бан
    conn = get_db_connection()
    if not conn:
        return {"success": False, "error": "Нет подключения к БД"}
    
    try:
        cursor = conn.cursor()
        
        # Баним пользователя
        cursor.execute("""
            UPDATE users 
            SET is_ban = 1 
            WHERE ID = ?
        """, (user_id,))
        
        rows_updated = cursor.rowcount
        
        if rows_updated == 0:
            conn.close()
            return {"success": False, "error": f"Пользователь с ID {user_id} не найден"}
        
        # Записываем в логи
        try:
            cursor.execute("""
                IF OBJECT_ID('admin_actions', 'U') IS NOT NULL
                BEGIN
                    INSERT INTO admin_actions (admin_id, user_id, action_type, details, timestamp)
                    VALUES (?, ?, 'ban_user', 'Пользователь забанен', GETDATE())
                END
            """, (admin_id, user_id))
        except Exception as log_error:
            print(f"⚠️ Не удалось записать в логи: {log_error}")
        
        conn.commit()
        conn.close()
        
        print(f"\n✅ Пользователь {user_info['full_name']} успешно забанен!")
        
        return {
            "success": True,
            "message": f"Пользователь {user_id} забанен",
            "user_id": user_id,
            "banned_by": admin_id
        }
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return {"success": False, "error": str(e)}

def unban_user_console(user_id: int, admin_id: int = 1):
    """Снятие бана с пользователя"""
    print(f"\n🔓 СНЯТИЕ БАНА ПОЛЬЗОВАТЕЛЯ ID {user_id}")
    print("="*50)
    
    user_info = get_user_info_db(user_id)
    if "error" in user_info:
        print(f"❌ Ошибка: {user_info['error']}")
        return user_info
    
    print(f"👤 Пользователь: {user_info['full_name']} (@{user_info['nickname']})")
    print(f"📊 Статус: {'❌ Забанен' if user_info['is_banned'] else '✅ УЖЕ АКТИВЕН'}")
    
    if not user_info['is_banned']:
        print("\n⚠️  Пользователь не забанен!")
        return {"success": False, "message": "Пользователь не забанен"}
    
    confirm = input(f"\n✅ Подтвердите снятие бана (y/n): ").strip().lower()
    if confirm != 'y':
        return {"success": False, "message": "Отменено"}
    
    conn = get_db_connection()
    if not conn:
        return {"success": False, "error": "Нет подключения к БД"}
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE users 
            SET is_ban = 0 
            WHERE ID = ?
        """, (user_id,))
        
        # Записываем в логи
        try:
            cursor.execute("""
                IF OBJECT_ID('admin_actions', 'U') IS NOT NULL
                BEGIN
                    INSERT INTO admin_actions (admin_id, user_id, action_type, details, timestamp)
                    VALUES (?, ?, 'unban_user', 'Бан снят', GETDATE())
                END
            """, (admin_id, user_id))
        except:
            pass
        
        conn.commit()
        conn.close()
        
        print(f"\n✅ Бан снят с пользователя {user_info['full_name']}!")
        
        return {
            "success": True,
            "message": f"Бан снят с пользователя {user_id}",
            "user_id": user_id,
            "unbanned_by": admin_id
        }
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return {"success": False, "error": str(e)}

def list_banned_users():
    """Список забаненных пользователей"""
    print("\n🚫 СПИСОК ЗАБАНЕННЫХ ПОЛЬЗОВАТЕЛЕЙ")
    print("="*50)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Нет подключения к БД")
        return
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT ID, nickname, name, surname, mail, is_ban
            FROM users 
            WHERE is_ban = 1
            ORDER BY ID
        """)
        
        banned_users = cursor.fetchall()
        conn.close()
        
        if not banned_users:
            print("✅ Забаненных пользователей нет")
            return
        
        print(f"\n📋 Найдено забаненных: {len(banned_users)}")
        print("-" * 50)
        
        for user in banned_users:
            print(f"   ID: {user[0]}")
            print(f"   Пользователь: {user[2]} {user[3]} (@{user[1]})")
            print(f"   Email: {user[4]}")
            print("-" * 30)
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        conn.close()

def create_giveaway_tickets_console():
    """Создание билетов для розыгрыша через консоль"""
    print("\n🎫 СОЗДАНИЕ БИЛЕТОВ ДЛЯ РОЗЫГРЫША")
    print("="*50)
    
    party_id = input("Введите ID вечеринки: ").strip()
    if not party_id.isdigit():
        print("❌ ID должен быть числом")
        return
    
    count = input("Введите количество билетов [10]: ").strip() or "10"
    if not count.isdigit():
        print("❌ Количество должно быть числом")
        return
    
    admin_id = input("Ваш ID администратора [1]: ").strip() or "1"
    
    import requests
    try:
        response = requests.post(
            f"{API_URL}/api/admin/create-giveaway-tickets",
            json={
                "party_id": int(party_id),
                "count": int(count),
                "admin_id": int(admin_id)
            }
        )
        
        result = response.json()
        
        if result.get("success"):
            print(f"\n✅ {result['message']}")
            print(f"🎉 Вечеринка: {result['party_name']}")
            print(f"📊 Диапазон ID: от {result['id_range']['end']} до {result['id_range']['start']}")
            print(f"\n📝 Сгенерированные билеты:")
            for ticket in result['tickets']:
                print(f"   • Билет #{ticket['db_id']} (ID: {ticket['negative_id']})")
            
            print(f"\n📌 Теперь сгенерируйте QR-коды командой:")
            print(f"python generate_giveaway_qrs.py --party {party_id}")
        else:
            print(f"\n❌ Ошибка: {result.get('error')}")
            
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")



def main():
    """Основная функция консоли администратора"""
    print("\n" + "="*60)
    print("👋 ДОБРО ПОЖАЛОВАТЬ В КОНСОЛЬ АДМИНИСТРАТОРА!")
    print("="*60)
    print("Система управления пользователями Need for Party")
    print("="*60)
    
    while True:
        print_menu()
        
        try:
            choice = input("\n📝 Выберите действие (0-22): ").strip()
            
            if choice == '0':
                print("\n👋 Выход из программы...")
                break
            
            elif choice == '1':
                user_id = input("Введите ID пользователя: ").strip()
                if user_id.isdigit():
                    result = get_user_info_db(int(user_id))
                    if "error" in result:
                        print(f"\n❌ Ошибка: {result['error']}")
                    else:
                        print(f"\n✅ Информация о пользователе:")
                        print(f"   ID: {result['user_id']}")
                        print(f"   Имя: {result['full_name']}")
                        print(f"   Никнейм: @{result['nickname']}")
                        print(f"   Email: {result['email']}")
                        print(f"   Возраст: {result['age']}")
                        print(f"   Пол: {result['gender']}")
                        print(f"   Статус: {'✅ Активен' if not result['is_banned'] else '❌ Забанен'}")
                        print(f"   Верификация: {'✅ Пройдена' if result['is_verified'] else '❌ Не пройдена'}")
                        print(f"   Реферальный код: {result['refer_code']}")
                        print(f"   Пригласил: {result['refer_from'] or 'Не приглашен никем'}")
                        print(f"   Статистика:")
                        print(f"     • Рефералов: {result['stats']['referrals']}")
                        print(f"     • Билетов: {result['stats']['tickets']}")
                else:
                    print("❌ Ошибка: ID должен быть числом")
            
            elif choice == '2':
                user_id = input("Введите ID пользователя для верификации: ").strip()
                admin_id = input("Введите ваш ID администратора [1]: ").strip() or "1"
                
                if user_id.isdigit() and admin_id.isdigit():
                    result = verify_user_console(int(user_id), int(admin_id))
                    if result.get("success"):
                        print(f"✅ {result.get('message', 'Успешно')}")
                    else:
                        print(f"❌ {result.get('error', 'Неизвестная ошибка')}")
                else:
                    print("❌ Ошибка: ID должны быть числами")
            
            elif choice == '3':
                user_id = input("Введите ID пользователя: ").strip()
                admin_id = input("Введите ID администратора [1]: ").strip() or "1"
                
                if user_id.isdigit() and admin_id.isdigit():
                    result = assign_role_console(int(user_id), int(admin_id))
                    if result.get("success"):
                        print(f"✅ {result.get('message', 'Успешно')}")
                    else:
                        print(f"❌ {result.get('error', 'Неизвестная ошибка')}")
                else:
                    print("❌ Ошибка: ID должны быть числами")
            
            elif choice == '4':
                user_id = input("Введите ID пользователя: ").strip()
                if user_id.isdigit():
                    result = check_roles_console(int(user_id))
                    if not result.get("success"):
                        print(f"❌ {result.get('error', 'Неизвестная ошибка')}")
                else:
                    print("❌ Ошибка: ID должен быть числом")
            
            elif choice == '5':
                user_id = input("Введите ID пользователя: ").strip()
                if user_id.isdigit():
                    result = get_user_roles_console(int(user_id))
                    if not result.get("success"):
                        print(f"❌ {result.get('error', 'Неизвестная ошибка')}")
                else:
                    print("❌ Ошибка: ID должен быть числом")
            
            elif choice == '6':
                user_id = input("Введите ID пользователя для добавления роли: ").strip()
                admin_id = input("Введите ID администратора [1]: ").strip() or "1"
                
                if user_id.isdigit() and admin_id.isdigit():
                    result = add_specific_role_console(int(user_id), int(admin_id))
                    if result.get("success"):
                        print(f"✅ {result.get('message', 'Успешно')}")
                    else:
                        print(f"❌ {result.get('error', 'Неизвестная ошибка')}")
                else:
                    print("❌ Ошибка: ID должны быть числами")
            
            elif choice == '7':
                user_id = input("Введите ID пользователя для удаления роли: ").strip()
                admin_id = input("Введите ID администратора [1]: ").strip() or "1"
                
                if user_id.isdigit() and admin_id.isdigit():
                    result = remove_specific_role_console(int(user_id), int(admin_id))
                    if result.get("success"):
                        print(f"✅ {result.get('message', 'Успешно')}")
                    else:
                        print(f"❌ {result.get('error', 'Неизвестная ошибка')}")
                else:
                    print("❌ Ошибка: ID должны быть числами")
            
            elif choice == '8':
                user_id = input("Введите ID пользователя для выбора роли: ").strip()
                if user_id.isdigit():
                    result = select_role_for_user_console(int(user_id))
                    if result.get("success"):
                        print(f"✅ {result.get('message', 'Успешно')}")
                        
                        print(f"\n🔄 Загружаем обновленные роли пользователя...")
                        roles_result = RoleManager.get_user_roles(int(user_id))
                        if roles_result.get("success"):
                            print(f"   Выбранная роль: {roles_result.get('selected_role', 'Не выбрана')}")
                            print(f"   Все роли: {', '.join(roles_result.get('all_roles', []))}")
                    else:
                        print(f"❌ {result.get('error', 'Неизвестная ошибка')}")
                else:
                    print("❌ Ошибка: ID должен быть числом")
            
            elif choice == '9':
                user_id = input("Введите ID пользователя для выдачи всех ролей: ").strip()
                admin_id = input("Введите ID администратора [1]: ").strip() or "1"
                
                if user_id.isdigit() and admin_id.isdigit():
                    result = assign_all_roles_console(int(user_id), int(admin_id))
                    if result.get("success"):
                        print(f"✅ {result.get('message', 'Успешно')}")
                    else:
                        print(f"❌ {result.get('error', 'Неизвестная ошибка')}")
                else:
                    print("❌ Ошибка: ID должны быть числами")
            
            elif choice == '10':
                user_id = input("Введите ID пользователя: ").strip()
                if user_id.isdigit():
                    result = get_user_stats(int(user_id))
                    if not result.get("success"):
                        print(f"❌ {result.get('error', 'Неизвестная ошибка')}")
                else:
                    print("❌ Ошибка: ID должен быть числом")
            
            elif choice == '11':
                result = view_all_system_roles()
                if not result.get("success"):
                    print(f"❌ {result.get('error', 'Неизвестная ошибка')}")
            
            elif choice == '12':
                user_id = input("Введите ID пользователя для исправления ролей: ").strip()
                if user_id.isdigit():
                    result = fix_user_roles(int(user_id))
                    if result.get("success"):
                        print(f"✅ {result.get('message', 'Успешно')}")
                    else:
                        print(f"❌ {result.get('error', 'Неизвестная ошибка')}")
                else:
                    print("❌ Ошибка: ID должен быть числом")
            
            elif choice == '13':
                user_id = input("Введите ID пользователя для очистки дубликатов: ").strip()
                if user_id.isdigit():
                    result = clean_user_duplicate_roles(int(user_id))
                    if result.get("success"):
                        print(f"✅ {result.get('message', 'Успешно')}")
                    else:
                        print(f"❌ {result.get('error', 'Неизвестная ошибка')}")
                else:
                    print("❌ Ошибка: ID должен быть числом")
            
            elif choice == '14':
                confirm = input("\n⚠️  Это удалит ВСЕ дубликаты ролей в системе. Продолжить? (y/n): ").strip().lower()
                if confirm == 'y':
                    result = clean_all_duplicate_roles()
                    if result.get("success"):
                        print(f"✅ {result.get('message', 'Успешно')}")
                    else:
                        print(f"❌ {result.get('error', 'Неизвестная ошибка')}")
            
            elif choice == '15':
                user_id = input("Введите ID пользователя: ").strip()
                if user_id.isdigit():
                    result = force_legend_check(int(user_id))
                    if result.get("success"):
                        print(f"✅ {result.get('message', 'Успешно')}")
                    else:
                        print(f"❌ {result.get('error', 'Неизвестная ошибка')}")
                else:
                    print("❌ Ошибка: ID должен быть числом")
            
            elif choice == '16':
                user_id = input("Введите ID пользователя: ").strip()
                if user_id.isdigit():
                    debug_user_roles_full(int(user_id))
                else:
                    print("❌ Ошибка: ID должен быть числом")
            
            elif choice == '17':
                user_id = input("Введите ID пользователя: ").strip()
                if user_id.isdigit():
                    role_name = input("Введите название роли (Enter для сброса всех): ").strip()
                    result = reset_selected_role(int(user_id), role_name if role_name else None)
                    if result.get("success"):
                        print(f"✅ {result.get('message', 'Успешно')}")
                    else:
                        print(f"❌ {result.get('error', 'Неизвестная ошибка')}")
                else:
                    print("❌ Ошибка: ID должен быть числом")
            
            elif choice == '18':
                user_id = input("Введите ID пользователя: ").strip()
                if user_id.isdigit():
                    role_name = input("Введите название роли для приоритета: ").strip()
                    result = fix_role_order(int(user_id), role_name if role_name else None)
                    if result.get("success"):
                        print(f"✅ {result.get('message', 'Успешно')}")
                    else:
                        print(f"❌ {result.get('error', 'Неизвестная ошибка')}")
                else:
                    print("❌ Ошибка: ID должен быть числом")
            
            elif choice == '19':
                check_parties_in_db()
            
            elif choice == '20':
                check_exact_role_names()
            
            elif choice == '21':
                view_verification_queue()
            
            elif choice == '22':
                user_id = input("Введите ID пользователя: ").strip()
                admin_id = input("Ваш ID администратора [1]: ").strip() or "1"
                if user_id.isdigit() and admin_id.isdigit():
                    view_user_document(int(user_id), int(admin_id))
                else:
                    print("❌ Ошибка: ID должны быть числами")

            elif choice == '23':
                user_id = input("Введите ID пользователя: ").strip()
                admin_id = input("Введите ID администратора [1]: ").strip() or "1"
                if user_id.isdigit() and admin_id.isdigit():
                    result = add_all_missing_roles(int(user_id), int(admin_id))
                    if result.get("success"):
                        print(f"✅ {result.get('message', 'Успешно')}")
                else:
                    print("❌ Ошибка: ID должны быть числами")

            elif choice == '24':
                user_id = input("Введите ID пользователя: ").strip()
                if user_id.isdigit():
                    check_user_roles_simple(int(user_id))
                else:
                    print("❌ Ошибка: ID должен быть числом")

            elif choice == '25':
                user_id = input("Введите ID пользователя: ").strip()
                if user_id.isdigit():
                    force_add_all_roles(int(user_id))
                else:
                    print("❌ Ошибка: ID должен быть числом")

            elif choice == '27':
                clean_all_user_roles()
            
            elif choice == '28':
                user_id = input("Введите ID пользователя для бана: ").strip()
                admin_id = input("Ваш ID администратора [1]: ").strip() or "1"
                if user_id.isdigit() and admin_id.isdigit():
                    result = ban_user_console(int(user_id), int(admin_id))
                else:
                    print("❌ Ошибка: ID должны быть числами")

            elif choice == '29':
                user_id = input("Введите ID пользователя для снятия бана: ").strip()
                admin_id = input("Ваш ID администратора [1]: ").strip() or "1"
                if user_id.isdigit() and admin_id.isdigit():
                    result = unban_user_console(int(user_id), int(admin_id))
                else:
                    print("❌ Ошибка: ID должны быть числами")

            elif choice == '30':
                list_banned_users()

            elif choice == '31':
                create_giveaway_tickets_console()

            elif choice == '32':
                party_id = input("Введите ID вечеринки: ").strip()
                if party_id.isdigit():
                    import requests
                    try:
                        response = requests.get(f"{API_URL}/api/admin/giveaway-status/{party_id}")
                        result = response.json()
                        
                        if result.get("success"):
                            print(f"\n📊 СТАТИСТИКА РОЗЫГРЫША")
                            print("="*50)
                            print(f"Всего билетов: {result['statistics']['total']}")
                            print(f"Доступно: {result['statistics']['available']}")
                            print(f"Активировано: {result['statistics']['claimed']}")
                            
                            if result['activated']:
                                print(f"\n👥 Активировали:")
                                for act in result['activated']:
                                    print(f"   • {act['user']} - {act['activated_at'][:10]}")
                        else:
                            print(f"❌ Ошибка: {result.get('error')}")
                    except Exception as e:
                        print(f"❌ Ошибка: {e}")
                else:
                    print("❌ ID должен быть числом")
            
            else:
                print("❌ Неверный выбор. Попробуйте снова.")
            
            if choice != '0':
                input("\n⏎ Нажмите Enter для продолжения...")
        
        except KeyboardInterrupt:
            print("\n\n👋 Выход из программы...")
            break
        except Exception as e:
            print(f"\n❌ Неожиданная ошибка: {e}")
            import traceback
            traceback.print_exc()
            input("\n⏎ Нажмите Enter для продолжения...")

if __name__ == "__main__":
    main()