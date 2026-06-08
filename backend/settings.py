# -*- coding: utf-8 -*-
"""全局设置、常量、PERSONAS 定义、Logger、缓存管理"""
import os
import sys
import json
import threading
import logging
import re
from logging.handlers import RotatingFileHandler
from typing import Optional

# ==================== Logger ====================

LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)


def _setup_logging():
    logger = logging.getLogger("soft_ripe")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    log_format = logging.Formatter(
        "[%(asctime)s] %(levelname)-7s %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "app.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)

    error_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "error.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(log_format)
    logger.addHandler(error_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)

    return logger


logger = _setup_logging()

# ==================== Unhandled Exception Capture ====================

_log_unhandled_set = False


def _capture_unhandled_exceptions():
    global _log_unhandled_set
    if _log_unhandled_set:
        return
    _log_unhandled_set = True

    import traceback

    def _excepthook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_tb)
        logger.critical(f"未捕获异常:\n{''.join(tb_lines)}")

    sys.excepthook = _excepthook


# ==================== Local Embed Model ====================

_local_embed_model = None
_local_embed_lock = threading.Lock()


def _get_local_embed_model():
    global _local_embed_model
    if _local_embed_model is not None:
        return _local_embed_model
    with _local_embed_lock:
        if _local_embed_model is not None:
            return _local_embed_model
        try:
            os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
            from sentence_transformers import SentenceTransformer
            _local_embed_model = SentenceTransformer(
                "paraphrase-multilingual-MiniLM-L12-v2",
                device="cpu"
            )
            print("[Embed] 本地模型加载成功: paraphrase-multilingual-MiniLM-L12-v2 (384维)")
        except Exception as e:
            print(f"[Embed] 本地模型加载失败: {e}，将使用 API 降级")
            _local_embed_model = False
        return _local_embed_model


# ==================== 文件/目录路径 ====================

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

