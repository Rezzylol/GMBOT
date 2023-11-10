import csv
import emoji
import os
import pytz
import random
import re
import requests
import threading
from collections import defaultdict
from datetime import datetime, timedelta
from telebot import TeleBot, types

VERSION = "0.0.1-alpha1 build 5"
API_KEY = os.getenv('API_KEY')
CONTROL_CHAT_ID = '-4070279760'
MAIN_CHAT_ID = '-1001735412957'
ATTEMPT_MAX = 3
ATTEMPT_TIMEOUT = 30
BESSAGES = 50
CREDITS_STARTING = 100
DONT_CONVERT = ["the", "that", "there", "they", "their", "them", "was", "were", "we're", "who", "what", "where", "when", "why", "how"]
URL_REPO = 'https://api.github.com/repos/Rezzylol/GMBOT/commits/main'
FILE_ATTEMPTS = '/data/attempts.csv'
FILE_CHECK_INS = '/data/check_ins.csv'
FILE_CREDITS = '/data/credits.csv'
FILE_IGNORE_LIST = '/data/ignore_list.csv'
FILE_MESSAGE_COUNT = '/data/message_count.txt'
FILE_MESSAGES = '/data/messages.txt'
FILE_QUOTES = '/data/quotes.txt'
GM_REGEX = r'^(gm|gm beverage|good morning|good morning beverage|good morning team|good morningverage|good rawrning)[,.!?]*\s*'
MESSAGES_MAX = 100
PAGE_SIZE = 10
TIME_ZONE = pytz.timezone('Pacific/Auckland')

def get_tz_now():
    return datetime.now(TIME_ZONE)

bot = TeleBot(API_KEY)
def log_to_control_chat(message):
    print(f"{get_tz_now().isoformat()} {message}")
    bot.send_message(CONTROL_CHAT_ID, f"{message}", parse_mode='HTML')

response = requests.get(URL_REPO)
if response.ok:
    commit_author = response.json()['commit']['author']['name']
    commit_date = datetime.strptime(response.json()['commit']['author']['date'], "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H:%M:%S")
    commit_message = response.json()['commit']['message']
    commit_sha = response.json()['sha'][:7]
    commit_url = response.json()['html_url']
    log_to_control_chat(f'init <code>{VERSION}</code>\n<a href="{commit_url}">{commit_date} - {commit_author}</a>')

for file_path in [FILE_ATTEMPTS, FILE_CHECK_INS, FILE_CREDITS, FILE_IGNORE_LIST]:
    if not os.path.isfile(file_path):
        with open(file_path, 'w', newline='') as file:
            writer = csv.writer(file)

for file_path in [FILE_MESSAGE_COUNT, FILE_MESSAGES]:
    if not os.path.isfile(file_path):
        with open(file_path, 'w', newline='') as file:
            pass

if os.path.isfile(FILE_QUOTES):
    with open(FILE_QUOTES, 'r') as file:
        quotes = [quote.strip() for quote in file if quote.strip()]

def send_paginated_list(file_path, list_name, message, page_number):
    with open(file_path, 'r', newline='') as file:
        reader = csv.reader(file)
        lines = list(reader)

    if not lines:
        log_to_control_chat("<i>no data available.</i>")
        return

    paginated_lines = list((lines[i:i + PAGE_SIZE] for i in range(0, len(lines), PAGE_SIZE)))
    if page_number < 0 or page_number >= len(paginated_lines):
        log_to_control_chat("<i>invalid page number.</i>")
        return

    page_content = paginated_lines[page_number]
    response = "\n".join([f"{PAGE_SIZE * page_number + i}. {','.join(row)}" for i, row in enumerate(page_content, start=1)])

    markup = types.InlineKeyboardMarkup()
    if page_number > 0:
        markup.add(types.InlineKeyboardButton("previous", callback_data=f"{list_name}_prev_{page_number - 1}"))
    if page_number < len(paginated_lines) - 1:
        markup.add(types.InlineKeyboardButton("next", callback_data=f"{list_name}_next_{page_number + 1}"))

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
        log_to_control_chat("<i>one or more line numbers are out of range.</i>")
        return

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

