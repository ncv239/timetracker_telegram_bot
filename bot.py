import logging
from uuid import uuid4

from telegram import __version__ as TG_VER
try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]
if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        f"This example is not compatible with your current PTB version {TG_VER}. To view the "
        f"{TG_VER} version of this example, "
        f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html"
    )

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
    PicklePersistence
)

from helpers import now_timestamp, timestamp_to_str, timedelta_to_str, aggregate_user_logs, init_user_data, reset_user_data, list_user_logs, save_list_of_rows_to_csv


# Enable logging
logging.basicConfig(filename="log.log", format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)


# Conversation Stages
STATE_START, STATE_TIMER_STARTED, STATE_ADDING_PROJECT, STATE_SETTINGS_DEL_PRJ, \
STATE_SETTING_TZ, STATE_PRJ_SELECTED, STATE_LOG_MENU_ENTERED, STATE_SETTINGS_OPENED = [str(i) for i in range(8)]


# Callback data
GOTO_RECORD, GOTO_LOGS, GOTO_SETTINGS, GOTO_TIMER_PAUSE, GOTO_TIMER_STOP, \
GOTO_TIMER_RESUME, GOTO_RESET, GOTO_LOGS_LIST, GOTO_LOGS_EXPORT, \
GOTO_MAIN_MENU, GOTO_SETTINGS_ADD_PRJ, GOTO_SETTINGS_DEL_PRJ, GOTO_SETTINGS_SET_TZ = [str(i) for i in range(13)]





# Define static inline Keybords
KEYBOARD_START = InlineKeyboardMarkup([[
        InlineKeyboardButton("⏺ Record", callback_data=GOTO_RECORD),
        InlineKeyboardButton("📊 Logs", callback_data=GOTO_LOGS),
        InlineKeyboardButton("⚙️", callback_data=GOTO_SETTINGS),
    ]])

KEYBOARD_TIMER_STARTED = InlineKeyboardMarkup([[
        InlineKeyboardButton("⏸", callback_data=GOTO_TIMER_PAUSE),
        InlineKeyboardButton("⏹", callback_data=GOTO_TIMER_STOP),
    ]])

KEYBOARD_TIMER_PAUSED = InlineKeyboardMarkup([[
        InlineKeyboardButton("⏯", callback_data=GOTO_TIMER_RESUME),
    ]])

KEYBOARD_LOGS = InlineKeyboardMarkup([[
        InlineKeyboardButton("List all logs", callback_data=GOTO_LOGS_LIST),
    ],[
        InlineKeyboardButton("Export as CSV", callback_data=GOTO_LOGS_EXPORT),
    ],[
        InlineKeyboardButton("🗑 Reset", callback_data=GOTO_RESET),
        InlineKeyboardButton("↩ Back", callback_data=GOTO_MAIN_MENU),
    ]])

KEYBOARD_SETTINGS = InlineKeyboardMarkup([[
        InlineKeyboardButton("Add Project", callback_data=GOTO_SETTINGS_ADD_PRJ),
        InlineKeyboardButton("Remove Project", callback_data=GOTO_SETTINGS_DEL_PRJ),
    ], [
        InlineKeyboardButton("Timezone", callback_data=GOTO_SETTINGS_SET_TZ)
    ], [
        InlineKeyboardButton("↩ Back", callback_data=GOTO_MAIN_MENU),
    ]])




