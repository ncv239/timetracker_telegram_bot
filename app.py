import os
from flask import Flask
import bot

API_TOKEN = os.environ['BOT_API_KEY']
PORT = int(os.environ.get('PORT', '8443'))
DEBUG_MODE = True

app = Flask(__name__)

@app.route('/')
def index():
    return 'index'


if __name__ == "__main__":
    bot_app = bot.main(API_TOKEN)
    
    if DEBUG_MODE:
      # use polling and flask app
        bot_app.run_polling()
        app.run(host='0.0.0.0', port=81)
    
    else:
        # use webhook on replit
        # add handlers
        bot_app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=API_TOKEN,
            webhook_url="https://TelegramBot-FlaskServer.ncv239.repl.co/" + API_TOKEN
        )

