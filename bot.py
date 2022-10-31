import logging
import os
from datetime import datetime, timedelta, timezone
from db import StatsDB

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    CallbackContext,
    Filters,
)

# Create a database handler
db = StatsDB()


# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)


# Stages
ZERO, STATE_START, SECOND, STATE_TIMER_STARTED, STATE_ADDING_PROJECT, STATE_REMOVING_PROJECT, STATE_SETTING_TZ = range(7)


# Callback data
ONE, TWO, THREE, FOUR = range(4)


# Define static inline Keybords
KEYBOARD_START = [[
        InlineKeyboardButton("⏺ Record", callback_data=str(ONE)),
        InlineKeyboardButton("📊 Logs", callback_data=str(TWO)),
        InlineKeyboardButton("⚙️", callback_data="##settings"),
    ]]

KEYBOARD_TIMER_STARTED = [[
        InlineKeyboardButton("⏸", callback_data="##pause_timer"),
        InlineKeyboardButton("⏹", callback_data="##stop_timer"),
    ]]

KEYBOARD_TIMER_PAUSED = [[
        InlineKeyboardButton("⏯", callback_data="##resume_timer"),
    ]]

KEYBOARD_LOGS = [[
        InlineKeyboardButton("🗑 Reset", callback_data="##reset_stats"),
        InlineKeyboardButton("↩ Back", callback_data="##start_over"),
    ]]

KEYBOARD_SETTINGS = [[
        InlineKeyboardButton("Add Project", callback_data="##settings_add_project"),
        InlineKeyboardButton("Remove Project", callback_data="##settings_remove_project"),
    ], [
        InlineKeyboardButton("Timezone", callback_data="##timezone")
    ], [
        InlineKeyboardButton("↩ Back", callback_data="##start_over"),
    ]]


def dtprint(dt, tz_offset=0) -> str:
    print("current tz_offset=", tz_offset)
    if type(dt) is datetime:
        return dt.astimezone(tz=timezone(timedelta(hours=tz_offset))).strftime("%d-%m-%Y %H:%M")
    elif type(dt) is timedelta:
        return timedelta(days=dt.days, seconds=dt.seconds)
    else:
        return ""


def start(update: Update, context: CallbackContext) -> int:
    if update.message is not None:
        user = update.message.from_user
        logger.info("User %s started the conversation.", user.username)
        db.add_user(str(user.id), user.username)
    else:
        logger.info("User %s started the conversation.", "SCRIPT")
    update.message.reply_text("Welcome to Time Tracker", reply_markup=InlineKeyboardMarkup(KEYBOARD_START))
    return STATE_START


