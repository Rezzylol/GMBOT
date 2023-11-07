import csv
import os
import pytz
import random
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from telebot import TeleBot, types
import threading

VERSION = "0.0.1-alpha0 build 0"
API_KEY = os.getenv('API_KEY')
CONTROL_CHAT_ID = '-4070279760'
ATTEMPT_MAX = 3
ATTEMPT_TIMEOUT = 30
FILE_CHECK_INS = '/data/check_ins.csv'
FILE_IGNORE_LIST = '/data/ignore_list.csv'
FILE_QUOTES = '/data/quotes.txt'
PAGE_SIZE = 10
TIME_ZONE = pytz.timezone('Pacific/Auckland')

def get_tz_now():
    return datetime.now(TIME_ZONE)

bot = TeleBot(API_KEY)
def log_to_control_chat(message):
    print(f"{get_tz_now().isoformat()} {message}")
    bot.send_message(CONTROL_CHAT_ID, f"{message}")

log_to_control_chat(f"init")

for file_path in [FILE_CHECK_INS, FILE_IGNORE_LIST]:
    if not os.path.isfile(file_path):
        with open(file_path, 'w', newline='') as file:
            writer = csv.writer(file)

if os.path.isfile(FILE_QUOTES):
    with open(FILE_QUOTES, 'r') as file:
        quotes = [quote.strip() for quote in file if quote.strip()]

def send_paginated_list(file_path, list_name, message, page_number):
    with open(file_path, 'r', newline='') as file:
        reader = csv.reader(file)
        lines = list(reader)

    if not lines:
        bot.send_message(CONTROL_CHAT_ID, "No data available.")
        return

    paginated_lines = list((lines[i:i + PAGE_SIZE] for i in range(0, len(lines), PAGE_SIZE)))
    if page_number < 0 or page_number >= len(paginated_lines):
        bot.send_message(CONTROL_CHAT_ID, "Invalid page number.")
        return

    page_content = paginated_lines[page_number]
    response = "\n".join([f"{PAGE_SIZE * page_number + i}. {','.join(row)}" for i, row in enumerate(page_content, start=1)])

    markup = types.InlineKeyboardMarkup()
    if page_number > 0:
        markup.add(types.InlineKeyboardButton("Previous", callback_data=f"{list_name}_prev_{page_number - 1}"))
    if page_number < len(paginated_lines) - 1:
        markup.add(types.InlineKeyboardButton("Next", callback_data=f"{list_name}_next_{page_number + 1}"))

    bot.send_message(CONTROL_CHAT_ID, response, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: '_prev_' in call.data or '_next_' in call.data)
def query_paginated(call):
    list_name, action, page_number = call.data.split('_')
    page_number = int(page_number)

    file_path = FILE_CHECK_INS if list_name == 'list' else FILE_IGNORE_LIST
    send_paginated_list(file_path, list_name, call.message, page_number)

def delete_lines_from_csv(file_path, line_numbers):
    line_numbers = [ln - 1 for ln in line_numbers]

    with open(file_path, 'r', newline='') as infile:
        rows = list(csv.reader(infile))

    if not all(0 <= ln < len(rows) for ln in line_numbers):
        log_to_control_chat("One or more line numbers are out of range.")
        raise ValueError("One or more line numbers are out of range.")

    with open(file_path, 'w', newline='') as outfile:
        writer = csv.writer(outfile)
        entries_deleted = 0
        for index, row in enumerate(rows):
            if index not in line_numbers:
                writer.writerow(row)
            else:
                entries_deleted += 1
    return entries_deleted

def get_random_math_question():
    num1 = random.randint(1, 4)
    num2 = random.randint(1, 4)
    operation = random.choice(['+'])
    question = f"{num1} {operation} {num2}"
    answer = eval(question)
    return question, answer

def check_ignore_list(username):
    try:
        with open(FILE_IGNORE_LIST, 'r+', newline='') as file:
            reader = csv.reader(file)
            ignore_list = {row[0]: datetime.fromisoformat(row[1]) for row in reader if row}
            if username in ignore_list:
                if get_tz_now() - ignore_list[username] < timedelta(days=7):
                    return True
                else:
                    ignore_list.pop(username)
                    file.seek(0)
                    writer = csv.writer(file)
                    writer.writerows([(user, date) for user, date in ignore_list.items()])
                    file.truncate()
            return False
    except FileNotFoundError:
        return False

