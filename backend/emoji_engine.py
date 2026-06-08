# -*- coding: utf-8 -*-
"""表情包引擎 — LLM 自主决定表情 + 人设/阶段感知

核心思路：不为表情单独调一次 LLM，而是在 AI 的 System Prompt 中
注入表情使用规则，AI 在生成回复时自行决定是否插入 <emoji:分类> 标记，
后端解析标记并替换为实际表情 URL。
"""

import os
import random
import re
from typing import Optional

from settings import logger, PERSONAS

# --- 配置 ---
EMOJI_DIR = os.path.join(os.path.dirname(__file__), "static", "emojis")
EMOJI_TAG_PATTERN = re.compile(r"<emoji:(\w+)>")

# 各人设的表情使用频率（用于 prompt 中的语气指导）
PERSONA_EMOJI_STYLE = {
    "sunny":       {"frequency": "较高", "tone": "活泼可爱，喜欢用开心的表情"},
    "clingy":      {"frequency": "较高", "tone": "撒娇卖萌，偶尔用委屈/可怜的表情"},
    "cool":        {"frequency": "很低", "tone": "几乎不用表情，偶尔在特别时刻用一个简单的"},
    "intellectual": {"frequency": "较低", "tone": "偶尔用温和的表情，不会太夸张"},
    "sensitive":   {"frequency": "中等", "tone": "情绪敏感，难过时可能用 sad 表情"},
    "independent": {"frequency": "低", "tone": "克制，偶尔用一个高冷的表情"},
    "gentle_mature": {"frequency": "中等", "tone": "温柔，偶尔用温暖的微笑表情"},
    "needy_mature": {"frequency": "中等", "tone": "渴望关注，偶尔用撒娇表情"},
    "career_woman": {"frequency": "很低", "tone": "几乎不用表情，偶尔用礼貌的微笑"},
}

# 各关系阶段的表情尺度限制
PHASE_EMOJI_RULES = {
    "acquaintance": "刚认识，不要用太亲密的表情（如 loved），保持礼貌距离",
    "ambiguous":    "暧昧期，可以适当用一点可爱的表情，但不要过于亲密",
    "observation":  "互相观察中，表情使用要克制，不要显得太主动",
    "heartbeat":    "心动期，可以多用一些表达好感的表情",
    "together":     "热恋期，可以自由使用各种表情，包括 loved",
    "passion":      "激情期，表情使用可以很大胆",
    "stable":       "稳定期，偶尔用表情点缀，不需要太频繁",
}


def get_emoji_categories() -> list:
    """获取所有已存在的表情分类目录"""
    if not os.path.exists(EMOJI_DIR):
        return []
    return sorted([
        d for d in os.listdir(EMOJI_DIR)
        if os.path.isdir(os.path.join(EMOJI_DIR, d))
    ])


def list_emoji_files(category: str) -> list:
    """列出分类下所有表情文件"""
    cat_dir = os.path.join(EMOJI_DIR, category)
    if not os.path.exists(cat_dir):
        return []
    return sorted([
        f for f in os.listdir(cat_dir)
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))
    ])


def get_random_emoji(category: str) -> Optional[str]:
    """
    从分类随机选一个表情，返回 URL 路径。

    Returns:
        /static/emojis/{category}/{filename} 或 None
    """
    files = list_emoji_files(category)
    if not files:
        logger.warning(f"[表情引擎] 分类 '{category}' 为空")
        return None

    choice = random.choice(files)
    return f"/static/emojis/{category}/{choice}"


def parse_emoji_tags(text: str) -> list:
    """
    从 AI 回复中提取所有 <emoji:分类> 标记。

    Returns:
        [{"tag": "<emoji:happy>", "category": "happy", "url": "/static/.../1.gif"}, ...]
        如果分类无文件，url 为 None，但 tag 仍会返回用于清理
    """
    results = []
    for m in EMOJI_TAG_PATTERN.finditer(text):
        category = m.group(1)
        url = get_random_emoji(category)
        results.append({
            "tag": m.group(0),
            "category": category,
            "url": url
        })
    return results


def replace_emoji_tags(text: str) -> tuple:
    """
    将 AI 回复中的 <emoji:分类> 替换为实际表情 URL。

    Returns:
        (clean_text, emoji_list)
        clean_text: 替换后的文本（<emoji:xxx> 被移除或替换为 URL）
        emoji_list: [{"category": "happy", "url": "/static/...", "tag": "<emoji:happy>"}, ...]
    """
    emoji_list = parse_emoji_tags(text)
    clean = text
    for item in emoji_list:
        clean = clean.replace(item["tag"], "", 1)

    # 清理多余空格
    clean = re.sub(r"\n{3,}", "\n\n", clean)
    clean = clean.strip()

    return clean, emoji_list


def build_emoji_prompt_instruction(persona_id: str, phase: str) -> str:
    """
    构建注入 System Prompt 的表情使用指导。

    根据人设和关系阶段，生成一段自然语言指令，告诉 AI
    如何使用 <emoji:分类> 标记。

    Returns:
        要注入 prompt 的文本，如果无需表情功能则返回空字符串
    """
    categories = get_emoji_categories()
    if not categories:
        return ""

    has_any = any(list_emoji_files(cat) for cat in categories)
    if not has_any:
        return ""

    style = PERSONA_EMOJI_STYLE.get(persona_id, {"frequency": "中等", "tone": "适度使用表情"})
    phase_rule = PHASE_EMOJI_RULES.get(phase, "适度使用表情")

    return (
        "## 表情包发送规则\n"
        "重要：你可以发送表情包！格式是在回复中插入 <emoji:分类名> 标记，系统会自动替换成真实的表情包图片。\n"
        "可用分类：" + ", ".join(categories) + "\n\n"
        "你的风格：" + style["tone"] + "，使用频率" + style["frequency"] + "。\n"
        "当前关系阶段：" + phase + " — " + phase_rule + "\n\n"
        "使用原则：\n"
        "- 当对方让你发表情包、发图片时，直接用 <emoji:happy> 这样的标记来发，不要说你发不了图\n"
        "- 开心/愉悦 → happy，难过/安慰 → sad，生气 → angry，惊讶 → surprised\n"
        "- 表达爱意/亲密 → loved，累/困 → tired，困惑 → confused，回避/敷衍 → evasive\n"
        "- 一个回复最多用 1-2 个表情，不要滥用\n"
        "- 如果不确定是否该用，就不需要用\n\n"
        "示例：\n"
        '"今天天气真好呀 <emoji:happy>"\n'
        '"别难过了…… <emoji:sad>"\n'
        '"你说什么？ <emoji:confused>"\n'
        '"给你发个可爱的表情包~ <emoji:happy>"'
    )