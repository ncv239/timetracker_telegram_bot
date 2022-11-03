from replit import db
from helpers import now_timestamp, timestamp_to_str, timedelta_to_str
from telegram.ext import ContextTypes
from itertools import groupby
from typing import Tuple, List


PROJECTLIST = [
    "Work",
    "Sport",
    "Education",
    "Portfolio"
]


class Storage():
    ''' A wrapper to the replit internal database. Note that in order to use it outside REPLIT platform,
    you must provide a URL to the storage (line `self.db = db` will not work)
    '''
    def __init__(self):
        self.db = db
    
    def add_user(self, user_id: int):
        user_id = str(user_id)
        if user_id not in self.db.keys():
            self.db[user_id] = {}
            self.init_user_data(user_id)
        else:
            print(f"Cannot add user with the Id {user_id}. This Id already exists in the Database")
    
    def user_data(self, user_id: int) -> dict:
        user_id = str(user_id)
        if user_id not in self.db.keys():
            self.add_user(user_id)
        return self.db[user_id]
    

    def init_user_data(self, user_id: int) -> None:
        ''' Function to initialise the data-structure of the current TG-User
        '''
        user_id = str(user_id)
        if not "settings" in self.db[user_id].keys():
            self.db[user_id]["settings"] = {}
            self.db[user_id]["settings"]["timezone"] = 0
            self.db[user_id]["settings"]["projects"] = PROJECTLIST
        if not "logs" in self.db[user_id].keys():
            self.db[user_id]["logs"] = {}  # a placeholder-dict for future logs
        
        self.db[user_id]["recording"] = None  # a placeholder to hold the ID of the current log

    def reset_user_data(self, user_id: int, only_logs: bool=False) -> None:
        ''' Function to clear the data of the current TG-User
        '''
        user_id = str(user_id)
        if only_logs:
            self.db[user_id]["logs"].clear()
            self.db[user_id]["recording"] = None
        else:
            self.db[user_id].clear()
            self.init_user_data(user_id)


    def aggregate_user_logs(self, user_id: int) -> Tuple[dict, str]:
        ''' Cerate a summary of user logs and return a dictionary + a string
        '''
        user_id = str(user_id)
        data = self.db[user_id]["logs"].values()
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


    def list_user_logs(self, user_id: int) -> Tuple[list, str]:
        ''' Helper function to collect user logs into a 2-d table (list of rows) and a string-representation
        '''
        user_id = str(user_id)
        rows = []
        header = ["id", "START", "STOP", "PROJECT", "DURATION", "PAUSE"]
        rows.append(header)
        rows_to_print = []
        header_to_print = ["START", "STOP", "PROJECT", "DURATION"]
        rows_to_print.append(header_to_print)
        rows_to_print.append("-" * 60)  # horizontal line
        
        # generate data
        for i, log in enumerate(self.db[user_id]["logs"].values()):
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
