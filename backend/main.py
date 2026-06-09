# -*- coding: utf-8 -*-
"""半熟时区 - 主应用入口 (API路由)"""
import os
import json
import uuid
import sys
import webbrowser
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from openai import OpenAI

from settings import (
    logger, _capture_unhandled_exceptions,
    PERSONAS, DATA_DIR, AGENTS_FILE, USERS_FILE, CONFIG_FILE, PENDING_PROACTIVE_DIR, NEED_DEFAULTS,
    RECALL_BUFFER, memu_systems, emotion_systems, proactive_engines,
    routine_learners, busy_managers, daily_life_managers, anniversary_checkers, breakup_managers,
    client, current_model, current_base_url, current_api_key,
)
from auth import (
    require_auth, _create_session_token, _verify_session_token,
    _hash_password, _check_rate_limit,
    UserProfile, UserRequest, ChatRequest, ConfigRequest, FrontendError,
    BaseModel,
)
from utils_json import parse_llm_json
from utils_time import get_time_context, execute_tool
from memu_system import MemUMemorySystem
from emotion_system import EmotionSystem, detect_interrogation_pattern, analyze_message_quality
from reply_engine import (
    MonologueStore, UserEvaluationStore,
    get_monologue_store, get_user_evaluation,
    calibrate_monologue, call_internal_monologue, compute_segment_delays, call_external_reply,
)
from proactive_engine import ProactiveMessageEngine, NeedStateEngine, get_need_state
from db import (
    init_db, load_messages, load_messages_paginated, save_message, clear_messages,
    get_last_n_messages, get_message_count, load_agents as _db_load_agents,
    save_agent, insert_agent, delete_agent_from_db,
)
from admin import admin_router
from image_recognizer import recognize_image_base64
from url_fetcher import process_urls_in_message
from emoji_engine import build_emoji_prompt_instruction, replace_emoji_tags

# ==================== 缓存访问器 ====================

def get_memu(agent_id: str, user_id: str) -> MemUMemorySystem:
    key = f"{agent_id}_{user_id}"
    if key not in memu_systems:
        memu_systems[key] = MemUMemorySystem(agent_id, user_id)
    return memu_systems[key]


def get_emotion(agent_id: str) -> EmotionSystem:
    if agent_id not in emotion_systems:
        emotion_systems[agent_id] = EmotionSystem(agent_id)
    return emotion_systems[agent_id]


def get_recall(agent_id: str) -> list:
    if agent_id not in RECALL_BUFFER:
        RECALL_BUFFER[agent_id] = []
    return RECALL_BUFFER[agent_id]


def add_to_recall(agent_id: str, role: str, content: str):
    recall = get_recall(agent_id)
    recall.append({"role": role, "content": content})
    if len(recall) > 30:
        recall[:] = recall[-30:]


def clear_recall(agent_id: str):
    if agent_id in RECALL_BUFFER:
        RECALL_BUFFER[agent_id] = []


def get_routine_learner(agent_id: str):
    from routine_learner import RoutineLearner
    if agent_id not in routine_learners:
        routine_learners[agent_id] = RoutineLearner(agent_id)
    return routine_learners[agent_id]


def get_busy_manager(agent_id: str):
    from ai_busy import AIBusyManager
    if agent_id not in busy_managers:
        busy_managers[agent_id] = AIBusyManager(agent_id)
    return busy_managers[agent_id]


def get_daily_life(agent_id: str, persona_id: str):
    from ai_daily_life import AIDailyLife
    if agent_id not in daily_life_managers:
        daily_life_managers[agent_id] = AIDailyLife(agent_id, persona_id)
    return daily_life_managers[agent_id]


def get_anniversary_checker(agent_id: str):
    from anniversary import AnniversaryChecker
    if agent_id not in anniversary_checkers:
        anniversary_checkers[agent_id] = AnniversaryChecker(agent_id)
    return anniversary_checkers[agent_id]


def get_breakup_manager(agent_id: str):
    from breakup_manager import BreakupManager
    if agent_id not in breakup_managers:
        breakup_managers[agent_id] = BreakupManager(agent_id)
    return breakup_managers[agent_id]


# ==================== 数据管理 ====================

def load_agents():
    return _db_load_agents()


def save_agents(agents_dict):
    for key, agent in agents_dict.items():
        save_agent(agent)


def save_messages(agent_id, msgs):
    clear_messages(agent_id)
    for msg in msgs:
        save_message(agent_id, msg)


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def _load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def _init_users_file():
    if not os.path.exists(USERS_FILE):
        _save_users([])


def get_or_create_agent(user_id: str, persona_id: str) -> dict:
    agents = load_agents()
    key = f"{user_id}_{persona_id}"
    if key not in agents:
        from persona_engine import get_persona_data, get_persona_core
        persona_data = get_persona_data(persona_id)
        if not persona_data:
            persona_data = PERSONAS.get(persona_id, PERSONAS["sunny"])
        persona_name = persona_data.get("name", persona_id)
        system_prompt = get_persona_core(persona_data)
        agent_id = str(uuid.uuid4())
        agent = {
            "agent_id": agent_id,
            "user_id": user_id,
            "persona_id": persona_id,
            "persona_name": persona_name,
            "system_prompt": system_prompt,
            "created_at": datetime.now().isoformat(),
            "relationship_days": 1,
            "phase": "acquaintance",
            "intimacy": 10,
            "passion": 5,
            "commitment": 5
        }
        save_agent(agent)
        emo = get_emotion(agent_id)
        emo.relationship["days"] = 1
        emo.save()
        agents[key] = agent
    else:
        existing_msgs = get_last_n_messages(agents[key]["agent_id"], 20)
        if existing_msgs and agents[key]["agent_id"] not in RECALL_BUFFER:
            RECALL_BUFFER.setdefault(agents[key]["agent_id"], []).extend(existing_msgs)
    return agents[key]


