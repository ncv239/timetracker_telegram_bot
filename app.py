import os
from flask import Flask
import bot

API_TOKEN = os.environ['BOT_API_KEY']
PORT = int(os.environ.get('PORT', '8443'))
APP_URL = os.environ['APP_URL']
WEBHOOKMODE = False

app = Flask(__name__)

@app.route('/')
def index():
    return 'index'


if __name__ == "__main__":
    bot_app = bot.main(API_TOKEN)
    if not WEBHOOKMODE:
      # use polling
        bot_app.run_polling()
        app.run(host='0.0.0.0', port=81)
    else:
        # use webhook on replit
        bot_app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=API_TOKEN,
            webhook_url=APP_URL + API_TOKEN
        )

