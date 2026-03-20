# auth.py
import re
import hashlib
import base64
import os
import secrets
import string

class PasswordValidator:
    """Валидатор паролей с проверкой сложности"""
    
    def __init__(self):
        self.min_length = 8
        self.max_length = 72  # Ограничение bcrypt
        self.require_uppercase = True
        self.require_lowercase = True
        self.require_digits = True
        self.require_special = True
        
    def validate(self, password: str) -> tuple:
        """
        Проверка пароля на сложность
        Возвращает (is_valid, error_message)
        """
        if len(password) < self.min_length:
            return False, f"Пароль должен быть минимум {self.min_length} символов"
        
        if len(password) > self.max_length:
            return False, f"Пароль не может быть длиннее {self.max_length} символов"
        
        if self.require_uppercase and not re.search(r'[A-Z]', password):
            return False, "Пароль должен содержать хотя бы одну заглавную букву"
        
        if self.require_lowercase and not re.search(r'[a-z]', password):
            return False, "Пароль должен содержать хотя бы одну строчную букву"
        
        if self.require_digits and not re.search(r'\d', password):
            return False, "Пароль должен содержать хотя бы одну цифру"
        
        if self.require_special and not re.search(r'[!@#$%^&*(),.?":{}|<>\-_]', password):
            return False, "Пароль должен содержать хотя бы один специальный символ (!@#$%^&*()_-)"
                
        # Проверка на распространенные пароли
        common_passwords = ['password', '12345678', 'qwerty123', 'password123', 
                           'admin123', '123456789', 'qwerty12345', 'P@ssw0rd']
        if password.lower() in common_passwords:
            return False, "Этот пароль слишком распространен, выберите другой"
        
        return True, "Пароль надежный"
    
    def generate_secure_password(self, length=12):
        """Генерация надежного пароля"""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        while True:
            password = ''.join(secrets.choice(alphabet) for _ in range(length))
            is_valid, _ = self.validate(password)
            if is_valid:
                return password

def hash_password_secure(password: str) -> str:
    """
    Безопасное хеширование пароля с солью
    Использует PBKDF2 с 600,000 итерациями
    """
    # Генерируем случайную соль (32 байта)
    salt = os.urandom(32)
    
    # Хешируем пароль с солью (600,000 итераций - современный стандарт)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        600000,  # Увеличили количество итераций
        dklen=32
    )
    
    # Конвертируем в base64 для хранения в БД
    salt_b64 = base64.b64encode(salt).decode('utf-8')
    key_b64 = base64.b64encode(key).decode('utf-8')
    
    # Возвращаем соль и ключ вместе
    return f"{salt_b64}:{key_b64}"

def verify_password_secure(plain_password: str, stored_hash: str) -> bool:
    """Проверка пароля"""
    try:
        salt_b64, key_b64 = stored_hash.split(':')
        salt = base64.b64decode(salt_b64)
        stored_key = base64.b64decode(key_b64)
        
        key = hashlib.pbkdf2_hmac(
            'sha256',
            plain_password.encode('utf-8'),
            salt,
            600000,
            dklen=32
        )
        
        # Безопасное сравнение
        return secrets.compare_digest(key, stored_key)
        
    except Exception as e:
        print(f"❌ Ошибка проверки пароля: {e}")
        return False

# Создаем глобальный экземпляр валидатора
password_validator = PasswordValidator()