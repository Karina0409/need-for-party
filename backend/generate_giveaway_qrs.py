# generate_giveaway_qrs.py
import os
import qrcode
from datetime import datetime
import argparse
from PIL import Image, ImageDraw, ImageFont
import json

from db_config import get_db_connection

class GiveawayQRGenerator:
    def __init__(self):
        self.output_dir = "giveaway_qrs"
        self.create_output_dir()
    
    def create_output_dir(self):
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            print(f"✅ Создана папка: {self.output_dir}")
    
    def get_giveaway_tickets(self, party_id):
        """Получение неактивированных билетов розыгрыша"""
        conn = get_db_connection()
        if not conn:
            print("❌ Нет подключения к БД")
            return []
        
        try:
            cursor = conn.cursor()
            
            # Ищем билеты с отрицательным id_user и date_sale = NULL
            cursor.execute("""
                SELECT t.id, t.id_user, p.name
                FROM tickets t
                JOIN parties p ON t.id_party = p.ID
                WHERE t.id_party = ? AND t.id_user < 0 AND t.date_sale IS NULL
                ORDER BY t.id_user
            """, (party_id,))
            
            tickets = cursor.fetchall()
            conn.close()
            
            print(f"🔍 Найдено билетов: {len(tickets)}")
            return tickets
            
        except Exception as e:
            print(f"❌ Ошибка получения билетов: {e}")
            conn.close()
            return []
    
    def create_qr_for_ticket(self, ticket_db_id, negative_id, party_name, output_path):
        """Создание QR-кода для билета"""
        print(f"  🏗️  Создаю QR для билета #{negative_id}...")
        
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=2,
        )
        
        # В QR-коде храним отрицательный ID
        qr.add_data(str(negative_id))
        qr.make(fit=True)
        
        qr_img = qr.make_image(fill_color="#00ccff", back_color="#0a0a1a")
        qr_img = qr_img.convert('RGB')
        
        # Добавляем информацию под QR
        width, height = qr_img.size
        new_height = height + 120
        
        full_img = Image.new('RGB', (width, new_height), "#0a0a1a")
        full_img.paste(qr_img, (0, 0))
        
        try:
            draw = ImageDraw.Draw(full_img)
            try:
                font = ImageFont.truetype("arial.ttf", 14)
                small_font = ImageFont.truetype("arial.ttf", 12)
            except:
                font = ImageFont.load_default()
                small_font = ImageFont.load_default()
            
            draw.text((10, height + 10), f"🎫 БЕСПЛАТНЫЙ БИЛЕТ #{negative_id}", fill="white", font=font)
            draw.text((10, height + 35), f"🎉 {party_name[:30]}", fill="#a0a0ff", font=small_font)
            draw.text((10, height + 60), f"📅 Действует до: {datetime.now().strftime('%d.%m.%Y')}", fill="#8888cc", font=small_font)
            draw.text((10, height + 85), f"🔢 Код: {negative_id}", fill="#8888cc", font=small_font)
            
        except Exception as e:
            print(f"⚠️ Ошибка добавления текста: {e}")
        
        full_img.save(output_path, "PNG", quality=95)
        return output_path
    
    def generate_for_party(self, party_id):
        """Генерация QR-кодов для всех билетов розыгрыша"""
        print(f"\n🔍 Поиск билетов для вечеринки ID {party_id}...")
        
        tickets = self.get_giveaway_tickets(party_id)
        
        if not tickets:
            print(f"❌ Нет доступных билетов для вечеринки ID {party_id}")
            print("   Возможные причины:")
            print("   • Все билеты уже активированы")
            print("   • Билеты не были созданы")
            print("   • Неправильный ID вечеринки")
            return []
        
        print(f"\n✅ Найдено {len(tickets)} билетов для генерации")
        
        # Получаем название вечеринки
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM parties WHERE ID = ?", (party_id,))
        party_result = cursor.fetchone()
        if not party_result:
            print(f"❌ Вечеринка с ID {party_id} не найдена")
            conn.close()
            return []
        
        party_name = party_result[0]
        conn.close()
        
        # Создаем папку для вечеринки
        safe_name = party_name.replace(' ', '_').replace('"', '').replace("'", '')[:30]
        party_folder = f"{self.output_dir}/party_{party_id}_{safe_name}"
        
        if not os.path.exists(party_folder):
            os.makedirs(party_folder)
            print(f"📁 Создана папка: {party_folder}")
        
        generated = []
        print(f"\n🏗️  Генерация QR-кодов:")
        
        for ticket in tickets:
            ticket_db_id, negative_id, _ = ticket
            # Используем абсолютное значение для имени файла
            file_number = abs(negative_id)
            qr_path = f"{party_folder}/ticket_{file_number:03d}.png"
            
            self.create_qr_for_ticket(ticket_db_id, negative_id, party_name, qr_path)
            generated.append({
                "db_id": ticket_db_id,
                "negative_id": negative_id,
                "qr_file": os.path.basename(qr_path)
            })
            print(f"  ✅ QR для билета #{negative_id} сохранен")
        
        # Создаем файл с информацией
        info = {
            "party_id": party_id,
            "party_name": party_name,
            "generated_at": datetime.now().isoformat(),
            "total_tickets": len(generated),
            "tickets": generated
        }
        
        info_path = f"{party_folder}/info.json"
        with open(info_path, 'w', encoding='utf-8') as f:
            json.dump(info, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 Создан файл информации: {info_path}")
        
        return generated

def main():
    parser = argparse.ArgumentParser(description='Генератор QR-кодов для розыгрышей')
    parser.add_argument('--party', type=int, required=True, help='ID вечеринки')
    
    args = parser.parse_args()
    
    print(f"\n🎫 Генерация QR-кодов для вечеринки ID {args.party}")
    print("="*50)
    
    generator = GiveawayQRGenerator()
    tickets = generator.generate_for_party(args.party)
    
    if tickets:
        print(f"\n✅ УСПЕШНО сгенерировано {len(tickets)} QR-кодов!")
        print(f"📁 Папка с файлами: {generator.output_dir}")
        print(f"\n📌 Инструкция:")
        print("   1. Файлы PNG можно распечатать")
        print("   2. info.json содержит соответствие QR-кодов и билетов")
        print("   3. При сканировании QR автоматически активирует билет")
    else:
        print("\n❌ Не удалось сгенерировать QR-коды")
        print("   Проверьте:")
        print("   • Правильный ли ID вечеринки?")
        print("   • Созданы ли билеты через админ-консоль?")
        print("   • Не активированы ли уже все билеты?")

if __name__ == "__main__":
    main()