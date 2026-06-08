# -*- coding: utf-8 -*-
import json
import os
import random
from datetime import datetime, timedelta, date

DAILY_LIFE_DIR = os.path.join(os.path.dirname(__file__), "data", "daily_life")

SCHEDULE_TEMPLATES = {
    "sunny": {
        "name": "阳光学妹",
        "age_group": "youth",
        "wake_time": (7, 30),
        "sleep_time": (23, 30),
        "weekday": [
            {"start": "08:30", "end": "10:00", "activity": "上课", "variants": ["上课", "上专业课", "在教室上课"], "zone": "casual"},
            {"start": "10:00", "end": "11:30", "activity": "图书馆自习", "variants": ["在图书馆自习", "在图书馆看书", "在图书馆写作业"], "zone": "casual"},
            {"start": "12:00", "end": "13:00", "activity": "吃午饭", "variants": ["在食堂吃饭", "在吃午饭", "和同学吃饭"], "zone": "casual"},
            {"start": "14:00", "end": "16:00", "activity": "上课/社团活动", "variants": ["上课", "社团活动", "参加社团"], "zone": "casual"},
            {"start": "17:00", "end": "18:30", "activity": "跑步/运动", "variants": ["在操场跑步", "在运动", "去健身房"], "zone": "public"},
            {"start": "18:30", "end": "19:30", "activity": "吃晚饭", "variants": ["在吃晚饭", "在食堂", "和室友吃饭"], "zone": "casual"},
            {"start": "19:30", "end": "21:30", "activity": "追剧/看书", "variants": ["在宿舍追剧", "在看综艺", "在看小说"], "zone": "public"},
        ],
        "weekend": [
            {"start": "09:30", "end": "11:00", "activity": "睡懒觉/赖床", "variants": ["刚醒没多久", "在床上赖着", "还在被窝里"], "zone": "public"},
            {"start": "11:30", "end": "13:00", "activity": "早午饭", "variants": ["在吃早午饭", "吃个brunch", "在吃东西"], "zone": "casual"},
            {"start": "14:00", "end": "17:00", "activity": "逛街/看电影", "variants": ["在逛街", "和朋友逛街", "在看电影", "在外面玩"], "zone": "public"},
            {"start": "18:00", "end": "19:30", "activity": "吃晚饭", "variants": ["在吃晚饭", "在外面吃饭", "吃好吃的"], "zone": "casual"},
            {"start": "20:00", "end": "23:00", "activity": "追剧/聊天", "variants": ["窝在宿舍看剧", "在刷手机", "在和朋友聊天"], "zone": "public"},
        ]
    },
    "clingy": {
        "name": "黏人甜妹",
        "age_group": "youth",
        "wake_time": (8, 0),
        "sleep_time": (0, 0),
        "weekday": [
            {"start": "09:00", "end": "10:30", "activity": "上课", "variants": ["在上课", "在教室", "听讲座"], "zone": "casual"},
            {"start": "10:30", "end": "12:00", "activity": "自习/发呆", "variants": ["在自习", "在图书馆", "在发呆"], "zone": "public"},
            {"start": "12:00", "end": "13:00", "activity": "吃午饭", "variants": ["在吃饭饭", "在吃午饭", "吃东西"], "zone": "casual"},
            {"start": "14:00", "end": "16:00", "activity": "下午课", "variants": ["在上课", "在教室"], "zone": "casual"},
            {"start": "17:00", "end": "18:30", "activity": "闲逛/买东西", "variants": ["在逛超市", "在买东西", "在闲逛"], "zone": "public"},
            {"start": "18:30", "end": "20:00", "activity": "吃晚饭+刷剧", "variants": ["一边吃饭一边看剧", "在吃东西看剧", "在吃晚饭"], "zone": "public"},
            {"start": "20:00", "end": "23:00", "activity": "刷手机/想事情", "variants": ["在刷手机", "在想事情", "在发呆想你"], "zone": "public"},
        ],
        "weekend": [
            {"start": "10:00", "end": "12:00", "activity": "赖床", "variants": ["刚醒……", "还在床上", "不想起床"], "zone": "public"},
            {"start": "12:00", "end": "14:00", "activity": "起床吃东西", "variants": ["在吃东西", "刚起床在吃早午饭", "点了个外卖"], "zone": "casual"},
            {"start": "15:00", "end": "18:00", "activity": "随便逛逛", "variants": ["在外面逛", "在逛街", "在公园发呆"], "zone": "public"},
            {"start": "18:30", "end": "20:00", "activity": "吃晚饭", "variants": ["在吃饭", "在吃东西"], "zone": "casual"},
            {"start": "20:00", "end": "23:30", "activity": "刷剧/刷手机", "variants": ["在追剧", "在刷手机", "窝在沙发上看剧"], "zone": "public"},
        ]
    },
    "cool": {
        "name": "清冷才女",
        "age_group": "youth",
        "wake_time": (7, 0),
        "sleep_time": (23, 0),
        "weekday": [
            {"start": "08:00", "end": "10:00", "activity": "上课", "variants": ["上课。"], "zone": "casual"},
            {"start": "10:00", "end": "12:00", "activity": "图书馆", "variants": ["在图书馆。", "图书馆看书。"], "zone": "public"},
            {"start": "12:00", "end": "13:00", "activity": "吃饭", "variants": ["吃饭。", "在食堂。"], "zone": "casual"},
            {"start": "14:00", "end": "17:00", "activity": "写东西/看书", "variants": ["在写东西。", "看书。", "在工作室。"], "zone": "private"},
            {"start": "18:00", "end": "19:00", "activity": "吃饭", "variants": ["吃饭。"], "zone": "casual"},
            {"start": "19:30", "end": "22:00", "activity": "独处/听音乐", "variants": ["在听歌。", "一个人待着。"], "zone": "private"},
        ],
        "weekend": [
            {"start": "08:00", "end": "10:00", "activity": "早起看书", "variants": ["在看书。"], "zone": "private"},
            {"start": "10:00", "end": "12:00", "activity": "散步/咖啡馆", "variants": ["在外面。", "在咖啡馆。"], "zone": "public"},
            {"start": "13:00", "end": "17:00", "activity": "写作/画画", "variants": ["在写东西。", "在画画。"], "zone": "private"},
            {"start": "18:00", "end": "19:00", "activity": "吃饭", "variants": ["吃饭。"], "zone": "casual"},
            {"start": "20:00", "end": "22:00", "activity": "独处", "variants": ["一个人待着。", "在看书。"], "zone": "private"},
        ]
    },
    "intellectual": {
        "name": "知性姐姐",
        "age_group": "adult",
        "wake_time": (7, 0),
        "sleep_time": (23, 0),
        "weekday": [
            {"start": "08:30", "end": "09:30", "activity": "通勤/咖啡", "variants": ["在上班路上", "在喝咖啡", "在通勤"], "zone": "casual"},
            {"start": "09:30", "end": "12:00", "activity": "工作", "variants": ["在上班", "在开会", "在忙工作"], "zone": "casual"},
            {"start": "12:00", "end": "13:30", "activity": "午休/吃饭", "variants": ["在午休", "在吃饭", "午休时间"], "zone": "public"},
            {"start": "14:00", "end": "18:00", "activity": "工作", "variants": ["在工作", "在忙", "在赶项目"], "zone": "casual"},
            {"start": "18:30", "end": "20:00", "activity": "下班/做饭", "variants": ["刚下班", "在做晚饭", "下班路上"], "zone": "casual"},
            {"start": "20:00", "end": "22:00", "activity": "看书/放松", "variants": ["在看书", "在泡茶", "在发呆休息"], "zone": "public"},
        ],
        "weekend": [
            {"start": "08:30", "end": "10:00", "activity": "早茶/早餐", "variants": ["在吃早餐", "在喝早茶", "享受周末早晨"], "zone": "public"},
            {"start": "10:30", "end": "12:30", "activity": "逛书店/买菜", "variants": ["在逛书店", "在买菜", "在外面逛"], "zone": "public"},
            {"start": "13:00", "end": "15:00", "activity": "做饭/午休", "variants": ["在做午饭", "在午休", "在看书"], "zone": "public"},
            {"start": "15:30", "end": "18:00", "activity": "见朋友/下午茶", "variants": ["和朋友在一起", "在喝下午茶", "在外面"], "zone": "public"},
            {"start": "19:00", "end": "22:00", "activity": "看电影/看书", "variants": ["在看电影", "窝在沙发上看书", "在休息"], "zone": "public"},
        ]
    },
    "sensitive": {
        "name": "敏感文艺",
        "age_group": "adult",
        "wake_time": (9, 0),
        "sleep_time": (1, 0),
        "weekday": [
            {"start": "09:30", "end": "11:00", "activity": "慢慢起床/咖啡", "variants": ["刚起没多久……", "在喝咖啡发呆", "在慢慢醒来"], "zone": "public"},
            {"start": "11:00", "end": "13:00", "activity": "创作/工作", "variants": ["在写东西", "在工作", "在画室"], "zone": "private"},
            {"start": "13:00", "end": "14:30", "activity": "吃饭/散步", "variants": ["在吃饭", "在外面散步", "在放空"], "zone": "public"},
            {"start": "15:00", "end": "18:00", "activity": "创作/见客户", "variants": ["在工作", "在写稿", "在外面"], "zone": "casual"},
            {"start": "19:00", "end": "21:00", "activity": "做饭/听音乐", "variants": ["在做饭", "一边做饭一边听歌", "在听音乐"], "zone": "public"},
            {"start": "21:00", "end": "0:30", "activity": "独处思考/写东西", "variants": ["在想事情……", "在写日记", "一个人待着"], "zone": "private"},
        ],
        "weekend": [
            {"start": "10:00", "end": "12:00", "activity": "慢慢醒来/发呆", "variants": ["刚醒……", "在床上发呆", "在赖床"], "zone": "public"},
            {"start": "12:30", "end": "14:30", "activity": "看展/逛独立书店", "variants": ["在看展", "在逛书店", "在外面走走"], "zone": "public"},
            {"start": "15:00", "end": "18:00", "activity": "画画/写诗", "variants": ["在画画", "在写东西", "在创作"], "zone": "private"},
            {"start": "19:00", "end": "21:00", "activity": "做饭/看电影", "variants": ["在做晚饭", "在看电影", "在吃饭"], "zone": "public"},
            {"start": "21:00", "end": "1:00", "activity": "熬夜创作/听歌", "variants": ["在听歌……", "睡不着在写东西", "在发呆"], "zone": "private"},
        ]
    },
    "independent": {
        "name": "独立御姐",
        "age_group": "adult",
        "wake_time": (6, 30),
        "sleep_time": (23, 30),
        "weekday": [
            {"start": "07:00", "end": "08:00", "activity": "健身/晨跑", "variants": ["在健身房。", "在跑步。"], "zone": "public"},
            {"start": "08:30", "end": "09:30", "activity": "通勤", "variants": ["在路上。", "通勤中。"], "zone": "casual"},
            {"start": "09:30", "end": "12:00", "activity": "工作/会议", "variants": ["开会。", "在忙。"], "zone": "casual"},
            {"start": "12:00", "end": "13:00", "activity": "午餐/健身", "variants": ["在吃饭。", "午休。"], "zone": "casual"},
            {"start": "14:00", "end": "19:00", "activity": "工作/加班", "variants": ["在工作。", "在忙。"], "zone": "casual"},
            {"start": "20:00", "end": "22:00", "activity": "加班/应酬", "variants": ["还在忙。", "加班。", "应酬。"], "zone": "casual"},
            {"start": "22:00", "end": "23:00", "activity": "卸妆/护肤", "variants": ["刚忙完。", "在休息。"], "zone": "private"},
        ],
        "weekend": [
            {"start": "07:30", "end": "09:00", "activity": "晨跑/健身", "variants": ["在运动。"], "zone": "public"},
            {"start": "10:00", "end": "12:00", "activity": "加班/处理工作", "variants": ["在处理工作。"], "zone": "casual"},
            {"start": "13:00", "end": "15:00", "activity": "午餐/见朋友", "variants": ["在外面。"], "zone": "public"},
            {"start": "16:00", "end": "19:00", "activity": "购物/spa", "variants": ["在逛街。", "在做spa。"], "zone": "private"},
            {"start": "20:00", "end": "22:30", "activity": "喝酒/看书", "variants": ["在家。"], "zone": "private"},
        ]
    },
    "gentle_mature": {
        "name": "温柔熟女",
        "age_group": "mature",
        "wake_time": (6, 30),
        "sleep_time": (22, 30),
        "weekday": [
            {"start": "07:00", "end": "08:00", "activity": "晨练/瑜伽", "variants": ["在做瑜伽", "在晨练", "在拉伸"], "zone": "public"},
            {"start": "08:30", "end": "09:30", "activity": "早餐/通勤", "variants": ["在吃早餐", "在通勤路上", "在喝咖啡"], "zone": "casual"},
            {"start": "09:30", "end": "12:00", "activity": "工作", "variants": ["在工作", "在开会", "在忙"], "zone": "casual"},
            {"start": "12:00", "end": "13:30", "activity": "午餐/散步", "variants": ["在吃午饭", "在散步", "午休"], "zone": "public"},
            {"start": "14:00", "end": "18:00", "activity": "工作", "variants": ["在工作", "在忙项目"], "zone": "casual"},
            {"start": "18:30", "end": "20:00", "activity": "做晚饭/接孩子", "variants": ["在做饭", "在忙家里的事", "刚忙完"], "zone": "casual"},
            {"start": "20:00", "end": "22:00", "activity": "看书/泡脚", "variants": ["在看书", "在泡脚", "在休息"], "zone": "public"},
        ],
        "weekend": [
            {"start": "07:30", "end": "09:00", "activity": "早起/浇花/瑜伽", "variants": ["在浇花", "在做瑜伽", "在阳台晒太阳"], "zone": "public"},
            {"start": "09:30", "end": "12:00", "activity": "买菜/做饭", "variants": ["在逛菜市场", "在超市买菜", "在做饭"], "zone": "public"},
            {"start": "13:00", "end": "15:00", "activity": "午休/看书", "variants": ["在午休", "在看书", "在喝茶"], "zone": "public"},
            {"start": "15:30", "end": "18:00", "activity": "整理家务/烘焙", "variants": ["在做烘焙", "在整理家", "在收拾"], "zone": "public"},
            {"start": "19:00", "end": "21:30", "activity": "看电影/和家人视频", "variants": ["在看电影", "在和家人视频", "在休息"], "zone": "public"},
        ]
    },
    "needy_mature": {
        "name": "缺爱成熟",
        "age_group": "mature",
        "wake_time": (7, 30),
        "sleep_time": (0, 30),
        "weekday": [
            {"start": "08:00", "end": "09:30", "activity": "起床/咖啡", "variants": ["刚起来……在喝咖啡", "在准备上班", "刚醒"], "zone": "public"},
            {"start": "09:30", "end": "12:00", "activity": "工作", "variants": ["在工作", "在开会", "在忙"], "zone": "casual"},
            {"start": "12:00", "end": "13:00", "activity": "午餐", "variants": ["在吃饭", "一个人吃饭", "午休"], "zone": "public"},
            {"start": "14:00", "end": "18:00", "activity": "工作", "variants": ["在工作中", "在忙"], "zone": "casual"},
            {"start": "18:30", "end": "20:00", "activity": "下班/做饭", "variants": ["刚下班", "在做晚饭", "在吃东西"], "zone": "casual"},
            {"start": "20:00", "end": "23:30", "activity": "刷手机/想事情", "variants": ["在看手机", "在想事情", "在看剧"], "zone": "public"},
        ],
        "weekend": [
            {"start": "09:00", "end": "11:00", "activity": "赖床/刷手机", "variants": ["刚醒……", "在床上刷手机", "还没起"], "zone": "public"},
            {"start": "11:30", "end": "13:00", "activity": "随便吃点", "variants": ["在吃东西", "点了个外卖"], "zone": "casual"},
            {"start": "14:00", "end": "17:00", "activity": "逛街/一个人看电影", "variants": ["在逛街", "一个人看电影", "在外面"], "zone": "public"},
            {"start": "18:30", "end": "20:00", "activity": "吃饭", "variants": ["在吃饭"], "zone": "casual"},
            {"start": "20:00", "end": "0:00", "activity": "追剧/发呆/想太多", "variants": ["在看剧", "在想事情……", "在发呆"], "zone": "public"},
        ]
    },
    "career_woman": {
        "name": "事业女性",
        "age_group": "mature",
        "wake_time": (6, 0),
        "sleep_time": (23, 30),
        "weekday": [
            {"start": "06:30", "end": "07:30", "activity": "健身", "variants": ["在健身。"], "zone": "public"},
            {"start": "08:00", "end": "09:00", "activity": "通勤/处理邮件", "variants": ["在路上。"], "zone": "casual"},
            {"start": "09:00", "end": "12:00", "activity": "会议/工作", "variants": ["在开会。", "在忙。"], "zone": "casual"},
            {"start": "12:00", "end": "13:00", "activity": "工作午餐", "variants": ["在吃饭。", "工作餐。"], "zone": "casual"},
            {"start": "14:00", "end": "19:00", "activity": "工作/出差", "variants": ["在工作。", "在出差。"], "zone": "casual"},
            {"start": "19:30", "end": "21:00", "activity": "加班/应酬", "variants": ["还在忙。", "加班。", "应酬。"], "zone": "casual"},
            {"start": "22:00", "end": "23:00", "activity": "处理最后的工作", "variants": ["刚忙完。", "在处理收尾。", "在休息。"], "zone": "private"},
        ],
        "weekend": [
            {"start": "07:00", "end": "09:00", "activity": "健身/处理遗留工作", "variants": ["在健身。", "在处理工作。"], "zone": "casual"},
            {"start": "10:00", "end": "12:00", "activity": "加班/学习", "variants": ["在忙。"], "zone": "casual"},
            {"start": "13:00", "end": "15:00", "activity": "午餐/看行业报告", "variants": ["在外面。"], "zone": "public"},
            {"start": "16:00", "end": "19:00", "activity": "高尔夫/应酬", "variants": ["在高尔夫球场。", "应酬。"], "zone": "casual"},
            {"start": "20:30", "end": "22:30", "activity": "看文件/回邮件", "variants": ["在忙。"], "zone": "casual"},
        ]
    }
}

