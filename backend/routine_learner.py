import json
import os
from datetime import datetime, timedelta
from collections import defaultdict

ROUTINE_DIR = os.path.join(os.path.dirname(__file__), "data", "routines")
DEFAULT_WINDOW_DAYS = 14


class RoutineLearner:

    def __init__(self, agent_id: str, window_days: int = DEFAULT_WINDOW_DAYS):
        self.agent_id = agent_id
        self.window_days = window_days
        os.makedirs(ROUTINE_DIR, exist_ok=True)
        self.file_path = os.path.join(ROUTINE_DIR, f"{agent_id}.json")
        self.data = self._load()
        self._cleanup_old_data()

    def _load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return {
            "hourly_activity": {},
            "learning_started": datetime.now().isoformat(),
            "confidence": 0.0
        }

    def _save(self):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def _cleanup_old_data(self):
        cutoff = (datetime.now() - timedelta(days=self.window_days)).isoformat()[:10]
        hourly = self.data.get("hourly_activity", {})
        for date_str in list(hourly.keys()):
            if date_str < cutoff:
                del hourly[date_str]

    def record_activity(self, timestamp: datetime = None):
        if timestamp is None:
            timestamp = datetime.now()
        date_str = timestamp.strftime("%Y-%m-%d")
        hour = timestamp.hour
        hourly = self.data.setdefault("hourly_activity", {})
        day_data = hourly.setdefault(date_str, {
            "active_hours": [],
            "first_activity": timestamp.isoformat(),
            "last_activity": timestamp.isoformat()
        })
        if hour not in day_data["active_hours"]:
            day_data["active_hours"].append(hour)
            day_data["active_hours"].sort()
        if timestamp.isoformat() < day_data["first_activity"]:
            day_data["first_activity"] = timestamp.isoformat()
        if timestamp.isoformat() > day_data["last_activity"]:
            day_data["last_activity"] = timestamp.isoformat()
        self._cleanup_old_data()
        self._update_confidence()
        self._save()

    def _update_confidence(self):
        days_count = len(self.data.get("hourly_activity", {}))
        self.data["confidence"] = min(1.0, days_count / self.window_days)

    def get_routine(self):
        hourly = self.data.get("hourly_activity", {})
        if len(hourly) < 3:
            return {
                "learned": False,
                "message": "数据不足，需要至少3天活跃数据"
            }

        hour_counts = defaultdict(int)
        first_hours = []
        last_hours = []

        for date_str, day_data in hourly.items():
            for h in day_data.get("active_hours", []):
                hour_counts[h] += 1
            if day_data.get("first_activity"):
                try:
                    first_hours.append(datetime.fromisoformat(day_data["first_activity"]).hour)
                except:
                    pass
            if day_data.get("last_activity"):
                try:
                    last_hours.append(datetime.fromisoformat(day_data["last_activity"]).hour)
                except:
                    pass

        total_days = len(hourly)
        active_hours = sorted([
            h for h, cnt in hour_counts.items()
            if cnt >= total_days * 0.3
        ])

        def avg_hour(hours):
            if not hours:
                return None
            return round(sum(hours) / len(hours))

        wake_hour = avg_hour(first_hours)
        sleep_hour = avg_hour(last_hours)

        busy_windows = []
        if active_hours and wake_hour is not None:
            prev = wake_hour
            for h in range(wake_hour + 1, (sleep_hour or 24)):
                if h in active_hours:
                    if h - prev >= 3:
                        busy_windows.append({"start": prev, "end": h})
                    prev = h

        return {
            "learned": True,
            "wake_hour": wake_hour,
            "sleep_hour": sleep_hour,
            "active_hours": active_hours,
            "busy_windows": busy_windows,
            "days_tracked": total_days,
            "confidence": self.data.get("confidence", 0)
        }

    def is_dnd_hour(self, hour: int = None) -> bool:
        if hour is None:
            hour = datetime.now().hour
        routine = self.get_routine()
        if not routine.get("learned"):
            return False
        sleep_hour = routine.get("sleep_hour")
        wake_hour = routine.get("wake_hour")
        if sleep_hour is not None and wake_hour is not None:
            if wake_hour <= sleep_hour:
                if hour < (wake_hour - 1) or hour > sleep_hour:
                    return True
            else:
                if hour > sleep_hour and hour < wake_hour:
                    return True
        return False

    def get_optimal_greeting_time(self, greeting_type: str = "morning") -> int:
        routine = self.get_routine()
        if routine.get("learned") and routine.get("wake_hour"):
            wake = routine["wake_hour"]
            if greeting_type == "morning":
                return min(23, max(6, wake + 1))
            elif greeting_type == "night":
                sleep_h = routine.get("sleep_hour")
                if sleep_h:
                    return max(21, min(23, sleep_h - 1))
                return 22
        if greeting_type == "morning":
            return 8
        return 22

    def get_routine_context_for_prompt(self) -> str:
        routine = self.get_routine()
        if not routine.get("learned"):
            return ""
        parts = []
        if routine.get("wake_hour"):
            parts.append(f"用户通常在{routine['wake_hour']}点左右起床")
        if routine.get("sleep_hour"):
            sleep_str = routine["sleep_hour"]
            if sleep_str <= 3:
                parts.append(f"用户经常熬夜到凌晨{sleep_str}点才睡")
            elif sleep_str >= 23:
                parts.append(f"用户通常在{sleep_str}点左右入睡")
            else:
                parts.append(f"用户通常{sleep_str}点左右休息")
        if routine.get("busy_windows"):
            window_texts = []
            for w in routine["busy_windows"]:
                window_texts.append(f"{w['start']}-{w['end']}点")
            parts.append(f"用户的忙碌时段大约是: {', '.join(window_texts)}")
        return "; ".join(parts)