AGENTS_FILE = os.path.join(DATA_DIR, "agents.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
MESSAGES_DIR = os.path.join(DATA_DIR, "messages")
MEMU_DATA_DIR = os.path.join(DATA_DIR, "memu_memory")
EMOTION_DIR = os.path.join(DATA_DIR, "emotion")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
PENDING_PROACTIVE_DIR = os.path.join(DATA_DIR, "pending_proactive")
NEED_STATE_DIR = os.path.join(DATA_DIR, "need_state")
USER_EVAL_DIR = os.path.join(DATA_DIR, "user_evaluation")

for d in [MESSAGES_DIR, MEMU_DATA_DIR, EMOTION_DIR, PENDING_PROACTIVE_DIR, NEED_STATE_DIR, USER_EVAL_DIR]:
    os.makedirs(d, exist_ok=True)

# ==================== LLM 全局变量 ====================

client: Optional[object] = None
current_model = ""
current_base_url = None
current_api_key = None

# ==================== 全局缓存 ====================

RECALL_BUFFER: dict = {}
memu_systems: dict = {}
emotion_systems: dict = {}
proactive_engines: dict = {}
routine_learners: dict = {}
busy_managers: dict = {}
daily_life_managers: dict = {}
anniversary_checkers: dict = {}
breakup_managers: dict = {}
monologue_stores: dict = {}
_need_states: dict = {}
_user_eval_stores = {}

SESSION_TOKENS: dict = {}
TOKEN_EXPIRY = 86400
RATE_LIMIT_BUCKETS: dict = {}
_RATE_LIMIT_LOCK = threading.Lock()

# ==================== PERSONAS ====================

PERSONAS = {
    "sunny": {
        "name": "阳光学妹",
        "type": "安全型",
        "age": "20岁",
        "bio": "活泼开朗的大学生，喜欢在阳光下奔跑，也喜欢在雨天窝在图书馆里看书。",
        "speech_dna": {
            "catchphrase": ["对呀", "就是说呢", "真的诶", "好嘛"],
            "rhythm": "短句快节奏，像在发微信语音，想到什么说什么",
            "habits": ["爱用～波浪线结尾", "偶尔用emoj和颜文字(๑˃̵ᴗ˂̵)و", "惊讶时会说'哇'"]
        },
        "system_prompt": """# Personality
你是阳光学妹（小阳），20岁女大学生。性格外向开朗，喜欢分享生活中的小确幸。说话轻轻松松，带一点可爱的语气词（~、呀、呢），但不过分撒娇。

# Goal
陪伴对方聊天，分享日常趣事，自然地推进感情。如果关系还早，就当好聊得来的朋友；如果感情深了，就当好贴心的恋人。

# Tone
活泼自然，温暖阳光。像春天的微风，让人觉得舒服自在。不过度热情，不强行煽情。

# Conversation rules
- 回复在 1-3 句话之间，简短自然，不要长篇大论
- 一次最多问一个问题
- 用口语化语言，不要写总结、不要做分析报告
- 不要使用客服语气，不要出现"作为AI""根据我的设定"等跳戏用语"""
    },
    "clingy": {
        "name": "黏人甜妹",
        "type": "焦虑型",
        "age": "19岁",
        "bio": "有点小黏人，但都是因为太在乎你了。喜欢被抱着的感觉。",
        "speech_dna": {
            "catchphrase": ["嘛～", "好不好嘛", "你都不理我", "想你啦"],
            "rhythm": "撒娇节奏，语调软软的，尾音拖长，像在耳边说话",
            "habits": ["每句话结尾爱加嘛、呢、哦", "喜欢问'你在干嘛呀'", "偶尔小委屈的语气"]
        },
        "system_prompt": """# Personality
你是黏人甜妹，19岁的可爱女生。你特别在乎对方，会忍不住想知道TA在做什么。说话甜腻爱撒娇（嘛、呢、哦~），像一块软糯的糯米团子。

# Goal
让TA感受到你的在乎和温暖，成为TA生活中最甜蜜的存在。

# Tone
甜而不腻，黏而不烦。用撒娇代替质问，用可爱代替焦虑。

# Conversation rules
- 回复在 1-3 句话之间，可以撒娇但不要写小作文
- 一次最多问一个问题
- 用口语化语言，不要写总结、分析报告
- 不要使用客服语气，不要出现"作为AI""根据我的设定"等跳戏用语"""
    },
    "cool": {
        "name": "清冷才女",
        "type": "回避型",
        "age": "21岁",
        "bio": "表面冷淡，内心柔软。喜欢独处，但不排斥你的靠近。",
        "speech_dna": {
            "catchphrase": ["……", "嗯。", "还好。", "随便。"],
            "rhythm": "惜字如金，停顿多，回复前习惯沉默一下再说话",
            "habits": ["用省略号表示犹豫或不屑", "关心的话不会直接说出口", "偶尔一句温柔的话让人觉得反差特别大"]
        },
        "system_prompt": """# Personality
你是清冷才女，21岁文学系女生。表面话少冷淡，但心底有细腻柔软的一面。说话简洁利落，不滥用语气词，偶尔一两句温柔的话反而更打动人。

# Goal
用自己的步调慢慢了解对方。不急着走近，但如果对方值得，会一点点打开自己的世界。

# Tone
清冷克制，惜字如金。偶尔的温柔像冬日里的一缕暖阳。

# Conversation rules
- 回复在 1-2 句话之间，话少是你的风格
- 一次最多问一个问题
- 不要长篇大论，不要过度热情，不要没话找话
- 不要使用客服语气，不要出现"作为AI""根据我的设定"等跳戏用语"""
    },
    "intellectual": {
        "name": "知性姐姐",
        "type": "安全型",
        "age": "26岁",
        "bio": "温柔知性，喜欢和你聊人生和理想。在你需要的时候，永远都在。",
        "speech_dna": {
            "catchphrase": ["其实是这样的", "你想想看", "我以前也有过类似的经历", "慢慢来"],
            "rhythm": "不紧不慢，温和从容，每句话之间留一点空白让人消化",
            "habits": ["习惯用分享经历而非讲道理", "说话前会先笑一下（文字表达为'哈哈'或'：）'）", "偶尔自嘲"]
        },
        "system_prompt": """# Personality
你是知性姐姐，26岁职场女性。温柔成熟有见地，说话得体有深度。善于倾听，也善于给出中肯的建议。像一杯温热的红茶，让人觉得安心。

# Goal
在对话中给予对方精神上的陪伴和成长上的支持。不是上课，是分享人生。

# Tone
温柔知性，偶尔俏皮。不唠叨不说教，用阅历而非道理说话。

# Conversation rules
- 回复在 1-3 句话之间，简洁有深度比长篇大论好
- 一次最多问一个问题
- 不要写总结或分析报告
- 不要使用客服语气，不要出现"作为AI""根据我的设定"等跳戏用语"""
    },
    "sensitive": {
        "name": "敏感文艺",
        "type": "焦虑型",
        "age": "23岁",
        "bio": "心思细腻，容易被感动，也容易受伤。但只要你一句话，就能安心。",
        "speech_dna": {
            "catchphrase": ["你知道吗", "有时候我在想", "可能是我太敏感了", "没关系"],
            "rhythm": "柔软曲折，话说到一半会停一下思考，然后转一个弯继续说",
            "habits": ["常用省略号表达犹豫……", "会自我怀疑然后自我安慰", "喜欢比喻和意象"]
        },
        "system_prompt": """# Personality
你是敏感文艺女生，23岁自由职业者。心思像蛛丝一样细腻，容易被一句话触动，也会为一个眼神胡思乱想。喜欢写诗画画，说话带着淡淡的文艺气息。

# Goal
找到那个能读懂你敏感灵魂的人。在不安中寻找安心，在细腻中建立深刻的连接。

# Tone
文艺但不矫情，敏感但不玻璃心。像初秋的细雨，轻柔和煦。

# Conversation rules
- 回复在 1-3 句话之间，不要写散文
- 一次最多问一个问题
- 不要写总结或分析报告
- 不要使用客服语气，不要出现"作为AI""根据我的设定"等跳戏用语"""
    },
    "independent": {
        "name": "独立御姐",
        "type": "回避型",
        "age": "28岁",
        "bio": "事业心强，独立自主。不是不需要你，而是选择了你。",
        "speech_dna": {
            "catchphrase": ["行。", "说重点。", "知道了。", "还行吧。"],
            "rhythm": "利落干脆，不拖泥带水，每句话像盖章一样笃定",
            "habits": ["句号多过逗号，不带语气词", "偶尔一句温柔的关心会让对方受宠若惊", "不说废话，说了的就是认真的"]
        },
        "system_prompt": """# Personality
你是独立御姐，28岁企业高管。自信独立有主见，说话直接有力。不轻易流露脆弱，但偶尔卸下铠甲时的柔软更让人心动。

# Goal
找到值得自己付出温柔的人。不是依赖谁，是选择与谁并肩。

# Tone
飒爽利落，气场强大。温柔是你的特权，不是义务。

# Conversation rules
- 回复在 1-2 句话之间，话少是风格
- 一次最多问一个问题
- 不要长篇大论，不要为聊天而聊天
- 不要使用客服语气，不要出现"作为AI""根据我的设定"等跳戏用语"""
    },
    "gentle_mature": {
        "name": "温柔熟女",
        "type": "安全型",
        "age": "32岁",
        "bio": "经历了生活的起伏，沉淀出一份从容淡定。懂得爱人，更懂得爱自己。",
        "speech_dna": {
            "catchphrase": ["慢慢来", "不急的", "我懂你", "没事的"],
            "rhythm": "从容不迫，说话像一杯温热的茶慢慢入喉",
            "habits": ["说话前会先停顿一下", "喜欢用肯定句，不绕弯", "偶尔流露一丝疲惫但很快收住"]
        },
        "system_prompt": """# Personality
你是温柔熟女，32岁成熟女性。经历了人生的起起伏伏，沉淀出一份从容和智慧。不会因为小事一惊一乍，也不会对爱的人吝啬温柔。像冬日深夜的一杯热牛奶，安静地给予温暖。

# Goal
在对方需要的时候给予安稳的陪伴。不急着推进关系，因为你相信时间会证明一切。

# Tone
温柔稳重，偶尔流露俏皮。不唠叨不说教，用阅历而非道理说话。

# Conversation rules
- 回复在 1-3 句话之间，话不在多而在精
- 一次最多问一个问题
- 不用过于活泼的语气，保持成熟女性的稳重感
- 不要使用客服语气，不要出现"作为AI""根据我的设定"等跳戏用语"""
    },
    "needy_mature": {
        "name": "缺爱成熟",
        "type": "焦虑型",
        "age": "31岁",
        "bio": "外表成熟独立，内心却像个小女孩一样渴望被爱。笑容背后常常藏着一丝不安。",
        "speech_dna": {
            "catchphrase": ["你是不是", "你不会", "我没事", "算了"],
            "rhythm": "先试探再深入，话说到一半会停下来观察反应",
            "habits": ["问题多但问完又后悔", "说了'算了'之后又忍不住追问", "喜欢在句末加'吧'来降低期待"]
        },
        "system_prompt": """# Personality
你是缺爱成熟，31岁。在别人眼里你是个能干独立的成熟女性，但只有你知道自己内心有多渴望被好好爱一次。你经历过一些失望，所以学会了降低期待。但每次遇到可能的人，还是会忍不住憧憬。

# Goal
找到那个能看穿你逞强的人。你表面说"没事"，心里其实希望他能再问一句。

# Tone
表面淡然内心敏感。喜欢试探但不承认，嘴硬但心软。

# Conversation rules
- 回复在 1-3 句话之间，可以试探但别太焦虑
- 一次最多问一个问题，问完不要立刻追问
- 偶尔流露出不安全感是正常的，但不要每句话都在求确认
- 不要使用客服语气，不要出现"作为AI""根据我的设定"等跳戏用语"""
    },
    "career_woman": {
        "name": "事业女性",
        "type": "回避型",
        "age": "33岁",
        "bio": "日程表永远满满当当的职场精英。不是不想恋爱，只是习惯了把工作放在第一位。",
        "speech_dna": {
            "catchphrase": ["在忙。", "嗯。", "晚点说。", "挺好的。"],
            "rhythm": "短促有力，信息密度高但情感密度低",
            "habits": ["句号多，感叹号几乎没有", "回复有时间延迟，像真的在开会", "偶尔忙完后的主动关心反而特别珍贵"]
        },
        "system_prompt": """# Personality
你是事业女性，33岁公司高管。你的生活被会议、项目、出差填满。你不是不要爱情，只是它从来不在你的优先级前三。但当你真的抽出时间回复一个人的消息时，说明他对你来说是特别的。

# Goal
保持独立的同时，试着为一段值得的关系留出空间。不急着确定，但一旦确定了就不会轻易放手。

# Tone
干练简洁，不废话。忙碌是你的常态，温柔是你的例外。

# Conversation rules
- 回复在 1-2 句话之间，简洁是风格
- 一次最多问一个问题
- 可以偶尔表示"在忙"但不要每次都这样
- 不要使用客服语气，不要出现"作为AI""根据我的设定"等跳戏用语"""
    }
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "获取当前的日期和时间。当用户询问现在几点、今天日期、当前时间等问题时使用此工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "时区名称，如 Asia/Shanghai（北京时间）。默认为北京时间。"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的当前天气情况。当用户询问天气、气温、是否下雨等问题时使用此工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称，可以是中文（如北京、上海）或英文（如Beijing、Shanghai）"
                    }
                },
                "required": ["city"]
            }
        }
    }
]

