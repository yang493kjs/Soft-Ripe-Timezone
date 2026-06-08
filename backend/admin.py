# -*- coding: utf-8 -*-
"""
管理员 API — 调试/管理端点
验证：所有端点要求在 query string 中传入 admin_user=admin888
"""
import os
import json
import shutil

import uuid

from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from pydantic import BaseModel
from datetime import datetime

admin_router = APIRouter(prefix="/api/admin", tags=["admin"])

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
ADMIN_USERNAME = "admin888"

# 延迟导入 db 模块
def _get_db():
    from db import load_agents, save_agent, load_messages, save_message, clear_messages, delete_agent_from_db
    return load_agents, save_agent, load_messages, save_message, clear_messages, delete_agent_from_db

# ———— 请求体 ————
class RelationshipEditReq(BaseModel):
    user_id: str
    persona_id: str
    intimacy: float = None
    passion: float = None
    commitment: float = None
    days: int = None
    phase: str = None

class ProactiveTriggerReq(BaseModel):
    user_id: str
    persona_id: str
    trigger_type: str = "context"

class PromptEditReq(BaseModel):
    user_id: str
    persona_id: str
    system_prompt: str = None


def _verify_admin(admin_user: str = Query(None)):
    if admin_user != ADMIN_USERNAME:
        raise HTTPException(status_code=403, detail="无管理员权限")
    return admin_user


# ——— 间接引用 main 模块里的函数（延迟导入，避免循环依赖） ———
def _get_emotion(agent_id):
    from main import get_emotion
    return get_emotion(agent_id)

def _get_agent_id(user_id, persona_id):
    from main import load_agents, PERSONAS
    agents = load_agents()
    key = f"{user_id}_{persona_id}"
    if key not in agents:
        raise HTTPException(status_code=404, detail=f"未找到 agent: {key}")
    return agents[key]["agent_id"]


def _save_agent_compat(agent):
    from db import save_agent
    save_agent(agent)


# ============================================================
# 1. 列出所有普通用户及其 agent
# ============================================================
@admin_router.get("/users")
def list_users(admin_user: str = Query(None)):
    _verify_admin(admin_user)
    from main import _load_users, load_agents
    users = _load_users()
    agents = load_agents()
    result = []
    for u in users:
        if u["username"] == ADMIN_USERNAME:
            continue
        user_agents = []
        for key, agent in agents.items():
            if key.startswith(u["username"] + "_"):
                user_agents.append({
                    "key": key,
                    "persona_id": agent.get("persona_id", ""),
                    "persona_name": agent.get("persona_name", ""),
                    "phase": agent.get("phase", "acquaintance"),
                    "days": agent.get("relationship_days", 1)
                })
        result.append({
            "username": u["username"],
            "created_at": u.get("created_at", ""),
            "agents": user_agents
        })
    return result


# ============================================================
# 2. 修改关系值（三角值 + 天数 + 阶段）
# ============================================================
@admin_router.post("/relationship")
def edit_relationship(req: RelationshipEditReq, admin_user: str = Query(None)):
    _verify_admin(admin_user)
    agent_id = _get_agent_id(req.user_id, req.persona_id)
    emo = _get_emotion(agent_id)
    rel = emo.relationship

    if req.intimacy is not None:
        rel["intimacy"] = max(0, min(100, round(req.intimacy, 2)))
    if req.passion is not None:
        rel["passion"] = max(0, min(100, round(req.passion, 2)))
    if req.commitment is not None:
        rel["commitment"] = max(0, min(100, round(req.commitment, 2)))

    if req.days is not None:
        rel["days"] = max(1, req.days)
        from datetime import date as date_type, timedelta
        new_first = datetime.now() - timedelta(days=rel["days"] - 1)
        rel["first_interaction"] = new_first.isoformat()

    if req.phase is not None:
        valid_phases = ["acquaintance", "ambiguous", "observation", "heartbeat", "together", "passion", "stable"]
        if req.phase in valid_phases:
            rel["phase"] = req.phase

    rel["tri_change_log"].append({
        "timestamp": datetime.now().isoformat(),
        "intimacy": rel["intimacy"],
        "passion": rel["passion"],
        "commitment": rel["commitment"],
        "details": "【管理员手动修改】",
        "trigger": "admin_edit"
    })

    emo.save()

    from db import load_agents, save_agent
    agents = load_agents()
    key = f"{req.user_id}_{req.persona_id}"
    if key in agents:
        agent = agents[key]
        agent.update({
            "intimacy": rel["intimacy"],
            "passion": rel["passion"],
            "commitment": rel["commitment"],
            "phase": rel["phase"],
            "relationship_days": rel["days"]
        })
        save_agent(agent)

    return {
        "status": "ok",
        "relationship": {
            "intimacy": rel["intimacy"],
            "passion": rel["passion"],
            "commitment": rel["commitment"],
            "days": rel["days"],
            "phase": rel["phase"]
        }
    }


