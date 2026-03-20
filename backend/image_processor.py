# image_processor.py
"""
Модуль для обработки изображений документов:
- Очистка метаданных (EXIF, GPS и т.д.)
- Поддержка всех популярных форматов
- Оптимизация размера
- Конвертация в безопасный формат
"""

from PIL import Image
import io
import logging
import os
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Словарь поддерживаемых форматов и их MIME-типов
SUPPORTED_FORMATS = {
    'JPEG': ['.jpg', '.jpeg', '.jfif', '.jpe'],
    'PNG': ['.png'],
    'GIF': ['.gif'],
    'BMP': ['.bmp'],
    'TIFF': ['.tiff', '.tif'],
    'WEBP': ['.webp'],
    'HEIC': ['.heic', '.heif'],  # Формат iPhone
    'ICO': ['.ico']
}

def get_supported_formats_text():
    """Возвращает текст со списком поддерживаемых форматов для UI"""
    all_formats = []
    for format_name, extensions in SUPPORTED_FORMATS.items():
        all_formats.extend(extensions)
    return ', '.join(all_formats)

def sanitize_document_image(image_bytes, filename=None):
    """
    ПОЛНАЯ САНИТАРНАЯ ОБРАБОТКА ИЗОБРАЖЕНИЯ ДОКУМЕНТА
    
    Args:
        image_bytes (bytes): исходное изображение
        filename (str, optional): имя файла для определения формата
    
    Returns:
        bytes: очищенное изображение в формате JPEG
    """
    try:
        # Открываем изображение
        img = Image.open(io.BytesIO(image_bytes))
        
        # Логируем исходную информацию
        logger.info(f"Исходное изображение: формат={img.format}, режим={img.mode}, размер={img.size}")
        
        # Конвертируем в RGB (убираем альфа-канал, прозрачность и т.д.)
        if img.mode in ('RGBA', 'LA', 'P'):
            # Создаем белый фон
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            if img.mode == 'RGBA':
                # Для PNG с прозрачностью
                background.paste(img, mask=img.split()[3])
            else:
                background.paste(img)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Оптимизируем размер (максимум 2048px по большей стороне)
        max_size = 2048
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = tuple(int(dim * ratio) for dim in img.size)
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            logger.info(f"Изменен размер: {img.size}")
        
        # Сохраняем без метаданных в формате JPEG
        output = io.BytesIO()
        
        # Сохраняем с фиксированным качеством и БЕЗ метаданных
        img.save(
            output,
            format='JPEG',
            quality=85,
            optimize=True,
            progressive=False,
            exif=b''  # Пустой EXIF = полное удаление метаданных
        )
        
        cleaned_bytes = output.getvalue()
        
        # Логируем результат
        logger.info(f"Изображение обработано: {len(image_bytes)} -> {len(cleaned_bytes)} байт")
        
        return cleaned_bytes
        
    except Exception as e:
        logger.error(f"Ошибка обработки изображения: {e}")
        # В случае критической ошибки возвращаем None
        return None

def is_image_valid(image_bytes):
    """
    Проверка, является ли файл корректным изображением
    
    Args:
        image_bytes (bytes): данные для проверки
    
    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.verify()  # Проверяет целостность файла
        return True, None
    except Exception as e:
        return False, str(e)

def get_image_info(image_bytes):
    """
    Получение информации об изображении (без сохранения метаданных)
    
    Args:
        image_bytes (bytes): данные изображения
    
    Returns:
        dict: информация об изображении
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        return {
            'format': img.format,
            'mode': img.mode,
            'width': img.width,
            'height': img.height,
            'size': len(image_bytes)
        }
    except Exception as e:
        return {'error': str(e)}