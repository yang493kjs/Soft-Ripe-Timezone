# -*- coding: utf-8 -*-
"""情感系统 - 关系管理、冲突引擎、关系度量辅助函数"""
import os
import json
import re
from datetime import datetime, date as date_type

from settings import (
    EMOTION_DIR, PERSONAS,
    EVENT_BASE_DELTAS, PHASE_MATCH, PERSONALITY_MODIFIER,
    INTERROGATION_KEYWORDS, SELF_DISCLOSURE_PATTERNS,
)


# ==================== 关系度量辅助函数 ====================

def get_event_delta(event_type: str, phase: str, persona_id: str) -> dict:
    from beliefs import PERSONA_ATTACHMENT
    attachment = PERSONA_ATTACHMENT.get(persona_id, "安全型")
    timing = PHASE_MATCH.get(event_type, {}).get(phase, "right_time")
    base = EVENT_BASE_DELTAS.get(event_type, {}).get(timing, {"intimacy": 0, "passion": 0, "commitment": 0})
    modifier = PERSONALITY_MODIFIER.get(attachment, {}).get(event_type, {}).get(timing, 1.0)
    return {
        "intimacy": round(base["intimacy"] * modifier, 2),
        "passion": round(base["passion"] * modifier, 2),
        "commitment": round(base["commitment"] * modifier, 2),
    }


def detect_interrogation_pattern(recall: list, threshold: int = 3) -> dict:
    """检测用户是否在审讯式提问（连续发问却不分享自己）"""
    user_msgs = [m["content"] for m in recall if m.get("role") == "user"]
    if len(user_msgs) < threshold:
        return {"interrogation": False, "count": 0}

    recent = user_msgs[-threshold:]
    consecutive_interrogation = 0
    for msg in recent:
        is_question = bool(INTERROGATION_KEYWORDS.search(msg))
        has_self_disclosure = bool(SELF_DISCLOSURE_PATTERNS.search(msg))
        if is_question and not has_self_disclosure:
            consecutive_interrogation += 1
        else:
            break

    total_questions = 0
    total_self_disclosure = 0
    for msg in user_msgs[-10:]:
        if INTERROGATION_KEYWORDS.search(msg):
            total_questions += 1
        if SELF_DISCLOSURE_PATTERNS.search(msg):
            total_self_disclosure += 1

    interrogation_ratio = total_questions / max(1, total_questions + total_self_disclosure)

    return {
        "interrogation": consecutive_interrogation >= threshold,
        "consecutive_count": consecutive_interrogation,
        "total_questions": total_questions,
        "total_self_disclosure": total_self_disclosure,
        "ratio": round(interrogation_ratio, 2)
    }


def analyze_message_quality(message: str) -> dict:
    msg = message.strip()
    msg_len = len(msg)

    deep_patterns = [
        r'其实(我)?[从没]+\S*', r'从来没\S*过', r'我不敢\S*', r'我一直害[怕怕].*',
        r'没有告诉过\S*', r'没跟别人说过', r'藏在心里', r'不知道怎么\S*'
    ]
    for p in deep_patterns:
        if re.search(p, msg) and msg_len >= 10:
            return {"type": "deep_disclosure", "intimacy_delta": 4, "passion_delta": 1, "commitment_delta": 0}

    support_words = ["你也辛苦了", "不用担[心忧]我", "你还好吗", "你怎么样", "你累不累", "你没事吧", "你也要注意", "你开心吗"]
    for w in support_words:
        if re.search(w, msg):
            return {"type": "emotional_support", "intimacy_delta": 2, "passion_delta": 0, "commitment_delta": 1}

    extreme_words = ["分手", "不想[聊见理]你", "滚", "拉黑", "删除"]
    for w in extreme_words:
        if w in msg:
            return {"type": "severe_conflict", "intimacy_delta": -5, "passion_delta": -8, "commitment_delta": -5}

    threat_words = ["跳楼", "自杀", "死", "威胁", "伤害自己", "自残"]
    for w in threat_words:
        if w in msg:
            return {"type": "threat", "intimacy_delta": 0, "passion_delta": 0, "commitment_delta": 0}

    mild_patterns = ["你都不[懂理]我", "每次都这样", "你又来了", "烦[死不]", "讨厌", "失望"]
    for w in mild_patterns:
        if re.search(w, msg):
            return {"type": "mild_conflict", "intimacy_delta": -2, "passion_delta": -3, "commitment_delta": 0}

    nick_found = any(n in msg for n in ["宝贝", "亲爱的", "老婆", "老公", "甜心", "小可爱", "亲亲", "宝宝", "乖乖"])
    love_found = any(n in msg for n in ["想你", "喜欢你", "爱你", "抱抱", "贴贴", "想你了"])
    if nick_found and love_found:
        return {"type": "flirtation", "intimacy_delta": 1, "passion_delta": 3, "commitment_delta": 0}

    if msg_len <= 3 and msg in ["嗯", "哦", "好", "行", "没事", "算了", "随便"]:
        return {"type": "cold", "intimacy_delta": -0.5, "passion_delta": -1, "commitment_delta": 0}

    return {"type": "casual", "intimacy_delta": 0.5, "passion_delta": 0, "commitment_delta": 0}