# ==================== FastAPI ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    global client, current_model, current_base_url, current_api_key
    _capture_unhandled_exceptions()
    logger.info("=" * 50)
    logger.info("半熟时区 后端服务启动中...")
    _init_users_file()
    init_db()
    logger.info("SQLite 数据库已初始化")
    logger.info("正在加载模型，耐心等待...")

    import asyncio
    from settings import _get_local_embed_model
    await asyncio.to_thread(_get_local_embed_model)
    logger.info("Embedding 模型已预加载完成")

    # 自动加载管理员配置的视觉模型
    cfg = load_config()
    vision_model = cfg.get("vision_model", "")
    if vision_model:
        logger.info(f"检测到视觉模型配置: {vision_model}，正在自动加载...")
        try:
            await _auto_load_vision_model(vision_model)
        except Exception as e:
            logger.warning(f"视觉模型自动加载失败: {e}，可稍后在管理员界面手动加载")

    logger.info("所有模型加载完成，服务就绪")

    api_key = cfg.get("api_key") or os.environ.get("OPENAI_API_KEY", "")
    base_url = cfg.get("base_url") or os.environ.get("OPENAI_BASE_URL", "")
    model = cfg.get("model") or os.environ.get("LLM_MODEL", "")
    if api_key:
        client = OpenAI(api_key=api_key, base_url=base_url if base_url else None)
        current_model = model
        current_base_url = base_url
        current_api_key = api_key
        logger.info(f"LLM 已配置: model={model}, base_url={base_url or 'default'}")
        # 同步更新 settings 中的全局变量
        import settings
        settings.client = client
        settings.current_model = model
        settings.current_base_url = base_url
        settings.current_api_key = api_key
    else:
        logger.warning("未配置 OPENAI_API_KEY，AI 回复将不可用")

    # 服务器完全就绪后自动打开浏览器
    webbrowser.open("http://localhost:8765")
    logger.info("浏览器已自动打开")

    yield
    logger.info("半熟时区 后端服务已停止")


app = FastAPI(title="半熟时区 API - MemU 记忆系统", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sys.modules['main'] = sys.modules[__name__]
app.include_router(admin_router)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(
        f"[API异常] {request.method} {request.url.path} | {exc}",
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "path": request.url.path}
    )


# ==================== API 路由 ====================

@app.get("/api/personas")
def get_personas():
    result = []
    for pid, p in PERSONAS.items():
        from persona_engine import get_persona_data
        persona_data = get_persona_data(pid)
        if persona_data:
            result.append({
                "id": pid,
                "name": persona_data.get("name", p.get("name", pid)),
                "type": persona_data.get("type", p.get("type", "")),
                "age": persona_data.get("age", p.get("age", "")),
                "bio": persona_data.get("bio", p.get("bio", "")),
                "avatar": persona_data.get("avatar", p.get("avatar", f"https://api.dicebear.com/7.x/adventurer/svg?seed={pid}&backgroundColor=fce7f3"))
            })
        else:
            result.append({
                "id": pid,
                "name": p["name"],
                "type": p["type"],
                "age": p["age"],
                "bio": p["bio"],
                "avatar": f"https://api.dicebear.com/7.x/adventurer/svg?seed={pid}&backgroundColor=fce7f3"
            })
    return result


@app.post("/api/users/register")
def register_user(req: UserRequest):
    raw = req.username.strip()
    if not raw:
        raise HTTPException(status_code=400, detail="用户名不能为空")
    if len(raw) > 30:
        raise HTTPException(status_code=400, detail="用户名最多30个字符")
    if not req.password:
        raise HTTPException(status_code=400, detail="请设置密码")
    if len(req.password) < 4:
        raise HTTPException(status_code=400, detail="密码至少4个字符")

    username = raw
    users = _load_users()

    for user in users:
        if user["username"] == username:
            raise HTTPException(status_code=409, detail="该用户名已存在，请直接登录")

    now = datetime.now().isoformat()
    pw_hash, pw_salt = _hash_password(req.password)
    new_user = {
        "username": username,
        "password_hash": pw_hash,
        "salt": pw_salt,
        "created_at": now,
        "last_active": now
    }
    users.append(new_user)
    _save_users(users)
    token = _create_session_token(username)
    return {
        "username": username,
        "is_new": True,
        "created_at": now,
        "token": token
    }


@app.post("/api/users/login")
def login_user(req: UserRequest):
    raw = req.username.strip()
    if not raw:
        raise HTTPException(status_code=400, detail="用户名不能为空")
    if not req.password:
        raise HTTPException(status_code=400, detail="请输入密码")

    username = raw
    users = _load_users()

    for user in users:
        if user["username"] == username:
            stored_hash = user.get("password_hash", "")
            stored_salt = user.get("salt", "")
            if not stored_hash or not stored_salt:
                raise HTTPException(status_code=400, detail="该账号未设置密码，请联系管理员")
            input_hash, _ = _hash_password(req.password, stored_salt)
            if input_hash != stored_hash:
                raise HTTPException(status_code=401, detail="密码错误")
            user["last_active"] = datetime.now().isoformat()
            _save_users(users)
            token = _create_session_token(username)
            return {
                "username": username,
                "is_new": False,
                "created_at": user["created_at"],
                "token": token
            }

    raise HTTPException(status_code=404, detail="用户不存在，请先注册")


@app.get("/api/users/me")
def get_current_user_me(user: dict = Depends(require_auth)):
    token = _create_session_token(user["username"])
    return {"username": user["username"], "token": token}


@app.post("/api/users/get-or-create")
def get_or_create_user(req: UserRequest):
    raw = req.username.strip()
    if not raw:
        raise HTTPException(status_code=400, detail="用户名不能为空")
    if len(raw) > 30:
        raise HTTPException(status_code=400, detail="用户名最多30个字符")
    username = raw

    users = _load_users()
    now = datetime.now().isoformat()

    for user in users:
        if user["username"] == username:
            if not req.password:
                raise HTTPException(status_code=400, detail="请输入密码")
            stored_hash = user.get("password_hash", "")
            stored_salt = user.get("salt", "")
            if not stored_hash or not stored_salt:
                raise HTTPException(status_code=400, detail="该账号未设置密码，请联系管理员")
            input_hash, _ = _hash_password(req.password, stored_salt)
            if input_hash != stored_hash:
                raise HTTPException(status_code=401, detail="密码错误")
            user["last_active"] = now
            _save_users(users)
            return {
                "username": username,
                "is_new": False,
                "created_at": user["created_at"]
            }

    if not req.password:
        raise HTTPException(status_code=400, detail="请设置密码")
    if len(req.password) < 4:
        raise HTTPException(status_code=400, detail="密码至少4个字符")

    pw_hash, pw_salt = _hash_password(req.password)
    new_user = {
        "username": username,
        "password_hash": pw_hash,
        "salt": pw_salt,
        "created_at": now,
        "last_active": now
    }
    users.append(new_user)
    _save_users(users)
    return {
        "username": username,
        "is_new": True,
        "created_at": now
    }


@app.get("/api/users")
def get_users():
    users = _load_users()
    users.sort(key=lambda u: u.get("last_active", ""), reverse=True)
    return [
        {
            "username": u["username"],
            "created_at": u.get("created_at", ""),
            "last_active": u.get("last_active", "")
        }
        for u in users
    ]


class ResetPasswordRequest(BaseModel):
    username: str
    new_password: str


