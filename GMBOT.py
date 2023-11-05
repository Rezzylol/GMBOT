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
    updated_logins = []

    with open(log_file, 'r') as f:
        lines = f.readlines()
        for line in lines:
            date_str, uid, logins = line.strip().split(':')
            log_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            if int(uid) == user_id and log_date == today:
                logins = str(int(logins) + 1)
            updated_logins.append(f'{date_str}: {uid}: {logins}\n')

        if not any(line.startswith(f'{today}: {user_id}:') for line in updated_logins):
            updated_logins.append(f'{today}: {user_id}: 1\n')

    with open(log_file, 'w') as f:
        f.writelines(updated_logins)

    # Return the updated login count
    return int(logins)

def get_leaderboard():
    user_logins = {}
    with open(log_file, 'r') as f:
        lines = f.readlines()
        for line in lines:
            _, user_id, logins = line.strip().split(':')
            user_logins[user_id] = user_logins.get(user_id, 0) + int(logins)
    
    sorted_users = sorted(user_logins.items(), key=itemgetter(1), reverse=True)
    leaderboard = []
    for user_id, logins in sorted_users:
        leaderboard.append(f'User {user_id}: {logins} logins')
    
    return leaderboard

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
    elif message.text.lower() in ['/goodmorning', 'good morning', 'gm', 'good morning beverage', 'gm beverage']:
            bot.reply_to(message, f"Good Morning, {message.from_user.first_name}! You've checked in {logins}/{days_since + 1}.")
    elif message.text.lower() == '/logins':
        leaderboard = get_leaderboard()
        if leaderboard:
            response = '\n'.join(leaderboard)
        else:
            response = 'No login data available.'
        bot.reply_to(message, response)

bot.polling()