def record(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    keyboard = [[InlineKeyboardButton(pr, callback_data=pr)] for pr in db.get_projects(str(update.effective_user.id))]
    query.edit_message_text(text="Select project to track", reply_markup=InlineKeyboardMarkup(keyboard))
    return SECOND


def start_timer(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    context.user_data["start"] = datetime.now()
    # context.user_data["start"] = query.message.edit_date
    context.user_data["prj"] = query.data  # store the selected project
    query.edit_message_text(
        text=f'''Timer started
        📝 project: {context.user_data["prj"]}
        📅 start: {dtprint(context.user_data["start"], db.get_timezone(str(update.effective_user.id)))}''', reply_markup=InlineKeyboardMarkup(KEYBOARD_TIMER_STARTED))
    return STATE_TIMER_STARTED

def stop_timer(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    query = update.callback_query
    query.answer()
    context.user_data["stop"] = datetime.now()
    # context.user_data["stop"] = query.message.edit_date
    if not "pause" in context.user_data:
        context.user_data["pause"] = timedelta()
    context.user_data["duration"] = context.user_data["stop"]-context.user_data["start"]-context.user_data["pause"]

    db.add_log(str(user.id), context.user_data["prj"], context.user_data["start"], context.user_data["stop"], context.user_data["pause"], context.user_data["duration"])

    msg_txt = f'''Timer stopped. Log created:
        📝 project:  {context.user_data["prj"]}
        📅 start:    {dtprint(context.user_data["start"], db.get_timezone(str(update.effective_user.id)))}
        📅 stop:     {dtprint(context.user_data["stop"], db.get_timezone(str(update.effective_user.id)))}
        🕓 pause:    {dtprint(context.user_data["pause"], db.get_timezone(str(update.effective_user.id)))}
        🕓 duration: {dtprint(context.user_data["duration"], db.get_timezone(str(update.effective_user.id)))}'''
    
    context.user_data["pause"] = timedelta()  # reset pause duration
    update.callback_query.edit_message_text(text=msg_txt, reply_markup=None)
    return start_over(update, context)


def pause_timer(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    context.user_data["pause_start"] = datetime.now()
    # context.user_data["pause_start"] = query.message.edit_date
    query.edit_message_text(
        text=f'''Timer paused:
        📝 project: {context.user_data["prj"]}
        📅 start:  {dtprint(context.user_data["start"], db.get_timezone(str(update.effective_user.id)))}
        📅 paused: {dtprint(context.user_data["pause_start"], db.get_timezone(str(update.effective_user.id)))}''',
        reply_markup=InlineKeyboardMarkup(KEYBOARD_TIMER_PAUSED))
    return STATE_START


def resume_timer(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    context.user_data["pause_end"] = datetime.now()
    # context.user_data["pause_end"] = query.message.edit_date
    if not "pause" in context.user_data:
        context.user_data["pause"] = timedelta()
    context.user_data["pause"] += context.user_data["pause_end"] - context.user_data["pause_start"]
    query.edit_message_text(
        text=f'''Timer resumed:
        📝 project: {context.user_data["prj"]}
        📅 start:  {dtprint(context.user_data["start"], db.get_timezone(str(update.effective_user.id)))}
        🕓 pause: {dtprint(context.user_data["pause"], db.get_timezone(str(update.effective_user.id)))}''', reply_markup=InlineKeyboardMarkup(KEYBOARD_TIMER_STARTED))
    return STATE_TIMER_STARTED

    
def stats(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    query = update.callback_query
    query.answer()
    query.edit_message_text(text=db.get_stats(str(user.id)), reply_markup=InlineKeyboardMarkup(KEYBOARD_LOGS))
    return SECOND


def reset_stats(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    db.reset_stats(str(user.id))
    query = update.callback_query
    query.answer()
    query.edit_message_text(text="Statistics logs were cleared", reply_markup=None)
    return start_over(update, context)
    

def start_over(update: Update, context: CallbackContext) -> int:
    if update.callback_query is not None and update.callback_query.data == "##start_over":  # if we have been rerouted here from "Back"
        update.callback_query.edit_message_text(text="Welcome to Time Tracker", reply_markup=InlineKeyboardMarkup(KEYBOARD_START))
    else:
        context.bot.send_message(update.effective_user.id, text="Welcome to Time Tracker", reply_markup=InlineKeyboardMarkup(KEYBOARD_START))
    return STATE_START

def settings(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    msg = f"Following Projects are registered:\n"+'\n'.join(['\t'+prj for prj in db.get_projects(str(user.id))])
    update.callback_query.edit_message_text(text=msg, reply_markup=InlineKeyboardMarkup(KEYBOARD_SETTINGS))
    return SECOND

def settings_remove_project_choose(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    keyboard = [[InlineKeyboardButton(pr, callback_data=pr)] for pr in db.get_projects(str(user.id))]
    msg = "Choose a project to delete from database (entries will be preserved)"
    update.callback_query.edit_message_text(text=msg, reply_markup=InlineKeyboardMarkup(keyboard))
    return STATE_REMOVING_PROJECT


def settings_remove_project_confirm(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    prj: str = update.callback_query.data
    db.remove_project(str(user.id), prj)
    update.callback_query.data = "##start_over"  #overwrite callback data to toggle desired behaviour in start_over
    return start_over(update, context)


def settings_add_project_choose(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    msg = "Please type a name of your new project"
    update.callback_query.edit_message_text(text=msg, reply_markup=None)
    return STATE_ADDING_PROJECT


def settings_add_project_confirm(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    db.add_project(str(user.id), update.message.text)
    return start_over(update, context)


def settings_set_timezone(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    msg = f"Current timezone offset is set to +{db.get_timezone(str(update.effective_user.id))}.\n\nPlease enter the new timezone offset (set 0 for UTC)"
    update.callback_query.edit_message_text(text=msg, reply_markup=None)
    return STATE_SETTING_TZ


def settings_set_timezone_confirm(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    try:
        offset = int(update.message.text)
    except:
        update.callback_query.edit_message_text(text="Please enter an integer!", reply_markup=None)
        return STATE_SETTING_TZ

    db.set_timezone(str(user.id), offset)
    return start_over(update, context)


def main(BOT_API_TOKEN) -> None:
    """Run the bot."""
    updater = Updater(BOT_API_TOKEN)

    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            STATE_START: [
                CallbackQueryHandler(record, pattern='^' + str(ONE) + '$'),
                CallbackQueryHandler(stats, pattern='^' + str(TWO) + '$'),
                CallbackQueryHandler(resume_timer, pattern="##resume_timer"),
                CallbackQueryHandler(settings, pattern="##settings"),
            ],
            SECOND: [
                CallbackQueryHandler(reset_stats, pattern='##reset_stats'),
                CallbackQueryHandler(start_over, pattern='##start_over'),
                CallbackQueryHandler(settings_add_project_choose, pattern='##settings_add_project'),
                CallbackQueryHandler(settings_remove_project_choose, pattern='##settings_remove_project'),
                CallbackQueryHandler(settings_set_timezone, pattern='##timezone'),
                CallbackQueryHandler(start_timer),
            ],
            STATE_TIMER_STARTED: [
                CallbackQueryHandler(pause_timer, pattern="##pause_timer"),
                CallbackQueryHandler(stop_timer, pattern="##stop_timer"),
            ],
            STATE_ADDING_PROJECT: [
                MessageHandler(Filters.all, settings_add_project_confirm),
            ],
            STATE_REMOVING_PROJECT: [
                CallbackQueryHandler(settings_remove_project_confirm),
            ],
            STATE_SETTING_TZ: [
                MessageHandler(Filters.all, settings_set_timezone_confirm),
            ],
        },
        fallbacks=[CommandHandler('start', start)],
    )

    # Add ConversationHandler to dispatcher that will be used for handling updates
    dispatcher.add_handler(conv_handler)

    # Start the Bot
    updater.start_polling()
    #updater.start_webhook()
    return updater

if __name__ == '__main__':
    upd = main(os.environ['BOT_API_KEY'])
    upd.idle()