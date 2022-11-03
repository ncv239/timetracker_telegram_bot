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


def save_list_of_rows_to_csv(list_of_rows: List[list], filename: str = "dummy.csv") -> str:
    ''' function saves a list of lists into CSV file'''
    with open(filename, "w") as f:
        writer = csv.writer(f)
        writer.writerows(list_of_rows)
    return filename