async def start(update: Update, context: ContextTypes.DEFAULT_TYPE, start_over: bool = False) -> int:
    ''' Initial callback function when we want to start the bot

    Args:
        update
        context
        start_over: bool - a flag to force bot to end ciurrent conversation and start a new one.
                            Useful, when you want to save a message instead of updating it

    '''
    if update.message:  # user wrote something (probably /start)
        user = update.message.from_user
        logger.info("User %s started the conversation.", user.username)
        logger.info("update.message is not None")

        # create initial user database
        init_user_data(context)
        # send a new message and start a conversation
        await context.bot.send_message(update.effective_user.id, text="Welcome to Time Tracker", reply_markup=KEYBOARD_START)

    else:  # user didnt write anything
        logger.info("User %s started the conversation.", "SCRIPT")
        logger.info("update.message is None")

        query = update.callback_query
        if query and not start_over:  # user pressed inline-keyboard-btn and we receive a query
            logger.info("update.callback_query is not None")
            logger.info(query.to_json())
            # answer the query
            await query.answer()
            # update the current conversation message
            await query.edit_message_text("Welcome to Time Tracker", reply_markup=KEYBOARD_START)
        else:  # user didnt press anything, hard-coded start over
            logger.info("update.callback_query is None")
            # send a new message and start a conversation
            await context.bot.send_message(update.effective_user.id, text="Welcome to Time Tracker", reply_markup=KEYBOARD_START)
    return STATE_START