# ============================================================
# 3. 获取当前关系值
# ============================================================
@admin_router.get("/relationship")
def get_relationship(user_id: str, persona_id: str, admin_user: str = Query(None)):
    _verify_admin(admin_user)
    agent_id = _get_agent_id(user_id, persona_id)
    emo = _get_emotion(agent_id)
    rel = emo.relationship
    return {
        "user_id": user_id,
        "persona_id": persona_id,
        "intimacy": rel["intimacy"],
        "passion": rel["passion"],
        "commitment": rel["commitment"],
        "days": rel["days"],
        "phase": rel["phase"],
        "total_messages": rel.get("total_messages", 0)
    }


# ============================================================
# 4. 强制触发主动消息
# ============================================================
@admin_router.post("/trigger-proactive")
def trigger_proactive(req: ProactiveTriggerReq, admin_user: str = Query(None)):
    _verify_admin(admin_user)
    agent_id = _get_agent_id(req.user_id, req.persona_id)

    from main import PERSONAS, get_emotion, get_memu, call_external_reply, add_to_recall, load_agents
    from db import save_message, load_messages
    agents = load_agents()
    key = f"{req.user_id}_{req.persona_id}"
    agent = agents[key]
    persona_name = agent.get("persona_name", "AI助手")
    persona_id = req.persona_id
    emo = get_emotion(agent_id)
    emo.refresh_days()
    memu = get_memu(agent_id, req.user_id)

    trigger_prompts = {
        "morning": "现在是早上，你刚起床，想跟Ta说声早安。自然一点，不要刻意。",
        "night": "天很晚了，注意到Ta还没休息，想关心一下。不要太啰嗦。",
        "late_night": "已经凌晨了，Ta还在线，你有点担心。想问问Ta为什么还没睡。",
        "missing": "你已经好几个小时没跟Ta说话了，有点想念Ta。用关心的语气主动说句话。",
        "context": "你突然想起你们之前聊过的话题，自然地延续这个话题聊下去。"
    }
    trigger_prompt = trigger_prompts.get(req.trigger_type, trigger_prompts["context"])

    speech_dna = PERSONAS.get(persona_id, {}).get("speech_dna")
    ai_content = call_external_reply(
        agent["system_prompt"], agent_id, trigger_prompt,
        {"phase": emo.relationship.get("phase", "acquaintance"), "emotion": "平静", "confidence": 0.8, "key_observations": []},
        persona_name, memu, emotion_system=emo, speech_dna=speech_dna
    )

    ai_msg = {
        "_id": str(__import__("uuid").uuid4()),
        "content": ai_content,
        "senderId": "ai",
        "timestamp": datetime.now().strftime("%H:%M"),
        "date": "今天",
        "proactive": True,
        "trigger_type": req.trigger_type
    }

    save_message(agent_id, ai_msg)
    memu.add_exchange("", ai_content)
    add_to_recall(agent_id, "assistant", ai_content)

    from main import PENDING_PROACTIVE_DIR
    pending_file = os.path.join(PENDING_PROACTIVE_DIR, f"{key}.json")
    pending_msgs = []
    if os.path.exists(pending_file):
        try:
            with open(pending_file, "r", encoding="utf-8") as f:
                pending_msgs = json.load(f)
        except:
            pending_msgs = []
    pending_msgs.append(ai_msg)
    with open(pending_file, "w", encoding="utf-8") as f:
        json.dump(pending_msgs, f, ensure_ascii=False, indent=2)

    return {"status": "ok", "message": ai_msg}