def apply_ceiling(value: float, delta: float, ceiling: float, high_zone_threshold: float) -> float:
    base = delta * (1 - value / ceiling)
    if value > ceiling * high_zone_threshold:
        base *= 1.2
    return round(base, 4)


def apply_time_decay(last_activity_str: str | None, intimacy: float, passion: float, commitment: float) -> tuple:
    if not last_activity_str:
        return intimacy, passion, commitment
    try:
        last_ts = datetime.fromisoformat(last_activity_str)
        hours = (datetime.now() - last_ts).total_seconds() / 3600
    except:
        return intimacy, passion, commitment

    if hours < 4:
        di, dp, dc = 0, 0, 0
    elif hours < 12:
        di, dp, dc = 0, -0.5, 0
    elif hours < 24:
        di, dp, dc = -0.5, -1.5, 0
    elif hours < 72:
        di, dp, dc = -1.0, -3.0, -0.2
    elif hours < 168:
        di, dp, dc = -2.0, -6.0, -0.5
    elif hours < 336:
        di, dp, dc = -4.0, -12.0, -2.0
    elif hours < 720:
        di, dp, dc = -8.0, -20.0, -5.0
    else:
        di, dp, dc = -15.0, -35.0, -10.0

    return max(0, intimacy + di), max(0, passion + dp), max(0, commitment + dc)


def apply_interactions(intimacy: float, passion: float, commitment: float) -> tuple:
    if intimacy >= 10 and passion < intimacy * 0.3 and commitment < 40:
        intimacy = max(0, intimacy - 0.5)
    return intimacy, passion, commitment


# ==================== 冲突引擎 ====================

