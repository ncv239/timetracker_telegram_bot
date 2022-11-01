import os
from flask import Flask
import bot

API_TOKEN = os.environ['BOT_API_KEY']


app = Flask(__name__)

@app.route('/')
def index():
    return 'Hello, from Flask!'


if __name__ == "__main__":
  bot_app = bot.main(API_TOKEN)
  bot_app.run_polling()
  app.run(host='0.0.0.0', port=81)

