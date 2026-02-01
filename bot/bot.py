import telebot
from telebot import types
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')  # БЕЗопасно из .env файла
WEB_APP_URL = "https://karina0409.github.io/need-for-party/"

bot = telebot.TeleBot(BOT_TOKEN)

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

if __name__ == "__main__":
    print("🤖 Бот запущен...")
    bot.polling(none_stop=True)