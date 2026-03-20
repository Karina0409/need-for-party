# encryption.py
from cryptography.fernet import Fernet
import base64
import os
import hashlib
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class EncryptionManager:
    """Менеджер для шифрования всех чувствительных данных"""
    
    def __init__(self, key_file='encryption.key'):
        self.key_file = key_file
        self.key = self._get_or_create_key()
        self.cipher = Fernet(self.key)
    
    def _get_or_create_key(self):
        """Получение или создание ключа шифрования"""
        if os.path.exists(self.key_file):
            with open(self.key_file, 'rb') as f:
                return f.read()
        
        # Создаем новый ключ
        key = Fernet.generate_key()
        with open(self.key_file, 'wb') as f:
            f.write(key)
        
        # Устанавливаем права доступа только для владельца (Unix)
        try:
            os.chmod(self.key_file, 0o600)
        except:
            pass
        
        return key
    
    def encrypt_data(self, data: bytes) -> bytes:
        """Шифрование данных"""
        try:
            # Добавляем временную метку для дополнительной защиты
            timestamp = datetime.now().isoformat().encode()
            data_with_timestamp = data + b'||' + timestamp
            return self.cipher.encrypt(data_with_timestamp)
        except Exception as e:
            print(f"❌ Ошибка шифрования: {e}")
            return None
    
    def decrypt_data(self, encrypted_data: bytes) -> bytes:
        """Дешифрование данных"""
        try:
            decrypted = self.cipher.decrypt(encrypted_data)
            # Отделяем данные от временной метки
            parts = decrypted.split(b'||')
            return parts[0]
        except Exception as e:
            print(f"❌ Ошибка дешифрования: {e}")
            return None
    
    def encrypt_string(self, text: str) -> str:
        """Шифрование строки (возвращает base64)"""
        if not text:
            return None
        encrypted = self.encrypt_data(text.encode('utf-8'))
        return base64.b64encode(encrypted).decode('utf-8') if encrypted else None
    
    def decrypt_string(self, encrypted_b64: str) -> str:
        """Дешифрование строки из base64"""
        if not encrypted_b64:
            return None
        try:
            encrypted = base64.b64decode(encrypted_b64.encode('utf-8'))
            decrypted = self.decrypt_data(encrypted)
            return decrypted.decode('utf-8') if decrypted else None
        except:
            return None

# Создаем глобальный экземпляр для использования во всем приложении
encryption_manager = EncryptionManager()

# Для обратной совместимости оставляем старые функции
def encrypt_document(document_data: bytes) -> bytes:
    return encryption_manager.encrypt_data(document_data)

def decrypt_document(encrypted_data: bytes) -> bytes:
    return encryption_manager.decrypt_data(encrypted_data)