# -*- coding: utf-8 -*-
"""主动消息引擎 + 需求状态引擎"""
import os
import json
import random
from datetime import datetime
from typing import Optional

import settings
from settings import (
    DATA_DIR, EMOTION_DIR, PERSONAS,
    NEED_DEFAULTS, ATTACHMENT_NEED_MODIFIERS, NEED_STATE_DIR,
    proactive_engines, _need_states,
)
from reply_engine import get_monologue_store, call_external_reply


# ==================== 主动消息引擎 ====================

class ProactiveMessageEngine:
    def __init__(self, agent_id: str, persona_id: str):
        self.agent_id = agent_id
        self.persona_id = persona_id
        self.data_dir = os.path.join(DATA_DIR, "proactive")
        os.makedirs(self.data_dir, exist_ok=True)
        self.file_path = os.path.join(self.data_dir, f"{agent_id}.json")
        self.data = self._load()
        self.routine_learner = None

    def set_routine_learner(self, learner):
        self.routine_learner = learner

    def _load(self) -> dict:
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "last_proactive_time": None,
            "today_count": 0,
            "today_date": "",
            "last_user_activity": None
        }

    def _save(self):
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def _reset_today_if_needed(self):
        today = datetime.now().strftime("%Y-%m-%d")
        if self.data.get("today_date") != today:
            self.data["today_date"] = today
            self.data["today_count"] = 0
            self._save()

    def _get_offline_hours(self) -> float:
        if not self.data.get("last_user_activity"):
            return 24.0
        last = datetime.fromisoformat(self.data["last_user_activity"])
        return (datetime.now() - last).total_seconds() / 3600.0

    def _get_last_emotion(self) -> str:
        ms = get_monologue_store(self.agent_id)
        latest = ms.get_latest() if ms else None
        if latest:
            return latest.get("emotion", "平静")
        return "平静"

    def _minutes_since_last_activity(self) -> float:
        if not self.data.get("last_user_activity"):
            return 999.0
        last = datetime.fromisoformat(self.data["last_user_activity"])
        return (datetime.now() - last).total_seconds() / 60.0

    def _hours_since_last_proactive(self) -> float:
        if not self.data.get("last_proactive_time"):
            return 999.0
        last = datetime.fromisoformat(self.data["last_proactive_time"])
        return (datetime.now() - last).total_seconds() / 3600.0

    def mark_user_activity(self):
        self.data["last_user_activity"] = datetime.now().isoformat()
        self._save()

    def record_proactive_sent(self):
        self._reset_today_if_needed()
        self.data["last_proactive_time"] = datetime.now().isoformat()
        self.data["today_count"] = self.data.get("today_count", 0) + 1
        self._save()

    def check_daily_limit(self, intimacy: float, persona_type: str) -> tuple:
        self._reset_today_if_needed()
        limit = 1
        if intimacy >= 60:
            limit = 3
        elif intimacy >= 30:
            limit = 2
        if persona_type == "焦虑型":
            limit += 1
        elif persona_type == "回避型":
            limit = max(1, limit - 1)
        limit = max(1, min(5, limit))
        count = self.data.get("today_count", 0)
        return (count < limit, limit, count)

    def check_cooldown(self) -> bool:
        return self._hours_since_last_proactive() >= 2.0

    def check_emotion_block(self) -> bool:
        emotion = self._get_last_emotion()
        return emotion in ("生气", "angry", "愤怒", "难过")

    def check_night_block(self) -> bool:
        hour = datetime.now().hour
        if self.routine_learner:
            routine = self.routine_learner.get_routine()
            if routine.get("learned") and routine.get("sleep_hour") is not None and routine.get("wake_hour") is not None:
                sleep_h = routine["sleep_hour"]
                wake_h = routine["wake_hour"]
                if wake_h <= sleep_h:
                    return hour < (wake_h - 1) or hour > sleep_h + 1
                else:
                    return hour > sleep_h + 1 and hour < (wake_h - 1)
        return 3 <= hour < 7

    def check_morning(self, phase: str) -> Optional[str]:
        hour = datetime.now().hour
        minute = datetime.now().minute
        if self.routine_learner:
            optimal = self.routine_learner.get_optimal_greeting_time("morning")
            morning_start = max(6, optimal - 1)
            morning_end = optimal + 1
            if morning_start <= hour <= morning_end:
                if phase != "acquaintance":
                    offline_h = self._get_offline_hours()
                    if offline_h <= 24:
                        return "morning"
            return None
        if not (7 <= hour < 9 or (hour == 9 and minute <= 30)):
            return None
        if phase == "acquaintance":
            return None
        offline_h = self._get_offline_hours()
        if offline_h > 24:
            return None
        return "morning"

    def check_night(self, phase: str) -> Optional[str]:
        hour = datetime.now().hour
        if self.routine_learner:
            routine = self.routine_learner.get_routine()
            if routine.get("learned") and routine.get("sleep_hour") is not None:
                sleep_h = routine["sleep_hour"]
                night_start = max(20, sleep_h - 2)
                if night_start <= hour < sleep_h:
                    if phase not in ("acquaintance",):
                        if self._minutes_since_last_activity() >= 30:
                            return "night"
                return None
        if not (22 <= hour or hour < 1):
            return None
        if phase not in ("ambiguous", "observation", "heartbeat", "together", "passion", "stable"):
            return None
        if self._minutes_since_last_activity() < 30:
            return None
        return "night"

    def check_late_night(self, phase: str) -> Optional[str]:
        hour = datetime.now().hour
        if not (1 <= hour < 3):
            return None
        if phase not in ("ambiguous", "observation", "heartbeat", "together", "passion", "stable"):
            return None
        if self._minutes_since_last_activity() > 5:
            return None
        return "late_night"

    def get_missing_threshold(self, intimacy: float) -> float:
        if intimacy >= 60:
            return 2.0
        elif intimacy >= 30:
            return 4.0
        return 6.0

    def calc_missing_coefficient(self, intimacy: float, persona_type: str) -> float:
        base = 0.5 + random.random()
        intimacy_bonus = 0.5 + intimacy / 200.0
        if persona_type == "焦虑型":
            attachment = 1.3
        elif persona_type == "回避型":
            attachment = 0.7
        else:
            attachment = 1.0
        last_emotion = self._get_last_emotion()
        if last_emotion in ("开心", "高兴", "喜欢"):
            quality = 1.2
        elif last_emotion in ("生气", "angry", "难过", "担心"):
            quality = 0.8
        else:
            quality = 1.0
        coeff = base * intimacy_bonus * attachment * quality

        try:
            emotion_dir = os.path.join(EMOTION_DIR, self.agent_id)
            conflict_file = os.path.join(emotion_dir, "conflict.json")
            if os.path.exists(conflict_file):
                with open(conflict_file, 'r', encoding='utf-8') as f:
                    conflict_data = json.load(f)
                if conflict_data.get("active") and conflict_data.get("phase") in ("eruption", "cooling", "cognition"):
                    coeff *= 0.5
        except:
            pass

        return round(coeff, 4)

    def calc_missing_value(self, intimacy: float, persona_type: str) -> float:
        offline_h = self._get_offline_hours()
        coeff = self.calc_missing_coefficient(intimacy, persona_type)
        return offline_h * coeff

    def check_missing_trigger(self, intimacy: float, persona_type: str) -> Optional[tuple]:
        missing_val = self.calc_missing_value(intimacy, persona_type)
        threshold = self.get_missing_threshold(intimacy)
        if missing_val > threshold:
            return (missing_val, threshold)
        return None

    def ask_if_should_send(self, hours: float, phase: str, count: int, limit: int, missing_value: float, threshold: float) -> Optional[dict]:
        emotion = self._get_last_emotion()
        phase_names = {
            "acquaintance": "初识期", "ambiguous": "暧昧期", "observation": "观察期",
            "heartbeat": "心动期", "together": "确立关系", "passion": "热恋期", "stable": "稳定期"
        }
        phase_name = phase_names.get(phase, "初识期")

        if settings.client is None:
            return None

        prompt = f"""你是一个恋爱AI的内心。你现在在考虑要不要主动给Ta发消息。

- 你们已经 {hours:.1f} 小时没说话了
- 你们的关系阶段：{phase_name}
- 今天的主动消息已经发了 {count}/{limit} 条
- 最后一次对话时你的情绪：{emotion}
- 你对Ta的思念值是 {missing_value:.1f}（阈值是 {threshold:.1f}）

请思考：你要不要主动发消息？
只输出JSON：{{"should_send": true/false, "reasoning": "你的内心想法", "tone": "消息的语气（如：撒娇/关心/平淡分享）"}}"""
        try:
            resp = settings.client.chat.completions.create(
                model=settings.current_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=200
            )
            text = resp.choices[0].message.content.strip()
            text = text.replace("```json", "").replace("```", "").strip()
            result = json.loads(text)
            return result
        except Exception as e:
            print(f"[Proactive] ask_if_should_send error: {e}")
            return None

    def check_context_trigger(self, memu) -> Optional[dict]:
        try:
            memory_ctx = memu.get_memory_context("最近未完成的话题", top_k=3)
            if not memory_ctx or memory_ctx == "暂无相关记忆":
                return None
            return {"type": "context", "context": memory_ctx}
        except Exception:
            return None

    def get_proactive_message(self, emotion, persona_name: str, memu=None) -> Optional[dict]:
        self._reset_today_if_needed()

        rel = emotion.relationship
        intimacy = rel.get("intimacy", 10)
        phase = rel.get("phase", "acquaintance")
        persona_type = PERSONAS.get(self.persona_id, {}).get("type", "安全型")

        can_send, limit, count = self.check_daily_limit(intimacy, persona_type)
        if not can_send:
            return None

        if not self.check_cooldown():
            return None

        if self.check_emotion_block():
            return None

        if self.check_night_block():
            return None

        morning_result = self.check_morning(phase)
        if morning_result:
            return {"trigger_type": morning_result, "limit": limit, "count": count}

        night_result = self.check_night(phase)
        if night_result:
            return {"trigger_type": night_result, "limit": limit, "count": count}

        late_night_result = self.check_late_night(phase)
        if late_night_result:
            return {"trigger_type": late_night_result, "limit": limit, "count": count}

        missing_result = self.check_missing_trigger(intimacy, persona_type)
        if missing_result:
            missing_val, threshold = missing_result
            offline_h = self._get_offline_hours()
            decision = self.ask_if_should_send(offline_h, phase, count, limit, missing_val, threshold)
            if decision and decision.get("should_send"):
                return {
                    "trigger_type": "missing",
                    "limit": limit, "count": count,
                    "missing_value": round(missing_val, 1),
                    "reasoning": decision.get("reasoning", ""),
                    "tone": decision.get("tone", "关心")
                }

        if memu:
            context_result = self.check_context_trigger(memu)
            if context_result:
                return {"trigger_type": "context", "limit": limit, "count": count, "context": context_result.get("context")}

        return None