@app.post("/api/users/reset-password")
def reset_password(req: ResetPasswordRequest):
    """忘记密码：输入用户名和新密码即可重置（无需旧密码）"""
    raw_username = req.username.strip()
    if not raw_username:
        raise HTTPException(status_code=400, detail="用户名不能为空")
    if not req.new_password:
        raise HTTPException(status_code=400, detail="新密码不能为空")
    if len(req.new_password) < 4:
        raise HTTPException(status_code=400, detail="密码至少4个字符")

    users = _load_users()
    for user in users:
        if user["username"] == raw_username:
            pw_hash, pw_salt = _hash_password(req.new_password)
            user["password_hash"] = pw_hash
            user["salt"] = pw_salt
            _save_users(users)
            return {"message": "密码重置成功", "username": raw_username}

    raise HTTPException(status_code=404, detail="用户不存在")


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


@app.post("/api/users/change-password")
def change_password(req: ChangePasswordRequest, user: dict = Depends(require_auth)):
    """修改密码：需验证旧密码"""
    if not req.old_password:
        raise HTTPException(status_code=400, detail="旧密码不能为空")
    if not req.new_password:
        raise HTTPException(status_code=400, detail="新密码不能为空")
    if len(req.new_password) < 4:
        raise HTTPException(status_code=400, detail="密码至少4个字符")

    username = user["username"]
    users = _load_users()

    for u in users:
        if u["username"] == username:
            stored_hash = u.get("password_hash", "")
            stored_salt = u.get("salt", "")
            if not stored_hash or not stored_salt:
                raise HTTPException(status_code=400, detail="该账号未设置密码，无法修改")
            input_hash, _ = _hash_password(req.old_password, stored_salt)
            if input_hash != stored_hash:
                raise HTTPException(status_code=401, detail="旧密码错误")
            pw_hash, pw_salt = _hash_password(req.new_password)
            u["password_hash"] = pw_hash
            u["salt"] = pw_salt
            _save_users(users)
            return {"message": "密码修改成功", "username": username}

    raise HTTPException(status_code=404, detail="用户不存在")


@app.get("/api/agent")
def get_agent(persona_id: str = "sunny", user: dict = Depends(require_auth)):
    user_id = user["user_id"]
    agent = get_or_create_agent(user_id, persona_id)
    agent_id = agent["agent_id"]
    msgs = load_messages(agent_id)
    emotion = get_emotion(agent_id)
    emotion.refresh_days()
    rel = emotion.relationship
    from persona_engine import get_persona_data
    persona_out = get_persona_data(persona_id) or PERSONAS.get(persona_id, PERSONAS["sunny"])
    return {
        "agent": agent,
        "message_count": len(msgs),
        "persona": persona_out,
        "relationship": {
            "phase": rel["phase"],
            "intimacy": rel["intimacy"],
            "passion": rel["passion"],
            "commitment": rel["commitment"],
            "days": rel.get("days", 1)
        },
        "shared_memories": emotion.shared
    }


@app.get("/api/check-proactive")
def check_proactive(persona_id: str = "", user: dict = Depends(require_auth)):
    user_id = user["user_id"]
    if not persona_id:
        return {"type": None}
    agents = load_agents()
    key = f"{user_id}_{persona_id}"
    if key not in agents:
        return {"type": None}
    agent = agents[key]
    agent_id = agent["agent_id"]
    persona_name = agent.get("persona_name", "AI助手")

    if key not in proactive_engines:
        proactive_engines[key] = ProactiveMessageEngine(agent_id, persona_id)
    engine = proactive_engines[key]

    routine_learner = get_routine_learner(agent_id)
    engine.set_routine_learner(routine_learner)

    emotion = get_emotion(agent_id)
    memu = get_memu(agent_id, user_id)
    emotion.refresh_days()

    persona_type_for_need = PERSONAS.get(persona_id, {}).get("type", "安全型")
    need_state = get_need_state(agent_id, persona_type_for_need)
    need_state.tick()

    breakup_mgr = get_breakup_manager(agent_id)
    if breakup_mgr.is_in_cooling():
        return {"type": None}
    if breakup_mgr.is_cooling_expired():
        return {"type": None}

    pending_file = os.path.join(PENDING_PROACTIVE_DIR, f"{key}.json")
    if os.path.exists(pending_file):
        try:
            with open(pending_file, "r", encoding="utf-8") as f:
                pending_msgs = json.load(f)
            if pending_msgs:
                msg = pending_msgs.pop(0)
                if pending_msgs:
                    with open(pending_file, "w", encoding="utf-8") as f:
                        json.dump(pending_msgs, f, ensure_ascii=False)
                else:
                    os.remove(pending_file)
                save_message(agent_id, msg)
                return {"type": "admin_triggered", "message": msg["content"], "_id": msg["_id"]}
        except:
            pass

    result = engine.get_proactive_message(emotion, persona_name, memu)
    if result is None:
        if not engine.check_cooldown():
            return {"type": None}
        triggered_needs = need_state.get_triggered_needs()
        if not triggered_needs:
            return {"type": None}
        top_need = triggered_needs[0]
        need_reset_val = NEED_DEFAULTS[top_need["need"]]["current"]
        result = {
            "trigger_type": "need_state",
            "need_key": top_need["need"],
            "need_label": top_need["label"],
            "need_value": top_need["value"],
            "trigger_msg": top_need["trigger_msg"]
        }
        need_state.data[top_need["need"]]["current"] = need_reset_val
        need_state.save()

    trigger_type = result["trigger_type"]

    trigger_prompts = {
        "morning": "现在是早上，你刚起床，想跟Ta说声早安。自然一点，不要刻意。",
        "night": "天很晚了，注意到Ta还没休息，想关心一下。不要太啰嗦。",
        "late_night": "已经凌晨了，Ta还在线，你有点担心。想问问Ta为什么还没睡。",
        "missing": f"你已经好几个小时没跟Ta说话了，有点想念Ta。用{result.get('tone', '关心')}的语气主动说句话。",
        "context": f"你突然想起你们之前聊过的话题：{result.get('context', '之前的话题')}。自然地延续这个话题。",
        "need_state": f"你的{result.get('need_label', '某种需求')}被触发了。你心里想说：{result.get('trigger_msg', '想跟你聊聊')}。用自然的语气主动说句话。"
    }

    trigger_prompt = trigger_prompts.get(trigger_type, "你想跟Ta说句话。自然一点。")

    ai_content = call_external_reply(
        agent["system_prompt"], agent_id, trigger_prompt,
        {"phase": emotion.relationship.get("phase", "acquaintance"), "emotion": "平静", "confidence": 0.8, "key_observations": []},
        persona_name, memu, emotion_system=emotion, persona_id=persona_id
    )

    engine.record_proactive_sent()

    ai_msg = {
        "_id": str(uuid.uuid4()),
        "content": ai_content,
        "senderId": "ai",
        "timestamp": datetime.now().strftime("%H:%M"),
        "date": "今天",
        "proactive": True,
        "trigger_type": trigger_type
    }

    memu.add_exchange("", ai_content)

    print(f"[Proactive] 触发类型={trigger_type} 内容={ai_content[:50]}...")

    return {
        "type": trigger_type,
        "message": ai_msg,
        "proactive_count": result.get("count", 0) + 1,
        "limit": result.get("limit", 1),
        "reasoning": result.get("reasoning", "")
    }


