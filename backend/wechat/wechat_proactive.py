# -*- coding: utf-8 -*-
"""微信主动消息推送

复用现有 ProactiveMessageEngine 的触发判断逻辑，
将生成的主动消息通过微信渠道发送给用户。

需求文档 4.6 节：主动消息推送机制
- 复用现有 ProactiveMessageEngine 判断是否应发送主动消息
- 通过微信机器人发送（而非 Web SSE）
- 每个机器人独立运行主动消息检查循环
"""
import asyncio
import logging
from typing import Optional, Dict
from datetime import datetime

from .ilink_types import Credentials
from .ilink_client import ILinkClient
from .bot_state import get_bot_state_manager
from .monitor import get_monitor_manager
from . import adapter as adapter_module

logger = logging.getLogger("soft_ripe.wechat.proactive")

# 主动消息检查间隔（秒）— 每 10 分钟检查一次
CHECK_INTERVAL = 600


class WeChatProactiveSender:
    """单个机器人的主动消息发送器"""

    def __init__(self, creds: Credentials):
        self.creds = creds
        self.bot_id = creds.ilink_bot_id
        self.bot_state = get_bot_state_manager()
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"机器人 {self.bot_id} 主动消息循环已启动")

    async def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info(f"机器人 {self.bot_id} 主动消息循环已停止")

    async def _run_loop(self) -> None:
        """主循环：周期性检查并触发主动消息"""
        # 启动后等待一段时间，避免与监控循环同时启动
        await asyncio.sleep(30)

        while self._running:
            try:
                await self._check_and_send()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"机器人 {self.bot_id} 主动消息检查失败: {e}", exc_info=True)

            await asyncio.sleep(CHECK_INTERVAL)

    async def _check_and_send(self) -> None:
        """
        检查是否应发送主动消息，若应发送则通过微信发送

        复用现有 ProactiveMessageEngine 的判断逻辑，
        但通过微信渠道发送（而非 Web SSE）。
        """
        user_id = self.bot_state.get_user_id(self.bot_id)
        if not user_id:
            return

        persona_id = self.bot_state.get_current_persona(self.bot_id)
        agent_id = f"{user_id}_{persona_id}"

        try:
            # 复用现有 ProactiveMessageEngine
            from proactive_engine import ProactiveMessageEngine
            from emotion_system import EmotionSystem
            from settings import PERSONAS
            from main import get_memu

            engine = ProactiveMessageEngine(agent_id, persona_id)
            emo = EmotionSystem(agent_id)
            rel = emo.relationship
            emotion = emo
            persona_name = PERSONAS.get(persona_id, {}).get("name", persona_id)

            # 尝试获取 memory engine（可选）
            memu = None
            try:
                memu = get_memu(agent_id, user_id)
            except Exception:
                pass

            # 判断是否应发送主动消息
            decision = engine.get_proactive_message(emotion, persona_name, memu)
            if not decision:
                return

            trigger_type = decision.get("trigger_type", "")
            logger.info(f"机器人 {self.bot_id} 触发主动消息: {trigger_type}")

            # 生成主动消息内容（复用现有逻辑）
            message_text = await self._generate_proactive_content(
                agent_id, persona_id, decision, emotion, persona_name, memu
            )
            if not message_text:
                return

            # 通过微信发送
            await self._send_proactive_via_wechat(user_id, message_text)

            # 记录已发送
            engine.record_proactive_sent()

        except ImportError as e:
            logger.error(f"导入主动消息引擎失败: {e}")
        except Exception as e:
            logger.error(f"主动消息处理失败: {e}", exc_info=True)

    async def _generate_proactive_content(
        self,
        agent_id: str,
        persona_id: str,
        decision: dict,
        emotion,
        persona_name: str,
        memu,
    ) -> Optional[str]:
        """
        生成主动消息内容

        复用现有 reply_engine 的主动消息生成逻辑。
        """
        try:
            from reply_engine import generate_proactive_message
            return generate_proactive_message(
                agent_id=agent_id,
                persona_id=persona_id,
                trigger_type=decision.get("trigger_type", ""),
                emotion=emotion,
                persona_name=persona_name,
                memory=memu,
                decision=decision,
            )
        except ImportError:
            # 回退：使用简单的模板
            trigger = decision.get("trigger_type", "")
            if trigger == "morning":
                return f"早安～今天也要好好开始哦"
            elif trigger == "night":
                return f"晚安～做个好梦"
            elif trigger == "missing":
                return f"好久没聊了，最近怎么样？"
            return None

    async def _send_proactive_via_wechat(self, user_id: str, message: str) -> None:
        """
        通过微信发送主动消息

        主动消息没有 context_token（非回复），需要直接发送。
        """
        # 获取该用户绑定的微信 openid
        # 注意：这里需要从用户绑定关系获取微信 user_id
        # 当前简化实现：从 bot_state 中获取该用户的机器人，再查询其最近活跃的微信对话方
        wechat_user_id = await self._get_wechat_user_id(user_id)
        if not wechat_user_id:
            logger.warning(f"用户 {user_id} 无微信绑定，无法发送主动消息")
            return

        # 复用 monitor 中的 client 发送
        monitor_mgr = get_monitor_manager()
        # 复用 monitor 中的 client 发送（避免重复创建 client）
        from .ilink_client import ILinkClient
        client = ILinkClient(self.creds)
        try:
            await client.send_text(wechat_user_id, message, context_token="")
            logger.info(f"主动消息已发送到微信 {wechat_user_id}: {message[:30]}...")
        finally:
            await client.close()

    async def _get_wechat_user_id(self, user_id: str) -> Optional[str]:
        """
        获取该系统用户对应的微信对话方 ID

        需求文档 4.6 节：每个用户绑定一个机器人，机器人与用户的微信账号对话。
        这里需要查询该机器人最近收到的消息的发送方。

        简化实现：从最近的消息记录中获取。
        完整实现应在 bot_state 中维护 bot_id → wechat_user_id 映射。
        """
        # TODO: 完整实现需要维护 bot_id → wechat_user_id 映射
        # 当前从 bot_state 扩展字段获取（如果有的话）
        from .bot_state import BotStateManager
        mgr = BotStateManager()
        state = mgr._states.get(self.bot_id)
        if state and hasattr(state, 'last_wechat_user_id'):
            return state.last_wechat_user_id
        return None


class ProactiveManager:
    """主动消息管理器（单例）"""

    _instance: Optional["ProactiveManager"] = None

    def __new__(cls) -> "ProactiveManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._senders: Dict[str, WeChatProactiveSender] = {}

    async def start_all(self) -> None:
        """启动所有机器人的主动消息循环"""
        from .auth import load_all_credentials
        creds_list = load_all_credentials()
        for creds in creds_list:
            await self.start_bot(creds)

    async def start_bot(self, creds: Credentials) -> bool:
        bot_id = creds.ilink_bot_id
        if bot_id in self._senders:
            return False
        sender = WeChatProactiveSender(creds)
        await sender.start()
        self._senders[bot_id] = sender
        return True

    async def stop_bot(self, bot_id: str) -> bool:
        sender = self._senders.pop(bot_id, None)
        if not sender:
            return False
        await sender.stop()
        return True

    async def stop_all(self) -> None:
        bot_ids = list(self._senders.keys())
        for bot_id in bot_ids:
            await self.stop_bot(bot_id)


def get_proactive_manager() -> ProactiveManager:
    return ProactiveManager()