# ============================================================
# 5. 修改提示词
# ============================================================
@admin_router.post("/update-prompt")
def update_prompt(req: PromptEditReq, admin_user: str = Query(None)):
    _verify_admin(admin_user)
    _get_agent_id(req.user_id, req.persona_id)

    from main import load_agents
    from persona_engine import load_persona, save_persona
    from db import save_agent

    agents = load_agents()
    key = f"{req.user_id}_{req.persona_id}"
    agent = agents[key]

    if req.system_prompt is not None:
        agent["system_prompt"] = req.system_prompt

    save_agent(agent)

    persona_data = load_persona(req.persona_id)
    if persona_data and req.system_prompt is not None:
        persona_data["core"] = req.system_prompt
        save_persona(req.persona_id, persona_data)

    return {"status": "ok", "message": "提示词已更新"}


# ============================================================
# 6. 获取当前提示词（包含 appearance / speech_patterns / mes_example）
# ============================================================
@admin_router.get("/prompt")
def get_prompt(user_id: str, persona_id: str, admin_user: str = Query(None)):
    _verify_admin(admin_user)
    _get_agent_id(user_id, persona_id)
    from main import load_agents
    from persona_engine import load_persona
    agents = load_agents()
    key = f"{user_id}_{persona_id}"
    system_prompt = agents[key].get("system_prompt", "")

    persona_data = load_persona(persona_id)
    prompt_parts = [system_prompt]

    if persona_data:
        appearance_text = persona_data.get("appearance", "")
        if appearance_text:
            prompt_parts.append(f"\n## 你的外貌\n{appearance_text}")

        speech_text = persona_data.get("speech_patterns", "")
        if speech_text:
            prompt_parts.append(f"\n## 你的说话风格（重要！严格遵循）\n{speech_text}")

        mes_examples = persona_data.get("mes_example", [])
        if mes_examples:
            examples_parts = []
            for ex in mes_examples:
                examples_parts.append(f"对方说：{ex.get('user', '')}\n你说：{ex.get('char', '')}")
            examples_text = "\n---\n".join(examples_parts)
            prompt_parts.append(f"\n## 对话示例\n{examples_text}")

    full_prompt = "\n".join(prompt_parts)
    return {
        "system_prompt": full_prompt,
        "persona_name": agents[key].get("persona_name", "")
    }


def _clean_agent_data(agent_id: str, user_id: str, persona_id: str):
    """清理一个 agent 的所有关联数据（文件系统中的）"""
    cleaned = []

    key = f"{user_id}_{persona_id}"

    def _rm(path):
        if os.path.isfile(path):
            os.remove(path)
            return True
        elif os.path.isdir(path):
            shutil.rmtree(path)
            return True
        return False

    # 聊天记录（JSON 文件清理）
    if _rm(os.path.join(DATA_DIR, "messages", f"{agent_id}.json")):
        cleaned.append("聊天记录")

    # 情感记忆
    if _rm(os.path.join(DATA_DIR, "emotion", agent_id)):
        cleaned.append("情感记忆")

    # MEMU 记忆
    if _rm(os.path.join(DATA_DIR, "memu_memory", agent_id)):
        cleaned.append("MEMU记忆")

    # 独白数据（JSON 文件清理）
    if _rm(os.path.join(DATA_DIR, "monologues", f"{agent_id}.json")):
        cleaned.append("独白数据")

    # 主动消息引擎
    if _rm(os.path.join(DATA_DIR, "proactive", f"{agent_id}.json")):
        cleaned.append("主动消息引擎")

    # 分手状态
    if _rm(os.path.join(DATA_DIR, "breakups", f"{agent_id}.json")):
        cleaned.append("分手状态")

    # 忙碌状态
    if _rm(os.path.join(DATA_DIR, "busy", f"{agent_id}.json")):
        cleaned.append("忙碌状态")

    # 纪念日
    if _rm(os.path.join(DATA_DIR, "anniversaries", f"{agent_id}.json")):
        cleaned.append("纪念日")

    # 日程例程
    if _rm(os.path.join(DATA_DIR, "routines", f"{agent_id}.json")):
        cleaned.append("日程例程")

    # 待推送队列
    if _rm(os.path.join(DATA_DIR, "pending_proactive", f"{key}.json")):
        cleaned.append("待推送队列")

    # 需求状态 (Need State Engine)
    if _rm(os.path.join(DATA_DIR, "need_state", f"{agent_id}.json")):
        cleaned.append("需求状态")

    # 用户评价
    if _rm(os.path.join(DATA_DIR, "user_evaluation", f"{agent_id}.json")):
        cleaned.append("用户评价")

    # SQLite 中的数据清理
    from db import clear_messages, clear_monologues
    clear_messages(agent_id)
    clear_monologues(agent_id)

    return cleaned