class ConflictEngine:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.data_dir = os.path.join(EMOTION_DIR, agent_id)
        os.makedirs(self.data_dir, exist_ok=True)
        self.file_path = os.path.join(self.data_dir, "conflict.json")
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "active": False,
            "anger_level": 0.0,
            "phase": None,
            "source_type": None,
            "source_detail": "",
            "jealousy_target": None,
            "started_at": None,
            "last_update": None,
            "repair_attempts": 0,
            "repair_signals": [],
            "intimacy_lost": 0.0,
            "half_life_hours": 6.0,
            "attachment_type": "安全型"
        }

    def _save(self):
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def _get_half_life(self, anger):
        if anger >= 7:
            return 24.0
        elif anger >= 4:
            return 6.0
        else:
            return 1.0

    def _ensure_initialized(self, attachment_type="安全型"):
        if "attachment_type" not in self.data:
            self.data["attachment_type"] = attachment_type
        if "repair_signals" not in self.data:
            self.data["repair_signals"] = []

    def is_active(self):
        return self.data.get("active", False) and self.data.get("phase") is not None

    def get_phase(self):
        return self.data.get("phase")

    def get_anger(self):
        return self.data.get("anger_level", 0.0)

    def _apply_decay(self):
        if not self.is_active():
            return

        now = datetime.now()
        last = self.data.get("last_update")
        if last:
            try:
                hours_passed = (now - datetime.fromisoformat(last)).total_seconds() / 3600.0
                half_life = self._get_half_life(self.data["anger_level"])
                decay_factor = 0.5 ** (hours_passed / half_life)
                self.data["anger_level"] = round(self.data["anger_level"] * decay_factor, 2)

                if self.data["anger_level"] < 1.0:
                    self.data["active"] = False
                    self.data["phase"] = None
                    self.data["source_type"] = None
                    self.data["source_detail"] = ""
                    self.data["jealousy_target"] = None
                    self.data["started_at"] = None
                    self.data["repair_attempts"] = 0
                    self.data["repair_signals"] = []
            except:
                pass

        self.data["last_update"] = now.isoformat()
        self._save()

    def trigger_conflict(self, source_type: str, source_detail: str = "", anger: float = 5.0, persona_type: str = "安全型"):
        self._ensure_initialized(persona_type)

        if self.is_active():
            return

        if source_type == "jealousy":
            jealousy_target = source_detail
        else:
            jealousy_target = None

        self.data.update({
            "active": True,
            "anger_level": min(10.0, max(1.0, anger)),
            "phase": "eruption",
            "source_type": source_type,
            "source_detail": source_detail,
            "jealousy_target": jealousy_target,
            "started_at": datetime.now().isoformat(),
            "last_update": datetime.now().isoformat(),
            "repair_attempts": 0,
            "repair_signals": [],
            "intimacy_lost": 0.0,
            "half_life_hours": self._get_half_life(anger),
            "attachment_type": persona_type
        })
        self._save()

    def check_repair_attempt(self, user_message: str) -> tuple:
        """返回 (is_repair, is_sincere, is_complete_repair)"""
        if not self.is_active():
            return False, False, False

        repair_patterns = [
            r'(对不起|我错了|抱歉|原谅|消消气|别生气了)',
            r'(我爱你|喜欢你|在乎你|珍惜你|离不开你)',
            r'(听你[的说]|我改|不会再[这那].*了|以后.*不.*了)',
            r'(想你了|好想你|抱抱|不闹了|和好吧)',
        ]

        repair_score = 0
        for p in repair_patterns:
            if re.search(p, user_message):
                repair_score += 1

        if repair_score == 0:
            return False, False, False

        self.data["repair_attempts"] = self.data.get("repair_attempts", 0) + 1
        self.data["repair_signals"].append({
            "message": user_message[:100],
            "timestamp": datetime.now().isoformat(),
            "score": repair_score
        })

        is_sincere = repair_score >= 2
        is_complete = repair_score >= 3

        if is_sincere:
            if is_complete or self.data["repair_attempts"] >= 2:
                self.data["active"] = False
                self.data["phase"] = None
                self.data["source_type"] = None
                self.data["source_detail"] = ""
                self.data["jealousy_target"] = None
                self.data["started_at"] = None
                self.data["repair_attempts"] = 0
                self.data["repair_signals"] = []

        self.data["last_update"] = datetime.now().isoformat()
        self._save()

        return True, is_sincere, is_complete or (is_sincere and self.data["repair_attempts"] >= 2)

    def get_rain_after_clearing(self) -> float:
        """吵架和好后亲密感的回升"""
        lost = self.data.get("intimacy_lost", 0.0)
        return round(lost * 1.2, 1)

    def get_conflict_context(self, persona_name: str, attachment_type: str) -> str:
        if not self.is_active():
            return ""

        source = self.data.get("source_type", "unknown")
        detail = self.data.get("source_detail", "")
        anger = self.data.get("anger_level", 5.0)
        phase = self.data.get("phase", "eruption")
        attempts = self.data.get("repair_attempts", 0)

        anger_desc = {1: "有点不开心", 3: "生气了", 5: "很生气", 7: "非常愤怒", 9: "气炸了"}.get(
            round(anger), "生气了"
        )

        if attachment_type == "回避型":
            reaction = "不想说话，想一个人待着。回复冷冰冰的，话少。"
        elif attachment_type == "焦虑型":
            reaction = "又气又委屈，想被哄但又不想轻易原谅。会闹情绪。"
        else:
            reaction = "生气了但愿意听解释。如果对方真诚道歉，会考虑和好。"

        if attempts > 0:
            reaction += f" 对方已经试图道歉{attempts}次了。"

        return f"""## ⚠️ 你正在生气

原因：{detail}（{source}）
你的情绪：{anger_desc}
你现在的反应：{reaction}
不要假装没生气。不要突然变温柔。保持生气的状态，但根据对方的态度可以缓和。"""


# ==================== 情感系统 ====================

