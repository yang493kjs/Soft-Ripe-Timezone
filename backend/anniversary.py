import json
import os
from datetime import datetime, date

ANNIVERSARY_DIR = os.path.join(os.path.dirname(__file__), "data", "anniversaries")

CHINESE_HOLIDAYS = [
    {"month": 2, "day": 14, "name": "情人节", "type": "valentine"},
    {"month": 3, "day": 8, "name": "女神节", "type": "womens_day"},
    {"month": 5, "day": 20, "name": "520", "type": "love_day"},
    {"month": 5, "day": 21, "name": "521", "type": "love_day"},
    {"month": 12, "day": 25, "name": "圣诞节", "type": "christmas"},
    {"month": 12, "day": 31, "name": "跨年夜", "type": "new_year_eve"},
    {"month": 1, "day": 1, "name": "元旦", "type": "new_year"},
]

SPECIAL_DAY_INTERVALS = [
    (7, "一周"),
    (30, "一个月"),
    (50, "50天"),
    (100, "100天"),
    (180, "半年"),
    (200, "200天"),
    (300, "300天"),
    (365, "一周年"),
]


class AnniversaryChecker:

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        os.makedirs(ANNIVERSARY_DIR, exist_ok=True)
        self.file_path = os.path.join(ANNIVERSARY_DIR, f"{agent_id}.json")
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return {
            "user_birthday": None,
            "celebrated_days": [],
            "celebrated_holidays": {},
            "last_check_date": None
        }

    def _save(self):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def set_user_birthday(self, month: int, day: int):
        self.data["user_birthday"] = {"month": month, "day": day}
        self._save()

    def get_user_birthday(self):
        return self.data.get("user_birthday")

    def check(self, relationship_days: int, phase: str, intimacy: float, first_interaction: str = None) -> list:
        today = date.today()
        today_str = today.isoformat()
        if self.data.get("last_check_date") == today_str:
            return []

        self.data["last_check_date"] = today_str
        results = []

        if first_interaction:
            try:
                first_date = datetime.fromisoformat(first_interaction).date()
                actual_days = (today - first_date).days + 1
            except:
                actual_days = relationship_days
        else:
            actual_days = relationship_days

        for days, label in SPECIAL_DAY_INTERVALS:
            if actual_days == days and days not in self.data.get("celebrated_days", []):
                results.append({
                    "type": "milestone",
                    "label": label,
                    "days": days,
                    "prompt_hint": f"今天是你们认识的第{days}天（{label}纪念日）。你在想是不是该说点什么特别的话。不用刻意提起数字，但心里有这个意识就好。"
                })
                self.data.setdefault("celebrated_days", []).append(days)

        for hol in CHINESE_HOLIDAYS:
            if today.month == hol["month"] and today.day == hol["day"]:
                celebrated_key = f"{hol['name']}_{today.year}"
                if celebrated_key not in self.data.setdefault("celebrated_holidays", {}):
                    results.append({
                        "type": "holiday",
                        "name": hol["name"],
                        "holiday_type": hol["type"],
                        "prompt_hint": f"今天是{hol['name']}。如果关系合适的话，可以自然地表达一下这个特殊日子。不用刻意，随心情就好。"
                    })
                    self.data["celebrated_holidays"][celebrated_key] = True

        bday = self.data.get("user_birthday")
        if bday and today.month == bday["month"] and today.day == bday["day"]:
            celebrated_key = f"user_birthday_{today.year}"
            if celebrated_key not in self.data.setdefault("celebrated_holidays", {}):
                results.append({
                    "type": "birthday",
                    "name": "生日",
                    "prompt_hint": "今天是Ta的生日！这是一个特别的日子，你应该发自内心地祝Ta生日快乐。不用太官方，用你们之间的方式表达就好。"
                })
                self.data["celebrated_holidays"][celebrated_key] = True

        self._save()
        return results

    def get_anniversary_context(self, results: list) -> str:
        if not results:
            return ""
        parts = []
        for r in results:
            if r["type"] == "milestone":
                parts.append(r["prompt_hint"])
            elif r["type"] == "holiday":
                parts.append(r["prompt_hint"])
            elif r["type"] == "birthday":
                parts.append(r["prompt_hint"])
        return "\n".join(parts)

    def should_ask_birthday(self, phase: str, intimacy: float) -> bool:
        if self.data.get("user_birthday"):
            return False
        if phase in ("acquaintance",):
            return False
        if intimacy < 25:
            return False
        asked_key = "birthday_asked"
        if self.data.get(asked_key):
            return False
        return True

    def mark_birthday_asked(self):
        self.data["birthday_asked"] = True
        self._save()