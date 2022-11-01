from datetime import datetime, timedelta
from telegram.ext import ContextTypes
from itertools import groupby
from typing import Tuple



PROJECTLIST = [
    "Work",
    "Sport",
    "Education",
    "Portfolio"
]


def now_timestamp() -> int:
    ''' return current date and time in epoch time '''
    return int(round(datetime.now().timestamp()))


def timestamp_to_str(ts: int, tz: int = 0, fmt: str = "%d-%m-%Y %H:%M") -> str:
    ''' convert a epoch timestamp to a human-readable string representation
    Args:
        ts : int - timestamp in seconds
        tz : int - timezone in hours (0 to 23)
        fmt : str - format of the return string
    '''
    return datetime.fromtimestamp(ts + tz*3600).strftime(fmt)

def timedelta_to_str(sec: int) -> str:
    return str(timedelta(seconds = sec))


def aggregate_user_logs(context: ContextTypes.DEFAULT_TYPE) -> Tuple[dict, str]:
    ''' Cerate a summary of user logs and return a dictionary + a string
    '''
    data = context.user_data["logs"].values()
    out = {}

    # populate the output dictionary
    for prj_name, grouped_logs in groupby(data, key=lambda x: x["name"]):
        item = {}
        grouped_logs = list(grouped_logs)
        out[prj_name] = {
            "duration": sum((log["stop"] - log["start"] - log["pause"]) for log in grouped_logs),
            "n_logs": len(grouped_logs)
            }
    # generate a nice string
    msg = f"Summary (Project Total Duration):\n" + "-"*60 +"\n"
    for prj_name in sorted(out.keys()):
        msg += f"📝 {prj_name} ({out[prj_name]['n_logs']:3d} logs): {timedelta_to_str(out[prj_name]['duration'])}\n"

    return (out, msg)


def reset_user_data(context: ContextTypes.DEFAULT_TYPE, only_logs=False) -> None:
    ''' Function to clear the data of the current TG-User
    '''
    if only_logs:
        context.user_data["logs"].clear()
        context.user_data["recording"] = None
    else:
        context.user_data.clear()
        init_user_data(context)


def init_user_data(context: ContextTypes.DEFAULT_TYPE) -> None:
    ''' Function to initialise the data-structure of the current TG-User
    '''
    if not "settings" in context.user_data.keys():
        context.user_data["settings"] = {}
        context.user_data["settings"]["timezone"] = 0
        context.user_data["settings"]["projects"] = PROJECTLIST
    if not "logs" in context.user_data.keys():
        context.user_data["logs"] = {}  # a placeholder-dict for future logs
    
    context.user_data["recording"] = None  # a placeholder to hold the ID of the current log