def update_ignore_list(username):
    log_to_control_chat(f"ignoring {username}")
    now = get_tz_now().isoformat()
    with open(FILE_IGNORE_LIST, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([username, now])

def check_in_user(message):
    username = message.from_user.username
    now = get_tz_now()
    date_today = now.date()
    with open(FILE_CHECK_INS, 'r+', newline='') as file:
        reader = csv.reader(file)
        writer = csv.writer(file)
        check_ins = [row for row in reader]
        for row in check_ins:
            check_in_date = datetime.fromisoformat(row[0]).date()
        writer.writerow([now.isoformat(), username])
        streak = 0
        last_check_in_date = None
        sorted_check_ins = sorted([row for row in reader if row[1] == username], key=lambda row: row[0])
        for row in sorted_check_ins:
            check_in_date = datetime.fromisoformat(row[0]).date()
            if last_check_in_date is None or (check_in_date - last_check_in_date).days == 1:
                streak += 1
            elif (check_in_date - last_check_in_date).days > 1:
                streak = 1
            last_check_in_date = check_in_date
    reply = f"Good morning, @{username}! You've been checked in for today. {streak} days in a row so far."
    bot.reply_to(message, reply)

def ask_math_question(message, attempts=0, sent_message=None):
    username = message.from_user.username
    if attempts == 0:
        question, answer = get_random_math_question()
        sent_message = bot.reply_to(message, f"What is {question}?")
    else:
        question, answer = get_random_math_question()
        bot.reply_to(message, f"Nope. What is {question}?")

    question_time = datetime.now()

    def check_timeout():
        if datetime.now() - question_time >= timedelta(seconds=ATTEMPT_TIMEOUT):
            bot.edit_message_text(chat_id=message.chat.id, message_id=sent_message.message_id, text=f"See you in 7 days!")
            update_ignore_list(username)

    def check_answer(msg):
        nonlocal answer, attempts
        if msg.from_user.username != username:
            return

        timeout_timer.cancel()

        try:
            user_answer = int(msg.text)
        except ValueError:
            bot.reply_to(msg, "That doesn't seem to be a number. Try again.")
            return

        if user_answer == answer:
            check_in_user(msg)
        else:
            attempts += 1
            if attempts >= ATTEMPT_MAX:
                bot.reply_to(msg, "See you in 7 days!")
                update_ignore_list(username)
            else:
                ask_math_question(message, attempts, sent_message)

    timeout_timer = threading.Timer(ATTEMPT_TIMEOUT, check_timeout)
    timeout_timer.start()

    bot.register_next_step_handler(sent_message, check_answer)

@bot.message_handler(commands=['list', 'ignored'])
def list_handler(message):
    list_name = message.text.strip('/').lower()
    file_path = FILE_CHECK_INS if list_name == 'list' else FILE_IGNORE_LIST

    if str(message.chat.id) == CONTROL_CHAT_ID:
        send_paginated_list(file_path, list_name, message, 0)
    else:
        bot.reply_to(message, "This command can only be used in the control chat.")

@bot.message_handler(commands=['ignore'])
def add_ignore(message):
    log_to_control_chat(f"{message.from_user.username} {message.text}")
    if str(message.chat.id) == CONTROL_CHAT_ID:
        try:
            _, username = message.text.split(' ')
            update_ignore_list(username)
            log_to_control_chat(f"Added {username} to ignore list.")
        except ValueError:
            log_to_control_chat("Please provide line numbers separated by commas, e.g. /ignore Keikuris")
        except Exception as e:
            log_to_control_chat(f"An error occurred: {e}")
    else:
        bot.reply_to(message, "This command can only be used in the control chat.")

@bot.message_handler(commands=['delete', 'unignore'])
def handle_delete(message):
    log_to_control_chat(f"{message.from_user.username} {message.text}")
    command = message.text.split()[0].lower()
    file_path = FILE_CHECK_INS if command == "/delete" else FILE_IGNORE_LIST
    if str(message.chat.id) == CONTROL_CHAT_ID:
        try:
            _, line_numbers = message.text.split(maxsplit=1)
            line_numbers = [int(ln.strip()) for ln in line_numbers.split(',')]
            deleted_count = delete_lines_from_csv(file_path, line_numbers)
            log_to_control_chat(f"Deleted {deleted_count} entries from the CSV.")
        except ValueError:
            log_to_control_chat(f"Please provide line numbers separated by commas, e.g. {command} 1,2,3...")
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
    if check_ignore_list(username):
        bot.reply_to(message, f"Good morning, @{username}! You've been ignored for 7 days for failing my test. Please try again later.")
    else:
        now = get_tz_now()
        date_today = now.date()
        check_ins_today = 0
        with open(FILE_CHECK_INS, 'r+', newline='') as file:
            reader = csv.reader(file)
            check_ins = [row for row in reader]
            for row in check_ins:
                check_in_date = datetime.fromisoformat(row[0]).date()
                if row[1] == username and check_in_date == date_today:
                    check_ins_today += 1
        today_check_ins = check_ins_today + 1
        if today_check_ins == 1:
            result = random.randint(1, 10)
            if result == 5:
                log_to_control_chat("math question triggered")
                ask_math_question(message)
            else:
                check_in_user(message)
        elif today_check_ins == 69:
            reply = "nice." # kei's easter egg
        else:
            reply = f"Good morning again, @{username}! Love the enthusiasm, you've tried to check in, like, {today_check_ins} times today now."
        bot.reply_to(message, reply)

@bot.message_handler(commands=['leaderboard'])
def leaderboard(message):
    log_to_control_chat(f"{message.from_user.username} {message.text}")
    user_data = defaultdict(lambda: {'streak': 0, 'total': 0, 'last_check_in': None, 'days_checked_in': set()})
    with open(FILE_CHECK_INS, 'r') as file:
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

@bot.message_handler(commands=['easteregg'])
def leaderboard(message):
    log_to_control_chat(f"{message.from_user.username} {message.text}")
    if message.from_user.is_premium:
        reply = random.choice(quotes)
    else:
        reply = "I'm sorry, this command is only available to Telegram Premium users."
    bot.reply_to(message, reply)

@bot.message_handler(commands=['about'])
def leaderboard(message):
    log_to_control_chat(f"{message.from_user.username} {message.text}")
    reply = (
        f"GMBOT {VERSION}\n"
        f"\n"
        f"Created by 🦊🔥 Rezzy & 🐺🐲 Kei\n"
        f"\n"
        f"Best viewed in Netscape Navigator, with a screen resolution of 800x600."
    )
    bot.reply_to(message, reply, parse_mode='HTML')

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