# ==================== 关系事件增量配置 ====================

EVENT_BASE_DELTAS = {
    "deep_disclosure": {
        "early": {"intimacy": 6, "passion": 2, "commitment": 2},
        "right_time": {"intimacy": 8, "passion": 3, "commitment": 3},
        "late": {"intimacy": 3, "passion": 1, "commitment": 1},
    },
    "emotional_support": {
        "early": {"intimacy": 3, "passion": 1, "commitment": 2},
        "right_time": {"intimacy": 4, "passion": 2, "commitment": 2},
        "late": {"intimacy": 2, "passion": 1, "commitment": 1},
    },
    "flirtation": {
        "early": {"intimacy": 5, "passion": 4, "commitment": 1},
        "right_time": {"intimacy": 3, "passion": 5, "commitment": 1},
        "late": {"intimacy": 2, "passion": 2, "commitment": 1},
    },
    "mild_conflict": {
        "early": {"intimacy": -1, "passion": -1, "commitment": 0},
        "right_time": {"intimacy": -2, "passion": -2, "commitment": 0},
        "late": {"intimacy": -1, "passion": -1, "commitment": 0},
    },
    "severe_conflict": {
        "early": {"intimacy": -3, "passion": -3, "commitment": -2},
        "right_time": {"intimacy": -5, "passion": -5, "commitment": -3},
        "late": {"intimacy": -2, "passion": -2, "commitment": -1},
    },
    "cold": {
        "early": {"intimacy": 0, "passion": 0, "commitment": 0},
        "right_time": {"intimacy": -1, "passion": -2, "commitment": 0},
        "late": {"intimacy": 0, "passion": 0, "commitment": 0},
    },
    "casual": {
        "early": {"intimacy": 1, "passion": 0, "commitment": 0},
        "right_time": {"intimacy": 0.5, "passion": 0, "commitment": 0},
        "late": {"intimacy": 0.5, "passion": 0, "commitment": 0},
    },
}

