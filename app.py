import csv
import emoji
import os
import pytz
import random
import re
import requests
import threading
import tiktoken
from collections import defaultdict
from datetime import datetime, timedelta
from openai import OpenAI
from telebot import TeleBot, types

VERSION = "0.0.1-alpha1 build 5"
ATTEMPT_MAX = 3
ATTEMPT_TIMEOUT = 30
BESSAGES = 50
BOT_USERNAME = '@GMBeverageBot'
CHAT_ID_CONTROL = '-4070279760'
CHAT_ID_MAIN = '-1001735412957'
CREDITS_STARTING = 100
FILE_ATTEMPTS = '/data/attempts.csv'
FILE_CHECK_INS = '/data/check_ins.csv'
FILE_CREDITS = '/data/credits.csv'
FILE_IGNORE_LIST = '/data/ignore_list.csv'
FILE_MESSAGE_COUNT = '/data/message_count.txt'
FILE_MESSAGES = '/data/messages.txt'
FILE_QUOTES = '/data/quotes.txt'
GM_REGEX = r'^(gm|gm beverage|good morning|good morning beverage|good morning team|good morningverage|good rawrning)[,.!?]*\s*'
MESSAGES_MAX = 1000
OPENAI_MODEL = "gpt-4-1106-preview"
OPENAI_MAX_TOKENS = 4096
OPENAI_SYSTEM_PROMPT = (
    "You are a helpful assistant.\n"
    "Don't begin your response with any greetings or acknowledgements.\n"
    "Your response must be no longer than 4096 characters.\n"
    "If you intend to use formatting, you must format bold, italic, underlined, strikethrough, and spoiler text, as well as inline links and pre-formatted code in your response as Telegram HTML syntax instead of Markdown.\n"
    "Some examples:\n"
    "* <b>bold</b>\n"
    "* <i>italic</i>\n"
    "* <u>underline</u>\n"
    "* <s>strikethrough</s>\n"
    "* <span class=\"tg-spoiler\">spoiler</span>\n"
    "* <a href=\"http://www.example.com/\">inline URL</a>\n"
    "* <code>inline fixed-width code</code>\n"
    "* <pre>pre-formatted fixed-width code block</pre>\n"
    "* <pre><code class=\"language-python\">pre-formatted fixed-width code block written in the Python programming language</code></pre>\n"
    "Please note:\n"
    "* Don't use formatting just for the sake of it, only use it if required as part of a request.\n"
    "* Only the tags mentioned above are currently supported.\n"
    "* All <, > and & symbols that are not a part of a tag or an HTML entity must be replaced with the corresponding HTML entities (< with &lt;, > with &gt; and & with &amp;).\n"
    "* All numerical HTML entities are supported.\n"
    "* The API currently supports only the following named HTML entities: &lt;, &gt;, &amp; and &quot;.\n"
    "* Use nested pre and code tags, to define programming language for pre entity.\n"
    "* Programming language can't be specified for standalone code tags."
)
PAGE_SIZE = 10
TIME_ZONE = pytz.timezone('Pacific/Auckland')
URL_REPO = 'https://api.github.com/repos/Rezzylol/GMBOT/commits/main'
VOWELS = 'aeiou'
DONT_CONVERT = [
    # Pronouns
    "I", "me", "you", "he", "him", "she", "her", "it", "we", "us", "they", "them",
    "my", "mine", "your", "yours", "his", "her", "hers", "its", "our", "ours",
    "their", "theirs", "this", "that", "these", "those", "who", "whom", "whose",
    "which", "what", "where", "when", "why", "how",

    # Prepositions
    "at", "in", "on", "for", "with", "about", "against", "between", "into",
    "through", "during", "before", "after", "above", "below", "to", "from",
    "up", "down", "in", "out", "on", "off", "over", "under", "again", "further",
    "then", "once", "here", "there", "when", "where", "why", "how", "all", "any",
    "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor",
    "not", "only", "own", "same", "so", "than", "too", "very", "s", "t", "can",
    "will", "just", "don", "should", "now",

    # Conjunctions
    "and", "but", "or", "yet", "so", "for", "nor",

    # Articles
    "a", "an", "the",

    # Modals
    "can", "could", "may", "might", "shall", "should", "will", "would", "must",

    # Auxiliaries
    "am", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "having", "do", "does", "did", "doing",

    # Others
    "as", "of", "if", "else", "though", "although", "until", "while", "since",
    "unless", "because"
]
CONTRACTION_ENDINGS = ["n't", "'s", "'ll", "'d", "'re", "'ve", "'m"]

