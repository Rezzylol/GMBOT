import csv
import os
import pytz
import random
import sys
from collections import defaultdict
from datetime import datetime
from telebot import TeleBot, types

API_KEY = os.getenv('API_KEY')
CONTROL_CHAT_ID = '-4070279760'
PAGE_SIZE = 10
CHECK_INS_FILE = '/data/check_ins.csv'
TIME_ZONE = pytz.timezone('Pacific/Auckland')

pagination_indexes = defaultdict(lambda: 0)

def get_tz_now():
    return datetime.now(TIME_ZONE).isoformat()

bot = TeleBot(API_KEY)
def log_to_control_chat(message):
    print(f"{get_tz_now()} {message}")
    bot.send_message(CONTROL_CHAT_ID, f"{get_tz_now()} {message}")

log_to_control_chat(f"init")

if not os.path.isfile(CHECK_INS_FILE):
    with open(CHECK_INS_FILE, 'w', newline='') as file:
        writer = csv.writer(file)

def chunked_data(data, chunk_size):
    for i in range(0, len(data), chunk_size):
        yield data[i:i + chunk_size]

def send_paginated_list(message, page_number):
    with open(CHECK_INS_FILE, 'r', newline='') as file:
        reader = csv.reader(file)
        lines = list(reader)

    paginated_lines = list(chunked_data(lines, PAGE_SIZE))
    page_content = paginated_lines[page_number]
    response = "\n".join([f"{PAGE_SIZE * page_number + i}. {','.join(row)}" for i, row in enumerate(page_content, start=1)])

    markup = types.InlineKeyboardMarkup()
    if page_number > 0:
        markup.add(types.InlineKeyboardButton("Previous", callback_data=f"list_prev_{page_number - 1}"))
    if page_number < len(paginated_lines) - 1:
        markup.add(types.InlineKeyboardButton("Next", callback_data=f"list_next_{page_number + 1}"))

    bot.send_message(CONTROL_CHAT_ID, response, reply_markup=markup)

def delete_lines_from_csv(line_numbers):
    line_numbers = [ln - 1 for ln in line_numbers]
    
    with open(CHECK_INS_FILE, 'r', newline='') as file:
        rows = list(csv.reader(file))

    if not all(0 <= ln < len(rows) for ln in line_numbers):
        log_to_control_chat("One or more line numbers are out of range.")
        raise ValueError("One or more line numbers are out of range.")

    with open(CHECK_INS_FILE, 'w', newline='') as file:
        writer = csv.writer(file)
        entries_deleted = 0
        for index, row in enumerate(rows):
            if index not in line_numbers:
                writer.writerow(row)
            else:
                entries_deleted += 1
    return entries_deleted

@bot.callback_query_handler(func=lambda call: call.data.startswith('list_'))
def query_paginated_list(call):
    action, page_number = call.data.split('_')[1:]
    page_number = int(page_number)
    send_paginated_list(call.message, page_number)

@bot.message_handler(commands=['list'])
def list_check_ins(message):
    if str(message.chat.id) == CONTROL_CHAT_ID:
        send_paginated_list(message, 0)
    else:
        bot.reply_to(message, "This command can only be used in the control chat.")

@bot.message_handler(commands=['delete'])
def delete_check_in(message):
    log_to_control_chat(f"{message.from_user.username} {message.text}")
    if str(message.chat.id) == CONTROL_CHAT_ID:
        try:
            _, line_numbers = message.text.split(maxsplit=1)
            line_numbers = [int(ln.strip()) for ln in line_numbers.split(',')]
            deleted_count = delete_lines_from_csv(line_numbers)
            log_to_control_chat(f"Deleted {deleted_count} entries from the CSV.")
        except ValueError:
            log_to_control_chat("Please provide line numbers separated by commas, e.g. /delete 1,2,3...")
        except Exception as e:
            log_to_control_chat(f"An error occurred: {e}")
    else:
        bot.reply_to(message, "This command can only be used in the control chat.")

