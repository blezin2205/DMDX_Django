import telebot
from . import views
from .models import Supply

bot = telebot.TeleBot("5584592059:AAHAJd0WPvh67xQIg0RUzbcZMBwgMQ2r6Cw")


@bot.message_handler(commands=["start"])
def start_command(message):
    sup = Supply.objects.first()
    bot.send_message(message.chat.id, sup.name, parse_mode='html')

bot.polling(none_stop=True)