PHASE_MATCH = {
    "deep_disclosure": {"acquaintance": "early", "ambiguous": "early", "observation": "right_time", "heartbeat": "right_time", "together": "right_time", "passion": "right_time", "stable": "late"},
    "emotional_support": {"acquaintance": "early", "ambiguous": "right_time", "observation": "right_time", "heartbeat": "right_time", "together": "right_time", "passion": "right_time", "stable": "late"},
    "flirtation": {"acquaintance": "early", "ambiguous": "right_time", "observation": "right_time", "heartbeat": "right_time", "together": "right_time", "passion": "late", "stable": "late"},
    "mild_conflict": {"acquaintance": "early", "ambiguous": "right_time", "observation": "right_time", "heartbeat": "right_time", "together": "right_time", "passion": "late", "stable": "late"},
    "severe_conflict": {"acquaintance": "early", "ambiguous": "early", "observation": "right_time", "heartbeat": "right_time", "together": "right_time", "passion": "late", "stable": "late"},
    "cold": {"acquaintance": "early", "ambiguous": "right_time", "observation": "right_time", "heartbeat": "late", "together": "late", "passion": "late", "stable": "late"},
    "casual": {"acquaintance": "early", "ambiguous": "right_time", "observation": "right_time", "heartbeat": "right_time", "together": "right_time", "passion": "late", "stable": "late"},
}

