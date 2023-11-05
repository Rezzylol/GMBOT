import telebot
import datetime
import os
import csv

API_KEY = os.getenv('API_KEY')
print(API_KEY)
bot = telebot.TeleBot(API_KEY)

checkin_data_path = '/data/checkin_data.csv'

if not os.path.exists(checkin_data_path):
    with open(checkin_data_path, 'w', newline='') as csvfile:
        fieldnames = ['user_id', 'username', 'date', 'checkin_count']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

checkin_counts = {}

@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.send_message(message.chat.id, "omg haiiiii :3c")

@bot.message_handler(func=lambda message: message.text.lower() in ['good morning', 'gm', 'good morning beverage', 'gm beverage'])
def handle_checkin(message):
    user_id = message.from_user.id
    username = message.from_user.username
    today = datetime.date.today().strftime('%Y-%m-%d')

    if user_id in checkin_counts and checkin_counts[user_id]['date'] == today:
        count = checkin_counts[user_id]['checkin_count']
        bot.send_message(message.chat.id, f"Good morning again, @{username}! Love the enthusiasm, but you've already checked in, like, {count} times today.")
    else:
        if user_id not in checkin_counts:
            checkin_counts[user_id] = {'username': username, 'date': today, 'checkin_count': 1}
        else:
            checkin_counts[user_id]['checkin_count'] += 1

        with open(checkin_data_path, 'a', newline='') as csvfile:
            fieldnames = ['user_id', 'username', 'date', 'checkin_count']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writerow({'user_id': user_id, 'username': username, 'date': today, 'checkin_count': checkin_counts[user_id]['checkin_count']})

        bot.send_message(message.chat.id, f"Good morning, @{username}! You've been checked in for today.")

@bot.message_handler(commands=['leaderboard'])
def handle_leaderboard(message):
    user_totals = {}
    with open(checkin_data_path, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            user_id = int(row['user_id'])
            checkin_count = int(row['checkin_count'])
            if user_id in user_totals:
                user_totals[user_id] += checkin_count
            else:
                user_totals[user_id] = checkin_count

    # Sort users by total check-in count and send leaderboard message
    sorted_users = sorted(user_totals.items(), key=lambda x: x[1], reverse=True)[:10]
    leaderboard_message = "Leaderboard:\n"
    for rank, (user_id, total_checkins) in enumerate(sorted_users, start=1):
        username = checkin_counts[user_id]['username']
        leaderboard_message += f"{rank}. @{username}: {total_checkins} check-ins\n"
    bot.send_message(message.chat.id, leaderboard_message)

if __name__ == "__main__":
    bot.polling(none_stop=True)