def get_tz_now():
    return datetime.now(TIME_ZONE)

bot = TeleBot(os.getenv('TOKEN'))
def log_to_control_chat(message, html=True):
    parse_mode = 'HTML' if html else None
    print(f"{get_tz_now().isoformat()} {message}")
    bot.send_message(CHAT_ID_CONTROL, f"{message}", parse_mode=parse_mode)

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

    bot.send_message(CHAT_ID_CONTROL, response, reply_markup=markup)

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
    log_to_control_chat(f"{username} ignore_user")
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
    log_to_control_chat(f"{message.from_user.username} check_in_user")
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
    log_to_control_chat(f"{message.from_user.username} ask_math_question")
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

    if str(message.chat.id) == CHAT_ID_CONTROL:
        send_paginated_list(file_path, list_name, message, 0)
    else:
        bot.reply_to(message, "<i>this command can only be used in the control chat.</i>", parse_mode='HTML')

@bot.message_handler(commands=['ignore'])
def add_ignore(message):
    if str(message.chat.id) == CHAT_ID_CONTROL:
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
    if str(message.chat.id) == CHAT_ID_CONTROL:
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
    log_to_control_chat(f"{message.from_user.username} check_in")
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
    log_to_control_chat(f"{message.from_user.username} {message.text}")
    user_id = message.from_user.id
    init_credits(user_id)
    credits = read_credits(user_id)

    bot.reply_to(message, f"you have <b>{credits} credits</b>.", parse_mode='HTML')

@bot.message_handler(commands=['diceroll'])
def roll_dice(message):
    log_to_control_chat(f"{message.from_user.username} {message.text}")
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

class RouletteGame:
    def __init__(self):
        self.bets = []
        self.credits = 0
        self.original_chat_id = None
        self.bet_type = None
        self.bet_value = None
        self.red_numbers = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
        self.black_numbers = [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35]

    def add_bet(self, bet):
        self.bets.append(bet)

    def remove_bet(self, index):
        self.bets.pop(index)

    def spin_wheel(self):
        result = random.randint(0, 36)
        payout = 0
        total_bet = sum(bet['amount'] for bet in self.bets)

        for bet in self.bets:
            if bet['type'] == 'straight':
                if int(bet['number']) == result:
                    payout += bet['amount'] * 35

            elif bet['type'] == 'split':
                numbers = [int(n) for n in bet['number'].split('/')]
                if result in numbers:
                    payout += bet['amount'] * 17

            elif bet['type'] == 'street':
                numbers = [int(n) for n in bet['number'].split('-')]
                if result in range(numbers[0], numbers[-1] + 1):
                    payout += bet['amount'] * 11

            elif bet['type'] == 'corner':
                numbers = [int(n) for n in bet['number'].split('/')]
                if result in numbers:
                    payout += bet['amount'] * 8

            elif bet['type'] == 'sixline':
                numbers = [int(n) for n in bet['number'].split('-')]
                if result in range(numbers[0], numbers[-1] + 1):
                    payout += bet['amount'] * 5

            elif bet['type'] == 'dozen':
                dozen_ranges = {1: range(1, 13), 2: range(13, 25), 3: range(25, 37)}
                if result in dozen_ranges[int(bet['number'])]:
                    payout += bet['amount'] * 2

            elif bet['type'] == 'column':
                column_numbers = {
                    1: [i for i in range(1, 37) if i % 3 == 1],
                    2: [i for i in range(1, 37) if i % 3 == 2],
                    3: [i for i in range(1, 37) if i % 3 == 0]
                }
                if result in column_numbers[int(bet['number'])]:
                    payout += bet['amount'] * 2

            elif bet['type'] == 'redblack':
                if (bet['number'] == 'Red' and result in self.red_numbers) or \
                   (bet['number'] == 'Black' and result in self.black_numbers):
                    payout += bet['amount']

            elif bet['type'] == 'evenodd':
                if (bet['number'] == 'Even' and result % 2 == 0 and result != 0) or \
                   (bet['number'] == 'Odd' and result % 2 == 1):
                    payout += bet['amount']

            elif bet['type'] == 'lowhigh':
                if (bet['number'] == 'Low' and 1 <= result <= 18) or \
                   (bet['number'] == 'High' and 19 <= result <= 36):
                    payout += bet['amount']

        if payout > 0:
            self.credits += payout
        else:
            self.credits -= total_bet

        return result, total_bet

