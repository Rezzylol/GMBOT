import telebot
from telebot import types
from constants import API_KEY

bot = telebot.TeleBot(API_KEY)

@bot.message_handler(commands=["start"])
def send_help_message(msg):
    bot.reply_to(msg, "omg haiiiii :3c")


@bot.message_handler(commands=["goodmorning"])
def send_help_message(msg):
    bot.reply_to(msg, f"Good Morning! {msg.from_user.first_name} youve checked in 0/0")

@bot.message_handler(func=lambda msg: msg.text == "good morning")
def send_multi_message(msg):
    bot.reply_to(msg, f"Good Morning! {msg.from_user.first_name} youve checked in 0/0")

@bot.message_handler(func=lambda msg: msg.text == "gm")
def send_multi_message(msg):
    bot.reply_to(msg, f"Good Morning! {msg.from_user.first_name} youve checked in 0/0")

@bot.message_handler(func=lambda msg: msg.text == "Good Morning")
def send_multi_message(msg):
    bot.reply_to(msg, f"Good Morning! {msg.from_user.first_name} youve checked in 0/0")

@bot.message_handler(func=lambda msg: msg.text == "Good morning")
def send_multi_message(msg):
    bot.reply_to(msg, f"Good Morning! {msg.from_user.first_name} youve checked in 0/0")

@bot.message_handler(func=lambda msg: msg.text == "GM")
def send_multi_message(msg):
    bot.reply_to(msg, f"Good Morning! {msg.from_user.first_name} youve checked in 0/0")


bot.polling()


#daily check in