@app.get("/api/routine")
def get_routine(persona_id: str = "sunny", user: dict = Depends(require_auth)):
    user_id = user["user_id"]
    agents = load_agents()
    key = f"{user_id}_{persona_id}"
    if key not in agents:
        return {"routine": None, "patterns": [], "confidence": 0}
    agent = agents[key]
    agent_id = agent["agent_id"]
    learner = get_routine_learner(agent_id)
    return learner.get_routine()


@app.post("/api/birthday")
def set_birthday(persona_id: str = "sunny", month: int = 1, day: int = 1, user: dict = Depends(require_auth)):
    user_id = user["user_id"]
    agents = load_agents()
    key = f"{user_id}_{persona_id}"
    if key not in agents:
        return {"success": False, "message": "请先与该角色开始聊天"}
    agent = agents[key]
    checker = get_anniversary_checker(agent["agent_id"])
    checker.set_user_birthday(month, day)
    return {"success": True, "birthday": {"month": month, "day": day}}


@app.get("/api/birthday")
def get_birthday(persona_id: str = "sunny", user: dict = Depends(require_auth)):
    user_id = user["user_id"]
    agents = load_agents()
    key = f"{user_id}_{persona_id}"
    if key not in agents:
        return {"birthday": None}
    agent = agents[key]
    checker = get_anniversary_checker(agent["agent_id"])
    return {"birthday": checker.get_user_birthday()}


@app.post("/api/log-error")
def log_frontend_error(req: FrontendError):
    logger.error(
        f"[前端错误] source={req.source} url={req.url} user={req.user_id} persona={req.persona_id}\n"
        f"  message: {req.message}\n"
        f"  stack: {req.stack or '无堆栈'}"
    )
    return {"status": "ok"}


