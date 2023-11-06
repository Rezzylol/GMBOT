import telebot
import os
import csv
from datetime import datetime
from collections import defaultdict

print(f"{datetime.now()} init")

API_KEY = os.getenv('API_KEY')
bot = telebot.TeleBot(API_KEY)

check_ins_file = '/data/check_ins.csv'

if not os.path.isfile(check_ins_file):
    with open(check_ins_file, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['username', 'date'])

@bot.message_handler(commands=['start'])
def send_welcome(message):
    print(f"{datetime.now()} {message.from_user.username} {message.text}")
    bot.reply_to(message, "omg haiiiii :3c")

@bot.message_handler(func=lambda message: message.text.lower() in ['good morning', 'gm', 'good morning beverage', 'gm beverage', 'good rawrning', 'good morning team', 'good morningverage'])
def check_in(message):
    print(f"{datetime.now()} {message.from_user.username} {message.text}")
    username = message.from_user.username
    now = datetime.now().date()
    check_ins_today = 0
    with open(check_ins_file, 'r+', newline='') as file:
        reader = csv.reader(file)
        writer = csv.writer(file)
        check_ins = [row for row in reader]
        for row in check_ins:
            if row[0] == username and row[1] == str(now):
                check_ins_today += 1
        writer.writerow([username, now])
    today_check_ins = check_ins_today + 1
    if today_check_ins == 1:
        streak = 0
        total_check_ins = 0
        last_check_in_date = None
        with open(check_ins_file, 'r') as file:
            reader = csv.reader(file)
            sorted_check_ins = sorted([row for row in reader if row[0] == username], key=lambda row: row[1])
            for row in sorted_check_ins:
                check_in_date = datetime.strptime(row[1], '%Y-%m-%d').date()
                if last_check_in_date is None or (check_in_date - last_check_in_date).days == 1:
                    streak += 1
                elif (check_in_date - last_check_in_date).days > 1:
                    streak = 1
                last_check_in_date = check_in_date
                total_check_ins += 1
        reply = f"Good morning, @{username}! You've been checked in for today. {streak} days in a row so far."
    elif today_check_ins == 69:
        reply = "nice." # kei's easter egg
    else:
        reply = f"Good morning again, @{username}! Love the enthusiasm, you've tried to check in, like, {today_check_ins} times today now."
    bot.reply_to(message, reply)

@bot.message_handler(commands=['leaderboard'])
def leaderboard(message):
    print(f"{datetime.now()} {message.from_user.username} {message.text}")
    user_data = defaultdict(lambda: {'streak': 0, 'total': 0, 'last_check_in': None, 'days_checked_in': set()})
    with open(check_ins_file, 'r') as file:
        reader = csv.reader(file)
        next(reader, None)
        for username, date_str in reader:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            user = user_data[username]
            if user['last_check_in'] is None or (date - user['last_check_in']).days == 1:
                user['streak'] += 1
            elif (date - user['last_check_in']).days > 1:
                user['streak'] = 1
            user['last_check_in'] = date
            if date_str not in user['days_checked_in']:
                user['total'] += 1
                user['days_checked_in'].add(date_str)
    top_streaks = sorted(user_data.items(), key=lambda item: item[1]['streak'], reverse=True)[:5]
    top_totals = sorted(user_data.items(), key=lambda item: item[1]['total'], reverse=True)[:5]
    streaks_message = "\n".join([f"{idx + 1}. @{username} - {data['streak']}" for idx, (username, data) in enumerate(top_streaks)])
    totals_message = "\n".join([f"{idx + 1}. @{username} - {data['total']}" for idx, (username, data) in enumerate(top_totals)])
    reply = f"🏆 Streaks:\n{streaks_message}\n\n🏆 Check-ins:\n{totals_message}"
    bot.reply_to(message, reply)

@bot.message_handler(func=lambda message: message.from_user.username == "majeflyer")
def rezzy(message):
    if (random.randint(1,2500)) == 55:
        print(f"{datetime.now()} rezzy's easter egg #1")
        bot.reply_to(message, "alright alright thats enough")

@bot.message_handler(func=lambda m: True)
def sabre(message):
    if (random.randint(1,1000)) == 55:
        print(f"{datetime.now()} rezzy's easter egg #2")
        bot.reply_to(message, "thoughts? @SabreDance")

bot.polling()