games = {}

@bot.message_handler(commands=['roulette'])
def start_roulette(message):
    games[message.from_user.id] = RouletteGame()
    init_credits(message.from_user.id)
    games[message.from_user.id].original_chat_id = message.chat.id
    games[message.from_user.id].original_credits = read_credits(message.from_user.id)
    games[message.from_user.id].credits = games[message.from_user.id].original_credits
    send_game_menu(message)

def send_game_menu(message):
    game = games[message.from_user.id]
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add(types.KeyboardButton("Add Bet"), types.KeyboardButton("Spin Wheel"))

    bet_list_str = "No bets placed." if not game.bets else ""
    for i, bet in enumerate(game.bets, 1):
        bet_list_str += f"\n{i}. @{message.from_user.username} put {bet['amount']} credits on {bet['number']}"

    response = f"Bets: {bet_list_str}"

    bot.send_message(message.from_user.id, response, reply_markup=markup)
    bot.send_message(games[message.from_user.id].original_chat_id, response)

@bot.message_handler(func=lambda message: message.text in ["Add Bet", "Spin Wheel"])
def handle_game_menu_options(message):
    game = games[message.from_user.id]

    if message.text == "Add Bet":
        send_bet_types(message)
    elif message.text == "Spin Wheel":
        result, total_bet = game.spin_wheel()
        write_credits(message.from_user.id, games[message.from_user.id].credits)

        if result == 0:
            color = 'Green'
            range_info = 'Zero'
        else:
            color = 'Red' if result in games[message.from_user.id].red_numbers else 'Black'
            odd_even = 'Odd' if result % 2 else 'Even'
            low_high = 'Low' if 1 <= result <= 18 else 'High'
            range_info = f"{odd_even}, {low_high}"

        announcement = f"{color} {result}, {range_info}"

        net_gain = games[message.from_user.id].credits - games[message.from_user.id].original_credits

        if net_gain > 0:
            response = f"{announcement}\n@{message.from_user.username} won {net_gain} credits.\nTotal bet: {total_bet} credits."
        elif net_gain < 0:
            response = f"{announcement}\n@{message.from_user.username} lost {abs(net_gain)} credits.\nTotal bet: {total_bet} credits."
        else:
            response = f"{announcement}\n@{message.from_user.username} neither won nor lost.\nTotal Bet: {total_bet} credits."

        bot.send_message(message.from_user.id, response)
        bot.send_message(games[message.from_user.id].original_chat_id, response)

@bot.callback_query_handler(func=lambda call: call.data.startswith("roulette_"))
def handle_query(call):
    game = games[call.from_user.id]

    if call.data.startswith("roulette_type_"):
        bet_type = call.data.split("_")[-1]
        ask_bet_value(call, bet_type)
    elif call.data.startswith("roulette_value_"):
        data_parts = call.data.split("_")
        bet_type = data_parts[2]
        bet_value = "_".join(data_parts[3:])
        game.bet_type, game.bet_value = bet_type, bet_value
        bot.send_message(call.from_user.id, "Enter the amount of credits you want to bet:")
    elif call.data.startswith("roulette_amount_"):
        bet_type, bet_value, bet_amount = call.data.split("_")[2:]
        bet_amount = int(bet_amount)
        if bet_amount <= 0 or bet_amount > game.credits:
            bot.send_message(call.from_user.id, "Invalid amount. Please enter a valid number of credits.")
            return
        game.add_bet({'type': bet_type, 'number': int(bet_value), 'amount': bet_amount})
        send_game_menu(call)