# ============================================================
# 7. 删除用户（清理所有数据）
# ============================================================
@admin_router.post("/delete-user")
def delete_user(user_id: str, admin_user: str = Query(None)):
    _verify_admin(admin_user)

    from main import _load_users, _save_users, load_agents
    from db import delete_agent_from_db

    users = _load_users()
    found = None
    for u in users:
        if u["username"] == user_id:
            found = u
            break
    if not found:
        raise HTTPException(status_code=404, detail="用户不存在")

    users.remove(found)
    _save_users(users)

    agents = load_agents()
    keys_to_delete = [k for k in agents if k.startswith(f"{user_id}_")]

    total_cleaned = []
    for k in keys_to_delete:
        agent = agents[k]
        agent_id = agent.get("agent_id", "")
        persona_id = agent.get("persona_id", "")
        if agent_id:
            total_cleaned.extend(_clean_agent_data(agent_id, user_id, persona_id))
            delete_agent_from_db(agent_id)

    for k in keys_to_delete:
        del agents[k]

    # 清理可能遗漏的以 user_id_ 开头的文件
    for item in os.listdir(DATA_DIR):
        item_path = os.path.join(DATA_DIR, item)
        if os.path.isfile(item_path) and item.startswith(user_id + "_"):
            os.remove(item_path)
        elif os.path.isdir(item_path):
            for sub in os.listdir(item_path):
                if sub.startswith(user_id + "_"):
                    sub_path = os.path.join(item_path, sub)
                    if os.path.isdir(sub_path):
                        shutil.rmtree(sub_path)
                    else:
                        os.remove(sub_path)

    return {"status": "ok", "detail": f"用户 {user_id} 已删除", "cleaned": list(set(total_cleaned))}


# ============================================================
# 7b. 删除用户的单个 AI 角色（清理该角色的所有数据）
# ============================================================
@admin_router.post("/delete-agent")
def delete_agent(user_id: str, persona_id: str, admin_user: str = Query(None)):
    _verify_admin(admin_user)

    from main import load_agents, clear_recall
    from db import delete_agent_from_db

    agents = load_agents()
    key = f"{user_id}_{persona_id}"
    if key not in agents:
        raise HTTPException(status_code=404, detail=f"未找到 agent: {key}")

    agent = agents[key]
    agent_id = agent.get("agent_id", "")
    persona_name = agent.get("persona_name", persona_id)

    # 清理内存中的对话缓冲区
    if agent_id:
        clear_recall(agent_id)

    # 清理文件系统上的所有数据
    cleaned = _clean_agent_data(agent_id, user_id, persona_id)

    # 从 agents 中删除
    del agents[key]
    delete_agent_from_db(agent_id)

    return {
        "status": "ok",
        "detail": f"已删除用户 {user_id} 的角色「{persona_name}」",
        "cleaned": cleaned
    }


class PersonaMetaUpdateReq(BaseModel):
    name: str = None
    type: str = None
    age: str = None
    avatar: str = None
    bio: str = None


# ============================================================
# 8. 获取用户的聊天记录（管理员查看）
# ============================================================
@admin_router.get("/messages")
def admin_get_messages(user_id: str, persona_id: str, admin_user: str = Query(None)):
    _verify_admin(admin_user)
    from main import load_agents, get_emotion, get_memu
    from db import load_messages

    agents = load_agents()
    key = f"{user_id}_{persona_id}"
    if key not in agents:
        raise HTTPException(status_code=404, detail=f"未找到 agent: {key}")

    agent = agents[key]
    agent_id = agent["agent_id"]
    msgs = load_messages(agent_id)

    try:
        emo = get_emotion(agent_id)
        emo.refresh_days()
        rel = emo.relationship
        memu = get_memu(agent_id, user_id)
        memu_status = memu.get_status()
        shared = emo.shared
    except Exception:
        rel = {"phase": "acquaintance", "intimacy": 10, "passion": 5, "commitment": 5, "days": 1}
        memu_status = None
        shared = {}

    return {
        "messages": msgs,
        "agent": {
            "phase": rel.get("phase", "acquaintance"),
            "relationship_days": rel.get("days", 1),
            "intimacy": rel.get("intimacy", 10),
            "passion": rel.get("passion", 5),
            "commitment": rel.get("commitment", 5),
            "persona_name": agent.get("persona_name", ""),
        },
        "memu_status": memu_status,
        "shared_memories": shared,
    }


