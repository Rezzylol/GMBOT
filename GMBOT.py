import telebot
import datetime
import os
import csv

print(f"Bot started at: {datetime.datetime.now()}")

API_KEY = os.getenv('API_KEY')
bot = telebot.TeleBot(API_KEY)

user_data = {}
checkin_data_path = '/data/checkin_data.csv'
if os.path.exists(checkin_data_path):
    with open(checkin_data_path, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            user_id = int(row['user_id'])
            date = row['date']
            checkin_count = int(row['checkin_count'])
            if user_id not in user_data:
                user_data[user_id] = {'username': row['username'], 'streak': 0, 'total_checkins': 0, 'last_checkin_date': None, 'attempt_count': 0}
            user_data[user_id]['total_checkins'] += checkin_count
            if user_data[user_id]['last_checkin_date'] == date:
                user_data[user_id]['streak'] += 1
            else:
                user_data[user_id]['streak'] = 1
            user_data[user_id]['last_checkin_date'] = date
            user_data[user_id]['attempt_count'] = 0

@bot.message_handler(commands=['start'])
def handle_start(message):
    print(f"{datetime.datetime.now()} {message.from_user.username} /start")

    bot.send_message(message.chat.id, "omg haiiiii :3c")

@bot.message_handler(func=lambda message: message.text.lower() in ['good morning', 'gm', 'good morning beverage', 'gm beverage'])
def handle_checkin(message):
    print(f"{datetime.datetime.now()} {message.from_user.username} gm")
    user_id = message.from_user.id
    username = message.from_user.username
    today = datetime.date.today().strftime('%Y-%m-%d')
        else:
            user_data[user_id]['streak'] = 1
            user_data[user_id]['attempt_count'] = 1
        user_data[user_id]['last_checkin_date'] = today

        with open(checkin_data_path, 'a', newline='') as csvfile:
            fieldnames = ['user_id', 'username', 'date', 'checkin_count']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writerow({'user_id': user_id, 'username': username, 'date': today, 'checkin_count': 1})

@bot.message_handler(commands=['leaderboard'])
def handle_leaderboard(message):
    print(f"{datetime.datetime.now()} {message.from_user.username} /leaderboard")
    sorted_streaks = sorted(user_data.items(), key=lambda x: x[1]['streak'], reverse=True)[:5]
    leaderboard_message = "Streak:\n"
    for rank, (user_id, data) in enumerate(sorted_streaks, start=1):
        username = data['username']
        streak = data['streak']
        leaderboard_message += f"{rank}. @{username} - {streak} days\n"
    leaderboard_message += "\n"
    sorted_checkins = sorted(user_data.items(), key=lambda x: x[1]['total_checkins'], reverse=True)[:5]
    leaderboard_message += "Check-ins:\n"
    for rank, (user_id, data) in enumerate(sorted_checkins, start=1):
        username = data['username']
        total_checkins = data['total_checkins']
        leaderboard_message += f"{rank}. @{username} - {total_checkins}\n"
    bot.send_message(message.chat.id, leaderboard_message)

if __name__ == "__main__":
    bot.polling(none_stop=True)
