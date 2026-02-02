import telebot
from telebot import types
import os
from dotenv import load_dotenv
import time

# Загружаем переменные окружения
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')  # БЕЗопасно из .env файла
WEB_APP_URL = f"https://karina0409.github.io/need-for-party/telegram_app.html?t={int(time.time())}"

bot = telebot.TeleBot(BOT_TOKEN)

current_version = int(time.time())  # Текущее время в секундах

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup()
    
    web_app = types.WebAppInfo(url=WEB_APP_URL)
    
    button = types.InlineKeyboardButton(
        text="🎮 Открыть Need for Party",
        web_app=web_app
    )
    markup.add(button)
    
    bot.send_message(
        message.chat.id,
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "Добро пожаловать в **Need for Party** 🎉\n\n"
        "Нажми кнопку ниже, чтобы открыть приложение",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['clear_cache'])
def clear_cache(message):
    bot.send_message(
        message.chat.id,
        "Очистка кэша WebApp...\n"
        "Пожалуйста, закройте и откройте бота заново."
    )


if __name__ == "__main__":
    print("🤖 Бот запущен...")
    bot.polling(none_stop=True)