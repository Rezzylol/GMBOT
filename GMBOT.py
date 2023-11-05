import telebot
import os
import datetime

API_KEY = os.getenv('API_KEY')
bot = telebot.TeleBot(API_KEY)
log_file = 'login_log.txt'
bot_inception_date = datetime.date.today()

if not os.path.exists(log_file):
    with open(log_file, "w"):
        pass

def log_login(user_id):
    today = datetime.date.today()
    with open(log_file, 'r') as f:
        lines = f.readlines()
        for line in lines:
            date_str, uid, logins = line.strip().split(':')
            log_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            if int(uid) == user_id and log_date == today:
                return int(logins)
    
    with open(log_file, 'a') as f:
        f.write(f'{today}: {user_id}: 1\n')
    return 1

def days_since_inception():
    current_date = datetime.date.today()
    delta = current_date - bot_inception_date
    return delta.days

@bot.message_handler(commands=['start', 'goodmorning', 'logins'])
def handle_messages(message):
    user_id = message.from_user.id
    logins = log_login(user_id)
    days_since = days_since_inception()

    if message.text.lower() == '/start':
        bot.reply_to(message, "omg haiiiii :3c")
    elif message.text.lower() in ['/goodmorning', 'good morning', 'gm']:
        bot.reply_to(message, f"Good Morning, {message.from_user.first_name}! You've checked in {logins}/{days_since + 1}.")
    elif message.text.lower() == '/logins':
        with open(log_file, 'r') as f:
            log_contents = f.read()
        bot.reply_to(message, f'Login Log:\n{log_contents}')

bot.polling()