def send_bet_types(message):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    bet_types = ['Straight', 'Split', 'Street', 'Corner', 'Six Line', 'Dozen', 'Column', 'Red/Black', 'Even/Odd', 'Low/High']
    row_size = 5
    for i in range(0, len(bet_types), row_size):
        row = [types.KeyboardButton(bet_type) for bet_type in bet_types[i:i + row_size]]
        markup.row(*row)

    bot.send_message(message.from_user.id, "Select a bet type", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text in ['Straight', 'Split', 'Street', 'Corner', 'Six Line', 'Dozen', 'Column', 'Red/Black', 'Even/Odd', 'Low/High'])
def handle_bet_type_selection(message):
    bet_type = message.text.lower().replace("/", "").replace(" ", "")
    ask_bet_value(message, bet_type)

def ask_bet_value(message, bet_type):
    markup = types.InlineKeyboardMarkup()

    if bet_type == 'straight':
        for i in range(37):
            markup.add(types.InlineKeyboardButton(str(i), callback_data=f"roulette_value_{bet_type}_{i}"))
    elif bet_type == 'split':
        for i in range(1, 36):
            if i % 3 != 0:
                markup.add(types.InlineKeyboardButton(f"{i}/{i+1}", callback_data=f"roulette_value_{bet_type}_{i}_{i+1}"))
            if i < 34:
                markup.add(types.InlineKeyboardButton(f"{i}/{i+3}", callback_data=f"roulette_value_{bet_type}_{i}_{i+3}"))
    elif bet_type == 'street':
        for i in range(1, 35, 3):
            markup.add(types.InlineKeyboardButton(f"{i}-{i+2}", callback_data=f"roulette_value_{bet_type}_{i}_{i+2}"))
    elif bet_type == 'corner':
        for i in [1, 2, 4, 5, 7, 8, 10, 11, 13, 14, 16, 17, 19, 20, 22, 23, 25, 26, 28, 29, 31, 32, 34]:
            markup.add(types.InlineKeyboardButton(f"{i}/{i+1}/{i+3}/{i+4}", callback_data=f"roulette_value_{bet_type}_{i}_{i+4}"))
    elif bet_type == 'sixline':
        for i in range(1, 34, 3):
            markup.add(types.InlineKeyboardButton(f"{i}-{i+5}", callback_data=f"roulette_value_{bet_type}_{i}_{i+5}"))
    elif bet_type == 'dozen':
        for i in range(1, 4):
            markup.add(types.InlineKeyboardButton(f"Dozen {i}", callback_data=f"roulette_value_{bet_type}_{i}"))
    elif bet_type == 'column':
        for i in range(1, 4):
            markup.add(types.InlineKeyboardButton(f"Column {i}", callback_data=f"roulette_value_{bet_type}_{i}"))
    elif bet_type == 'redblack':
        markup.add(types.InlineKeyboardButton("Red", callback_data=f"roulette_value_{bet_type}_Red"))
        markup.add(types.InlineKeyboardButton("Black", callback_data=f"roulette_value_{bet_type}_Black"))
    elif bet_type == 'evenodd':
        markup.add(types.InlineKeyboardButton("Even", callback_data=f"roulette_value_{bet_type}_Even"))
        markup.add(types.InlineKeyboardButton("Odd", callback_data=f"roulette_value_{bet_type}_Odd"))
    elif bet_type == 'lowhigh':
        markup.add(types.InlineKeyboardButton("Low (1-18)", callback_data=f"roulette_value_{bet_type}_Low"))
        markup.add(types.InlineKeyboardButton("High (19-36)", callback_data=f"roulette_value_{bet_type}_High"))

    bot.send_message(message.from_user.id, f"Select a value for {bet_type} bet", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text.isdigit(), content_types=['text'])