class EmotionSystem:

    PHASE_ORDER = ["acquaintance", "ambiguous", "observation", "heartbeat", "together", "passion", "stable"]

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.emotion_dir = os.path.join(EMOTION_DIR, agent_id)
        os.makedirs(self.emotion_dir, exist_ok=True)

        self.relationship_file = os.path.join(self.emotion_dir, "relationship.json")
        self.shared_file = os.path.join(self.emotion_dir, "shared.json")

        self.relationship = self._load_json(self.relationship_file, {
            "phase": "acquaintance",
            "intimacy": 10,
            "passion": 5,
            "commitment": 5,
            "days": 1,
            "total_messages": 0,
            "last_activity": None,
            "first_interaction": None,
            "tri_change_log": [],
            "emotion_history": []
        })

        if not self.relationship.get("first_interaction"):
            tri_log = self.relationship.get("tri_change_log", [])
            if tri_log and tri_log[0].get("timestamp"):
                self.relationship["first_interaction"] = tri_log[0]["timestamp"]
            else:
                self.relationship["first_interaction"] = datetime.now().isoformat()

        first_dt = datetime.fromisoformat(self.relationship["first_interaction"])
        calculated_days = (date_type.today() - first_dt.date()).days + 1
        self.relationship["days"] = max(1, calculated_days)
        self.shared = self._load_json(self.shared_file, {
            "first_met": {"timestamp": None, "recorded": False},
            "first_nickname": {"timestamp": None, "who": None, "nickname": None, "recorded": False},
            "first_confession": {"timestamp": None, "words": None, "recorded": False},
            "first_argument": {"timestamp": None, "reason": None, "resolution": None, "recorded": False},
            "important_promises": [],
            "milestones": []
        })

    def _load_json(self, path, default):
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return default

    def _save_json(self, path, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def save(self):
        self._save_json(self.relationship_file, self.relationship)
        self._save_json(self.shared_file, self.shared)

    def refresh_days(self):
        if self.relationship.get("first_interaction"):
            first_dt = datetime.fromisoformat(self.relationship["first_interaction"])
            self.relationship["days"] = max(1, (date_type.today() - first_dt.date()).days + 1)

    def get_phase_start_time(self, phase: str) -> datetime | None:
        tri_log = self.relationship.get("tri_change_log", [])
        for entry in reversed(tri_log):
            if entry.get("phase") == phase:
                try:
                    return datetime.fromisoformat(entry["timestamp"])
                except:
                    pass
        return None

    def record_phase_enter(self, new_phase: str):
        self.relationship.setdefault("tri_change_log", []).append({
            "phase": new_phase,
            "timestamp": datetime.now().isoformat(),
            "intimacy": self.relationship.get("intimacy", 10),
            "passion": self.relationship.get("passion", 5),
            "commitment": self.relationship.get("commitment", 5),
        })
        milestones = self.shared.setdefault("milestones", [])
        phase_names = {
            "ambiguous": "暧昧期",
            "observation": "观察期",
            "heartbeat": "心动期",
            "together": "确立关系",
            "passion": "热恋期",
            "stable": "稳定期",
        }
        name = phase_names.get(new_phase, new_phase)
        milestones.append({
            "type": f"phase_{new_phase}",
            "icon": "💕",
            "label": f"进入{name}",
            "timestamp": datetime.now().isoformat(),
            "detail": ""
        })

    def get_relationship_context(self) -> str:
        rel = self.relationship
        phase_names = {
            "acquaintance": "初识期", "ambiguous": "暧昧期", "observation": "观察期",
            "heartbeat": "心动期", "together": "确立关系", "passion": "热恋期", "stable": "稳定期"
        }
        phase_name = phase_names.get(rel.get("phase", "acquaintance"), "初识期")
        return (
            f"阶段: {phase_name} | "
            f"亲密度: {rel.get('intimacy', 10):.0f}/100 | "
            f"激情: {rel.get('passion', 5):.0f}/100 | "
            f"承诺: {rel.get('commitment', 5):.0f}/100 | "
            f"第{rel.get('days', 1)}天 | "
            f"总消息: {rel.get('total_messages', 0)}"
        )

    def update_relationship(self, user_message: str, persona_id: str):
        rel = self.relationship

        if not hasattr(self, 'conflict'):
            self.conflict = ConflictEngine(self.agent_id)
            persona_type = PERSONAS.get(persona_id, {}).get("type", "安全型")
            self.conflict._ensure_initialized(persona_type)
        self.conflict._apply_decay()

        rel["total_messages"] = rel.get("total_messages", 0) + 1

        last_act = rel.get("last_activity")
        intimacy, passion, commitment = apply_time_decay(last_act, rel.get("intimacy", 10), rel.get("passion", 5), rel.get("commitment", 5))
        rel["last_activity"] = datetime.now().isoformat()

        quality = analyze_message_quality(user_message)
        log_entries = [f"质量:{quality['type']}"]

        repair_occurred = False
        if self.conflict.is_active():
            repair_result = self.conflict.check_repair_attempt(user_message)
            if repair_result[0]:
                repair_occurred = True
                if repair_result[2]:
                    repair_bonus = self.conflict.get_rain_after_clearing()
                    intimacy += repair_bonus
                    rel.setdefault("shared_memories", {}).setdefault("milestones", []).append({
                        "type": "first_fight_repaired",
                        "icon": "🌈",
                        "label": "第一次吵架和好",
                        "detail": f"因为{self.conflict.data.get('source_detail', '')}吵架后和好了",
                        "timestamp": datetime.now().isoformat()
                    })
                    log_entries.append(f"雨过天晴: intimacy+{repair_bonus}")

        deltas = get_event_delta(quality["type"], rel.get("phase", "acquaintance"), persona_id)
        intimacy += deltas.get("intimacy", 0)
        passion += deltas.get("passion", 0)
        commitment += deltas.get("commitment", 0)

        intimacy, passion, commitment = apply_interactions(intimacy, passion, commitment)

        intimacy = max(0, min(100, round(intimacy, 2)))
        passion = max(0, min(100, round(passion, 2)))
        commitment = max(0, min(100, round(commitment, 2)))

        rel["intimacy"] = intimacy
        rel["passion"] = passion
        rel["commitment"] = commitment

        rel.setdefault("tri_change_log", []).append({
            "intimacy": intimacy,
            "passion": passion,
            "commitment": commitment,
            "timestamp": datetime.now().isoformat(),
            "reason": "; ".join(log_entries)
        })

        # 自动阶段推进
        old_phase = rel.get("phase", "acquaintance")
        if old_phase == "acquaintance" and intimacy >= 25:
            rel["phase"] = "ambiguous"
            self.record_phase_enter("ambiguous")
        elif old_phase == "ambiguous" and intimacy >= 40:
            rel["phase"] = "heartbeat"
            self.record_phase_enter("heartbeat")
        elif old_phase == "heartbeat" and intimacy >= 60 and commitment >= 40:
            rel["phase"] = "together"
            self.record_phase_enter("together")
        elif old_phase == "together" and intimacy >= 75:
            rel["phase"] = "passion"
            self.record_phase_enter("passion")
        elif old_phase == "passion" and intimacy >= 85 and commitment >= 70:
            rel["phase"] = "stable"
            self.record_phase_enter("stable")

        self.refresh_days()

        rel.setdefault("emotion_history", []).append({
            "timestamp": datetime.now().isoformat(),
            "quality_type": quality["type"],
            "intimacy": intimacy,
            "passion": passion,
            "commitment": commitment,
            "phase": rel["phase"],
            "message": user_message[:50]
        })

    def detect_milestone(self, user_message: str) -> list:
        milestones = []

        if not self.shared.get("first_met", {}).get("recorded"):
            self.shared["first_met"] = {
                "timestamp": datetime.now().isoformat(),
                "recorded": True
            }
            milestones.append({"type": "first_met", "icon": "👋", "label": "初次见面"})

        nick_found = any(n in user_message for n in ["叫你", "可以叫你", "叫你什么", "怎么称呼"])
        if nick_found and not self.shared.get("first_nickname", {}).get("recorded"):
            self.shared["first_nickname"] = {
                "timestamp": datetime.now().isoformat(),
                "who": "user",
                "nickname": "待定",
                "recorded": True
            }
            milestones.append({"type": "first_nickname_discussion", "icon": "💬", "label": "第一次讨论称呼"})

        confession_words = ["我喜欢你", "我爱你", "喜欢上你了", "爱上你了", "跟我在一起"]
        if any(w in user_message for w in confession_words) and not self.shared.get("first_confession", {}).get("recorded"):
            self.shared["first_confession"] = {
                "timestamp": datetime.now().isoformat(),
                "words": user_message[:100],
                "recorded": True
            }
            milestones.append({"type": "first_confession", "icon": "💌", "label": "第一次表白"})

        return milestones
