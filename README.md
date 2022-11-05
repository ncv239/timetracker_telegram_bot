# Yet another Time Tracker Telegram Bot

[Youtube Demo](https://youtu.be/ISSHWr3Guss); Telegram Demo -  [@TimeTrackerNCV_bot](https://t.me/TimeTrackerNCV_bot); [REPL.IT Demo](https://replit.com/@ncv239/TelegramBot-FlaskServer)

## Summary:
A [telegram bot](https://core.telegram.org/bots) that helps you to track time spend on diffent projects and helps me (hopefully) to pass the final project submission of the [CS50 Harvard Course](https://cs50.harvard.edu/x/2022/).
 
 
## Description
The bot offers basic functionality to log user-activities. This is done as a timer with start/stop/pause buttons. As soon as the timer is stopped, the activity is considered to be finished and is saved under the user-specified category. In addition to that the user can add/remove the categories and list the saved logs.
 
So that is it in a nutshell! Let's talk about implementation.
 
## Design Challenges:
### Language
Python was the chosen programming language, since I am mostly comfortable with it.
 
### Telegram-Bot-API
Telegram offers a communication channel with the bot via a simple HTTPS-interface, so it is possible to write a low-level web-app for manually sending and receiving HTTP-requests. However, there exists a [variety](https://core.telegram.org/bots/samples) of wrappers to speed the development process up. For this project the [python-telegram-bot](https://python-telegram-bot.org/) library was chosen, since it offers the best documentation.
 
### Hosting
The next problem is to host the bot. The hosting service should stay online 24/7, ideally be free and offer CRUD functionality for bot's data. At first Heroku was under the magnifying glass, but afterwards the [REPLIT](https://replit.com/) was chosen as the most intuitive service with an integrated development environment.
 
 
### Storing the data
The bot has to be able to save users data. So the storage question comes into play. Following approaches considered were
- **sql database** > probably an overkill for this app
- **native python-telegram-bot PicklePersistance** > is simple, but will create a DB file localy. Not desired behaviour, since all files are public in Replit
- **native key-value pair storage of replit** > simple and private, storage of choice
 
 
## Code Walkthrough:

The project structure is damn simple:
- `app.py`
- `bot.py`
- `db.py`
- `helpers.py`

The `helpers.py` file defines some utility functions not worth to be mentioned.

The `bot.py` file desribes the bot itself that is built asyncroniously based on [this](https://docs.python-telegram-bot.org/en/v20.0a4/examples.conversationbot2.html) example. Conceptually the menu functionality is realized in a form of conversation with the `ConversationHandler`, which divides the conversation into steps aka `states` and connects requests to the appropriate callbacks. So at the beginning of the file we define the conversation states, keyboards and callbacks. Later on in the `main()` function we define the database, initialize the bot, register the convesation handler and finally return the instance of the fully-prepared bot.

The `db.py` contains a wrapper to the replit internal database with some helper methods (e.g. default user creation).

The `app.py` file import the preconfigured bot from `bot.py` and starts it. We cannot simply run the `bot_app` because of the replit limitations. The chosen host will stop the script after some sleep time. So we need to create a web-server and send a request to it repetiavly, thus keeping our app running. To do that a flask web server is created with the bot-polling running in parallel. The replit-server recieves requests every 10 min via [cron-jobs](https://cron-job.org/en/). 

However this approach has a downside. Bot-Polling asks the telegram-API for updates continiously and blocks the bandwidth. Polling is a way to receive an update by repeatedly asking server for new information. Most of the server calls will end with *sorry no updates for you, try again later*, being wasted. A far more effecient approach here is to use the so-called webhook - the push update mechanism. The server (telegram API in our case) sends an a HTTP-Post request to the specific URL whenever an update is availabel. The bot at the same time is configured to listen for incoming requests on that specific URL. Therefore the server is called only when it is necessary, thus saving us a lot of API-calls. The last line in `app.py` creates a webhook-connection to telegram server.