@app.post("/api/chat")
async def chat(req: ChatRequest, user: dict = Depends(require_auth)):
    user_id = user["user_id"]

    if not _check_rate_limit(user_id):
        raise HTTPException(status_code=429, detail="消息发送太快了，请稍等一下")

    agent = get_or_create_agent(user_id, req.persona_id)
    agent_id = agent["agent_id"]
    persona_name = agent.get("persona_name", "AI助手")

    memu = get_memu(agent_id, user_id)
    emotion = get_emotion(agent_id)
    emotion.refresh_days()

    key = f"{user_id}_{req.persona_id}"
    if key not in proactive_engines:
        proactive_engines[key] = ProactiveMessageEngine(agent_id, req.persona_id)
    proactive_engines[key].mark_user_activity()

    routine_learner = get_routine_learner(agent_id)
    routine_learner.record_activity()

    persona_type = PERSONAS.get(req.persona_id, {}).get("type", "安全型")
    need_state = get_need_state(agent_id, persona_type)
    need_state.tick()
    need_state.reset_on_activity()

    user_msg = {
        "_id": str(uuid.uuid4()),
        "content": req.message or "[图片]",
        "senderId": "user",
        "timestamp": datetime.now().strftime("%H:%M"),
        "date": "今天",
        "status": "sent"
    }
    # 持久化图片数据到 extra 字段
    if req.image_base64:
        user_msg["image"] = f"data:{req.image_mime_type};base64,{req.image_base64}"
    save_message(agent_id, user_msg)

    add_to_recall(agent_id, "user", req.message)

    # ==================== 图片识别 & URL 抓取 ====================
    augmented_message = req.message
    image_result = {"success": False, "text": "", "vision_supported": False}
    urls_result = {"urls": [], "fetched": {}}

    if req.image_base64:
        image_result = recognize_image_base64(req.image_base64, req.image_mime_type)
        if image_result["success"]:
            augmented_message = req.message + "\n" + image_result["text"]
            add_to_recall(agent_id, "user", image_result["text"])
        elif image_result.get("human_hint"):
            augmented_message = req.message + "\n" + image_result["human_hint"]
            # 注意：失败提示不存入 recall，它是系统指令而非用户说的话
            # 否则后续即使识别成功，AI 仍会从 recall 中读到此提示并误以为自己看不到图片

    if req.message:
        urls_result = process_urls_in_message(req.message)
        if urls_result["fetched"]:
            url_contexts = []
            for url, text in urls_result["fetched"].items():
                url_contexts.append(f"[用户分享的链接内容] URL: {url}\n{text}")
            url_context_text = "\n\n".join(url_contexts)
            augmented_message += "\n\n" + url_context_text
            add_to_recall(agent_id, "user", url_context_text)

    breakup_manager = get_breakup_manager(agent_id)
    restart_info = breakup_manager.handle_restart()
    if restart_info:
        persona_type = PERSONAS.get(req.persona_id, {}).get("type", "安全型")
        emotion.relationship["phase"] = "acquaintance"
        emotion.relationship["intimacy"] = max(5, emotion.relationship.get("intimacy", 10) * 0.3)
        emotion.relationship["passion"] = max(2, emotion.relationship.get("passion", 5) * 0.3)
        emotion.relationship["commitment"] = max(2, emotion.relationship.get("commitment", 5) * 0.3)
        emotion.relationship["tri_change_log"] = []
        emotion.save()
        restart_msg = breakup_manager.get_restart_message(persona_type)
        ai_msg = {
            "_id": str(uuid.uuid4()),
            "content": restart_msg,
            "senderId": "ai",
            "timestamp": datetime.now().strftime("%H:%M"),
            "date": "今天",
            "restart": True
        }
        save_message(agent_id, ai_msg)
        add_to_recall(agent_id, "assistant", restart_msg)
        memu.add_exchange(req.message, restart_msg)
        segments = [restart_msg]
        delays = [0]
        return {"message": ai_msg, "segments": segments, "delays": delays}

    if breakup_manager.is_in_cooling():
        persona_type = PERSONAS.get(req.persona_id, {}).get("type", "安全型")
        cooling_msgs = {
            "安全型": "我现在不想聊。等我们都冷静下来再说吧。",
            "焦虑型": "你发消息过来我看到了……但我还没准备好。再给我一点时间吧。",
            "回避型": "……现在别找我。我需要一个人待会儿。"
        }
        cooling_msg = cooling_msgs.get(persona_type, "我现在不太想说话，过一阵子再说吧。")
        ai_msg = {
            "_id": str(uuid.uuid4()),
            "content": cooling_msg,
            "senderId": "ai",
            "timestamp": datetime.now().strftime("%H:%M"),
            "date": "今天",
            "cooling": True
        }
        save_message(agent_id, ai_msg)
        add_to_recall(agent_id, "assistant", cooling_msg)
        memu.add_exchange(req.message, cooling_msg)
        segments = [cooling_msg]
        delays = [0]
        return {"message": ai_msg, "segments": segments, "delays": delays}

    if breakup_manager.detect_breakup_intent(req.message):
        persona_type = PERSONAS.get(req.persona_id, {}).get("type", "安全型")
        phase = emotion.relationship.get("phase", "acquaintance")
        days = emotion.relationship.get("days", 1)
        breakup_manager.initiate_breakup(persona_type, phase, days)
        breakup_reply = breakup_manager.get_breakup_reply(persona_type, phase, days)
        ai_msg = {
            "_id": str(uuid.uuid4()),
            "content": breakup_reply,
            "senderId": "ai",
            "timestamp": datetime.now().strftime("%H:%M"),
            "date": "今天",
            "breakup": True
        }
        save_message(agent_id, ai_msg)
        add_to_recall(agent_id, "assistant", breakup_reply)
        memu.add_exchange(req.message, breakup_reply)
        emotion.save()
        segments = [breakup_reply]
        delays = [0]
        return {"message": ai_msg, "segments": segments, "delays": delays}

    milestones = emotion.detect_milestone(req.message)
    emotion.update_relationship(req.message, req.persona_id)

    busy_manager = get_busy_manager(agent_id)
    daily_life = get_daily_life(agent_id, req.persona_id)
    persona_type = PERSONAS.get(req.persona_id, {}).get("type", "安全型")
    rel = emotion.relationship
    phase = rel.get("phase", "acquaintance")
    intimacy = rel.get("intimacy", 10)
    last_activity = rel.get("last_activity")
    hours_since_last = 24.0
    if last_activity:
        try:
            hours_since_last = (datetime.now() - datetime.fromisoformat(last_activity)).total_seconds() / 3600
        except:
            pass

    daily_life.check_activity_change()
    activity_ctx = daily_life.get_activity_context_for_prompt()
    _time_context, _time_context_compact = get_time_context()
    activity_ctx = (activity_ctx + "\n" + _time_context_compact) if activity_ctx else _time_context_compact

    busy_reply = busy_manager.generate_busy_reply(persona_type, phase)
    if busy_reply:
        ai_msg = {
            "_id": str(uuid.uuid4()),
            "content": busy_reply,
            "senderId": "ai",
            "timestamp": datetime.now().strftime("%H:%M"),
            "date": "今天",
            "busy": True
        }
        save_message(agent_id, ai_msg)
        add_to_recall(agent_id, "assistant", busy_reply)
        memu.add_exchange(req.message, busy_reply)
        emotion.save()
        segments = [busy_reply]
        delays = [0]
        return {"message": ai_msg, "segments": segments, "delays": delays}
    else:
        busy_manager.try_enter_busy(phase, intimacy, hours_since_last)

    anniversary_checker = get_anniversary_checker(agent_id)
    anniversary_results = anniversary_checker.check(
        relationship_days=emotion.relationship.get("days", 1),
        phase=phase,
        intimacy=intimacy,
        first_interaction=emotion.relationship.get("first_interaction")
    )
    anniversary_context = anniversary_checker.get_anniversary_context(anniversary_results)
    if anniversary_results:
        print(f"[纪念日] {', '.join(r.get('label', r.get('name', '')) for r in anniversary_results)}")
        emotion.save()

    time_aware_system_prompt = _time_context + "\n\n" + agent["system_prompt"]
    emoji_instruction = build_emoji_prompt_instruction(req.persona_id, phase)
    monologue = call_internal_monologue(time_aware_system_prompt, memu, emotion, agent_id, req.persona_id, augmented_message, activity_context=activity_ctx)
    monologue = calibrate_monologue(monologue, agent_id, emotion)
    if anniversary_context:
        monologue.setdefault("key_observations", []).append(f"[特殊日子提醒] {anniversary_context}")
    monologue_store = get_monologue_store(agent_id)
    monologue_store.append(monologue)
    print(f"[内心独白] phase={monologue['phase']} confidence={monologue['confidence']} emotion={monologue['emotion']}")

    user_eval_store = get_user_evaluation(agent_id)
    user_eval_from_mono = monologue.get("user_evaluation", {})
    if user_eval_from_mono:
        user_eval_store.update(user_eval_from_mono)
    eval_context = user_eval_store.get_evaluation_context()

    recall = get_recall(agent_id)
    recent_user_msgs = [m["content"] for m in recall[-10:] if m.get("role") == "user"]

    interro_result = detect_interrogation_pattern(recall)
    if interro_result["interrogation"]:
        penalty = -1.0 - 0.5 * (interro_result["consecutive_count"] - 3)
        rel = emotion.relationship
        rel["intimacy"] = max(0, round(rel.get("intimacy", 10) + penalty, 2))
        rel["passion"] = max(0, round(rel.get("passion", 5) + penalty * 0.5, 2))
        print(f"[审讯检测] 连续{interro_result['consecutive_count']}条审问 | 好感度{penalty:.1f}")

    current_activity = daily_life.get_current_activity()
    disclosure = daily_life.get_disclosure_guidance(phase, current_activity)
    share_activity = monologue.get("share_activity", False)
    if not disclosure["can_disclose"]:
        share_activity = False

    if share_activity and disclosure["activity_text"]:
        reply_activity_context = f"""{_time_context}
【你当前的生活状态】
你现在正在: {disclosure['activity_text']}
你可以自然地提到正在做的事，但不需要每句话都报告。像真人一样，偶尔提到就好。
如果对方没问你在干嘛，就不用特意说。"""
    else:
        reply_activity_context = f"""{_time_context}
【你当前的生活状态】
你现在正在忙自己的事。
如果有人问你在干嘛，用模糊的表达回应，比如'有点事在忙'、'在忙呢'、'没什么呀'等。
不要编造具体的生活事件。"""

    # 将 emoji 指令注入 activity_context，避免被 persona_core 覆盖
    if emoji_instruction:
        reply_activity_context += "\n\n" + emoji_instruction

    ai_content = call_external_reply(
        time_aware_system_prompt, agent_id, augmented_message, monologue, persona_name, memu,
        emotion_system=emotion, user_is_typing=req.user_is_typing, persona_id=req.persona_id,
        recent_context=recent_user_msgs, interrogation_context=interro_result,
        evaluation_context=eval_context, activity_context=reply_activity_context
    )

    # ==================== 表情包解析 ====================
    if not ai_content or not ai_content.strip():
        logger.warning(f"[空回复] AI返回空内容，使用兜底回复")
        ai_content = "嗯……我看到了，但现在有点不知道该怎么回应。要不要换个话题聊聊？"
    ai_content_clean, emoji_list = replace_emoji_tags(ai_content)
    if emoji_list:
        print(f"[表情引擎] 检测到 {len(emoji_list)} 个表情: {[e['category'] for e in emoji_list]}")

    raw_segments = ai_content_clean.split("<SEGMENT>")
    segments = [s.strip() for s in raw_segments if s.strip()]
    if not segments:
        segments = [ai_content_clean]
    delays = compute_segment_delays(segments)

    ai_msg = {
        "_id": str(uuid.uuid4()),
        "content": ai_content_clean,
        "senderId": "ai",
        "timestamp": datetime.now().strftime("%H:%M"),
        "date": "今天"
    }
    if emoji_list:
        ai_msg["emojis"] = emoji_list
    save_message(agent_id, ai_msg)

    add_to_recall(agent_id, "assistant", ai_content_clean)
    # 如果有表情包，注入提示让 AI 知道自己发了什么表情
    if emoji_list:
        emoji_categories = [e['category'] for e in emoji_list]
        emoji_note = f"[系统备注] 你刚刚在回复中发送了表情包（分类：{', '.join(emoji_categories)}）。如果用户问你关于这个表情包的问题，你可以根据分类含义来回答（happy=开心, sad=难过, angry=生气, surprised=惊讶, loved=爱意, tired=累/困, confused=困惑, evasive=回避/敷衍, reminded=回忆）。"
        add_to_recall(agent_id, "assistant", emoji_note)
    memu.add_exchange(req.message, ai_content_clean)

    rel = emotion.relationship
    lt = monologue.get("love_triangle", {})
    if lt:
        old_i = rel.get("intimacy", 10)
        old_p = rel.get("passion", 5)
        old_c = rel.get("commitment", 5)

        mono_i = lt.get("intimacy", old_i)
        mono_p = lt.get("passion", old_p)
        mono_c = lt.get("commitment", old_c)

        di = mono_i - old_i
        dp = mono_p - old_p
        dc = mono_c - old_c

        max_delta = 5.0
        di = max(-max_delta, min(max_delta, di))
        dp = max(-max_delta, min(max_delta, dp))
        dc = max(-max_delta, min(max_delta, dc))

        rel["intimacy"] = max(0, min(100, old_i + di))
        rel["passion"] = max(0, min(100, old_p + dp))
        rel["commitment"] = max(0, min(100, old_c + dc))

        if di != 0 or dp != 0 or dc != 0:
            print(f"[独白微调] 整值({old_i:.1f},{old_p:.1f},{old_c:.1f}) → Δ({di:+.1f},{dp:+.1f},{dc:+.1f}) → ({rel['intimacy']:.1f},{rel['passion']:.1f},{rel['commitment']:.1f})")
        else:
            print(f"[独白一致] ({rel['intimacy']:.1f},{rel['passion']:.1f},{rel['commitment']:.1f})")

    if monologue.get("phase") != rel.get("phase"):
        if monologue.get("phase_changed"):
            old_phase = rel.get("phase", "acquaintance")
            rel["phase"] = monologue["phase"]
            emotion.record_phase_enter(monologue["phase"])
            print(f"[阶段推进] {old_phase} → {monologue['phase']}")
    emotion.save()

    monologue["love_triangle"] = {
        "intimacy": rel["intimacy"],
        "passion": rel["passion"],
        "commitment": rel["commitment"]
    }
    monologue_store.data[-1] = monologue
    monologue_store._save()

    user_msg["status"] = "read"
    from db import get_conn
    conn = get_conn()
    conn.execute("UPDATE messages SET status='read' WHERE id=?", (user_msg["_id"],))
    conn.commit()

    rel = emotion.relationship
    agent["phase"] = rel["phase"]
    agent["intimacy"] = rel["intimacy"]
    agent["passion"] = rel["passion"]
    agent["commitment"] = rel["commitment"]
    agent["relationship_days"] = rel.get("days", 1)

    save_agent(agent)

    return {
        "user_message": user_msg,
        "ai_message": ai_msg,
        "agent": agent,
        "milestones": milestones,
        "relationship": {
            "phase": rel["phase"],
            "intimacy": rel["intimacy"],
            "passion": rel["passion"],
            "commitment": rel["commitment"],
            "days": rel.get("days", 1)
        },
        "shared_memories": emotion.shared,
        "memu_status": memu.get_status(),
        "monologue": monologue,
        "segments": segments,
        "delays": delays,
        "emojis": emoji_list,
        "urls_fetched": urls_result,
        "image_recognized": image_result,
    }