@bot.message_handler(commands=['restart'])
def restart_bot(message):
    log_to_control_chat(f"{message.from_user.username} {message.text}")
    if str(message.chat.id) == CONTROL_CHAT_ID:
        log_to_control_chat("restarting...")
        sys.exit()
    else:
        bot.reply_to(message, "This command can only be used in the control chat.")

@bot.message_handler(commands=['debug'])
def debug_bot(message):
    log_to_control_chat(message)

@bot.message_handler(func=lambda message: message.text.lower() in ['good morning', 'gm', 'good morning beverage', 'gm beverage', 'good rawrning', 'good morning team', 'good morningverage'])
def check_in(message):
    log_to_control_chat(f"{message.from_user.username} {message.text}")
    username = message.from_user.username
    now = get_tz_now()
    date_today = datetime.now(TIME_ZONE).date()
    check_ins_today = 0
    with open(CHECK_INS_FILE, 'r+', newline='') as file:
        reader = csv.reader(file)
        writer = csv.writer(file)
        check_ins = [row for row in reader]
        for row in check_ins:
            check_in_date = datetime.fromisoformat(row[0]).date()
            if row[1] == username and check_in_date == date_today:
                check_ins_today += 1
        writer.writerow([now, username])
    today_check_ins = check_ins_today + 1
    if today_check_ins == 1:
        streak = 0
        total_check_ins = 0
        last_check_in_date = None
        with open(CHECK_INS_FILE, 'r') as file:
            reader = csv.reader(file)
            sorted_check_ins = sorted([row for row in reader if row[1] == username], key=lambda row: row[0])
            for row in sorted_check_ins:
                check_in_date = datetime.fromisoformat(row[0]).date()
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
    log_to_control_chat(f"{message.from_user.username} {message.text}")
    user_data = defaultdict(lambda: {'streak': 0, 'total': 0, 'last_check_in': None, 'days_checked_in': set()})
    with open(CHECK_INS_FILE, 'r') as file:
        reader = csv.reader(file)
        for datetime_str, username in reader:
            date = datetime.fromisoformat(datetime_str).date()
            user = user_data[username]
            if user['last_check_in'] is None or (date - user['last_check_in']).days == 1:
                user['streak'] += 1
            elif (date - user['last_check_in']).days > 1:
                user['streak'] = 1
            user['last_check_in'] = date
            if date not in user['days_checked_in']:
                user['total'] += 1
                user['days_checked_in'].add(date)
    top_streaks = sorted(user_data.items(), key=lambda item: item[1]['streak'], reverse=True)[:5]
    top_totals = sorted(user_data.items(), key=lambda item: item[1]['total'], reverse=True)[:5]
    streaks_message = "\n".join([f"{idx + 1}. {username} - {data['streak']}" for idx, (username, data) in enumerate(top_streaks)])
    totals_message = "\n".join([f"{idx + 1}. {username} - {data['total']}" for idx, (username, data) in enumerate(top_totals)])
    reply = f"🏆 Streaks:\n{streaks_message}\n\n🏆 Check-ins:\n{totals_message}"
    bot.reply_to(message, reply)

@bot.message_handler(func=lambda message: message.from_user.username == "majeflyer")
def rezzy(message):
    result = random.randint(1, 2500)
    if result == 55:
        log_to_control_chat("rezzy's easter egg #1 triggered")
        bot.reply_to(message, "alright alright thats enough")
    elif 50 <= result <= 60:
        log_to_control_chat(f"rezzy's easter egg #1 close result: {result}")

@bot.message_handler(func=lambda m: True)
def sabre(message):
    result = random.randint(1, 1000)
    if result == 55:
        log_to_control_chat("rezzy's easter egg #2 triggered")
        bot.reply_to(message, "thoughts? @SabreDance")
    elif 50 <= result <= 60:
        log_to_control_chat(f"rezzy's easter egg #2 close result: {result}")

bot.polling()