def ignore_user(username):
    log_to_control_chat(f"ignore_user {username}")
    now = get_tz_now().isoformat()
    with open(FILE_IGNORE_LIST, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([username, now])

def log_attempt(username):
    now = get_tz_now().isoformat()
    with open(FILE_ATTEMPTS, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([now, username])

def check_in_user(message):
    log_to_control_chat(f"check_in_user {message.from_user.username}")
    username = message.from_user.username
    now = get_tz_now()
    date_today = now.date()
    streak = 0
    with open(FILE_CHECK_INS, 'r+', newline='') as file:
        reader = csv.reader(file)
        check_ins = sorted((row for row in reader if row[1] == username), key=lambda row: row[0])
        file.seek(0, 2)
        writer = csv.writer(file)
        writer.writerow([now.isoformat(), username])
        for i in range(len(check_ins)-1, -1, -1):
            check_in_date = datetime.fromisoformat(check_ins[i][0]).date()
            if i == len(check_ins) - 1:
                streak = 1
            else:
                if (check_in_date - prev_date).days == 1:
                    streak += 1
                elif (check_in_date - prev_date).days > 1:
                    break
            prev_date = check_in_date
    bot.reply_to(message, f"good morning, @{username}! you've been checked in for today. <b>{streak} days</b> in a row so far.", parse_mode='HTML')

def ask_math_question(message, attempts=0, sent_message=None):
    log_to_control_chat(f"ask_math_question {message.from_user.username}")
    username = message.from_user.username
    if attempts == 0:
        question, answer = get_random_math_question()
        sent_message = bot.reply_to(message, f"what is <b>{question}</b>?", parse_mode='HTML')
    else:
        question, answer = get_random_math_question()
        bot.reply_to(message, f"nope. what is <b>{question}</b>?", parse_mode='HTML')

    question_time = datetime.now()

    def check_timeout():
        if datetime.now() - question_time >= timedelta(seconds=ATTEMPT_TIMEOUT):
            bot.edit_message_text(chat_id=message.chat.id, message_id=sent_message.message_id, text=f"see you in <b>7 days</b>!", parse_mode='HTML')
            ignore_user(username)

    def check_answer(msg):
        nonlocal answer, attempts
        if msg.from_user.username != username:
            return

        timeout_timer.cancel()

        try:
            user_answer = int(msg.text)
        except ValueError:
            bot.reply_to(msg, "that is <b>not</b> a number. try again.", parse_mode='HTML')
            return

        if user_answer == answer:
            check_in_user(msg)
        else:
            attempts += 1
            if attempts >= ATTEMPT_MAX:
                bot.reply_to(msg, "see you in <b>7 days</b>!", parse_mode='HTML')
                ignore_user(username)
            else:
                ask_math_question(message, attempts, sent_message)

    timeout_timer = threading.Timer(ATTEMPT_TIMEOUT, check_timeout)
    timeout_timer.start()

    bot.register_next_step_handler(sent_message, check_answer)

def get_message_count():
    try:
        with open(FILE_MESSAGE_COUNT, 'r') as file:
            return int(file.read().strip())
    except FileNotFoundError:
        return 0
    except ValueError:
        return 0

def increment_message_count():
    count = get_message_count() + 1
    with open(FILE_MESSAGE_COUNT, 'w') as file:
        file.write(str(count))
    return count

@bot.message_handler(commands=['list', 'ignored'])
def list_handler(message):
    list_name = message.text.strip('/').lower()
    file_path = FILE_CHECK_INS if list_name == 'list' else FILE_IGNORE_LIST

    if str(message.chat.id) == CONTROL_CHAT_ID:
        send_paginated_list(file_path, list_name, message, 0)
    else:
        bot.reply_to(message, "<i>this command can only be used in the control chat.</i>", parse_mode='HTML')

@bot.message_handler(commands=['ignore'])
def add_ignore(message):
    if str(message.chat.id) == CONTROL_CHAT_ID:
        try:
            _, username = message.text.split(' ')
            ignore_user(username)
        except ValueError:
            log_to_control_chat("provide line numbers separated by commas, e.g. <code>/ignore Keikuris</code>")
        except Exception as e:
            log_to_control_chat(f"<i>an error occurred</i>\n<code>{e}</code>")
    else:
        bot.reply_to(message, "<i>this command can only be used in the control chat.</i>", parse_mode='HTML')

@bot.message_handler(commands=['delete', 'unignore'])
def delete_handler(message):
    command = message.text.split()[0].lower()
    file_path = FILE_CHECK_INS if command == "/delete" else FILE_IGNORE_LIST
    if str(message.chat.id) == CONTROL_CHAT_ID:
        try:
            _, line_numbers = message.text.split(maxsplit=1)
            line_numbers = [int(ln.strip()) for ln in line_numbers.split(',')]
            deleted_count = delete_lines_from_csv(file_path, line_numbers)
            log_to_control_chat(f"<i>deleted {deleted_count} entries from the csv.</i>")
        except ValueError:
            log_to_control_chat(f"provide line numbers separated by commas, e.g. <code>{command} 1,2,3...</code>")
        except Exception as e:
            log_to_control_chat(f"<i>an error occurred: {e}</i>")
    else:
        bot.reply_to(message, "<i>this command can only be used in the control chat.</i>", parse_mode='HTML')

@bot.message_handler(commands=['debug'])
def debug_bot(message):
    log_to_control_chat(message)

@bot.message_handler(func=lambda message: re.match(GM_REGEX, message.text.lower()))
def check_in(message):
    log_to_control_chat(f"check_in {message.from_user.username}")
    username = message.from_user.username
    if check_ignore_list(username):
        bot.reply_to(message, f"good morning, @{username}! you've been ignored for <b>7 days</b> for failing my test. please try again later.", parse_mode='HTML')
    else:
        log_attempt(username)
        now = get_tz_now()
        date_today = now.date()
        check_ins_today = 0
        attempts_today = 0
        with open(FILE_CHECK_INS, 'r+', newline='') as file:
            reader = csv.reader(file)
            check_ins = [row for row in reader]
            for row in check_ins:
                check_in_date = datetime.fromisoformat(row[0]).date()
                if row[1] == username and check_in_date == date_today:
                    check_ins_today += 1
        with open(FILE_ATTEMPTS, 'r', newline='') as file:
            reader = csv.reader(file)
            attempts_today = sum(1 for row in reader if row[1] == username and datetime.fromisoformat(row[0]).date() == date_today)
        if check_ins_today == 0:
            result = random.randint(1, 10)
            if result == 5:
                ask_math_question(message)
            else:
                check_in_user(message)
        elif attempts_today == 69:
            bot.reply_to(message, "nice.") # kei's easter egg
        else:
            bot.reply_to(message, f"good morning again, @{username}! love the enthusiasm, you've tried to check in, like, <b>{attempts_today} times</b> today.", parse_mode='HTML')

@bot.message_handler(func=lambda message: message.text.lower() in ['good night', 'gn'])
def goodnight(message):
    bot.reply_to(message, "oh no! don't go to bed! your streak is now <b>0</b>.", parse_mode='HTML')

@bot.message_handler(commands=['leaderboard'])
def leaderboard(message):
    log_to_control_chat(f"{message.text} {message.from_user.username}")
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
    bot.reply_to(message, f"🏆 <b>streaks</b>\n{streaks_message}\n\n🏆 <b>check-ins</b>\n{totals_message}", parse_mode='HTML')

def init_credits(user_id):
    if read_credits(user_id) is None:
        write_credits(user_id, CREDITS_STARTING)

def read_credits(user_id):
    with open(FILE_CREDITS, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row['user_id'] == str(user_id):
                return int(row['credits'])
    return None

def write_credits(user_id, credits):
    temp_file = FILE_CREDITS + '.tmp'
    with open(FILE_CREDITS, 'r') as file, open(temp_file, 'w', newline='') as outfile:
        reader = csv.DictReader(file)
        writer = csv.DictWriter(outfile, fieldnames=['user_id', 'credits'])
        writer.writeheader()
        found = False
        for row in reader:
            if row['user_id'] == str(user_id):
                row['credits'] = credits
                found = True
            writer.writerow(row)
        if not found:
            writer.writerow({'user_id': user_id, 'credits': credits})
    os.replace(temp_file, FILE_CREDITS)

@bot.message_handler(commands=['credits'])
def credits(message):
    log_to_control_chat(f"{message.text} {message.from_user.username}")
    user_id = message.from_user.id
    init_credits(user_id)
    credits = read_credits(user_id)

    bot.reply_to(message, f"you have <b>{credits} credits</b>.", parse_mode='HTML')

@bot.message_handler(commands=['diceroll'])
def roll_dice(message):
    log_to_control_chat(f"{message.text} {message.from_user.username}")
    user_id = message.from_user.id
    init_credits(user_id)
    credits = read_credits(user_id)

    if credits < 10:
        bot.reply_to(message, "you don't have enough credits.")
        return

    result = random.randint(1, 6)

    if result == 6:
        credits += 1000
        response = f"congratulations! you rolled a {result} and won 1000 credits! you now have <b>{credits} credits</b>."
    elif result == 5:
        credits += 25
        response = f"you rolled a {result} and won 25 credits. you now have <b>{credits} credits</b>."
    elif result == 4:
        response = f"you rolled a {result}. No credits won or lost. you have <b>{credits} credits</b>."
    elif result == 3:
        credits -= 5
        response = f"you rolled a {result} and lost 5 credits. you now have <b>{credits} credits</b>."
    elif result == 2:
        credits -= 5
        response = f"you rolled a {result} and lost 10 credits. you now have <b>{credits} credits</b>."
    elif result == 1:
        credits = 0
        response = f"oops! you rolled a {result} and lost all your credits. you now have <b>{credits} credits</b>."

    write_credits(user_id, credits)
    bot.reply_to(message, response, parse_mode='HTML')

@bot.message_handler(commands=['easteregg'])
def leaderboard(message):
    log_to_control_chat(f"{message.text} {message.from_user.username}")
    if message.from_user.is_premium:
        reply = random.choice(quotes)
    else:
        reply = "i'm sorry, this command is only available to <b>Telegram Premium</b> users."
    bot.reply_to(message, reply, parse_mode='HTML')

@bot.message_handler(commands=['about'])
def leaderboard(message):
    log_to_control_chat(f"{message.text} {message.from_user.username}")
    reply = (
        f"<b>gmbot</b> <code>{VERSION}</code>\n"
        f"\n"
        f"created by 🦊🔥 Rezzy & 🐺🐲 Kei\n"
        f"\n"
        f"<i>best viewed in netscape navigator, with a screen resolution of 800x600.</i>"
    )
    bot.reply_to(message, reply, parse_mode='HTML')

@bot.message_handler(func=lambda message: message.from_user.username == "majeflyer")
def rezzy(message):
    result = random.randint(1, 2500)
    if result == 55:
        log_to_control_chat(f"rezzy")
        bot.reply_to(message, "alright alright thats enough")
    elif 50 <= result <= 60:
        log_to_control_chat(f"rezzy<=5")

@bot.message_handler(func=lambda m: True)
def handle_all_messages(message):
    if str(message.chat.id) == MAIN_CHAT_ID:
        message_lower = message.text.lower()

        with open(FILE_MESSAGES, 'a') as file:
            file.write(re.sub(r'\s+', ' ', message_lower) + ' ')
        
        message_count = increment_message_count()

        if message_count >= MESSAGES_MAX:
            with open(FILE_MESSAGES, 'r') as file:
                all_messages = file.read().split()
            
            if len(all_messages) >= 10:
                selected_messages = ' '.join(random.sample(all_messages, 10))

                bot.reply_to(message, selected_messages)
                
                #with open(FILE_MESSAGES, 'w') as file:
                #    file.truncate(0)
                with open(FILE_MESSAGE_COUNT, 'w') as file:
                    file.write('0')

        if message_count == BESSAGES or message_count == BESSAGES + 1:
            words = message_lower.split()
            bessage = []
            for word in words:
                if emoji.emoji_count(word) > 0:
                    bessage.append(word)
                elif word in DONT_CONVERT:
                    bessage.append(word)
                elif len(word) < 3:
                    bessage.append(word)
                elif word[0] in 'aeiou':
                    bessage.append('b' + word)
                elif word[:2] == 'th':
                    bessage.append('b' + word[2:])
                else:
                    bessage.append('b' + word[1:])
            bessage = ' '.join(bessage)
            bot.reply_to(message, bessage)

    result = random.randint(1, 1000)
    if result == 55:
        log_to_control_chat(f"sabre {message.from_user.username}")
        bot.reply_to(message, "thoughts? @SabreDance")
    elif 50 <= result <= 60:
        log_to_control_chat(f"sabre<=5 {message.from_user.username}")

bot.polling()
