import telebot
from telebot import types
from constants import API_KEY
import requests
import os
from datetime import date
import time

bot = telebot.TeleBot(API_KEY)

@bot.message_handler(commands=["start"])
def send_help_message(msg):
    bot.reply_to(msg, "omg haiiiii :3c")

import datetime


# Bot uptime
bot_inception_date = datetime.date.today()

# log file where login timestamps and counts will be stored
log_file = 'login_log.txt'

#creates log file

if not os.path.exists(log_file):
    with open(log_file, "w") as f:
        pass

# Define a function to log the login
def log_login(user_id):
    today = datetime.date.today()
    with open(log_file, 'r') as f:
        lines = f.readlines()
        for line in lines:
            date_str, uid, logins = line.strip().split(':')
            log_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            if int(uid) == user_id and log_date == today:
                # User already logged in today
                return int(logins)
    
    with open(log_file, 'a') as f:
        f.write(f'{today}: {user_id}: 1\n')
    return 1

# function to calculate the days since bot inception
def days_since_inception():
    current_date = datetime.date.today()
    delta = current_date - bot_inception_date
    return delta.days

# /start command
@bot.message_handler(commands=['goodmorning'])
def start(message):
    user_id = message.from_user.id
    logins = log_login(user_id)
    days_since = days_since_inception()
    bot.reply_to(message, f"Good Morning, {message.from_user.first_name}! You've checked in {logins}/{days_since}.")

# Check logins
@bot.message_handler(commands=['logins'])
def display_logins(message):
    with open(log_file, 'r') as f:
        log_contents = f.read()
    bot.reply_to(message, f'Login Log:\n{log_contents}')


#old auto responses

@bot.message_handler(func=lambda msg: msg.text == "good morning")
def send_multi_message(msg):
    bot.reply_to(msg, f"Good morning! dont forget to check in with /goodmorning")

@bot.message_handler(func=lambda msg: msg.text == "gm")
def send_multi_message(msg):
    bot.reply_to(msg, f"Good morning! dont forget to check in with /goodmorning")

@bot.message_handler(func=lambda msg: msg.text == "Good Morning")
def send_multi_message(msg):
    bot.reply_to(msg, f"Good morning! dont forget to check in with /goodmorning")

@bot.message_handler(func=lambda msg: msg.text == "Good morning")
def send_multi_message(msg):
    bot.reply_to(msg, f"Good morning! dont forget to check in with /goodmorning")

@bot.message_handler(func=lambda msg: msg.text == "GM")
def send_multi_message(msg):
    bot.reply_to(msg, f"Good morning! dont forget to check in with /goodmorning")


bot.polling()