# ============================================================
# 9. 清除用户聊天记录及AI记忆（管理员操作）
# ============================================================
@admin_router.post("/clear-messages")
def admin_clear_messages(user_id: str, persona_id: str, admin_user: str = Query(None)):
    _verify_admin(admin_user)
    from main import load_agents, clear_recall
    from db import clear_messages

    agents = load_agents()
    key = f"{user_id}_{persona_id}"
    if key not in agents:
        raise HTTPException(status_code=404, detail=f"未找到 agent: {key}")

    agent_id = agents[key]["agent_id"]
    clear_messages(agent_id)
    clear_recall(agent_id)  # 清除内存中的对话缓冲区

    from db import clear_monologues
    clear_monologues(agent_id)

    cleared = ["聊天记录", "独白数据"]

    emotion_dir = os.path.join(DATA_DIR, "emotion", agent_id)
    if os.path.isdir(emotion_dir):
        shutil.rmtree(emotion_dir)
        cleared.append("情感记忆")

    memu_dir = os.path.join(DATA_DIR, "memu_memory", agent_id)
    if os.path.isdir(memu_dir):
        shutil.rmtree(memu_dir)
        cleared.append("MEMU记忆")

    monologue_file = os.path.join(DATA_DIR, "monologues", f"{agent_id}.json")
    if os.path.exists(monologue_file):
        os.remove(monologue_file)
        cleared.append("独白数据")

    proactive_file = os.path.join(DATA_DIR, "proactive", f"{agent_id}.json")
    if os.path.exists(proactive_file):
        os.remove(proactive_file)
        cleared.append("主动消息引擎")

    breakup_file = os.path.join(DATA_DIR, "breakups", f"{agent_id}.json")
    if os.path.exists(breakup_file):
        os.remove(breakup_file)
        cleared.append("分手状态")

    busy_file = os.path.join(DATA_DIR, "busy", f"{agent_id}.json")
    if os.path.exists(busy_file):
        os.remove(busy_file)
        cleared.append("忙碌状态")

    anniversary_file = os.path.join(DATA_DIR, "anniversaries", f"{agent_id}.json")
    if os.path.exists(anniversary_file):
        os.remove(anniversary_file)
        cleared.append("纪念日")

    routine_file = os.path.join(DATA_DIR, "routines", f"{agent_id}.json")
    if os.path.exists(routine_file):
        os.remove(routine_file)
        cleared.append("日程例程")

    pending_file = os.path.join(DATA_DIR, "pending_proactive", f"{key}.json")
    if os.path.exists(pending_file):
        os.remove(pending_file)
        cleared.append("待推送队列")

    return {"status": "ok", "detail": f"用户 {user_id} 与 {agents[key].get('persona_name', persona_id)} 的以下数据已清除：{'、'.join(cleared)}"}


# ============================================================
# 10. Lorebook 条目管理
# ============================================================
class LorebookEntryReq(BaseModel):
    user_id: str = None
    persona_id: str = None
    entry_id: str = None
    title: str = None
    priority: int = None
    enabled: bool = None
    keys: list = None
    content: str = None


@admin_router.get("/persona-lorebook")
def get_persona_lorebook(persona_id: str, admin_user: str = Query(None)):
    _verify_admin(admin_user)
    from persona_engine import load_persona, list_all_personas
    data = load_persona(persona_id)
    if not data:
        return {"persona_id": persona_id, "found": False, "available_personas": list_all_personas()}
    return {
        "persona_id": persona_id,
        "name": data.get("name", ""),
        "core": data.get("core", ""),
        "entries": data.get("entries", []),
        "found": True
    }


