from datetime import datetime
from imp import get_suffixes
from replit import db
from datetime import datetime, timedelta
# from pandas import DataFrame
from uuid import uuid4
from pandas import Timedelta

PROJECTLIST = [
    "Work",
    "Sport",
    "Education",
    "Portfolio"
]

class StatsDB():
    def __init__(self):
        self.db = db
        self._default_user = {"user_name": "", "logs": {}, "projects": PROJECTLIST, "timezone": 0}

    
    def add_user(self, user_id: str, user_name: str):
        if user_id not in self.db.keys():
            self.db[user_id] =  self._default_user
        else:
            print(f"Cannot add user with the Id {user_id}. This Id already exists in the Database")
    
    def get_user(self, user_id: str) -> dict:
        if user_id in self.db.keys():
            return self.db[user_id]
        else:
            print(f"User with the Id {user_id} does not exist in the Database")
            return {}
    
    def list_users(self) -> str:
        msg = ""
        for userid in self.db.keys():
            msg += f"username: {self.db[userid]['user_name']}, id: {userid}"
            msg += "\n"
        return msg

    def add_log(self, user_id: str, topic: str, start: datetime, end: datetime, pause: timedelta, duration: timedelta):
        self.get_user(user_id)["logs"][str(uuid4())] = [topic, start.isoformat(), end.isoformat(), Timedelta(pause).isoformat(), Timedelta(duration).isoformat()]

    def get_log(self, user_id: str, log_id: str) -> dict:
        usr = self.get_user(user_id)
        if log_id in usr["logs"].keys():
            return usr["logs"][log_id]
        else:
            raise ValueError(f"Log with the Id {log_id} does not exist in the Database of the user {user_id}")
    
    def get_stats(self, user_id: str) -> str:
        usr = self.get_user(user_id)
        
        date_earliest = datetime.max.replace(tzinfo=None)
        date_latest = datetime.min.replace(tzinfo=None)

        topics_count = {}
        topics_duration = {}

        for _, log in usr["logs"].items():
            topic, start, end, pause, duration = log[0], datetime.fromisoformat(log[1]).replace(tzinfo=None), datetime.fromisoformat(log[2]).replace(tzinfo=None), Timedelta(log[3]), Timedelta(log[4])
            
            if start < date_earliest:
                date_earliest = start
            if end > date_latest:
                date_latest = end

            if topic not in topics_count:
                topics_count[topic] = 0
            topics_count[topic] += 1

            if topic not in topics_duration:
                topics_duration[topic] = timedelta()
            topics_duration[topic] += end-start-pause
        
        msg = f"Stats:\n📅 {date_earliest.strftime('%d-%m-%Y')} - {date_latest.strftime('%d-%m-%Y')}\n------------------\n"
        for t in topics_count.keys():
            substring = f"📝 {t}: {topics_count[t]} logs, 🕓 total time {timedelta(days=topics_duration[t].days, seconds=topics_duration[t].seconds//60)}\n"
            msg += substring
        
        return msg
    
    def reset_stats(self, user_id: str):
        self.db[user_id]["logs"] = {}
    

    def add_project(self, user_id: str, prj: str):
        if not "projects" in self.db[user_id].keys():
            self.db[user_id]["projects"] = PROJECTLIST
        
        if prj in self.db[user_id]["projects"]:
            print(f"Project {prj} already exists in the Database. Skipping")
            return
        
        self.db[user_id]["projects"].append(prj)

    def remove_project(self, user_id: str, prj: str):
        if not prj in self.db[user_id]["projects"]:
            print(f"Project {prj} does not exist in the Database")
            return

        prj_index = self.db[user_id]["projects"].index(prj)
        del self.db[user_id]["projects"][prj_index]

    def get_projects(self, user_id: str) -> list:
        user = self.get_user(user_id)
        if user and "projects" in user.keys():  # if the user exists
            return user["projects"]
        else:
            return []


    def set_timezone(self, user_id: str, tz: int):
        user = self.get_user(user_id)
        user["timezone"] = tz


    def get_timezone(self, user_id: str) -> int:
        user = self.get_user(user_id)
        if "timezone" in user.keys():
            return user["timezone"]
        else:
            print("No Timzone information found, returning UTC (offset=0)")
            return 0