@app.get("/api/messages")
def get_messages(persona_id: str = "", limit: int = 50, before_id: str = "", user: dict = Depends(require_auth)):
    user_id = user["user_id"]
    if not persona_id:
        return {"messages": [], "agent": None}
    agents = load_agents()
    key = f"{user_id}_{persona_id}"
    if key not in agents:
        return {"messages": [], "agent": None, "relationship": {"phase": "acquaintance", "intimacy": 10, "passion": 5, "commitment": 5, "days": 1}}
    agent = agents[key]
    agent_id = agent["agent_id"]
    if before_id:
        msgs = load_messages_paginated(agent_id, limit=limit, before_id=before_id)
    else:
        msgs = load_messages_paginated(agent_id, limit=limit)
    total = get_message_count(agent_id)
    emotion = get_emotion(agent_id)
    emotion.refresh_days()
    memu = get_memu(agent_id, user_id)
    rel = emotion.relationship
    return {
        "messages": msgs,
        "total": total,
        "has_more": len(msgs) == limit and len(msgs) < total,
        "agent": agent,
        "relationship": {
            "phase": rel["phase"],
            "intimacy": rel["intimacy"],
            "passion": rel["passion"],
            "commitment": rel["commitment"],
            "days": rel.get("days", 1)
        },
        "shared_memories": emotion.shared,
        "memu_status": memu.get_status()
    }