@admin_router.post("/persona-lorebook")
def update_persona_lorebook(req: LorebookEntryReq, admin_user: str = Query(None)):
    _verify_admin(admin_user)
    from persona_engine import load_persona, save_persona
    if not req.persona_id:
        raise HTTPException(status_code=400, detail="需要提供 persona_id")
    data = load_persona(req.persona_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"未找到 persona: {req.persona_id}")

    if req.entry_id is None:
        data["core"] = req.content if req.content is not None else data.get("core", "")
    else:
        entries = data.get("entries", [])
        found = False
        for e in entries:
            if e.get("id") == req.entry_id:
                if req.title is not None:
                    e["title"] = req.title
                if req.priority is not None:
                    e["priority"] = req.priority
                if req.enabled is not None:
                    e["enabled"] = req.enabled
                if req.keys is not None:
                    e["keys"] = req.keys
                if req.content is not None:
                    e["content"] = req.content
                found = True
                break
        if not found:
            raise HTTPException(status_code=404, detail=f"未找到条目: {req.entry_id}")

    save_persona(req.persona_id, data)
    return {"status": "ok"}


@admin_router.post("/persona-lorebook/add-entry")
def add_persona_lorebook_entry(req: LorebookEntryReq, admin_user: str = Query(None)):
    _verify_admin(admin_user)
    from persona_engine import load_persona, save_persona
    import uuid
    if not req.persona_id:
        raise HTTPException(status_code=400, detail="需要提供 persona_id")
    data = load_persona(req.persona_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"未找到 persona: {req.persona_id}")

    new_entry = {
        "id": req.entry_id or str(uuid.uuid4())[:8],
        "title": req.title or "新条目",
        "priority": req.priority or 50,
        "enabled": req.enabled if req.enabled is not None else True,
        "keys": req.keys or [],
        "content": req.content or ""
    }
    data.setdefault("entries", []).append(new_entry)
    save_persona(req.persona_id, data)
    return {"status": "ok", "entry": new_entry}


@admin_router.post("/persona-lorebook/delete-entry")
def delete_persona_lorebook_entry(persona_id: str, entry_id: str, admin_user: str = Query(None)):
    _verify_admin(admin_user)
    from persona_engine import load_persona, save_persona
    data = load_persona(persona_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"未找到 persona: {persona_id}")
    entries = data.get("entries", [])
    original_len = len(entries)
    data["entries"] = [e for e in entries if e.get("id") != entry_id]
    if len(data["entries"]) == original_len:
        raise HTTPException(status_code=404, detail=f"未找到条目: {entry_id}")
    save_persona(persona_id, data)
    return {"status": "ok", "detail": f"条目 {entry_id} 已删除"}


# ============================================================
# 12. 获取所有角色模板元信息
# ============================================================
@admin_router.get("/personas")
def get_all_personas(admin_user: str = Query(None)):
    _verify_admin(admin_user)
    from persona_engine import list_all_persona_meta
    return list_all_persona_meta()


# ============================================================
# 13. 更新角色模板元信息（名称/头像/类型/年龄/简介）
# ============================================================
@admin_router.put("/personas/{persona_id}")
def update_persona_meta(persona_id: str, req: PersonaMetaUpdateReq, admin_user: str = Query(None)):
    _verify_admin(admin_user)
    from persona_engine import load_persona, save_persona
    data = load_persona(persona_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"未找到 persona: {persona_id}")

    if req.name is not None:
        data["name"] = req.name
    if req.type is not None:
        data["type"] = req.type
    if req.age is not None:
        data["age"] = req.age
    if req.avatar is not None:
        data["avatar"] = req.avatar
    if req.bio is not None:
        data["bio"] = req.bio

    save_persona(persona_id, data)
    return {
        "status": "ok",
        "persona_id": persona_id,
        "name": data.get("name", ""),
        "type": data.get("type", ""),
        "age": data.get("age", ""),
        "avatar": data.get("avatar", ""),
        "bio": data.get("bio", "")
    }