def handle_bet_amount(message):
    game = games[message.from_user.id]

    if game.bet_type is None or game.bet_value is None:
        bot.send_message(message.from_user.id, "Please select a bet type and value first.")
        return

    bet_amount = int(message.text)
    if bet_amount <= 0 or bet_amount > game.credits:
        bot.send_message(message.from_user.id, "Invalid amount. Please enter a valid number of credits.")
        return

    game.add_bet({'type': game.bet_type, 'number': game.bet_value, 'amount': bet_amount})
    game.bet_type, game.bet_value = None, None
    send_game_menu(message)

@bot.message_handler(commands=['easteregg'])
def leaderboard(message):
    log_to_control_chat(f"{message.from_user.username} {message.text}")
    if message.from_user.is_premium:
        reply = random.choice(quotes)
    else:
        reply = "i'm sorry, this command is only available to <b>Telegram Premium</b> users."
    bot.reply_to(message, reply, parse_mode='HTML')

@bot.message_handler(commands=['about'])
def leaderboard(message):
    log_to_control_chat(f"{message.from_user.username} {message.text}")
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
        log_to_control_chat(f"rezzy<=5", False)

@bot.message_handler(func=lambda message: message.text and (BOT_USERNAME in message.text))
def handle_message(message):
    client = OpenAI()
    prompt = message.text.replace(BOT_USERNAME, '').strip()
    prompt_tokens = len(tiktoken.encoding_for_model(OPENAI_MODEL).encode(prompt)) + 7
    max_tokens = OPENAI_MAX_TOKENS - prompt_tokens

    log_to_control_chat(f"{message.from_user.username} ai model={OPENAI_MODEL}, prompt_tokens={prompt_tokens}, max_tokens={max_tokens}")

    try:
        completion = client.chat.completions.create(
            model = OPENAI_MODEL,
            messages = [
                {"role": "system", "content": f"If you need to address me, my name is @{message.from_user.username}.\n" + OPENAI_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            max_tokens = max_tokens
        )
    except Exception as e:
        log_to_control_chat(f"ai error: {e}")
    else:
        reply = completion.choices[0].message.content
        try:
            bot.reply_to(message, reply[:4096], parse_mode='HTML')
        except Exception as e:
            log_to_control_chat(f"bot error: {e}\n\n{completion}")

@bot.message_handler(func=lambda m: True)
def handle_all_messages(message):
    if message.reply_to_message and message.text.startswith('s/'):
        original_text = message.reply_to_message.text
        parts = message.text.split('/')
        pattern, replacement = parts[1], parts[2]
        new_text = re.sub(re.compile(pattern, re.IGNORECASE), replacement, original_text)
        bot.reply_to(message.reply_to_message, new_text[:4096])

    if str(message.chat.id) == CHAT_ID_MAIN:
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
                if emoji.emoji_count(word[0]) > 0:
                    bessage.append(word)
                elif word in DONT_CONVERT:
                    bessage.append(word)
                elif word[0] in VOWELS:
                    bessage.append('b' + word)
                elif word[0] not in VOWELS and word[1] not in VOWELS:
                    bessage.append('b' + word[2:])
                elif any(word.endswith(ending) for ending in CONTRACTION_ENDINGS):
                    bessage.append(word)
                else:
                    bessage.append('b' + word[1:])
            bessage = ' '.join(bessage)
            bot.reply_to(message, bessage)

        result = random.randint(1, 1000)
        if result == 55:
            log_to_control_chat(f"{message.from_user.username} sabre")
            bot.reply_to(message, "thoughts? @SabreDance")
        elif 50 <= result <= 60:
            log_to_control_chat(f"{message.from_user.username} sabre<=5", False)

bot.polling()