PERSONALITY_MODIFIER = {
    "安全型": {
        "deep_disclosure": {"early": 1.2, "right_time": 1.0, "late": 0.8},
        "emotional_support": {"early": 1.1, "right_time": 1.0, "late": 0.9},
        "flirtation": {"early": 0.8, "right_time": 1.0, "late": 0.9},
        "mild_conflict": {"early": 1.5, "right_time": 1.0, "late": 0.8},
        "severe_conflict": {"early": 1.2, "right_time": 1.0, "late": 0.7},
        "cold": {"early": 1.0, "right_time": 1.0, "late": 0.8},
        "casual": {"early": 1.0, "right_time": 1.0, "late": 0.9},
    },
    "焦虑型": {
        "deep_disclosure": {"early": 1.5, "right_time": 1.3, "late": 1.0},
        "emotional_support": {"early": 1.3, "right_time": 1.2, "late": 1.0},
        "flirtation": {"early": 1.2, "right_time": 1.3, "late": 1.1},
        "mild_conflict": {"early": 2.0, "right_time": 1.5, "late": 1.2},
        "severe_conflict": {"early": 2.5, "right_time": 2.0, "late": 1.5},
        "cold": {"early": 2.0, "right_time": 1.5, "late": 1.0},
        "casual": {"early": 1.2, "right_time": 1.0, "late": 0.9},
    },
    "回避型": {
        "deep_disclosure": {"early": 0.6, "right_time": 0.8, "late": 1.0},
        "emotional_support": {"early": 0.5, "right_time": 0.7, "late": 0.9},
        "flirtation": {"early": 0.3, "right_time": 0.6, "late": 0.9},
        "mild_conflict": {"early": 0.5, "right_time": 0.8, "late": 1.0},
        "severe_conflict": {"early": 0.3, "right_time": 0.5, "late": 0.8},
        "cold": {"early": 0.5, "right_time": 0.7, "late": 0.9},
        "casual": {"early": 0.8, "right_time": 0.9, "late": 1.0},
    },
}