# ============================================================
# 13b. 获取角色模板完整详情（含提示词工程 / 角色档案 / 外貌 / 说话风格等）
# ============================================================
@admin_router.get("/personas/{persona_id}/template")
def get_persona_template(persona_id: str, admin_user: str = Query(None)):
    _verify_admin(admin_user)
    from persona_engine import get_persona_data, list_all_personas

    data = get_persona_data(persona_id)
    if not data:
        return {
            "persona_id": persona_id,
            "found": False,
            "available_personas": list_all_personas()
        }

    return {
        "persona_id": persona_id,
        "found": True,
        "name": data.get("name", ""),
        "type": data.get("type", ""),
        "age": data.get("age", ""),
        "avatar": data.get("avatar", ""),
        "bio": data.get("bio", ""),
        "core": data.get("core", ""),
        "appearance": data.get("appearance", ""),
        "speech_patterns": data.get("speech_patterns", ""),
        "first_mes": data.get("first_mes", ""),
        "mes_example": data.get("mes_example", []),
        "entries": data.get("entries", []),
        "entry_count": len(data.get("entries", []))
    }


class PersonaTemplateUpdateReq(BaseModel):
    """角色模板全局更新请求 — 修改后新注册用户将使用新模板，不影响已有用户"""
    name: str = None
    type: str = None
    age: str = None
    avatar: str = None
    bio: str = None
    core: str = None              # 提示词工程（system prompt）
    appearance: str = None        # 外貌描述
    speech_patterns: str = None   # 说话风格
    first_mes: str = None         # 开场白
    mes_example: list = None      # 对话示例
    entries: list = None          # 角色档案条目（Lorebook 详细背景故事）


@admin_router.put("/personas/{persona_id}/template")
def update_persona_template(persona_id: str, req: PersonaTemplateUpdateReq, admin_user: str = Query(None)):
    """全局更新角色模板 — 修改后仅影响新注册该角色的用户，不影响已注册用户"""
    _verify_admin(admin_user)
    from persona_engine import get_persona_data, save_persona

    data = get_persona_data(persona_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"未找到 persona: {persona_id}")

    # 逐字段更新（只更新传入的非 None 字段）
    if req.name is not None:
        data["name"] = req.name
    if req.type is not None:
        data["type"] = req.type
    if req.age is not None:
        data["age"] = req.age
    if req.avatar is not None:
        data["avatar"] = req.avatar
    if req.bio is not None:
        data["bio"] = req.bio
    if req.core is not None:
        data["core"] = req.core
    if req.appearance is not None:
        data["appearance"] = req.appearance
    if req.speech_patterns is not None:
        data["speech_patterns"] = req.speech_patterns
    if req.first_mes is not None:
        data["first_mes"] = req.first_mes
    if req.mes_example is not None:
        data["mes_example"] = req.mes_example
    if req.entries is not None:
        data["entries"] = req.entries

    save_persona(persona_id, data)

    return {
        "status": "ok",
        "message": f"角色模板「{data.get('name', persona_id)}」已全局更新。新注册该角色的用户将使用新模板，已注册用户不受影响。",
        "persona_id": persona_id,
        "updated_fields": [k for k, v in req.dict().items() if v is not None]
    }


# ============================================================
# 14. 上传角色头像
# ============================================================
AVATAR_DIR = os.path.join(os.path.dirname(__file__), "static", "avatars")

@admin_router.post("/personas/{persona_id}/avatar")
async def upload_persona_avatar(persona_id: str, file: UploadFile = File(...), admin_user: str = Query(None)):
    _verify_admin(admin_user)
    from persona_engine import load_persona, save_persona

    data = load_persona(persona_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"未找到 persona: {persona_id}")

    # 验证文件类型
    ext = os.path.splitext(file.filename or "avatar.png")[1].lower()
    if ext not in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
        raise HTTPException(status_code=400, detail="仅支持 PNG/JPG/JPEG/GIF/WEBP 格式")

    # 确保目录存在
    os.makedirs(AVATAR_DIR, exist_ok=True)

    # 生成唯一文件名
    filename = f"{persona_id}_{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join(AVATAR_DIR, filename)

    # 保存文件
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    # 更新 persona 数据
    avatar_url = f"/avatars/{filename}"
    data["avatar"] = avatar_url
    save_persona(persona_id, data)

    return {
        "status": "ok",
        "persona_id": persona_id,
        "avatar": avatar_url
    }