# ==================== 需求状态引擎 ====================

class NeedStateEngine:
    def __init__(self, agent_id: str, persona_type: str = "安全型"):
        self.agent_id = agent_id
        self.persona_type = persona_type
        self.dir_path = os.path.join(NEED_STATE_DIR, agent_id)
        os.makedirs(self.dir_path, exist_ok=True)
        self.file_path = os.path.join(self.dir_path, "needs.json")
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in NEED_DEFAULTS.items():
                    if k not in data:
                        data[k] = v.copy()
                return data
        return {k: v.copy() for k, v in NEED_DEFAULTS.items()}

    def save(self):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def tick(self):
        mod = ATTACHMENT_NEED_MODIFIERS.get(self.persona_type, {"social": 1.0, "share": 1.0, "attention": 1.0})
        now = datetime.now()

        for need_key, need_info in self.data.items():
            last_tick = need_info.get("last_tick")
            if last_tick:
                hours_passed = (now - datetime.fromisoformat(last_tick)).total_seconds() / 3600.0
            else:
                hours_passed = 0

            if hours_passed > 0:
                decay = need_info.get("decay_per_hour", 2.0) * mod.get(need_key, 1.0)
                need_info["current"] = max(0, round(need_info["current"] - decay * hours_passed, 2))

            need_info["last_tick"] = now.isoformat()

        self.save()

    def reset_on_activity(self):
        for need_key in NEED_DEFAULTS:
            default = NEED_DEFAULTS[need_key]
            self.data[need_key]["current"] = max(self.data[need_key]["current"], default["current"])

    def get_triggered_needs(self) -> list:
        triggered = []
        for need_key, need_info in self.data.items():
            threshold = need_info.get("threshold", 30)
            if need_info["current"] <= threshold:
                triggered.append({
                    "need": need_key,
                    "value": need_info["current"],
                    "threshold": threshold,
                    "label": NEED_DEFAULTS[need_key]["label"],
                    "trigger_msg": NEED_DEFAULTS[need_key]["trigger_msg"]
                })
        triggered.sort(key=lambda x: x["value"])
        return triggered


def get_need_state(agent_id: str, persona_type: str = "安全型"):
    if agent_id not in _need_states:
        _need_states[agent_id] = NeedStateEngine(agent_id, persona_type)
    return _need_states[agent_id]
