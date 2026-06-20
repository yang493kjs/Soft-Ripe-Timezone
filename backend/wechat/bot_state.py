# -*- coding: utf-8 -*-
"""机器人状态管理

管理每个机器人归属的用户及当前激活的角色。
采用双文件协同持久化策略（需求文档 4.7 节）：
- 凭证文件（auth.py 管理）：存 bot_id, user_id 等登录凭证
- bot_state 文件（本模块管理）：存 bot_id → user_id 映射 + current_persona 等运行时状态

存储路径：~/.soft_ripe_timezone/wechat_bot_state.json
"""
import os
import json
import logging
import threading
from datetime import datetime
from typing import Optional, Dict, List

logger = logging.getLogger("soft_ripe.wechat.bot_state")

DEFAULT_PERSONA = "sunny"


class BotState:
    """单个机器人的状态"""

    def __init__(
        self,
        bot_id: str,
        user_id: str,
        current_persona: str = DEFAULT_PERSONA,
        default_persona: str = DEFAULT_PERSONA,
        created_at: str = "",
    ):
        self.bot_id = bot_id
        self.user_id = user_id
        self.current_persona = current_persona
        self.default_persona = default_persona
        self.created_at = created_at or datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "current_persona": self.current_persona,
            "default_persona": self.default_persona,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, bot_id: str, d: dict) -> "BotState":
        return cls(
            bot_id=bot_id,
            user_id=d.get("user_id", ""),
            current_persona=d.get("current_persona", DEFAULT_PERSONA),
            default_persona=d.get("default_persona", DEFAULT_PERSONA),
            created_at=d.get("created_at", ""),
        )


class BotStateManager:
    """
    机器人状态管理器（单例）

    线程安全，内存中维护所有机器人状态，变更时立即持久化到文件。
    """

    _instance: Optional["BotStateManager"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "BotStateManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._states: Dict[str, BotState] = {}
        self._file_lock = threading.Lock()
        self._state_file = self._get_state_file_path()

    def _get_state_file_path(self) -> str:
        return os.path.join(
            os.path.expanduser("~"),
            ".soft_ripe_timezone",
            "wechat_bot_state.json",
        )

    # ==================== 持久化 ====================

    def load(self) -> None:
        """
        从文件加载状态

        启动时调用。若文件不存在或损坏，状态为空（由上层从凭证文件重建）。
        """
        with self._file_lock:
            if not os.path.exists(self._state_file):
                logger.info("bot_state 文件不存在，将在注册时创建")
                return
            try:
                with open(self._state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._states = {
                    bot_id: BotState.from_dict(bot_id, state)
                    for bot_id, state in data.items()
                }
                logger.info(f"已加载 {len(self._states)} 个机器人状态")
            except Exception as e:
                logger.error(f"加载 bot_state 失败: {e}，将使用空状态")
                self._states = {}

    def persist(self) -> None:
        """将内存中的状态写入文件"""
        with self._file_lock:
            dir_path = os.path.dirname(self._state_file)
            os.makedirs(dir_path, mode=0o700, exist_ok=True)
            data = {
                bot_id: state.to_dict()
                for bot_id, state in self._states.items()
            }
            with open(self._state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    # ==================== 状态操作 ====================

    def register_bot(self, bot_id: str, user_id: str, default_persona: str = DEFAULT_PERSONA) -> BotState:
        """
        注册新机器人

        Args:
            bot_id: 机器人 ID
            user_id: 归属的系统用户 ID
            default_persona: 默认角色

        Returns:
            创建的 BotState
        """
        state = BotState(
            bot_id=bot_id,
            user_id=user_id,
            current_persona=default_persona,
            default_persona=default_persona,
        )
        self._states[bot_id] = state
        self.persist()
        logger.info(f"已注册机器人 {bot_id} → 用户 {user_id}")
        return state

    def unregister_bot(self, bot_id: str) -> bool:
        """删除机器人状态"""
        if bot_id in self._states:
            del self._states[bot_id]
            self.persist()
            logger.info(f"已注销机器人 {bot_id}")
            return True
        return False

    def get_user_id(self, bot_id: str) -> Optional[str]:
        """获取机器人归属的用户 ID"""
        state = self._states.get(bot_id)
        return state.user_id if state else None

    def get_current_persona(self, bot_id: str) -> str:
        """获取当前激活角色，不存在则返回默认值"""
        state = self._states.get(bot_id)
        if state:
            return state.current_persona
        return DEFAULT_PERSONA

    def set_current_persona(self, bot_id: str, persona_id: str) -> bool:
        """
        切换角色

        先更新内存状态，再写入文件，保证一致性。
        """
        state = self._states.get(bot_id)
        if not state:
            logger.warning(f"机器人 {bot_id} 不存在，无法切换角色")
            return False
        state.current_persona = persona_id
        self.persist()
        logger.info(f"机器人 {bot_id} 角色切换为 {persona_id}")
        return True

    def get_all_personas(self, user_id: str) -> List[str]:
        """
        获取该用户的所有角色 ID

        当前直接返回 settings.PERSONAS 的所有 key。
        未来可扩展为只返回该用户创建过的角色。
        """
        try:
            from settings import PERSONAS
            return list(PERSONAS.keys())
        except ImportError:
            return [DEFAULT_PERSONA]

    def get_bot_by_user(self, user_id: str) -> Optional[str]:
        """获取该用户绑定的机器人 ID（每个用户最多一个机器人）"""
        for bot_id, state in self._states.items():
            if state.user_id == user_id:
                return bot_id
        return None

    def get_all_bots(self) -> Dict[str, BotState]:
        """获取所有机器人状态（管理员用）"""
        return dict(self._states)

    def is_online(self, bot_id: str) -> bool:
        """检查机器人是否在线（凭证是否存在）"""
        from .auth import load_credentials
        creds = load_credentials(bot_id)
        return creds is not None and bool(creds.bot_token)


# 全局单例
def get_bot_state_manager() -> BotStateManager:
    return BotStateManager()