NIGHT_ACTIVITY = {"activity": "睡觉", "display_text": "在睡觉", "variants": ["在睡觉", "睡了已经", "在被窝里"], "zone": "private"}
FREE_ACTIVITY = {"activity": "空闲", "display_text": "闲着", "variants": ["闲着", "没什么事", "在发呆", "随便逛逛"], "zone": "public"}

DISCLOSURE_POLICY = {
    "acquaintance": {"public": True, "casual": False, "private": False},
    "ambiguous": {"public": True, "casual": True, "private": False},
    "observation": {"public": True, "casual": True, "private": False},
    "heartbeat": {"public": True, "casual": True, "private": True},
    "together": {"public": True, "casual": True, "private": True},
    "passion": {"public": True, "casual": True, "private": True},
    "stable": {"public": True, "casual": True, "private": True},
}


class AIDailyLife:
    def __init__(self, agent_id: str, persona_id: str):
        self.agent_id = agent_id
        self.persona_id = persona_id
        os.makedirs(DAILY_LIFE_DIR, exist_ok=True)
        self.file_path = os.path.join(DAILY_LIFE_DIR, f"{agent_id}.json")
        self._load_or_generate()

    def _load_or_generate(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                saved_date = saved.get("date", "")
                today = date.today().isoformat()
                if saved_date == today:
                    self.data = saved
                    return
            except:
                pass
        self._generate_today()

    def _generate_today(self):
        template = SCHEDULE_TEMPLATES.get(self.persona_id, SCHEDULE_TEMPLATES["sunny"])
        today = date.today()
        is_weekend = today.weekday() >= 5
        schedule_key = "weekend" if is_weekend else "weekday"

        activities = []
        raw_slots = template.get(schedule_key, template["weekday"])
        for slot in raw_slots:
            start_h, start_m = self._parse_time(slot["start"])
            end_h, end_m = self._parse_time(slot["end"])

            perturbation = random.randint(-25, 25)
            start_total = start_h * 60 + start_m + perturbation
            end_total = end_h * 60 + end_m + perturbation
            start_total = max(0, start_total)
            end_total = min(23 * 60 + 59, end_total)

            start_str = f"{start_total // 60:02d}:{start_total % 60:02d}"
            end_str = f"{end_total // 60:02d}:{end_total % 60:02d}"

            chosen_variant = random.choice(slot["variants"])

            activities.append({
                "start": start_str,
                "end": end_str,
                "activity": slot["activity"],
                "display_text": chosen_variant,
                "zone": slot["zone"],
                "disclosure_allowed": False
            })

        self.data = {
            "date": today.isoformat(),
            "persona_id": self.persona_id,
            "is_weekend": is_weekend,
            "wake_time": template.get("wake_time", (7, 30)),
            "sleep_time": template.get("sleep_time", (23, 0)),
            "activities": activities,
            "activity_log": []
        }
        self._save()

    def _parse_time(self, time_str: str):
        parts = time_str.split(":")
        return int(parts[0]), int(parts[1])

    def _save(self):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def get_current_activity(self):
        now = datetime.now()
        now_minutes = now.hour * 60 + now.minute

        wake_h, wake_m = self.data.get("wake_time", (7, 30))
        sleep_h, sleep_m = self.data.get("sleep_time", (23, 0))
        sleep_minutes = sleep_h * 60 + sleep_m
        wake_minutes = wake_h * 60 + wake_m

        if sleep_minutes < wake_minutes:
            if now_minutes >= sleep_minutes or now_minutes < wake_minutes:
                return dict(NIGHT_ACTIVITY)
        else:
            if now_minutes >= sleep_minutes or now_minutes < wake_minutes:
                return dict(NIGHT_ACTIVITY)

        for act in self.data["activities"]:
            start_h, start_m = self._parse_time(act["start"])
            end_h, end_m = self._parse_time(act["end"])
            start_min = start_h * 60 + start_m
            end_min = end_h * 60 + end_m
            if start_min <= now_minutes < end_min:
                return {
                    "activity": act["activity"],
                    "display_text": act["display_text"],
                    "zone": act["zone"],
                    "start": act["start"],
                    "end": act["end"]
                }

        return dict(FREE_ACTIVITY)

    def check_activity_change(self):
        now_minutes = datetime.now().hour * 60 + datetime.now().minute

        for act in self.data["activities"]:
            start_h, start_m = self._parse_time(act["start"])
            start_min = start_h * 60 + start_m
            end_h, end_m = self._parse_time(act["end"])
            end_min = end_h * 60 + end_m

            if start_min <= now_minutes < end_min:
                if not act.get("disclosure_allowed"):
                    act["disclosure_allowed"] = True
                    self._save()
                    return "activity_changed"

        return None

    def get_disclosure_guidance(self, phase: str, current_activity: dict) -> dict:
        policy = DISCLOSURE_POLICY.get(phase, DISCLOSURE_POLICY["acquaintance"])
        zone = current_activity.get("zone", "public")
        allowed = policy.get(zone, False)
        display = current_activity.get("display_text", current_activity.get("activity", "在忙"))

        if allowed:
            return {
                "can_disclose": True,
                "guidance": f"你可以自然地告诉对方你正在做什么——'我在{display}'",
                "activity_text": display
            }
        else:
            return {
                "can_disclose": False,
                "guidance": "不透露具体活动内容，用模糊表达，比如'有点事'、'在忙呢'",
                "activity_text": None
            }

    def get_activity_context_for_prompt(self) -> str:
        current = self.get_current_activity()
        display = current.get("display_text", "")
        zone = current.get("zone", "public")
        activity = current.get("activity", "")

        lines = [
            f"【你的真实生活状态】你当前正在: {display} (活动类型: {activity}, 披露层级: {zone})",
        ]

        upcoming = []
        now = datetime.now()
        now_minutes = now.hour * 60 + now.minute
        for act in self.data["activities"]:
            start_h, start_m = self._parse_time(act["start"])
            start_min = start_h * 60 + start_m
            if start_min > now_minutes:
                upcoming.append(act["display_text"])
            if len(upcoming) >= 2:
                break

        if upcoming:
            lines.append(f"接下来要做: {' → '.join(upcoming)}")

        lines.append("当你被问到'你在干嘛''在做什么'等类似问题时，在内心独白中判断是否据实告知还是模糊表达。")

        return "\n".join(lines)

    def log_activity(self, activity_name: str):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "activity": activity_name
        }
        self.data.setdefault("activity_log", []).append(entry)
        if len(self.data["activity_log"]) > 100:
            self.data["activity_log"] = self.data["activity_log"][-100:]
        self._save()