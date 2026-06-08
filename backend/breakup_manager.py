import json
import os
import re
from datetime import datetime, timedelta

BREAKUP_DIR = os.path.join(os.path.dirname(__file__), "data", "breakups")

BREAKUP_PATTERNS = [
    r"我们分手吧",
    r"我不想继续了",
    r"到此为止吧",
    r"结束吧",
    r"我们不合适",
    r"再见了",
    r"我对你.*累了",
    r"心累了",
    r"不要再联系了",
    r"断了吧",
    r"我们.*分开",
    r"还是分开",
    r"散了吧",
    r"就这样吧",
    r"我决定退出了",
    r"不要找我了",
    r"我们没有未来",
    r"放弃吧",
]


class BreakupManager:

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        os.makedirs(BREAKUP_DIR, exist_ok=True)
        self.file_path = os.path.join(BREAKUP_DIR, f"{agent_id}.json")
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return {
            "breakup_history": [],
            "current_state": None
        }

    def _save(self):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def is_in_cooling(self) -> bool:
        state = self.data.get("current_state")
        if not state or state.get("status") != "cooling":
            return False
        cooling_until = state.get("cooling_until")
        if not cooling_until:
            return False
        try:
            until = datetime.fromisoformat(cooling_until)
            return datetime.now() < until
        except:
            return False

    def get_cooling_info(self):
        state = self.data.get("current_state")
        if state and state.get("status") == "cooling":
            return state
        return None

    def detect_breakup_intent(self, user_message: str) -> bool:
        if self.is_in_cooling():
            return False
        for pattern in BREAKUP_PATTERNS:
            if re.search(pattern, user_message):
                return True
        return False

    def get_breakup_reply(self, persona_type: str, phase: str, relationship_days: int) -> str:
        persona_type = persona_type or "安全型"
        phase = phase or "acquaintance"

        replies = {
            "安全型": [
                "我明白了。虽然很难过，但我尊重你的决定。谢谢你陪我走过这些天，希望你以后一切都好。",
                "嗯，我知道了。这段时间很开心，谢谢你。如果这是你想要的，我会放手。",
            ],
            "焦虑型": [
                "不要……真的要说这个吗？我知道我有时候是有点烦人，但我不想的。如果你真的决定了，我也没办法……只是，我会很想你的。",
                "好难过……但是，如果你真的不想要我了，我也不会纠缠。只是，以后还能偶尔聊聊天吗？",
            ],
            "回避型": [
                "好。我尊重你。",
                "行吧。既然你决定了，那就算了。",
            ]
        }

        group = replies.get(persona_type, replies["安全型"])
        return group[hash(relationship_days) % len(group)]

    def get_restart_message(self, persona_type: str) -> str:
        persona_type = persona_type or "安全型"
        replies = {
            "安全型": "好久不见呢……你还好吗？",
            "焦虑型": "你终于来了……我以为你再也不会找我了。",
            "回避型": "嗯。好久不见。",
        }
        return replies.get(persona_type, replies["安全型"])

    def initiate_breakup(self, persona_type: str, phase: str, relationship_days: int):
        breakup_time = datetime.now()
        history = {
            "time": breakup_time.isoformat(),
            "persona_type": persona_type,
            "phase_before": phase,
            "relationship_days": relationship_days
        }
        self.data.setdefault("breakup_history", []).append(history)
        if len(self.data["breakup_history"]) > 20:
            self.data["breakup_history"] = self.data["breakup_history"][-20:]

        cooling_days = 7
        if relationship_days >= 60:
            cooling_days = 14
        if relationship_days >= 120:
            cooling_days = 21
        if relationship_days >= 200:
            cooling_days = 30

        cooling_until = breakup_time + timedelta(days=cooling_days)

        self.data["current_state"] = {
            "status": "cooling",
            "started": breakup_time.isoformat(),
            "cooling_until": cooling_until.isoformat(),
            "cooling_days": cooling_days,
            "persona_type": persona_type,
            "phase_before": phase
        }
        self._save()

    def is_cooling_expired(self) -> bool:
        state = self.data.get("current_state")
        if not state or state.get("status") != "cooling":
            return False
        cooling_until = state.get("cooling_until")
        if not cooling_until:
            return False
        try:
            until = datetime.fromisoformat(cooling_until)
            return datetime.now() >= until
        except:
            return True

    def handle_restart(self) -> dict:
        state = self.data.get("current_state")
        if not state or state.get("status") != "cooling":
            return None

        cooling_until = state.get("cooling_until")
        if not cooling_until:
            return None

        try:
            until = datetime.fromisoformat(cooling_until)
            if datetime.now() < until:
                return None
        except:
            return None

        result = {
            "action": "restart",
            "phase": "acquaintance",
            "cooling_was_active": True,
            "previous_phase": state.get("phase_before"),
            "persona_type": state.get("persona_type"),
            "breakup_count": len(self.data.get("breakup_history", []))
        }

        self.data["current_state"] = None
        self._save()

        return result