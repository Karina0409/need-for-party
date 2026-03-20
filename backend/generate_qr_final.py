# generate_qr_final.py
import os
import qrcode
from datetime import datetime
import argparse
from db_config import get_db_connection

def main():
    party_id = 7  # Можете изменить на нужный ID
    
    print(f"\n🎫 Генерация QR-кодов для вечеринки ID {party_id}")
    print("="*50)
    
    # Подключаемся к БД
    conn = get_db_connection()
    if not conn:
        print("❌ Нет подключения к БД")
        return
    
    cursor = conn.cursor()
    
    # Получаем название вечеринки
    cursor.execute("SELECT name FROM parties WHERE ID = ?", (party_id,))
    party = cursor.fetchone()
    if not party:
        print("❌ Вечеринка не найдена")
        conn.close()
        return
    
    party_name = party[0]
    print(f"📍 Вечеринка: {party_name}")
    
    # Получаем неактивированные билеты
    cursor.execute("""
        SELECT ID, id_user 
        FROM tickets 
        WHERE id_party = ? AND id_user < 0 AND date_sale IS NULL
        ORDER BY id_user
    """, (party_id,))
    
    tickets = cursor.fetchall()
    conn.close()
    
    print(f"🔍 Найдено билетов: {len(tickets)}")
    
    if not tickets:
        print("❌ Нет доступных билетов")
        return
    
    # Создаем папку для QR-кодов
    folder_name = f"giveaway_qr_party_{party_id}_{party_name.replace(' ', '_')}"
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
        print(f"📁 Создана папка: {folder_name}")
    
    print(f"\n🏗️  Генерация QR-кодов:")
    
    for ticket in tickets:
        ticket_id, negative_id = ticket
        
        # Создаем QR-код
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=2,
        )
        qr.add_data(str(negative_id))
        qr.make(fit=True)
        
        # Создаем изображение
        img = qr.make_image(fill_color="#00ccff", back_color="#0a0a1a")
        
        # Сохраняем
        filename = f"{folder_name}/ticket_{abs(negative_id):03d}.png"
        img.save(filename)
        
        print(f"  ✅ Билет #{negative_id} (DB ID: {ticket_id}) -> {filename}")
    
    print(f"\n✅ Готово! {len(tickets)} QR-кодов сохранены в папке {folder_name}")
    print(f"\n📌 Информация о билетах:")
    print(f"   • Всего билетов: {len(tickets)}")
    print(f"   • Диапазон ID: от {tickets[-1][1]} до {tickets[0][1]}")
    print(f"\n   Теперь вы можете:")
    print(f"   1. Распечатать QR-коды из папки")
    print(f"   2. Разместить их в городе")
    print(f"   3. При сканировании пользователь получит бесплатный билет")

if __name__ == "__main__":
    main()