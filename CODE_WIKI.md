# 半熟时区 (Soft-Ripe Timezone) — Code Wiki

> 一个开源的 AI 恋人陪伴应用，具备长期记忆、三维情感演化、主动互动、人设 Lorebook 等能力。

---

## 目录

1. [项目概述](#1-项目概述)
2. [系统架构](#2-系统架构)
3. [目录结构](#3-目录结构)
4. [核心模块说明](#4-核心模块说明)
   - [4.1 主入口与路由 (main.py)](#41-主入口与路由-mainpy)
   - [4.2 全局配置 (settings.py)](#42-全局配置-settingspy)
   - [4.3 回复引擎 (reply_engine.py)](#43-回复引擎-reply_enginepy)
   - [4.4 情感系统 (emotion_system.py)](#44-情感系统-emotion_systempy)
   - [4.5 MemU 记忆系统 (memu_system.py)](#45-memu-记忆系统-memu_systempy)
   - [4.6 人设引擎 (persona_engine.py)](#46-人设引擎-persona_enginepy)
   - [4.7 主动消息引擎 (proactive_engine.py)](#47-主动消息引擎-proactive_enginepy)
   - [4.8 用户习惯学习 (routine_learner.py)](#48-用户习惯学习-routine_learnerpy)
   - [4.9 AI 日常生活 (ai_daily_life.py)](#49-ai-日常生活-ai_daily_lifepy)
   - [4.10 忙闲管理 (ai_busy.py)](#410-忙闲管理-ai_busypy)
   - [4.11 分手管理 (breakup_manager.py)](#411-分手管理-breakup_managerpy)
   - [4.12 纪念日 (anniversary.py)](#412-纪念日-anniversarypy)
   - [4.13 信念系统 (beliefs.py)](#413-信念系统-beliefspy)
   - [4.14 表情包引擎 (emoji_engine.py)](#414-表情包引擎-emoji_enginepy)
   - [4.15 认证系统 (auth.py)](#415-认证系统-authpy)
   - [4.16 数据库 (db.py)](#416-数据库-dbpy)
   - [4.17 管理员 API (admin.py)](#417-管理员-api-adminpy)
   - [4.18 图片识别 (image_recognizer.py)](#418-图片识别-image_recognizerpy)
   - [4.19 URL 抓取 (url_fetcher.py)](#419-url-抓取-url_fetcherpy)
   - [4.20 工具函数 (utils_json.py / utils_time.py)](#420-工具函数-utils_jsonpy--utils_timepy)
   - [4.21 微信连接模块 (wechat/)](#421-微信连接模块-wechat)
   - [4.22 AI 人设 JSON 配置 (personas/)](#422-ai-人设-json-配置-personas)
   - [4.23 前端 (frontend/)](#423-前端-frontend)
5. [数据流详解](#5-数据流详解)
6. [关键类与函数速查](#6-关键类与函数速查)
7. [依赖清单](#7-依赖清单)
8. [项目运行方式](#8-项目运行方式)

---

## 1. 项目概述

**半熟时区** 是一款开源 AI 恋人陪伴应用。核心创新点包括：

| 特性 | 说明 |
|---|---|
| **9 种 AI 人设** | 阳光学妹、温柔治愈、傲娇高冷、粘人女友…… 每种人格拥有独立信念系统 |
| **三维情感引擎** | 基于 Sternberg 爱情三角理论，亲密/激情/承诺三轴动态演化 |
| **MemU 长期记忆** | 情节记忆 + 语义分类 + 过程记忆，跨越会话记住你的喜好和点滴 |
| **主动互动** | AI 会根据你的习惯和状态，在适当时机主动发起对话 |
| **情感表情动效** | 聊天时伴随 GIF 动效表达情绪 |
| **纪念日管理** | 自动记录重要日子，AI 会主动送上祝福 |
| **日常生活模拟** | 每个 AI 拥有独立日程表，回复自然融入"现在在做什么" |
| **隐私优先** | 所有数据本地存储，无需注册第三方账号 |
| **模型自由切换** | 兼容所有 OpenAI 协议模型，UI 界面运行时热切换 |

---

## 2. 系统架构

```
┌─────────────────────────────────────────────────────┐
│  前端层 (Vue 3 + Vite + vue-advanced-chat)           │
│  ┌─────────────────────────────────────────────────┐ │
│  │  App.vue (聊天界面 + 设置面板 + 人设切换)        │ │
│  └─────────────────────────────────────────────────┘ │
└────────────────────────┬────────────────────────────┘
                         │ HTTP/JSON API
┌────────────────────────▼────────────────────────────┐
│  API层 (FastAPI)                                      │
│  ┌──────────────────────────────────────────────────┐│
│  │  main.py: 路由注册 + 认证中间件 + CORS            ││
│  │  auth.py: Session Token + 速率限制               ││
│  │  admin.py: 管理后台 API                           ││
│  └──────────────────────────────────────────────────┘│
└────────────────────────┬────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────┐
│  核心引擎层                                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐ │
│  │reply_    │ │emotion_  │ │memu_     │ │persona_ │ │
│  │engine    │ │system    │ │system    │ │engine   │ │
│  └──────────┘ └──────────┘ └──────────┘ └─────────┘ │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐ │
│  │proactive │ │routine_  │ │ai_daily_ │ │ai_busy  │ │
│  │_engine   │ │learner   │ │life      │ │         │ │
│  └──────────┘ └──────────┘ └──────────┘ └─────────┘ │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐ │
│  │breakup_  │ │anniver-  │ │emoji_    │ │beliefs  │ │
│  │manager   │ │sary      │ │engine    │ │         │ │
│  └──────────┘ └──────────┘ └──────────┘ └─────────┘ │
└────────────────────────┬────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────┐
│  数据层                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │ SQLite       │  │ JSON 文件     │  │ 本地向量    │ │
│  │ (app.db)     │  │ (messages/   │  │ 嵌入模型    │ │
│  │              │  │  agents/...)  │  │ (384维)    │ │
│  └──────────────┘  └──────────────┘  └────────────┘ │
└─────────────────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────┐
│  外部依赖                                              │
│  ┌──────────────────────────────────────────────────┐│
│  │  LLM API (OpenAI / DeepSeek / Ollama ...)        ││
│  │  sentence-transformers (本地文本嵌入)              ││
│  └──────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────┘
```

---

## 3. 目录结构

```
Soft-Ripe Timezone/
├── backend/                          # Python 后端
│   ├── main.py                       # FastAPI 主入口 & 全部路由
│   ├── settings.py                   # 全局配置、PERSONAS、常量、Logger
│   ├── auth.py                       # 认证系统 (Session Token)
│   ├── db.py                         # SQLite 数据库操作
│   ├── reply_engine.py               # 回复引擎 (独白 + 回复生成)
│   ├── emotion_system.py             # 情感系统 + 冲突引擎
│   ├── memu_system.py                # MemU 三维记忆系统
│   ├── persona_engine.py             # 人设 Lorebook 引擎
│   ├── proactive_engine.py           # 主动消息引擎 + 需求状态
│   ├── routine_learner.py            # 用户作息习惯学习
│   ├── ai_daily_life.py              # AI 日常生活模拟
│   ├── ai_busy.py                    # 忙闲状态管理
│   ├── anniversary.py                # 纪念日管理
│   ├── breakup_manager.py            # 分手管理
│   ├── beliefs.py                    # 信念系统
│   ├── emoji_engine.py               # 表情包引擎
│   ├── url_fetcher.py                # URL 链接内容抓取
│   ├── image_recognizer.py           # 图片识别 (API + 本地降级)
│   ├── admin.py                      # 管理员 API
│   ├── diagnose.py                   # 诊断工具
│   ├── inject_persona_fields.py      # 人设字段注入脚本
│   ├── utils_json.py                 # LLM JSON 容错解析
│   ├── utils_time.py                 # 时间/天气工具函数
│   ├── requirements.txt              # Python 依赖
│   ├── personas/                     # 9 种人设 JSON 配置
│   │   ├── sunny.json                # 阳光学妹
│   │   ├── clingy.json               # 黏人甜妹
│   │   ├── cool.json                 # 清冷才女
│   │   ├── intellectual.json         # 知性姐姐
│   │   ├── sensitive.json            # 敏感文艺
│   │   ├── independent.json          # 独立御姐
│   │   ├── gentle_mature.json        # 温柔熟女
│   │   ├── needy_mature.json         # 缺爱成熟
│   │   └── career_woman.json         # 事业女性
│   ├── static/                       # 静态资源
│   │   ├── avatars/                  # 人设头像
│   │   └── emojis/                   # 表情 GIF
│   ├── wechat/                       # 微信连接模块
│   │   ├── __init__.py               # 模块入口
│   │   ├── adapter.py                # iLink 协议适配器
│   │   ├── auth.py                   # 微信认证
│   │   ├── bot_state.py              # 机器人状态管理
│   │   ├── cdma.py                   # CDN 媒体上传下载
│   │   ├── ilink_client.py           # iLink 异步客户端
│   │   ├── ilink_types.py            # iLink 数据类型
│   │   ├── media.py                  # 媒体处理
│   │   ├── monitor.py                # 消息监控
│   │   └── wechat_proactive.py       # 微信主动消息
│   └── data/                         # 运行时数据 (gitignored)
│       ├── config.json               # API 配置
│       ├── users.json                # 用户信息
│       ├── app.db                    # SQLite 数据库
│       ├── memu_memory/              # MemU 记忆数据
│       ├── emotion/                  # 情感状态
│       ├── proactive/                # 主动消息队列
│       ├── routines/                 # 习惯学习数据
│       ├── anniversaries/            # 纪念日数据
│       ├── breakups/                 # 分手状态
│       ├── busy/                     # 忙闲状态
│       ├── daily_life/               # 日常生活状态
│       ├── need_state/               # 需求状态
│       ├── user_evaluation/          # 用户评价
│       └── messages/                 # (迁移到 SQLite 前遗留)
├── frontend/                         # Vue 3 前端
│   ├── src/
│   │   ├── App.vue                   # 主组件 (登录/聊天/设置)
│   │   └── main.js                   # 入口
│   ├── index.html
│   ├── vite.config.js
│   ├── package.json
│   └── package-lock.json
├── start.bat                         # Windows 一键启动
├── start.sh                          # Linux 一键启动
├── showcase.html                     # 展示页面
├── CODE_WIKI.md                      # 本文档
├── README.md
└── LICENSE                           # MIT
```

---

## 4. 核心模块说明

### 4.1 主入口与路由 (main.py)

**文件**: [backend/main.py](file:///d:/yuyan/Soft-Ripe%20Timezone/backend/main.py)

**职责**: 应用入口、FastAPI 服务启动、全部 API 路由注册、全局缓存管理。

**关键函数/类**:

| 函数 | 说明 |
|---|---|
| `lifespan(app)` | FastAPI 生命周期管理器。初始化：加载嵌入模型、视觉模型、LLM 配置、微信模块；自动打开浏览器 |
| `get_or_create_agent(user_id, persona_id)` | 获取或创建 AI 伴侣 Agent。按 `{user_id}_{persona_id}` 键值查找，不存在则创建新 Agent |
| `chat()` | `POST /api/chat` — 核心聊天接口。处理图片识别→URL抓取→分手检测→情感更新→忙闲判断→纪念日→内心独白→回复生成→表情解析→记忆存储→关系值同步 |
| `check_proactive()` | `GET /api/check-proactive` — 轮询接口，检查 AI 是否需要主动发起对话 |
| `configure()` | `POST /api/config` — 配置/切换 LLM 模型、API Key、Base URL（运行时热切换） |

**API 路由一览**:

| 路径 | 方法 | 说明 |
|---|---|---|
| `/api/personas` | GET | 获取所有人设列表 |
| `/api/users/register` | POST | 用户注册 |
| `/api/users/login` | POST | 用户登录 |
| `/api/users/me` | GET | 获取当前用户信息 |
| `/api/chat` | POST | 核心聊天接口 |
| `/api/messages` | GET | 获取聊天记录（支持分页） |
| `/api/memory` | GET | 获取记忆状态 |
| `/api/config` | POST | 切换 LLM 配置 |
| `/api/config/status` | GET | 获取配置状态 |
| `/api/check-proactive` | GET | 检查主动消息 |
| `/api/wechat/qrcode` | POST | 获取微信登录二维码 |
| `/api/wechat/qrstatus` | GET | 查询微信扫码状态 |
| `/api/vision-model/load` | POST | 加载本地视觉模型 |

---

### 4.2 全局配置 (settings.py)

**文件**: [backend/settings.py](file:///d:/yuyan/Soft-Ripe%20Timezone/backend/settings.py)

**职责**: 集中管理所有全局常量、配置变量、缓存字典、Logger。

**关键内容**:

| 变量/常量 | 说明 |
|---|---|
| `PERSONAS` | 9 种人设的完整定义（name/type/age/bio/speech_dna/system_prompt） |
| `EVENT_BASE_DELTAS` | 关系事件对三维情感的基础影响值（按阶段分 early/right_time/late） |
| `PHASE_MATCH` | 事件类型到关系阶段的映射 |
| `PERSONALITY_MODIFIER` | 不同依恋风格对事件影响的修正系数 |
| `NEED_DEFAULTS` | 需求状态引擎默认值（social/share/attention 三种需求） |
| `ATTACHMENT_NEED_MODIFIERS` | 依恋风格对需求衰减速度的修正 |
| `USER_EVAL_DIMS` | 用户评价系统的 5 个维度定义 |
| `RECALL_BUFFER` | 短期对话回忆缓存（每 Agent 最多 30 条） |
| `memu_systems` / `emotion_systems` 等 | 全局引擎实例缓存 |
| `TOOLS` | LLM 函数调用定义（get_current_time / get_weather） |

**路径常量**:

```python
DATA_DIR         # backend/data/
AGENTS_FILE      # backend/data/agents.json
USERS_FILE       # backend/data/users.json
CONFIG_FILE      # backend/data/config.json
MEMU_DATA_DIR    # backend/data/memu_memory/
EMOTION_DIR      # backend/data/emotion/
```

---

### 4.3 回复引擎 (reply_engine.py)

**文件**: [backend/reply_engine.py](file:///d:/yuyan/Soft-Ripe%20Timezone/backend/reply_engine.py)

**职责**: 核心回复生成流程：内心独白 → 评价更新 → 回复构建 → 分段延迟。

**关键类/函数**:

| 名称 | 说明 |
|---|---|
| `UserEvaluationStore` | 用户评价存储。维护 5 个维度（真诚度/社交能力/兴趣/情商/边界感），每个维度 0-100 分 |
| `MonologueStore` | 内心独白历史存储（持久化到 SQLite） |
| `call_internal_monologue()` | 调用 LLM 生成内心独白。分析：当前阶段、情绪、关系三角值、用户评价变化 |
| `calibrate_monologue()` | 校准独白结果。规则：置信度<0.5 回滚、阶段跳跃限制在 1 级、最短停留期 3 天 |
| `call_external_reply()` | 生成对外回复。组装完整 prompt：人设核心 + 记忆 + 关系状态 + 人设 Lorebook + 阶段准则 + 语气指南 + 对话示例 + 分段规则 |
| `compute_segment_delays()` | 计算多段回复的发送延迟（模拟真人打字节奏） |
| `get_compact_style_rules()` | 根据用户消息长度动态调整回复长度规则 |
| `get_reply_examples()` | 按亲密度返回对应阶段的对话正反示例 |
| `get_intimacy_tone_guide()` | 按亲密度返回语气指导 |
| `PHASE_BEHAVIORS` | 7 个关系阶段的详细行为准则字典（核心 prompt 内容） |

**独白 Prompt 结构**:
```
你的爱情信念 + 当前关系状态 + 长期记忆 + 上次独白状态 + 三角值 + 用户消息 + 阶段对应关系
→ 输出 JSON: {phase, phase_changed, confidence, reasoning, emotion, share_activity, love_triangle, key_observations, user_evaluation}
```

**回复 Prompt 结构**:
```
system_prompt + 说话风格 + 对话示例 + 摘要行 + 记忆 + Lorebook + 关系状态 + 内心状态 + 审问警告 + 用户评价 + 阶段准则 + 语气指南 + 冲突上下文 + 输入规则 + 对话示例 + 分段规则
```

---

### 4.4 情感系统 (emotion_system.py)

**文件**: [backend/emotion_system.py](file:///d:/yuyan/Soft-Ripe%20Timezone/backend/emotion_system.py)

**职责**: 基于 Sternberg 爱情三角理论的关系情感管理 + 冲突引擎。

**关键类/函数**:

| 名称 | 说明 |
|---|---|
| `EmotionSystem` | 核心情感系统。管理 `relationship.json` 和 `shared.json` |
| `ConflictEngine` | 冲突引擎。管理争吵的爆发/冷却/修复全周期 |
| `analyze_message_quality()` | 分析用户消息质量类型：deep_disclosure / emotional_support / flirtation / mild_conflict / severe_conflict / cold / casual |
| `get_event_delta()` | 计算事件对三轴的综合影响（考虑阶段匹配 + 人格修正） |
| `apply_time_decay()` | 时间衰减计算（离线 4h 内无衰减，最长 720h 大幅度衰减） |
| `detect_interrogation_pattern()` | 检测用户是否在"审讯式提问"（连续提问不分享自己） |

**情感三轴**:

```
亲密 (Intimacy):     0-100  心理亲近感与理解
激情 (Passion):      0-100  情感吸引力与心动
承诺 (Commitment):   0-100  对关系的投入与维系
```

**关系阶段**:
```
acquaintance(初识) → ambiguous(暧昧) → observation(观察)
→ heartbeat(心动) → together(在一起) → passion(热恋) → stable(稳定)
```

**阶段自动推进**:
```
acquaintance → intimacy≥25 → ambiguous
ambiguous    → intimacy≥40 → heartbeat
heartbeat    → intimacy≥60 + commitment≥40 → together
together     → intimacy≥75 → passion
passion      → intimacy≥85 + commitment≥70 → stable
```

---

### 4.5 MemU 记忆系统 (memu_system.py)

**文件**: [backend/memu_system.py](file:///d:/yuyan/Soft-Ripe%20Timezone/backend/memu_system.py)

**职责**: 三维长期记忆存储与语义检索。

**关键类**:

| 名称 | 说明 |
|---|---|
| `MemUMemorySystem` | 记忆系统主类。管理三种记忆类型 |

**三种记忆类型**:

| 类型 | 存储位置 | 说明 |
|---|---|---|
| **情节记忆 (Episodic)** | `memu_memory/{agent_id}/{user_id}/episodic/YYYY-MM-DD.json` | 按天存储对话摘要，7 天后自动清理 |
| **语义记忆 (Semantic)** | `memu_memory/{agent_id}/{user_id}/categories/*.json` | LLM 自动分类并提取关键信息（如"用户基本信息""关系状态"），每条记忆包含 embedding 向量 |
| **过程记忆 (Procedural)** | `memu_memory/{agent_id}/{user_id}/procedural.json` | 长期积累的相处经验 insight，最多 20 条 |

**核心方法**:

| 方法 | 说明 |
|---|---|
| `add_exchange(user_msg, ai_msg)` | 添加一次对话交换。存储情节记忆，累积到 6 条后触发后台 flush |
| `_do_flush()` | 调用 LLM 分析最近对话，提取/更新语义分类和记忆条目 |
| `get_memory_context(current_message, top_k)` | 获取用于 LLM prompt 的完整记忆上下文（情节 + 语义 + 语义搜索 + 过程） |
| `_search_relevant(query, top_k)` | 语义搜索：本地 embedding 余弦相似度（0.7权重）+ 重要性（0.3权重），阈值 >0.4 |
| `_get_embedding(text)` | 获取文本向量：优先本地 `paraphrase-multilingual-MiniLM-L12-v2`，降级到 API `text-embedding-3-small` |

---

### 4.6 人设引擎 (persona_engine.py)

**文件**: [backend/persona_engine.py](file:///d:/yuyan/Soft-Ripe%20Timezone/backend/persona_engine.py)

**职责**: 角色档案加载、Lorebook 关键词匹配注入、核心身份提示词构建。

**灵感来源**: SillyTavern World Info / Lorebook 架构

**关键函数**:

| 名称 | 说明 |
|---|---|
| `load_persona(persona_id)` | 从 `personas/{persona_id}.json` 加载人设数据 |
| `get_persona_data(persona_id)` | 获取人设数据，优先读 JSON 文件，回退到 `PERSONAS` 字典并自动创建 JSON |
| `get_persona_core(persona_data)` | 构建身份提示词：name + age + type + core prompt + ground_truths + appearance |
| `resolve_lorebook(persona_data, user_message, recent_context)` | 扫描用户消息匹配关键词 → 按优先级排序 → 递归激活（3层）→ Token 预算控制（2000） |
| `save_persona(persona_id, data)` | 保存人设 JSON 到磁盘 |

**Lorebook 匹配规则**:
1. 扫描最近 5 条上下文 + 当前用户消息
2. 关键词匹配：字符串包含 或 `/regex/` 正则
3. 按 `priority` 降序排列
4. 递归激活：已激活条目内容中出现其他条目 title 则激活（最多 3 层）
5. Token 预算控制：不超过 2000 字符

---

### 4.7 主动消息引擎 (proactive_engine.py)

**文件**: [backend/proactive_engine.py](file:///d:/yuyan/Soft-Ripe%20Timezone/backend/proactive_engine.py)

**职责**: AI 主动发起对话的时机判断 + 需求状态管理。

**关键类**:

| 名称 | 说明 |
|---|---|
| `ProactiveMessageEngine` | 主动消息引擎。管理每日限额、冷却时间、触发条件判断 |
| `NeedStateEngine` | 需求状态引擎。管理三种内在需求的衰减与触发 |

**主动触发场景**:

| 场景 | 条件 |
|---|---|
| **早安** | 上午 7-9 点，非初识期，离线 <24h |
| **晚安** | 22点后，暧昧期以上，离线 >=30 分钟 |
| **深夜** | 1-3 点，暧昧期以上，刚离线 <=5 分钟 |
| **想念** | 思念值超过阈值（亲密度决定），且 LLM 确认"应该发" |
| **话题延续** | 记忆系统有未完成的话题 |
| **需求触发** | 社交需求/分享欲/被关注需求衰减到阈值以下 |

**每日主动限额**:
- 亲密度 <30: 1 条
- 亲密度 30-60: 2 条
- 亲密度 >=60: 3 条
- 焦虑型 +1，回避型 -1

**三种内在需求**:
| 需求 | 初始值 | 衰减/小时 | 触发阈值 |
|---|---|---|---|
| 社交需求 (social) | 60 | 2.5 | 30 |
| 分享欲 (share) | 50 | 1.8 | 25 |
| 被关注 (attention) | 80 | 1.2 | 35 |

---

### 4.8 用户习惯学习 (routine_learner.py)

**文件**: [backend/routine_learner.py](file:///d:/yuyan/Soft-Ripe%20Timezone/backend/routine_learner.py)

**职责**: 分析用户活跃时间段，学习作息规律。

**关键类**:

| 名称 | 说明 |
|---|---|
| `RoutineLearner` | 习惯学习器。记录用户每天的活跃小时，分析起床/睡眠/忙碌窗口 |

**核心方法**:

| 方法 | 说明 |
|---|---|
| `record_activity()` | 记录一次用户活跃行为（当前小时标记为活跃） |
| `get_routine()` | 分析并返回：wake_hour, sleep_hour, active_hours, busy_windows, confidence |
| `get_optimal_greeting_time(type)` | 获取最佳问候时间（早安/晚安） |
| `is_dnd_hour(hour)` | 判断当前是否在用户免打扰时段 |

学习窗口：14 天，置信度 = 跟踪天数 / 14

---

### 4.9 AI 日常生活 (ai_daily_life.py)

**文件**: [backend/ai_daily_life.py](file:///d:/yuyan/Soft-Ripe%20Timezone/backend/ai_daily_life.py)

**职责**: 为每个 AI 人设生成独立日程表，回复时自然融入生活状态。

**关键类**:

| 名称 | 说明 |
|---|---|
| `AIDailyLife` | 日常生活管理器。每天生成一次日程 |

**关键方法**:

| 方法 | 说明 |
|---|---|
| `get_current_activity()` | 根据当前时间返回正在进行的活动 |
| `get_disclosure_guidance(phase, activity)` | 根据关系阶段和活动隐私层级，判断能否透露当前活动 |
| `get_activity_context_for_prompt()` | 构建注入 prompt 的当前活动上下文 |

**SCHEDULE_TEMPLATES**: 9 种人设的完整日程模板（工作日/周末），包含起床时间、睡眠时间、每个时段的活动

**披露策略 (DISCLOSURE_POLICY)**:
- public 区域：所有阶段均可透露
- casual 区域：非初识期可透露
- private 区域：心动期及以上可透露

---

### 4.10 忙闲管理 (ai_busy.py)

**文件**: [backend/ai_busy.py](file:///d:/yuyan/Soft-Ripe%20Timezone/backend/ai_busy.py)

**职责**: 模拟 AI 忙碌状态，让 AI 回复看起来更真实。

**关键类**:

| 名称 | 说明 |
|---|---|
| `AIBusyManager` | 忙闲管理器。随机触发忙碌状态，生成忙碌回复 |

**核心方法**:

| 方法 | 说明 |
|---|---|
| `try_enter_busy(phase, intimacy, hours_since_last)` | 概率进入忙碌状态。基础概率3%，9-11点和14-17点提高到8% |
| `is_currently_busy()` | 检查是否在忙碌状态 |
| `generate_busy_reply(persona_type, phase)` | 根据人设类型生成忙碌回复 |
| `get_away_notice(persona_type)` | 生成"今天比较忙"的提前告知 |

规则：每天最多 2 次忙碌，非初识期触发，每次持续 1.5-3.5 小时。

---

### 4.11 分手管理 (breakup_manager.py)

**文件**: [backend/breakup_manager.py](file:///d:/yuyan/Soft-Ripe%20Timezone/backend/breakup_manager.py)

**职责**: 检测分手意图、触发分手流程、冷却期管理、关系重启。

**关键类**:

| 名称 | 说明 |
|---|---|
| `BreakupManager` | 分手管理器 |

**核心方法**:

| 方法 | 说明 |
|---|---|
| `detect_breakup_intent(user_message)` | 正则匹配 18 种分手模式 |
| `initiate_breakup(persona_type, phase, days)` | 开始分手流程，设置冷却期 |
| `is_in_cooling()` | 检查是否在冷却期内 |
| `is_cooling_expired()` | 检查冷却期是否已过 |
| `handle_restart()` | 冷却期结束后自动重启关系 |
| `get_breakup_reply()` | 按人设类型返回分手回复（安全型→尊重/焦虑型→不舍/回避型→简洁） |

**冷却期长度**:
- 普通: 7 天
- 关系≥60天: 14 天
- 关系≥120天: 21 天
- 关系≥200天: 30 天

---

### 4.12 纪念日 (anniversary.py)

**文件**: [backend/anniversary.py](file:///d:/yuyan/Soft-Ripe%20Timezone/backend/anniversary.py)

**职责**: 关系里程碑纪念日和节日祝福。

**关键类**:

| 名称 | 说明 |
|---|---|
| `AnniversaryChecker` | 纪念日检查器 |

**检查范围**:
- 关系里程碑：7天/30天/50天/100天/180天/200天/300天/365天
- 通用节日：情人节/女神节/520/521/圣诞节/跨年夜/元旦
- 用户生日

**核心方法**:

| 方法 | 说明 |
|---|---|
| `check(relationship_days, phase, intimacy, first_interaction)` | 检查今天是否有纪念日（每天仅检查一次） |
| `set_user_birthday(month, day)` | 设置用户生日 |
| `get_anniversary_context(results)` | 构建注入 prompt 的纪念日上下文 |
| `should_ask_birthday(phase, intimacy)` | 判断是否该问用户生日（非初识且亲密度≥25） |

---

### 4.13 信念系统 (beliefs.py)

**文件**: [backend/beliefs.py](file:///d:/yuyan/Soft-Ripe%20Timezone/backend/beliefs.py)

**职责**: 定义 AI 角色的爱情信念系统，影响回复的行为逻辑底层。

**关键函数**:

| 名称 | 说明 |
|---|---|
| `get_beliefs(attachment_type)` | 获取核心信念 + 依恋风格专属信念 |
| `get_beliefs_for_persona(persona_id)` | 获取指定人设的信念集 |

**信念类型**:
- **核心信念** (8条): 如"爱情不是轰轰烈烈的激情，而是日复一日的选择"
- **安全型额外** (4条): 如"信任是关系的基石"
- **焦虑型额外** (4条): 如"我不需要完美才能被爱"
- **回避型额外** (4条): 如"亲密不是束缚，合适的距离让两个人都舒适"

---

### 4.14 表情包引擎 (emoji_engine.py)

**文件**: [backend/emoji_engine.py](file:///d:/yuyan/Soft-Ripe%20Timezone/backend/emoji_engine.py)

**职责**: AI 在回复中自主插入表情包标记，后端解析替换为实际表情 URL。

**核心函数**:

| 名称 | 说明 |
|---|---|
| `build_emoji_prompt_instruction(persona_id, phase)` | 构建注入 System Prompt 的表情使用指导 |
| `replace_emoji_tags(text)` | 将 AI 回复中的 `<emoji:分类>` 标记替换为表情 URL |
| `parse_emoji_tags(text)` | 提取所有表情标记 |
| `get_random_emoji(category)` | 从分类中随机选取一个表情文件 |

**可用表情分类**: angry / confused / evasive / happy / loved / reminded / sad / surprised / tired

**人设表情风格**: 9 种人设各有不同的频率和语气设置。

---

### 4.15 认证系统 (auth.py)

**文件**: [backend/auth.py](file:///d:/yuyan/Soft-Ripe%20Timezone/backend/auth.py)

**职责**: Session Token 管理、密码哈希、速率限制。

**关键函数**:

| 名称 | 说明 |
|---|---|
| `_create_session_token(username)` | 创建 32 字节 hex Session Token，有效期 24h |
| `_verify_session_token(token)` | 验证 Token 有效性，自动续期 |
| `_hash_password(password, salt)` | SHA-256 密码哈希 |
| `_check_rate_limit(user_id, max_per_minute)` | 速率限制，默认每分钟最多 8 次 |
| `require_auth(authorization)` | FastAPI 依赖注入，验证 Bearer Token |

---

### 4.16 数据库 (db.py)

**文件**: [backend/db.py](file:///d:/yuyan/Soft-Ripe%20Timezone/backend/db.py)

**职责**: SQLite 数据库操作，替代旧的 JSON 文件存储。

**表结构**:

| 表 | 字段 |
|---|---|
| `messages` | id, agent_id(FK), content, sender_id('user'/'ai'), timestamp, date, status, extra, created_at |
| `agents` | agent_id(PK), user_id, persona_id(UNIQUE组合), persona_name, system_prompt, phase, intimacy, passion, commitment, relationship_days, created_at |
| `monologues` | id(PK), agent_id, data_json, timestamp |

**连接管理**: 线程本地存储 (threading.local)，WAL 模式，每线程独立连接。

---

### 4.17 管理员 API (admin.py)

**文件**: [backend/admin.py](file:///d:/yuyan/Soft-Ripe%20Timezone/backend/admin.py)

**职责**: 调试和管理接口，通过 Query 参数 `admin_user=admin888` 验证。

**API 接口**:

| 路径 | 方法 | 说明 |
|---|---|---|
| `/api/admin/users` | GET | 列出所有用户及 AI 角色 |
| `/api/admin/relationship` | GET/POST | 查看/修改关系值 |
| `/api/admin/prompt` | GET | 查看完整系统提示词 |
| `/api/admin/update-prompt` | POST | 修改角色的系统提示词 |
| `/api/admin/trigger-proactive` | POST | 强制触发 AI 主动消息 |
| `/api/admin/messages` | GET | 查看完整聊天记录 |
| `/api/admin/delete-user` | POST | 删除用户及关联数据 |
| `/api/admin/delete-agent` | POST | 删除指定 AI 角色 |

---

### 4.18 图片识别 (image_recognizer.py)

**文件**: [backend/image_recognizer.py](file:///d:/yuyan/Soft-Ripe%20Timezone/backend/image_recognizer.py)

**职责**: 多方案图片内容识别，优雅降级。

**识别流程**:
1. 检测本地视觉模型 (`VISION_MODEL_INSTANCE`) → 若加载则使用（Qwen3-VL，GPU推理后移回CPU）
2. 检测 API 视觉能力（关键词匹配：gpt-4o/gpt-4-turbo/vision/vl 等）
3. API 视觉识别 → 失败则尝试本地模型
4. 全部失败 → 返回 `VISION_UNAVAILABLE_HINT`，让 AI 自然告知用户看不到图片

**本地视觉模型配置**: 支持 Qwen3-VL-2B/4B/8B，4bit 量化加载到 CPU 内存，推理时瞬移 GPU。

---

### 4.19 URL 抓取 (url_fetcher.py)

**文件**: [backend/url_fetcher.py](file:///d:/yuyan/Soft-Ripe%20Timezone/backend/url_fetcher.py)

**职责**: 提取用户消息中的 URL 并抓取网页内容。

**核心函数**:

| 名称 | 说明 |
|---|---|
| `extract_urls(text)` | 正则提取所有 URL |
| `fetch_and_extract_text(url)` | 抓取网页并提取正文（优先级：article > main > .main-content > #content > body） |
| `process_urls_in_message(message)` | 处理消息中的 URL（最多 3 个），返回抓取结果 |

---

### 4.20 工具函数 (utils_json.py / utils_time.py)

**文件**: [backend/utils_json.py](file:///d:/yuyan/Soft-Ripe%20Timezone/backend/utils_json.py) / [backend/utils_time.py](file:///d:/yuyan/Soft-Ripe%20Timezone/backend/utils_time.py)

**utils_json.py**: LLM JSON 容错解析

| 函数 | 说明 |
|---|---|
| `parse_llm_json(raw)` | 4 层容错解析：直接解析 → 正则提取 → 修复尾随逗号/引号 → 激进修复 |
| `_repair_llm_json(text)` | 修复尾随逗号、单引号问题 |
| `_aggressive_repair_json(text)` | 状态机修复：处理注释、换行、引号 |

**utils_time.py**: 时间和天气工具（LLM 函数调用）

| 函数 | 说明 |
|---|---|
| `get_current_time(timezone)` | 获取指定时区的当前时间 |
| `get_time_context()` | 获取完整/紧凑版时间上下文（含时段描述、睡眠警告） |
| `get_weather(city)` | 查询城市天气（wttr.in API） |
| `execute_tool(name, args)` | 工具调用分发 |

---

### 4.21 微信连接模块 (wechat/)

**目录**: [backend/wechat/](file:///d:/yuyan/Soft-Ripe%20Timezone/backend/wechat/)

**职责**: 将 AI 伴侣绑定到微信账号，通过微信进行消息收发。

| 文件 | 说明 |
|---|---|
| `__init__.py` | 模块入口：初始化、获取二维码、扫码轮询、凭证管理 |
| `ilink_client.py` | iLink 异步 HTTP 客户端（微信连接协议） |
| `ilink_types.py` | iLink 数据类型定义（Pydantic 模型） |
| `adapter.py` | iLink 协议适配器（消息编解码、心跳、重连） |
| `auth.py` | 微信扫码认证 |
| `bot_state.py` | 机器人状态管理（绑定关系、当前人设） |
| `monitor.py` | 消息监控（持续监听用户消息并转发给 AI） |
| `wechat_proactive.py` | 微信主动消息（通过定时任务发送主动消息） |
| `cdma.py` | CDN 媒体上传下载（处理图片/文件的传输加密） |
| `media.py` | 媒体消息处理 |

---

### 4.22 AI 人设 JSON 配置 (personas/)

**目录**: [backend/personas/](file:///d:/yuyan/Soft-Ripe%20Timezone/backend/personas/)

9 种人设的完整 JSON 配置，结构如下：

```json
{
  "persona_id": "sunny",
  "name": "阳光学妹",
  "type": "安全型",
  "age": "20岁",
  "avatar": "/avatars/sunny.jpg",
  "bio": "...",
  "core": "角色核心身份提示词 (Markdown)",
  "ground_truths": ["核心事实列表（不可违背的设定）"],
  "appearance": "外貌描述",
  "speech_patterns": "说话风格指南",
  "first_mes": "首次见面问候语",
  "mes_example": [{"user": "...", "char": "..."}],
  "entries": [
    {
      "id": "sunny_childhood",
      "title": "西湖边的童年",
      "priority": 90,
      "enabled": true,
      "keys": ["关键词列表", "/正则匹配/"],
      "content": "Lorebook 条目内容..."
    }
  ]
}
```

---

### 4.23 前端 (frontend/)

**目录**: [frontend/](file:///d:/yuyan/Soft-Ripe%20Timezone/frontend/)

**技术栈**: Vue 3 + Vite + vue-advanced-chat

**文件**:

| 文件 | 说明 |
|---|---|
| `src/App.vue` | 单页应用主组件（~2000+ 行）：登录/注册、聊天界面、人设选择、设置面板、记忆面板、关系仪表盘 |
| `src/main.js` | Vue 应用入口 |
| `index.html` | HTML 模板 |
| `vite.config.js` | Vite 构建配置 |
| `package.json` | 前端依赖 |

---

## 5. 数据流详解

### 用户发送消息的完整流程

```
1. 用户输入消息 → POST /api/chat
2. authenticate → 验证 Bearer Token
3. rate limit check → 每分钟最多 8 次
4. get_or_create_agent → 获取/创建 Agent
5. 获取 MemU / Emotion / ProactiveEngine 实例
6. 记录用户活跃 → routine_learner.record_activity()
7. 保存用户消息到 SQLite
8. 图片识别 (有图时):
   └─ API 视觉识别 → 失败 → 本地视觉模型 → 失败 → 降级提示
9. URL 抓取 (有链接时):
   └─ 提取 URL → 抓取网页 → 提取正文
10. 分手检测:
    ├─ handle_restart: 冷却期结束 → 重启关系
    ├─ is_in_cooling: 冷却中 → 返回冷却回复
    └─ detect_breakup_intent: 检测到分手意图 → 触发分手流程
11. 里程碑检测 + 情感更新 (analyze_message_quality + get_event_delta)
12. 忙闲检查:
    ├─ generate_busy_reply: 忙碌中 → 返回忙碌回复
    └─ try_enter_busy: 概率进入忙碌
13. 纪念日检查
14. 时间上下文 + 表情注入
15. 调用 LLM 内心独白:
    └─ 构建独白 prompt → 调用 LLM → 解析 JSON → 校准
16. 用户评价更新
17. 审讯检测:
    └─ 连续提问不分享 → 降低好感 + 注入审问警告
18. 日常生活上下文:
    └─ check_activity_change → get_disclosure_guidance
19. 调用 LLM 生成回复:
    └─ 构建完整回复 prompt → 调用 LLM → 处理工具调用(天气/时间)
20. 表情解析 → 替换 <emoji:xxx> 为实际 URL
21. 分段处理 → 计算发送延迟
22. 保存 AI 回复到 SQLite + Recall Buffer
23. 记忆系统更新: add_exchange → 情节记忆
24. 情感系统保存: 三角值同步 + 阶段推进
25. 返回: AI 回复 + 分段 + 延迟 + 关系状态 + 记忆状态
```

### 主动消息轮询流程

```
1. 前端定时轮询 GET /api/check-proactive
2. 检查冷却期（分手）
3. 检查 Pending Proactive 队列
4. ProactiveMessageEngine 检查:
   ├─ 每日限额
   ├─ 冷却时间 (≥2h)
   ├─ 情绪阻挡 (生气/难过时不发)
   ├─ 夜间阻挡 (3-7点不发)
   ├─ 早安触发
   ├─ 晚安触发
   ├─ 深夜触发
   ├─ 想念触发 (思念值 > 阈值 + LLM 确认)
   └─ 话题延续触发
5. 触发 → 调用 LLM 生成主动消息
6. 返回主动消息给前端
```

---

## 6. 关键类与函数速查

### 核心类

| 类名 | 模块 | 职责 |
|---|---|---|
| `EmotionSystem` | `emotion_system` | 三维情感状态管理 |
| `ConflictEngine` | `emotion_system` | 争吵周期管理 |
| `MemUMemorySystem` | `memu_system` | 三维长期记忆 |
| `ProactiveMessageEngine` | `proactive_engine` | 主动消息触发 |
| `NeedStateEngine` | `proactive_engine` | 内在需求衰减管理 |
| `UserEvaluationStore` | `reply_engine` | 用户评价系统 |
| `MonologueStore` | `reply_engine` | 内心独白历史 |
| `RoutineLearner` | `routine_learner` | 用户习惯学习 |
| `AIDailyLife` | `ai_daily_life` | AI 日常生活 |
| `AIBusyManager` | `ai_busy` | 忙闲状态 |
| `AnniversaryChecker` | `anniversary` | 纪念日管理 |
| `BreakupManager` | `breakup_manager` | 分手管理 |
| `NeedStateEngine` | `proactive_engine` | 需求状态引擎 |

### 核心函数

| 函数 | 模块 | 职责 |
|---|---|---|
| `call_internal_monologue()` | `reply_engine` | 生成 AI 内心独白 |
| `call_external_reply()` | `reply_engine` | 生成 AI 对外回复 |
| `calibrate_monologue()` | `reply_engine` | 校准独白结果 |
| `analyze_message_quality()` | `emotion_system` | 分析消息类型 |
| `get_event_delta()` | `emotion_system` | 计算事件情感影响 |
| `detect_interrogation_pattern()` | `emotion_system` | 检测审讯模式 |
| `resolve_lorebook()` | `persona_engine` | Lorebook 注入 |
| `get_persona_core()` | `persona_engine` | 构建身份提示词 |
| `parse_llm_json()` | `utils_json` | 容错 JSON 解析 |
| `get_time_context()` | `utils_time` | 时间上下文 |

---

## 7. 依赖清单

### 后端 (Python)

| 包 | 版本 | 用途 |
|---|---|---|
| `fastapi` | >=0.115 | Web 框架 |
| `python-multipart` | >=0.0.9 | 文件上传 |
| `uvicorn` | 0.30.0 | ASGI 服务器 |
| `openai` | 1.109.1 | LLM API 调用 |
| `pydantic` | 2.13.4 | 数据验证 |
| `beautifulsoup4` | >=4.12 | HTML 解析 |
| `lxml` | >=5.1 | XML/HTML 解析 |
| `requests` | >=2.31 | HTTP 请求 |
| `Pillow` | >=10.0 | 图片处理 |
| `sentence-transformers` | >=3.0 | 本地文本嵌入 |
| `torch` | >=2.1 | 深度学习框架 |
| `transformers` | >=4.44 | 视觉模型加载 |
| `huggingface-hub` | >=0.24 | 模型下载 |
| `bitsandbytes` | >=0.43 | 4bit 量化 |
| `httpx` | >=0.27 | 异步 HTTP (微信模块) |
| `pycryptodome` | >=3.20 | 加密 (微信模块) |

### 前端 (Node.js)

| 包 | 用途 |
|---|---|
| `vue` | 前端框架 |
| `vite` | 构建工具 |
| `vue-advanced-chat` | 聊天 UI 组件 |

---

## 8. 项目运行方式

### 环境要求

| 依赖 | 版本 |
|---|---|
| Python | 3.10+ |
| Node.js | 16+ |
| npm | 随 Node.js |
| API Key | OpenAI 兼容 API |

### 一键启动

**Windows**: 双击 `start.bat`，自动完成：环境检查 → 安装依赖 → 构建前端 → 启动后端 → 打开浏览器

**Linux**: 运行 `bash start.sh`，同上

### 手动启动

```bash
# 1. 后端
cd backend
pip install -r requirements.txt
python main.py

# 2. 前端（新开终端）
cd frontend
npm install
npm run dev
```

### 访问

- 访问 `http://localhost:5173`（前端开发服务器）
- 或 `http://localhost:8765`（后端直接服务静态文件）

### 配置 API Key

首次启动后，在 UI 设置面板中配置：
- **API Key**: OpenAI 或其他兼容 API 密钥
- **Base URL**: API 端点地址（可更换为 DeepSeek / Qwen / Ollama 等）
- **Model**: 模型名称（如 `gpt-4o-mini`、`deepseek-chat`）

### 管理员账号

默认管理员：`admin888`（首次需注册，密码自设）

---

*本文档由 AI 自动生成，基于对项目源码的全面分析。*