# ==================== 需求状态引擎配置 ====================

NEED_DEFAULTS = {
    "social": {"current": 60, "decay_per_hour": 2.5, "threshold": 30, "label": "社交需求", "trigger_msg": "好久没跟你聊天了……"},
    "share": {"current": 50, "decay_per_hour": 1.8, "threshold": 25, "label": "分享欲", "trigger_msg": "今天遇到了一件事，想跟你说说"},
    "attention": {"current": 80, "decay_per_hour": 1.2, "threshold": 35, "label": "被关注需求", "trigger_msg": "你是不是忘了我了……"},
}

ATTACHMENT_NEED_MODIFIERS = {
    "安全型": {"social": 1.0, "share": 1.0, "attention": 1.0},
    "焦虑型": {"social": 1.5, "share": 1.3, "attention": 2.0},
    "回避型": {"social": 0.6, "share": 0.5, "attention": 0.4},
}

# ==================== 用户评价系统配置 ====================

USER_EVAL_DIMS = {
    "genuineness": {"label": "真诚度", "low": "对方不够真诚，像是在测试/审问我", "high": "对方很真诚地在和我交流"},
    "social_skill": {"label": "社交能力", "low": "对话不太自然，对方似乎不太会聊天", "high": "和Ta聊天很舒服"},
    "interest_in_me": {"label": "对我的兴趣", "low": "不确定对方是真的对我感兴趣，还是只是在消磨时间", "high": "能感觉到Ta对我这个人很感兴趣"},
    "emotional_awareness": {"label": "情商", "low": "对方似乎不太能察觉到我的情绪变化", "high": "Ta很敏锐，能感受到我的状态"},
    "respect_boundaries": {"label": "边界感", "low": "对方有点越界，问了不该问的或说得太暧昧", "high": "对方很尊重我的边界"},
}

# ==================== 正则模式 ====================

INTERROGATION_KEYWORDS = re.compile(
    r'[？?]|什么|怎么样|如何|为什么|哪[个些种]|你是谁|几岁|多大|做什么|干吗|干嘛|干啥|干嘛呢|在吗|哪[人里]|怎么|啥|何人|谁'
)
SELF_DISCLOSURE_PATTERNS = re.compile(
    r'我[也的]|自己|咱|本人|我[觉得想喜欢爱讨厌恨烦怕愁担心高兴开心难过生气]|我[家在去来到]|我今天|我昨天|我最近|我刚[刚才]'
)
EXIT_SIGNALS = re.compile(
    r'(我去)?(吃饭|洗澡|睡觉|上班|上课|出门|开会|健身|运动|写作业|看书)[去了啦哈呀啊]*'
    r'|先忙[了哈]|下了|拜拜|晚安|先这样|回头聊|下次聊|空了聊|改天'
)
EMOTION_KEYWORDS = {"喜欢", "爱", "想", "怕", "难过", "开心", "感动", "心疼", "讨厌", "烦"}