async def record(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # answer a query (when user clicked an inline-button)
    await update.callback_query.answer()
    logger.info(f"RECORD PRESSED: upd={update.to_json()}")
    # build a keyboard with list of all projects from user database, note that the project name will be send as a callback_data
    keyboard = [[InlineKeyboardButton(prj, callback_data=prj)] for prj in context.user_data["settings"]["projects"]]
    keyboard.append([InlineKeyboardButton("↩ Back", callback_data=GOTO_MAIN_MENU)])

    # update message and a keyboard
    await update.callback_query.edit_message_text(text="Select project to track", reply_markup=InlineKeyboardMarkup(keyboard))

    # return a pointer to the next state in the conversation
    return STATE_PRJ_SELECTED


async def start_timer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query

    # answer the query
    await query.answer()

    # start a log entry
    log_id = uuid4()
    context.user_data["logs"][log_id] = {}
    #context.user_data["logs"][log_id]["start"] = query.message.edit_date  # integer, epoch time
    context.user_data["logs"][log_id]["name"] = query.data  # name of the project (callback data)
    context.user_data["logs"][log_id]["start"] = now_timestamp()  # integer, epoch time
    context.user_data["logs"][log_id]["stop"] = context.user_data["logs"][log_id]["start"]  # DEFAULT VALUE
    context.user_data["logs"][log_id]["pause"] = 0

    # store the key of current log for quick access
    context.user_data["recording"] = log_id

    # edit the message
    await query.edit_message_text(
        text=f'''Timer started
        📝 project: {context.user_data["logs"][log_id]["name"]}
        📅 start: {timestamp_to_str(context.user_data["logs"][log_id]["start"], tz=context.user_data["settings"]["timezone"],
                    fmt="%d.%m.%Y %H:%M:%S")}''',
        reply_markup=KEYBOARD_TIMER_STARTED)

    return STATE_TIMER_STARTED


async def stop_timer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # answer the query
    query = update.callback_query
    await query.answer(text="Timer stopped")

    # add stop log to the user_data
    log_id = context.user_data["recording"]
    context.user_data["logs"][log_id]["stop"] = now_timestamp()

    # reset the current recording to be None
    context.user_data["recording"] = None
    
    # make aliases
    _start = context.user_data["logs"][log_id]["start"]
    _stop = context.user_data["logs"][log_id]["stop"]
    _pause = context.user_data["logs"][log_id]["pause"]
    _tz = context.user_data["settings"]["timezone"]

    # generate new text
    msg_txt = f'''Timer stopped. Log created:
        📝 project:  {context.user_data["logs"][log_id]["name"]}
        📅 start:    {timestamp_to_str(_start, tz=_tz)}
        📅 stop:     {timestamp_to_str(_stop, tz=_tz)}
        🕓 pause:    {timedelta_to_str(_pause)}
        🕓 duration: {timedelta_to_str(_stop - _start - _pause)}'''
    
    # edit text
    await query.edit_message_text(text=msg_txt, reply_markup=None)

    # start over
    return await start(update, context, start_over=True)


async def pause_timer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    # query answer
    await query.answer(text="Timer paused")

    # get the id of current record
    log_id = context.user_data["recording"]
    
    # get new starting point for pause duration
    context.user_data["logs"][log_id]["pause"] = now_timestamp() - context.user_data["logs"][log_id]["pause"]

    # edit msg
    await query.edit_message_text(
        text=f'''Timer paused:
        📝 project: {context.user_data["logs"][log_id]["name"]}
        📅 start:  {timestamp_to_str(context.user_data["logs"][log_id]["start"])}
        📅 paused: {timestamp_to_str(now_timestamp())}''',
        reply_markup=KEYBOARD_TIMER_PAUSED)
    return STATE_START


async def resume_timer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    # answer query
    await query.answer(text="Timer resumed")

    # get the id of current record
    log_id = context.user_data["recording"]

    # calculate pause duration
    context.user_data["logs"][log_id]["pause"] = now_timestamp() - context.user_data["logs"][log_id]["pause"]

    await query.edit_message_text(
        text=f'''Timer resumed:
        📝 project: {context.user_data["logs"][log_id]["name"]}
        📅 start:  {timestamp_to_str(context.user_data["logs"][log_id]["start"])}
        🕓 pause: {timedelta_to_str(context.user_data["logs"][log_id]["pause"])}''',
        reply_markup=KEYBOARD_TIMER_STARTED)
    return STATE_TIMER_STARTED

    
async def logs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    
    # answer query
    await query.answer()

    # logic to aggregate logs
    aggr_Logs, msg = aggregate_user_logs(context)
    
    # update the logs section
    await query.edit_message_text(text=msg, reply_markup=KEYBOARD_LOGS)
    return STATE_LOG_MENU_ENTERED


async def logs_list_table(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    # answer query
    await query.answer()

    # logic to aggregate logs
    log_list, msg = list_user_logs(context)
    # update the logs section
    await query.edit_message_text(text=msg, reply_markup=KEYBOARD_LOGS)
    return STATE_LOG_MENU_ENTERED

async def logs_list_export(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    # answer query
    await query.answer()

    # logic to aggregate logs
    log_list, msg = list_user_logs(context)
    filename = save_list_of_rows_to_csv(log_list, "export.csv")
    
    # update the logs section
    await context.bot.send_document(query["message"]["chat"].id, document=open(filename, "rb"))
    return STATE_LOG_MENU_ENTERED


async def reset_logs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # answer query
    query = update.callback_query
    await query.answer()

    # actually reset logs
    reset_user_data(context, only_logs=True)
    
    # edit the current converasation message
    await query.edit_message_text(text="User Logs were cleared", reply_markup=None)

    #start a new conversation
    return await start(update, context, start_over=True)
    

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # answer query
    query = update.callback_query
    await query.answer()

    # generate a display message
    msg = f'Settings:\n' + '-'*60 + '\n\tTimezone: +' + str(context.user_data["settings"]["timezone"]) + ' GMT' + '\n\tProjects:'
    for prj in sorted(context.user_data["settings"]["projects"]):
        msg += "\n\t\t"+prj

    # edit the msg text
    await query.edit_message_text(text=msg, reply_markup=KEYBOARD_SETTINGS)

    return STATE_SETTINGS_OPENED


async def settings_remove_project_choose(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # answer query
    query = update.callback_query
    await query.answer()


    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(pr, callback_data=pr)] for pr in sorted(context.user_data["settings"]["projects"])])
    msg = "Choose a project to delete from database (entries will be preserved)"
    await update.callback_query.edit_message_text(text=msg, reply_markup=keyboard)
    
    return STATE_SETTINGS_DEL_PRJ


async def settings_remove_project_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # answer query
    query = update.callback_query
    await query.answer(text=f"Project {query.data} deleted from database")

    # delete project from database, it was saved in query.data
    context.user_data["settings"]["projects"].remove(query.data)
    
    # start new conversation
    return await start(update, context)


async def settings_add_project_choose(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # answer query
    query = update.callback_query
    await query.answer()

    msg = "Please type a name of your new project"
    await update.callback_query.edit_message_text(text=msg, reply_markup=None)

    return STATE_ADDING_PROJECT


async def settings_add_project_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # NOTE no need to answer query, since no inline-keyboard button was presses
    logger.info(f"settings_add_project_confirm {update.message.text}")

    # add project to the database
    if not (prj := update.message.text) in context.user_data["settings"]["projects"]:
        context.user_data["settings"]["projects"].append(prj)

    return await start(update, context)


async def settings_set_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # answer query
    query = update.callback_query
    await query.answer()

    msg = f'Current timezone: +{context.user_data["settings"]["timezone"]} GMT.\n\nPlease enter new timezone (set 0 for UTC)'
    await update.callback_query.edit_message_text(text=msg, reply_markup=None)

    return STATE_SETTING_TZ


async def settings_set_timezone_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        tz = int(update.message.text)
    except ValueError:  # if we try to convert a string
        #await update.callback_query.edit_message_text(text="Please enter an integer!", reply_markup=None)
        return STATE_SETTING_TZ
    
    context.user_data["settings"]["timezone"] = tz
    return await start(update, context)


def main(BOT_API_TOKEN) -> None:
    """Run the bot."""
    database = PicklePersistence(filepath='db')

    application = Application.builder().token(BOT_API_TOKEN).persistence(persistence=database).build()


    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            STATE_START: [
                CallbackQueryHandler(record, pattern=GOTO_RECORD),
                CallbackQueryHandler(logs, pattern=GOTO_LOGS),
                CallbackQueryHandler(resume_timer, pattern=GOTO_TIMER_RESUME),
                CallbackQueryHandler(settings, pattern=GOTO_SETTINGS),
            ],
            STATE_SETTINGS_OPENED: [
                CallbackQueryHandler(settings_add_project_choose, pattern=GOTO_SETTINGS_ADD_PRJ),
                CallbackQueryHandler(settings_remove_project_choose, pattern=GOTO_SETTINGS_DEL_PRJ),
                CallbackQueryHandler(settings_set_timezone, pattern=GOTO_SETTINGS_SET_TZ),
                CallbackQueryHandler(start, pattern=GOTO_MAIN_MENU),
            ],
            STATE_PRJ_SELECTED: [
                CallbackQueryHandler(start, pattern=GOTO_MAIN_MENU),
                CallbackQueryHandler(start_timer),
            ],
            STATE_LOG_MENU_ENTERED: [
                CallbackQueryHandler(logs_list_table, pattern=GOTO_LOGS_LIST),
                CallbackQueryHandler(logs_list_export, pattern=GOTO_LOGS_EXPORT),
                CallbackQueryHandler(reset_logs, pattern=GOTO_RESET),
                CallbackQueryHandler(start, pattern=GOTO_MAIN_MENU),
            ],
            STATE_TIMER_STARTED: [
                CallbackQueryHandler(pause_timer, pattern=GOTO_TIMER_PAUSE),
                CallbackQueryHandler(stop_timer, pattern=GOTO_TIMER_STOP),
            ],
            STATE_ADDING_PROJECT: [
                MessageHandler(filters.ALL, settings_add_project_confirm),
            ],
            STATE_SETTINGS_DEL_PRJ: [
                CallbackQueryHandler(settings_remove_project_confirm),
            ],
            STATE_SETTING_TZ: [
                MessageHandler(filters.ALL, settings_set_timezone_confirm),
            ],
        },
        fallbacks=[CommandHandler('start', start)],
    )

    # Register conv handler
    application.add_handler(conv_handler)

    # Start the Bot
    #application.run_polling()

    return application