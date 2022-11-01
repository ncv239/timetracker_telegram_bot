from datetime import datetime, timedelta
from telegram.ext import ContextTypes
from itertools import groupby
from typing import Tuple, List
import csv


PROJECTLIST = [
    "Work",
    "Sport",
    "Education",
    "Portfolio"
]


def now_timestamp() -> int:
    ''' return current date and time in epoch time '''
    return int(round(datetime.now().timestamp()))


def timestamp_to_str(ts: int, tz: int = 0, fmt: str = "%d.%m.%Y %H:%M") -> str:
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


def list_user_logs(context: ContextTypes.DEFAULT_TYPE) -> Tuple[list, str]:
    rows = []
    header = ["id", "START", "STOP", "PROJECT", "DURATION", "PAUSE"]
    rows.append(header)
    rows_to_print = []
    header_to_print = ["START", "STOP", "PROJECT", "DURATION"]
    rows_to_print.append(header_to_print)
    rows_to_print.append("-" * 60)  # horizontal line
    
    # generate data
    for i, log in enumerate(context.user_data["logs"].values()):
        row = [str(i), timestamp_to_str(log["start"]), timestamp_to_str(log["stop"]), log["name"], timedelta_to_str(log["stop"] - log["start"] - log["pause"]), timedelta_to_str(log["pause"])]
        row_to_print = [timestamp_to_str(log["start"]), timestamp_to_str(log["stop"]), log["name"], timedelta_to_str(log["stop"] - log["start"] - log["pause"])]
        rows.append(row)
        rows_to_print.append(row_to_print)

    # create a message
    msg = ""
    for row in rows_to_print:
        if isinstance(row, str):
            msg += row+'\n'
            continue

        line = " - ".join(row)
        line += '\n'
        msg += line

    return rows, msg


def save_list_of_rows_to_csv(list_of_rows: List[list], filename: str = "dummy.csv") -> str:
    ''' function saves a list of lists into CSV file'''
    with open(filename, "w") as f:
        writer = csv.writer(f)
        writer.writerows(list_of_rows)
    return filename


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
