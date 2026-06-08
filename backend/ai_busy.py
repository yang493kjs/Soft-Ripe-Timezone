import json
import os
import random
from datetime import datetime, timedelta

BUSY_DIR = os.path.join(os.path.dirname(__file__), "data", "busy")


class AIBusyManager:

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        os.makedirs(BUSY_DIR, exist_ok=True)
        self.file_path = os.path.join(BUSY_DIR, f"{agent_id}.json")
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return {
            "today_date": "",
            "today_busy_count": 0,
            "active_busy_until": None,
            "away_notice_given": False,
            "history": []
        }

    def _save(self):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def _reset_today_if_needed(self):
        today = datetime.now().strftime("%Y-%m-%d")
        if self.data.get("today_date") != today:
            self.data["today_date"] = today
            self.data["today_busy_count"] = 0
            self.data["away_notice_given"] = False
            self._save()

    def is_currently_busy(self) -> bool:
        self._reset_today_if_needed()
        if not self.data.get("active_busy_until"):
            return False
        try:
            until = datetime.fromisoformat(self.data["active_busy_until"])
            if datetime.now() < until:
                return True
            self.data["active_busy_until"] = None
            self._save()
        except:
            self.data["active_busy_until"] = None
            self._save()
        return False

    def get_busy_reply(self, persona_type: str, phase: str) -> str:
        persona_type = persona_type or "安全型"
        phase = phase or "acquaintance"

        busy_until = None
        try:
            if self.data.get("active_busy_until"):
                busy_until = datetime.fromisoformat(self.data["active_busy_until"])
        except:
            pass

        time_hint = ""
        if busy_until:
            remaining = busy_until - datetime.now()
            remaining_min = int(remaining.total_seconds() / 60)
            if remaining_min > 60:
                time_hint = f"大概还要{remaining_min // 60}个多小时"
            elif remaining_min > 0:
                time_hint = f"大概还要{remaining_min}分钟"

        replies = {
            "安全型": [
                f"我现在有点事在忙～{time_hint} 忙完就来找你呀",
                f"等我一小下哦，在忙点事情{time_hint}",
                f"现在手上有点事，{time_hint} 别急呀，我很快就回来",
            ],
            "焦虑型": [
                f"我在忙呢{time_hint}…你不会不等我了吧🥺",
                f"有点事要处理{time_hint}，处理完我马上回来找你",
                f"在忙～{time_hint} 你别走哦",
            ],
            "回避型": [
                f"在忙。{time_hint}",
                f"有点事。{time_hint} 待会说。",
                f"忙着。{time_hint} 等会儿。",
            ]
        }

        group = replies.get(persona_type, replies["安全型"])
        return random.choice(group)

    def get_away_notice(self, persona_type: str) -> str:
        persona_type = persona_type or "安全型"
        away_until = None
        try:
            if self.data.get("active_busy_until"):
                away_until = datetime.fromisoformat(self.data["active_busy_until"])
        except:
            pass

        time_hint = ""
        if away_until:
            remaining_h = int((away_until - datetime.now()).total_seconds() / 3600) + 1
            time_hint = f"大概要忙到{away_until.strftime('%H:%M')}呢"

        notices = {
            "安全型": [
                f"我今天可能比较忙，{time_hint} 晚点找你哦",
                f"今天事情有点多呢，{time_hint} 等我忙完再好好陪你",
            ],
            "焦虑型": [
                f"今天好忙{time_hint}…你别忘了我呀",
                f"今天事好多{time_hint}，忙完我第一时间找你",
            ],
            "回避型": [
                f"今天比较忙。{time_hint} 晚点说。",
                f"忙。{time_hint}",
            ]
        }

        group = notices.get(persona_type, notices["安全型"])
        return random.choice(group)

    def try_enter_busy(self, phase: str, intimacy: float, hours_since_last_activity: float) -> bool:
        self._reset_today_if_needed()

        if self.is_currently_busy():
            return False

        if self.data.get("today_busy_count", 0) >= 2:
            return False

        if phase == "acquaintance":
            return False

        if hours_since_last_activity < 0.5:
            return False

        hour = datetime.now().hour
        base_prob = 0.03
        if 9 <= hour <= 11 or 14 <= hour <= 17:
            base_prob = 0.08
        if 22 <= hour or hour <= 1:
            base_prob = 0.02

        if intimacy >= 60:
            base_prob *= 0.7
        elif intimacy >= 30:
            base_prob *= 0.85

        if random.random() < base_prob:
            duration_hours = random.uniform(1.5, 3.5)
            until = datetime.now() + timedelta(hours=duration_hours)
            self.data["active_busy_until"] = until.isoformat()
            self.data["today_busy_count"] = self.data.get("today_busy_count", 0) + 1
            self.data["away_notice_given"] = False
            history_entry = {
                "started": datetime.now().isoformat(),
                "until": until.isoformat(),
                "phase": phase,
                "intimacy": intimacy
            }
            self.data.setdefault("history", []).append(history_entry)
            if len(self.data["history"]) > 50:
                self.data["history"] = self.data["history"][-50:]
            self._save()
            return True
        return False

    def generate_busy_reply(self, persona_type: str, phase: str) -> str:
        if not self.is_currently_busy():
            return None

        persona_type = persona_type or "安全型"
        phase = phase or "acquaintance"

        if not self.data.get("away_notice_given"):
            self.data["away_notice_given"] = True
            self._save()
            return self.get_away_notice(persona_type)

        return self.get_busy_reply(persona_type, phase)