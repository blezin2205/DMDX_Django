# import telebot
#
# bot = telebot.TeleBot("5584592059:AAHAJd0WPvh67xQIg0RUzbcZMBwgMQ2r6Cw")
#
# @bot.message_handler(commands=["start"])
# def start_command(message):
#      bot.send_message(message.chat.id, "Hello", parse_mode='html')
#
# bot.polling(none_stop=True)

# from aiogram import Bot, Dispatcher, executor, types
#
#
# bot = Bot(token="5584592059:AAHAJd0WPvh67xQIg0RUzbcZMBwgMQ2r6Cw")
# dp = Dispatcher(bot)
#
# @dp.message_handler(commands=['start', 'help'])
# async def send_welcome(message: types.Message):
#     await message.reply("Hi!\nI'm EchoBot!\nPowered by aiogram.")
#
#
# dp.start_polling(dp)
