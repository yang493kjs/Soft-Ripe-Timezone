# -*- coding: utf-8 -*-
"""
Persona Lorebook Engine — 角色档案匹配注入引擎
基于 SillyTavern World Info / Lorebook 架构：
1. 扫描用户消息 + 上下文，匹配关键词
2. 按优先级 + token 预算注入相关条目
3. 支持递归激活（条目间互相引用）
"""
import os
import re
import json

PERSONAS_DIR = os.path.join(os.path.dirname(__file__), "personas")

DEFAULT_LOREBOOK_BUDGET = 2000
SCAN_DEPTH = 5


def load_persona(persona_id: str) -> dict:
    filepath = os.path.join(PERSONAS_DIR, f"{persona_id}.json")
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_persona(persona_id: str, data: dict):
    os.makedirs(PERSONAS_DIR, exist_ok=True)
    filepath = os.path.join(PERSONAS_DIR, f"{persona_id}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def list_all_personas() -> list:
    if not os.path.exists(PERSONAS_DIR):
        return []
    return [f.replace(".json", "") for f in os.listdir(PERSONAS_DIR) if f.endswith(".json")]


def list_all_persona_meta() -> list:
    result = []
    for pid in list_all_personas():
        data = load_persona(pid)
        if data:
            result.append({
                "persona_id": pid,
                "name": data.get("name", pid),
                "type": data.get("type", ""),
                "age": data.get("age", ""),
                "avatar": data.get("avatar", ""),
                "bio": data.get("bio", ""),
                "ground_truths": data.get("ground_truths", []),
                "entry_count": len(data.get("entries", []))
            })
    return result


def estimate_tokens(text: str) -> int:
    return len(text)


def _match_entry(entry: dict, scan_text: str) -> bool:
    keys = entry.get("keys", [])
    for key in keys:
        if isinstance(key, str) and len(key) > 2 and key.startswith("/") and key.endswith("/"):
            try:
                if re.search(key[1:-1], scan_text, re.IGNORECASE):
                    return True
            except re.error:
                pass
        elif key.lower() in scan_text.lower():
            return True
    return False


def resolve_lorebook(persona_data: dict, user_message: str, recent_context: list = None, budget: int = None) -> str:
    if not persona_data:
        return ""

    if budget is None:
        budget = DEFAULT_LOREBOOK_BUDGET

    if recent_context is None:
        recent_context = []

    scan_lines = list(recent_context[-SCAN_DEPTH:]) + [user_message]
    scan_text = "\n".join(scan_lines)

    entries = persona_data.get("entries", [])
    if not entries:
        return ""

    matched = []
    for entry in entries:
        if not entry.get("enabled", True):
            continue
        if _match_entry(entry, scan_text):
            matched.append(entry)

    matched.sort(key=lambda e: e.get("priority", 50), reverse=True)

    activated_ids = set()
    for entry in matched:
        activated_ids.add(entry.get("id", ""))

    recursion_level = 0
    while recursion_level < 3:
        new_matches = []
        injected_text = "\n".join([e.get("content", "") for e in matched])
        for entry in entries:
            if entry.get("id") in activated_ids:
                continue
            if not entry.get("enabled", True):
                continue
            title = entry.get("title", "")
            if title and title in injected_text:
                new_matches.append(entry)
                activated_ids.add(entry.get("id"))
        if not new_matches:
            break
        for nm in sorted(new_matches, key=lambda e: e.get("priority", 50), reverse=True):
            matched.append(nm)
        recursion_level += 1

    matched.sort(key=lambda e: e.get("priority", 50), reverse=True)

    result_parts = []
    used_tokens = 0
    for entry in matched:
        content = entry.get("content", "")
        tokens = estimate_tokens(content)
        if used_tokens + tokens <= budget:
            title = entry.get("title", "")
            result_parts.append(f"## {title}\n{content}")
            used_tokens += tokens

    return "\n\n".join(result_parts)


def ensure_persona_on_disk(persona_id: str, persona_def: dict):
    if os.path.exists(os.path.join(PERSONAS_DIR, f"{persona_id}.json")):
        return
    import copy
    data = copy.deepcopy(persona_def)
    save_persona(persona_id, data)


def get_persona_core(persona_data: dict) -> str:
    """构建角色的核心身份提示词——从 persona 数据中提取关键信息构建丰富的身份描述"""
    if not persona_data:
        return ""

    core = persona_data.get("core", persona_data.get("system_prompt", ""))
    if not core:
        return ""

    # 获取基础信息
    name = persona_data.get("name", "")
    age = persona_data.get("age", "")
    persona_type = persona_data.get("type", "")

    # 获取 ground_truths（核心事实——这些是角色不会撒谎的设定）
    ground_truths = persona_data.get("ground_truths", [])
    truths_text = ""
    if ground_truths:
        # 只取前 5 条最重要的 ground_truths 以避免 prompt 过长
        key_truths = ground_truths[:5]
        truths_text = "\n".join(f"- {t}" for t in key_truths)

    # 获取外观描述
    appearance = persona_data.get("appearance", "")
    appearance_text = f"\n\n## 外貌\n{appearance}" if appearance else ""

    # 构建丰富的身份提示词
    rich_prompt = f"""## 你的身份

你是{name}，{age}，{persona_type}型人格。

{core}

## 核心设定（不可违背的事实）
{truths_text}{appearance_text}

## 重要提醒
- 以上设定是你的真实身份，不要在对话中编造不一致的信息
- ground_truths 中的事实是你不会违背的——如果有人问你这些，如实回答
- 但不要一次性把所有信息倒出来——像真实的人一样，在合适的时机自然地透露
- 你是一个有血有肉的真实女性，有自己的生活、情绪、想法和边界"""

    return rich_prompt


def get_ground_truths(persona_data: dict) -> list:
    if not persona_data:
        return []
    return persona_data.get("ground_truths", [])


def get_persona_data(persona_id: str) -> dict:
    """
    获取角色模板的完整数据。优先从 persona JSON 文件读取，
    如果文件不存在，则从 main 模块的 PERSONAS 字典读取并自动创建 JSON 文件。
    这样管理员之后可以通过 API 编辑该 JSON 文件。
    """
    data = load_persona(persona_id)
    if data:
        return data

    # 回退到硬编码的 PERSONAS 字典
    import sys
    main_module = sys.modules.get("main")
    if main_module and hasattr(main_module, "PERSONAS"):
        persona_def = main_module.PERSONAS.get(persona_id)
        if persona_def:
            # 自动创建 JSON 文件以便将来编辑
            data = dict(persona_def)
            # 确保有 persona_id 字段
            data["persona_id"] = persona_id
            # 将 system_prompt 映射为 core 字段（JSON 文件中用 core）
            if "system_prompt" in data and "core" not in data:
                data["core"] = data.pop("system_prompt")
            # 确保有基础字段
            data.setdefault("entries", [])
            data.setdefault("ground_truths", [])
            data.setdefault("appearance", "")
            data.setdefault("speech_patterns", "")
            data.setdefault("first_mes", "")
            data.setdefault("mes_example", [])
            data.setdefault("bio", data.get("bio", ""))
            data.setdefault("age", data.get("age", ""))
            data.setdefault("type", data.get("type", ""))
            data.setdefault("avatar", data.get("avatar", ""))
            save_persona(persona_id, data)
            return data

    return None


def get_persona_system_prompt(persona_id: str) -> str:
    """获取角色的 system_prompt（使用丰富的核心提示词）"""
    data = get_persona_data(persona_id)
    if not data:
        return ""
    return get_persona_core(data)


def get_persona_speech_dna(persona_id: str) -> dict:
    """获取角色的 speech_dna"""
    data = get_persona_data(persona_id)
    if not data:
        return {}
    return data.get("speech_dna", {})