@app.get("/api/memory")
def get_memory_api(persona_id: str = "", user: dict = Depends(require_auth)):
    user_id = user["user_id"]
    if not persona_id:
        return {"memu_status": None, "categories": [], "relationship": {}, "shared": {}, "milestones": [], "promises": []}
    agents = load_agents()
    key = f"{user_id}_{persona_id}"
    if key not in agents:
        return {"memu_status": None, "categories": [], "relationship": {}, "shared": {}, "milestones": [], "promises": []}
    agent_id = agents[key]["agent_id"]
    memu = get_memu(agent_id, user_id)
    emotion = get_emotion(agent_id)
    emotion.refresh_days()

    categories = memu.get_categories()
    status = memu.get_status()

    return {
        "memu_status": status,
        "categories": categories,
        "relationship": emotion.relationship,
        "shared": emotion.shared,
        "milestones": emotion.shared.get("milestones", []),
        "promises": emotion.shared.get("important_promises", [])
    }


@app.post("/api/memory/flush")
def flush_memory(persona_id: str = "", user: dict = Depends(require_auth)):
    user_id = user["user_id"]
    agents = load_agents()
    key = f"{user_id}_{persona_id}"
    if key not in agents:
        return {"status": "ok", "memu_status": None}
    agent_id = agents[key]["agent_id"]
    memu = get_memu(agent_id, user_id)
    memu.flush_sync()
    return {"status": "ok", "memu_status": memu.get_status()}


@app.post("/api/config")
def configure(req: ConfigRequest):
    global client, current_model, current_base_url, current_api_key
    try:
        client = OpenAI(
            api_key=req.api_key,
            base_url=req.base_url if req.base_url else None
        )
        current_model = req.model
        current_base_url = req.base_url
        current_api_key = req.api_key
        # 同步更新 settings 中的全局变量
        import settings
        settings.client = client
        settings.current_model = req.model
        settings.current_base_url = req.base_url
        settings.current_api_key = req.api_key
        test_resp = client.chat.completions.create(
            model=req.model,
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=5
        )
        save_config({"api_key": req.api_key, "base_url": req.base_url, "model": req.model})
        return {"status": "ok", "message": f"MemU 记忆系统就绪，模型: {req.model}"}
    except Exception as e:
        client = None
        settings.client = None
        return {"status": "error", "message": str(e)}


@app.get("/api/config/status")
def config_status():
    masked_key = ""
    if current_api_key:
        pk = current_api_key
        if len(pk) > 8:
            masked_key = pk[:4] + "****" + pk[-4:]
        else:
            masked_key = pk[:2] + "****"
    return {
        "configured": client is not None,
        "model": current_model if client else None,
        "base_url": current_base_url if client else None,
        "has_api_key": bool(current_api_key),
        "masked_key": masked_key,
        "memu_version": "0.2.2"
    }


# ==================== 本地视觉模型 API ====================

import threading
from pathlib import Path

VISION_MODEL_MAP = {
    "qwen3vl2b": "Qwen/Qwen3-VL-2B-Instruct",
    "qwen3vl4b": "Qwen/Qwen3-VL-4B-Instruct",
    "qwen3vl7b": "Qwen/Qwen3-VL-7B-Instruct",
}

VISION_CACHE_DIR = Path(os.path.expanduser("~/.cache/huggingface/hub"))
VISION_DOWNLOAD_STATUS = {}
VISION_MODEL_LOADED = {}
VISION_MODEL_INSTANCE = None
VISION_PROCESSOR_INSTANCE = None
VISION_CURRENT_MODEL = None


async def _auto_load_vision_model(model: str):
    """自动加载视觉模型（启动时调用）"""
    global VISION_MODEL_INSTANCE, VISION_PROCESSOR_INSTANCE, VISION_CURRENT_MODEL
    if not model or model not in VISION_MODEL_MAP:
        return
    import torch
    from transformers import Qwen3VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig

    model_id = VISION_MODEL_MAP[model]
    model_dir = VISION_CACHE_DIR / ("models--" + model_id.replace("/", "--"))
    if not model_dir.exists() or not any(model_dir.glob("snapshots/*")):
        logger.warning(f"视觉模型未下载: {model}，跳过自动加载")
        return

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
    )
    device_map = "auto"
    logger.info(f"正在加载视觉模型: {model} ({model_id}) ...")
    VISION_MODEL_INSTANCE = Qwen3VLForConditionalGeneration.from_pretrained(
        model_id, cache_dir=str(VISION_CACHE_DIR), device_map=device_map,
        torch_dtype=torch.bfloat16, quantization_config=bnb_config
    )
    VISION_PROCESSOR_INSTANCE = AutoProcessor.from_pretrained(model_id, cache_dir=str(VISION_CACHE_DIR))
    VISION_CURRENT_MODEL = model
    logger.info(f"视觉模型 {model} 已自动加载完成")


@app.get("/api/vision-model/status")
def vision_model_status(model: str):
    """检查本地视觉模型是否已下载和已加载"""
    if model not in VISION_MODEL_MAP:
        return {"downloaded": False, "loaded": False, "message": "未知模型"}
    model_id = VISION_MODEL_MAP[model]
    model_dir = VISION_CACHE_DIR / ("models--" + model_id.replace("/", "--"))
    downloaded = model_dir.exists() and any(model_dir.glob("snapshots/*"))
    loaded = VISION_MODEL_INSTANCE is not None and VISION_CURRENT_MODEL == model
    return {
        "downloaded": downloaded,
        "loaded": loaded,
        "model": model,
        "model_path": str(model_dir) if downloaded else None
    }


@app.post("/api/vision-model/download")
async def vision_model_download(request: Request):
    """下载本地视觉模型（SSE 流式进度）"""
    import asyncio
    
    body = await request.json()
    model = body.get("model", "")
    if model not in VISION_MODEL_MAP:
        return JSONResponse({"detail": "未知模型"}, status_code=400)
    
    model_id = VISION_MODEL_MAP[model]
    
    async def event_generator():
        try:
            # 使用 Python 脚本下载模型
            yield f"data: {json.dumps({'status': 'starting', 'progress': 0, 'message': '开始下载模型...'})}\n\n"
            
            script = f"""
import sys
sys.path.insert(0, r'{os.path.dirname(os.path.abspath(__file__))}')
from transformers import AutoProcessor, Qwen3VLForConditionalGeneration
import torch
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

print("PROGRESS:10", flush=True)
print("STATUS:下载模型配置...", flush=True)

# 只下载，不加载
from huggingface_hub import snapshot_download
snapshot_download(
    '{model_id}',
    cache_dir=r'{VISION_CACHE_DIR}',
    resume_download=True,
    max_workers=4,
)
print("PROGRESS:100", flush=True)
print("COMPLETE", flush=True)
"""
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "-c", script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env={**os.environ, "PYTHONIOENCODING": "utf-8", "HF_HUB_DISABLE_PROGRESS_BARS": "1"}
            )
            
            async for line in proc.stdout:
                try:
                    line = line.decode('utf-8', errors='replace').strip()
                except Exception:
                    continue
                if line.startswith("PROGRESS:"):
                    pct = int(line.split(":")[1])
                    yield f"data: {json.dumps({'status': 'downloading', 'progress': pct})}\n\n"
                elif line.startswith("STATUS:"):
                    msg = line.split(":", 1)[1]
                    yield f"data: {json.dumps({'status': 'downloading', 'progress': vision_download_status.get(model, 0), 'message': msg})}\n\n"
                elif line == "COMPLETE":
                    yield f"data: {json.dumps({'status': 'complete', 'progress': 100, 'message': '模型下载完成！'})}\n\n"
                    break
            
            await proc.wait()
            if proc.returncode != 0:
                yield f"data: {json.dumps({'status': 'error', 'message': '下载过程出错'})}\n\n"
                
        except Exception as e:
            yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@app.post("/api/vision-model/load")
