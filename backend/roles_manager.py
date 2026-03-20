"""
Менеджер ролей для Need for Party
Адаптировано для работы с типом TEXT в SQL Server
"""

from db_config import get_db_connection
from typing import Dict, List, Set
import logging
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RoleManager:
    """
    Управление ролями пользователей с учетом ограничений БД:
    - Поле 'name' в таблице roles имеет тип TEXT
    - Таблица user_role связывает пользователей и роли
    - Роли добавляются автоматически по условиям
    """
    
    # Маппинг правильных названий ролей на то, что в БД (исправляем опечатки)
    ROLE_MAPPINGS = {
        'Участник': 'Участник',
        'Рисковый': 'Рисковый',
        'Душа компании': 'Душа компании',
        'Весельчак': 'Весельчак',
        'Тусовщик': 'Тусовщик',
        'Ас тусовок': 'Ас тусовок',
        'Танцор': 'Танцор',
        'Ас танцпола': 'Ас танспола',  # Опечатка в БД!
        'Любитель выпить': 'Любитель выпить',
        'Глава бара': 'Глава бара',
        'Легенда': 'Легенда'
    }
    
    # Обратный маппинг (из БД в правильное название)
    REVERSE_MAPPINGS = {v: k for k, v in ROLE_MAPPINGS.items()}
    
    # Роли, которые может выдавать администратор
    ADMIN_ROLES = ['Танцор', 'Ас танцпола', 'Любитель выпить', 'Глава бара']
    
    # Роли для автоматического назначения по условиям
    AUTO_ROLES = ['Участник', 'Рисковый', 'Душа компании', 'Весельчак', 'Тусовщик', 'Ас тусовок', 'Легенда']
    
    # Добавьте список ролей только для админов (не показывать пользователям)
    ADMIN_ONLY_ROLES = ['Админ', 'Бармен', 'Диджей', 'Охрана', 'Организатор', 'Ведущий']

    @classmethod
    def _get_db_role_name(cls, display_name: str) -> str:
        """Получить название роли как оно хранится в БД"""
        return cls.ROLE_MAPPINGS.get(display_name, display_name)
    
    @classmethod
    def _get_display_name(cls, db_name: str) -> str:
        """Получить правильное название роли для отображения"""
        return cls.REVERSE_MAPPINGS.get(db_name, db_name)
    
    @classmethod
    def _get_role_id_by_name(cls, cursor, role_name: str) -> int:
        """Получить ID роли по названию (работает с типом TEXT)"""
        try:
            db_role_name = cls._get_db_role_name(role_name)
            cursor.execute("""
                SELECT ID FROM roles 
                WHERE CAST(name AS NVARCHAR(MAX)) = ?
            """, (db_role_name,))
            result = cursor.fetchone()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Ошибка получения ID роли '{role_name}': {e}")
            return None
    
    @classmethod
    def _get_role_name_by_id(cls, cursor, role_id: int) -> str:
        """Получить название роли по ID (работает с типом TEXT)"""
        try:
            cursor.execute("""
                SELECT CAST(name AS NVARCHAR(MAX)) 
                FROM roles 
                WHERE ID = ?
            """, (role_id,))
            result = cursor.fetchone()
            db_name = result[0] if result else None
            return cls._get_display_name(db_name) if db_name else None
        except Exception as e:
            logger.error(f"Ошибка получения названия роли ID {role_id}: {e}")
            return None
    
    @classmethod
    def _user_has_role(cls, cursor, user_id: int, role_name: str) -> bool:
        """Проверить, есть ли у пользователя указанная роль"""
        try:
            role_id = cls._get_role_id_by_name(cursor, role_name)
            if not role_id:
                return False
            
            cursor.execute("""
                SELECT 1 FROM user_role 
                WHERE id_user = ? AND id_role = ?
            """, (user_id, role_id))
            return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Ошибка проверки роли '{role_name}' у пользователя {user_id}: {e}")
            return False
    
    @classmethod
    def _get_user_role_ids(cls, cursor, user_id: int) -> List[int]:
        """Получить список ID ролей пользователя"""
        try:
            cursor.execute("""
                SELECT id_role FROM user_role 
                WHERE id_user = ?
            """, (user_id,))
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка получения ролей пользователя {user_id}: {e}")
            return []
    
    @classmethod
    def _get_user_role_names(cls, cursor, user_id: int) -> List[str]:
        """Получить список названий ролей пользователя"""
        role_ids = cls._get_user_role_ids(cursor, user_id)
        role_names = []
        
        for role_id in role_ids:
            role_name = cls._get_role_name_by_id(cursor, role_id)
            if role_name:
                role_names.append(role_name)
        
        return role_names
    
    @classmethod
    def _add_role_to_user(cls, cursor, user_id: int, role_name: str, admin_id: int = None) -> bool:
        """Добавить роль пользователю"""
        try:
            role_id = cls._get_role_id_by_name(cursor, role_name)
            if not role_id:
                logger.error(f"Роль '{role_name}' не найдена в БД")
                return False
            
            # Проверяем, есть ли уже эта роль
            if cls._user_has_role(cursor, user_id, role_name):
                logger.info(f"У пользователя {user_id} уже есть роль '{role_name}'")
                return False
            
            # Добавляем роль (БЕЗ assigned_by - такой колонки нет в БД!)
            cursor.execute("""
                INSERT INTO user_role (id_user, id_role) 
                VALUES (?, ?)
            """, (user_id, role_id))
            
            logger.info(f"✅ Добавлена роль '{role_name}' пользователю {user_id}" + 
                    (f" (выдана админом {admin_id})" if admin_id else " (автоматически)"))
            return True
            
        except Exception as e:
            logger.error(f"Ошибка добавления роли '{role_name}' пользователю {user_id}: {e}")
            return False
    
    @classmethod
    def check_and_update_roles(cls, user_id: int) -> Dict:
        """
        Проверяет и обновляет роли пользователя автоматически по условиям
        """
        conn = get_db_connection()
        if not conn:
            return {"success": False, "error": "Нет подключения к БД"}
        
        try:
            cursor = conn.cursor()
            added_roles = []
            
            # Получаем текущие роли пользователя
            current_roles = cls._get_user_role_names(cursor, user_id)
            logger.info(f"Пользователь {user_id}: текущие роли: {current_roles}")
            
            # 1. Если нет ни одной роли - добавляем 'Участник'
            if not current_roles:
                logger.info(f"У пользователя {user_id} нет ролей. Добавляем 'Участник'...")
                if cls._add_role_to_user(cursor, user_id, 'Участник'):
                    added_roles.append('Участник')
                    conn.commit()
                    current_roles = ['Участник']
            
            # 2. Проверяем верификацию для роли 'Рисковый' - ТОЛЬКО если верифицирован!
            cursor.execute("SELECT is_verificated FROM users WHERE ID = ?", (user_id,))
            user = cursor.fetchone()
            
            # ВАЖНО: Добавляем роль 'Рисковый' ТОЛЬКО если пользователь верифицирован
            if user and user[0] == 1 and 'Рисковый' not in current_roles:
                if cls._add_role_to_user(cursor, user_id, 'Рисковый'):
                    added_roles.append('Рисковый')
                    logger.info(f"✅ Пользователь {user_id} верифицирован, добавлена роль 'Рисковый'")
            
            # ... остальные проверки ...
            
            # Сохраняем изменения
            if added_roles:
                conn.commit()
                logger.info(f"Пользователь {user_id}: добавлены роли: {added_roles}")
            
            conn.close()
            
            return {
                "success": True,
                "user_id": user_id,
                "added_roles": added_roles,
                "current_roles": current_roles
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления ролей: {e}")
            if conn:
                conn.close()
            return {"success": False, "error": str(e)}
    
    @classmethod
    def assign_admin_role(cls, user_id: int, role_name: str, admin_id: int) -> Dict:
        """
        Назначение роли администратором.
        Доступные роли: Танцор, Ас танцпола, Любитель выпить, Глава бара
        """
        # Исправляем название роли (учитываем опечатку в БД)
        db_role_name = role_name
        if role_name == 'Ас танцпола':
            db_role_name = 'Ас танспола'
        
        if role_name not in cls.ADMIN_ROLES:
            return {
                "success": False, 
                "error": f"Эту роль может выдавать только администратор. Доступные роли: {', '.join(cls.ADMIN_ROLES)}"
            }
        
        conn = get_db_connection()
        if not conn:
            return {"success": False, "error": "Нет подключения к БД"}
        
        try:
            cursor = conn.cursor()
            
            # Проверяем, есть ли уже эта роль
            role_id = cls._get_role_id_by_name(cursor, db_role_name)
            if not role_id:
                conn.close()
                return {"success": False, "error": f"Роль '{role_name}' не найдена в БД"}
            
            cursor.execute("SELECT 1 FROM user_role WHERE id_user = ? AND id_role = ?", (user_id, role_id))
            if cursor.fetchone():
                conn.close()
                return {"success": False, "error": f"Роль '{role_name}' уже есть у пользователя"}
            
            # Добавляем роль
            cursor.execute("INSERT INTO user_role (id_user, id_role) VALUES (?, ?)", (user_id, role_id))
            
            # Записываем в логи администратора (с проверкой существования таблицы)
            try:
                cursor.execute("""
                    IF OBJECT_ID('admin_actions', 'U') IS NOT NULL
                    BEGIN
                        INSERT INTO admin_actions (admin_id, user_id, action_type, details, timestamp)
                        VALUES (?, ?, 'assign_role', ?, GETDATE())
                    END
                """, (admin_id, user_id, f"Назначена роль: {role_name}"))
            except Exception as log_error:
                logger.warning(f"Не удалось записать в логи администратора: {log_error}")
            
            conn.commit()
            
            # Проверяем автоматические роли (может добавиться Легенда)
            cls.check_and_update_roles(user_id)
            
            conn.close()
            
            return {
                "success": True,
                "message": f"Роль '{role_name}' успешно назначена пользователю {user_id}",
                "user_id": user_id,
                "role": role_name,
                "assigned_by": admin_id
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка назначения роли администратором: {e}")
            if conn:
                conn.rollback()
                conn.close()
            return {"success": False, "error": str(e)}
    
    @classmethod
    def verify_user(cls, user_id: int, admin_id: int) -> Dict:
        """Верификация пользователя администратором"""
        conn = get_db_connection()
        if not conn:
            return {"success": False, "error": "Нет подключения к БД"}
        
        try:
            cursor = conn.cursor()
            
            # Верифицируем пользователя
            cursor.execute("""
                UPDATE users 
                SET is_verificated = 1 
                WHERE ID = ?
            """, (user_id,))
            
            rows_updated = cursor.rowcount
            
            if rows_updated == 0:
                conn.close()
                return {"success": False, "error": f"Пользователь с ID {user_id} не найден"}
            
            # Записываем в логи
            try:
                cursor.execute("""
                    INSERT INTO admin_actions (admin_id, user_id, action_type, details, timestamp)
                    VALUES (?, ?, 'verify_user', 'Верификация аккаунта', GETDATE())
                """, (admin_id, user_id))
            except Exception as log_error:
                logger.warning(f"Не удалось записать в логи: {log_error}")
            
            conn.commit()
            
            # Проверяем роли (добавится "Рисковый" если верификация прошла)
            role_result = cls.check_and_update_roles(user_id)
            
            conn.close()
            
            return {
                "success": True,
                "message": f"Пользователь {user_id} успешно верифицирован",
                "user_id": user_id,
                "verified_by": admin_id,
                "role_update": role_result
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка верификации пользователя {user_id}: {e}")
            if conn:
                conn.rollback()
                conn.close()
            return {"success": False, "error": str(e)}
    
    @classmethod
    def get_user_roles(cls, user_id: int) -> Dict:
        """Получение всех ролей пользователя - Легенда НЕ переопределяет выбор"""
        conn = get_db_connection()
        if not conn:
            return {"success": False, "error": "Нет подключения к БД"}
        
        try:
            cursor = conn.cursor()
            
            # Получаем все роли в порядке добавления
            cursor.execute("""
                SELECT ur.ID, CAST(r.name AS NVARCHAR(MAX)) as role_name
                FROM user_role ur
                JOIN roles r ON ur.id_role = r.ID
                WHERE ur.id_user = ?
                ORDER BY ur.ID DESC
            """, (user_id,))
            
            all_records = cursor.fetchall()
            
            # Собираем уникальные роли
            unique_roles = set()
            all_roles = []
            admin_roles = []
            auto_roles = []
            
            admin_given = ['Танцор', 'Ас танцпола', 'Любитель выпить', 'Глава бара']
            admin_only = ['Админ', 'Бармен', 'Диджей', 'Охрана', 'Организатор', 'Ведущий']
            
            # ВАЖНО: Выбранная роль - первая НЕ-ЛЕГЕНДА в списке
            selected_role = None
            
            for record_id, role_name in all_records:
                if not role_name:
                    continue
                    
                role_name = str(role_name).strip()
                if role_name == 'Ас танспола':
                    role_name = 'Ас танцпола'
                
                # Пропускаем админские роли
                if role_name in admin_only:
                    continue
                
                # Добавляем в уникальные
                if role_name not in unique_roles:
                    unique_roles.add(role_name)
                    all_roles.append(role_name)
                    
                    if role_name in admin_given:
                        admin_roles.append(role_name)
                    elif role_name != 'Легенда':
                        auto_roles.append(role_name)
                
                # ВАЖНО: Выбираем ПЕРВУЮ НЕ-ЛЕГЕНДУ
                if selected_role is None and role_name != 'Легенда' and role_name not in admin_only:
                    selected_role = role_name
            
            # Если нет выбранной роли, но есть Легенда
            if selected_role is None and 'Легенда' in unique_roles:
                selected_role = 'Легенда'
            
            conn.close()
            
            return {
                "success": True,
                "user_id": user_id,
                "all_roles": all_roles,
                "auto_roles": sorted(auto_roles),
                "admin_roles": sorted(admin_roles),
                "total_count": len(all_roles),
                "has_legend": 'Легенда' in unique_roles,
                "selected_role": selected_role,
                "has_custom_selection": selected_role is not None and selected_role != 'Легенда'
            }
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            if conn:
                conn.close()
            return {"success": False, "error": str(e)}
        
    @classmethod
    def get_all_roles_info(cls) -> Dict:
        """Получить информацию обо всех ролях в системе"""
        conn = get_db_connection()
        if not conn:
            return {"success": False, "error": "Нет подключения к БД"}
        
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT ID, CAST(name AS NVARCHAR(MAX)) as name 
                FROM roles 
                ORDER BY CAST(name AS NVARCHAR(MAX))
            """)
            
            roles = []
            for row in cursor.fetchall():
                role_id, db_name = row
                display_name = cls._get_display_name(db_name)
                roles.append({
                    "id": role_id,
                    "db_name": db_name,
                    "display_name": display_name,
                    "type": "admin" if display_name in cls.ADMIN_ROLES else "auto"
                })
            
            conn.close()
            
            return {
                "success": True,
                "total_roles": len(roles),
                "roles": roles
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения списка ролей: {e}")
            if conn:
                conn.close()
            return {"success": False, "error": str(e)}

# Тестирование при запуске файла
if __name__ == "__main__":
    print("🧪 Тестирование RoleManager...")
    
    # Тест 1: Получить все роли
    print("\n1. Получение всех ролей в системе:")
    all_roles = RoleManager.get_all_roles_info()
    if all_roles["success"]:
        for role in all_roles["roles"]:
            print(f"   ID {role['id']}: {role['db_name']} -> {role['display_name']} ({role['type']})")
    else:
        print(f"   ❌ Ошибка: {all_roles['error']}")
    
    # Тест 2: Получить роли пользователя 1
    print("\n2. Роли пользователя ID 1:")
    user_roles = RoleManager.get_user_roles(1)
    if user_roles["success"]:
        print(f"   Все роли: {user_roles['all_roles']}")
        print(f"   Автоматические: {user_roles['auto_roles']}")
        print(f"   От админа: {user_roles['admin_roles']}")
    else:
        print(f"   ❌ Ошибка: {user_roles['error']}")
    
    # Тест 3: Проверить обновление ролей для пользователя 1
    print("\n3. Проверка/обновление ролей пользователя ID 1:")
    update_result = RoleManager.check_and_update_roles(1)
    if update_result["success"]:
        print(f"   ✅ Успешно!")
        print(f"   Добавлены роли: {update_result.get('added_roles', [])}")
        print(f"   Всего ролей: {update_result.get('current_roles', [])}")
        print(f"   Посещений: {update_result.get('stats', {}).get('total_visits', 0)}")
        print(f"   Рефералов: {update_result.get('stats', {}).get('referral_count', 0)}")
    else:
        print(f"   ❌ Ошибка: {update_result['error']}")
    
    print("\n✅ Тестирование завершено")