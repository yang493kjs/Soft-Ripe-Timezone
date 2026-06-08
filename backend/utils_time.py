# -*- coding: utf-8 -*-
"""时间和天气工具函数"""
import json
import urllib.request
import urllib.parse
from datetime import datetime


def get_current_time(timezone: str = "Asia/Shanghai") -> str:
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(timezone)
        now = datetime.now(tz)
    except:
        now = datetime.now()
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    weekday = weekdays[now.weekday()]
    return f"当前时间：{now.strftime('%Y年%m月%d日')} {weekday} {now.strftime('%H:%M:%S')}（{timezone}）"


def get_time_context() -> tuple:
    """获取当前时间上下文，返回 (完整版, 紧凑版)"""
    now = datetime.now()
    hour = now.hour
    minute = now.minute
    weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][now.weekday()]

    if 6 <= hour < 9:
        period, feel = "清晨", "天刚亮，空气清新"
    elif 9 <= hour < 12:
        period, feel = "上午", "上午阳光正好"
    elif 12 <= hour < 14:
        period, feel = "中午", "中午，适合吃饭休息"
    elif 14 <= hour < 17:
        period, feel = "下午", "下午时段"
    elif 17 <= hour < 19:
        period, feel = "傍晚", "傍晚，天色渐暗"
    elif 19 <= hour < 22:
        period, feel = "晚上", "晚上，天已经黑了"
    elif 22 <= hour < 24:
        period, feel = "深夜", "深夜了，外面一片漆黑"
    else:
        period, feel = "凌晨", "凌晨，所有人都睡了，外面一片漆黑"

    sleep_warn = ""
    if 0 <= hour < 6:
        sleep_warn = f"""

⛔ 时间硬约束（最高优先级，覆盖其他所有规则）：
现在真实时间是凌晨{hour:02d}:{minute:02d}，外面一片漆黑，所有人睡了。
你本来在睡觉，是被消息吵醒的。
🚫 绝对禁止说的话：提到"太阳""阳光""天亮""出去""画速写""跑步""上课""食堂""写生"等任何白天活动。
🚫 绝对禁止回复"早呀""早上好"——凌晨不是早上！
✅ 正确反应：你被吵醒了，迷迷糊糊的。回复要短，可以反问"这么晚了还没睡呀？"或"你怎么醒着？"
你是半梦半醒的状态，不是精神饱满的状态。"""
    elif 6 <= hour < 7:
        sleep_warn = "\n（现在是清晨六点多，天刚蒙蒙亮。你如果醒了可能还有点迷糊，不要精神饱满地打招呼。）"
    elif 22 <= hour < 24:
        sleep_warn = "\n（现在是深夜了，你准备睡觉或已经躺下了。回复要简短。如果对方还在聊天，可以问'还不休息吗'。）"

    full_context = f"""
【当前时间】
今天是{weekday}，{period}（{hour:02d}:{minute:02d}）。{feel}。{sleep_warn}
"""
    compact_context = f"[当前真实时间：{weekday} {period} {hour:02d}:{minute:02d}]{sleep_warn}"

    return full_context, compact_context


def get_weather(city: str) -> str:
    try:
        url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1&lang=zh"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        current = data["current_condition"][0]
        temp = current["temp_C"]
        feels_like = current["FeelsLikeC"]
        desc = current["weatherDesc"][0]["value"]
        humidity = current["humidity"]
        wind = current["windspeedKmph"]
        wind_dir = current["winddir16Point"]
        location = data["nearest_area"][0]["areaName"][0]["value"]
        result = f"{location}: {temp}C(体感{feels_like}C), {desc}, 湿度{humidity}%, 风速{wind}km/h {wind_dir}"
        return result
    except Exception as e:
        return f"获取天气失败: {str(e)}"


def execute_tool(tool_name: str, arguments: dict) -> str:
    if tool_name == "get_current_time":
        return get_current_time(arguments.get("timezone", "Asia/Shanghai"))
    elif tool_name == "get_weather":
        return get_weather(arguments.get("city", "北京"))
    return f"未知工具: {tool_name}"