async def vision_model_load(request: Request):
    """加载本地视觉模型到内存"""
    body = await request.json()
    model = body.get("model", "")
    if model not in VISION_MODEL_MAP:
        return JSONResponse({"detail": "未知模型"}, status_code=400)
    
    global VISION_MODEL_INSTANCE, VISION_PROCESSOR_INSTANCE, VISION_CURRENT_MODEL
    
    try:
        import torch
        from transformers import Qwen3VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig
        
        model_id = VISION_MODEL_MAP[model]
        
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
        )
        
        VISION_MODEL_INSTANCE = Qwen3VLForConditionalGeneration.from_pretrained(
            model_id,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True,
        )
        VISION_PROCESSOR_INSTANCE = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
        VISION_CURRENT_MODEL = model
        
        return {"status": "ok", "message": f"模型 {model} 已加载"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/vision-model/unload")
async def vision_model_unload():
    """卸载本地视觉模型，释放 GPU 显存"""
    global VISION_MODEL_INSTANCE, VISION_PROCESSOR_INSTANCE, VISION_CURRENT_MODEL
    import gc
    import torch
    
    if VISION_MODEL_INSTANCE is not None:
        del VISION_MODEL_INSTANCE
        VISION_MODEL_INSTANCE = None
    if VISION_PROCESSOR_INSTANCE is not None:
        del VISION_PROCESSOR_INSTANCE
        VISION_PROCESSOR_INSTANCE = None
    VISION_CURRENT_MODEL = None
    
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    
    return {"status": "ok", "message": "模型已卸载，显存已释放"}


@app.post("/api/vision-model/recognize")
async def vision_model_recognize(request: Request):
    """使用本地视觉模型识别图片"""
    global VISION_MODEL_INSTANCE, VISION_PROCESSOR_INSTANCE
    
    if VISION_MODEL_INSTANCE is None or VISION_PROCESSOR_INSTANCE is None:
        return JSONResponse({"detail": "视觉模型未加载，请先加载模型"}, status_code=400)
    
    try:
        import torch
        from PIL import Image
        from io import BytesIO
        import base64
        from qwen_vl_utils import process_vision_info
        
        body = await request.json()
        image_data = body.get("image", "")  # base64 encoded image
        prompt = body.get("prompt", "请用中文简洁描述这张图片的主要内容。")
        
        # 解码图片
        if image_data.startswith("data:"):
            image_data = image_data.split(",", 1)[1]
        image_bytes = base64.b64decode(image_data)
        pil_image = Image.open(BytesIO(image_bytes)).convert("RGB")
        
        # 缩放
        max_size = 768
        if max(pil_image.size) > max_size:
            ratio = max_size / max(pil_image.size)
            new_size = (int(pil_image.size[0] * ratio), int(pil_image.size[1] * ratio))
            pil_image = pil_image.resize(new_size, Image.LANCZOS)
        
        # 构建消息
        messages = [{
            "role": "user",
            "content": [
                {"type": "image", "image": pil_image},
                {"type": "text", "text": prompt},
            ],
        }]
        
        text_input = VISION_PROCESSOR_INSTANCE.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = VISION_PROCESSOR_INSTANCE(
            text=[text_input],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        )
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        if device == "cuda":
            inputs = inputs.to(device)
        
        with torch.inference_mode():
            generated_ids = VISION_MODEL_INSTANCE.generate(
                **inputs,
                max_new_tokens=100,
                do_sample=False,
            )
        
        generated_ids_trimmed = [
            out_ids[len(in_ids):]
            for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        output_text = VISION_PROCESSOR_INSTANCE.batch_decode(
            generated_ids_trimmed,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )[0]
        
        return {"status": "ok", "description": output_text.strip()}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.delete("/api/messages")
def clear_messages_endpoint(persona_id: str = "sunny", user: dict = Depends(require_auth)):
    user_id = user["user_id"]
    agents = load_agents()
    key = f"{user_id}_{persona_id}"
    if key not in agents:
        return {"status": "ok"}
    agent = agents[key]
    clear_messages(agent["agent_id"])
    RECALL_BUFFER.pop(agent["agent_id"], None)
    return {"status": "ok"}


@app.get("/api/monologue/latest")
def get_latest_monologue(persona_id: str = "sunny", user: dict = Depends(require_auth)):
    user_id = user["user_id"]
    agents = load_agents()
    key = f"{user_id}_{persona_id}"
    if key not in agents:
        return {"monologue": None}
    agent = agents[key]
    store = get_monologue_store(agent["agent_id"])
    latest = store.get_latest()
    return {"monologue": latest}


@app.get("/api/monologue/history")
def get_monologue_history(persona_id: str = "sunny", limit: int = 10, user: dict = Depends(require_auth)):
    user_id = user["user_id"]
    agents = load_agents()
    key = f"{user_id}_{persona_id}"
    if key not in agents:
        return {"history": [], "count": 0}
    agent = agents[key]
    store = get_monologue_store(agent["agent_id"])
    history = store.get_history(limit)
    return {"history": history, "count": len(history)}


# ==================== 静态文件 & SPA ====================

_DIST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "dist")
_AVATAR_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "avatars")
_EMOJI_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "emojis")

os.makedirs(_AVATAR_DIR, exist_ok=True)
os.makedirs(_EMOJI_DIR, exist_ok=True)
app.mount("/avatars", StaticFiles(directory=_AVATAR_DIR), name="avatars")
app.mount("/static/emojis", StaticFiles(directory=_EMOJI_DIR), name="emojis")

if os.path.isdir(_DIST_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(_DIST_DIR, "assets")), name="assets")

    @app.get("/")
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str = ""):
        index_path = os.path.join(_DIST_DIR, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"detail": "前端未构建，请运行 npm run build"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)
