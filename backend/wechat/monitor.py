# -*- coding: utf-8 -*-
"""长轮询监控循环

参考 weclaw/ilink/monitor.go：
- 每个机器人一个独立的监控协程
- 使用 getupdates 长轮询拉取新消息
- 维护 get_updates_buf 游标，保证消息不丢失
- 错误时退避重试，避免空转
"""
import asyncio
import logging
from typing import Optional, Dict

from .ilink_types import (
    Credentials, WeixinMessage,
    MessageType, MessageState,
)
from .ilink_client import ILinkClient
from .adapter import WeChatAdapter
from .bot_state import get_bot_state_manager

logger = logging.getLogger("soft_ripe.wechat.monitor")


class BotMonitor:
    """单个机器人的监控循环"""

    def __init__(self, creds: Credentials):
        self.creds = creds
        self.bot_id = creds.ilink_bot_id
        self.client = ILinkClient(creds)
        self.adapter = WeChatAdapter(self.client, self.bot_id)
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._get_updates_buf = ""
        self._consecutive_errors = 0

    async def start(self) -> None:
        """启动监控循环"""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"机器人 {self.bot_id} 监控已启动")

    async def stop(self) -> None:
        """停止监控循环"""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self.client.close()
        logger.info(f"机器人 {self.bot_id} 监控已停止")

    async def _run_loop(self) -> None:
        """主循环（参考 weclaw 的 RunMonitorLoop）"""
        while self._running:
            try:
                await self._poll_once()
                self._consecutive_errors = 0
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._consecutive_errors += 1
                backoff = min(2 ** self._consecutive_errors, 60)
                logger.error(
                    f"机器人 {self.bot_id} 监控出错 (连续 {self._consecutive_errors} 次): {e}, "
                    f"{backoff}秒后重试"
                )
                await asyncio.sleep(backoff)

    async def _poll_once(self) -> None:
        """执行一次长轮询"""
        # 长轮询（最多阻塞 35 秒）
        resp = await self.client.get_updates(self._get_updates_buf)

        # 更新游标
        if resp.get_updates_buf:
            self._get_updates_buf = resp.get_updates_buf

        # 处理每条消息
        for msg in resp.msgs:
            try:
                await self._dispatch_message(msg)
            except Exception as e:
                logger.error(f"处理消息失败 seq={msg.seq}: {e}", exc_info=True)

    async def _dispatch_message(self, msg: WeixinMessage) -> None:
        """分发消息到适配器"""
        # 只处理用户消息且状态为完成
        if msg.message_type != MessageType.USER:
            return
        if msg.message_state != MessageState.FINISH:
            return

        logger.info(
            f"机器人 {self.bot_id} 收到消息: from={msg.from_user_id}, "
            f"items={len(msg.item_list)}, seq={msg.seq}"
        )

        await self.adapter.handle_message(msg)


class MonitorManager:
    """监控管理器（单例）— 管理所有机器人的监控循环"""

    _instance: Optional["MonitorManager"] = None

    def __new__(cls) -> "MonitorManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._monitors: Dict[str, BotMonitor] = {}

    async def start_all(self) -> None:
        """启动所有已保存凭证的机器人监控"""
        from .auth import load_all_credentials
        creds_list = load_all_credentials()
        logger.info(f"准备启动 {len(creds_list)} 个机器人监控")
        for creds in creds_list:
            await self.start_bot(creds)

    async def start_bot(self, creds: Credentials) -> bool:
        """启动指定机器人的监控"""
        bot_id = creds.ilink_bot_id
        if bot_id in self._monitors:
            logger.warning(f"机器人 {bot_id} 监控已在运行")
            return False

        monitor = BotMonitor(creds)
        await monitor.start()
        self._monitors[bot_id] = monitor
        return True

    async def stop_bot(self, bot_id: str) -> bool:
        """停止指定机器人的监控"""
        monitor = self._monitors.pop(bot_id, None)
        if not monitor:
            return False
        await monitor.stop()
        return True

    async def stop_all(self) -> None:
        """停止所有监控"""
        bot_ids = list(self._monitors.keys())
        for bot_id in bot_ids:
            await self.stop_bot(bot_id)
        logger.info("所有机器人监控已停止")

    def is_running(self, bot_id: str) -> bool:
        """检查机器人监控是否在运行"""
        return bot_id in self._monitors

    def get_running_bots(self) -> list:
        """获取所有正在运行的机器人 ID"""
        return list(self._monitors.keys())


def get_monitor_manager() -> MonitorManager:
    """获取监控管理器单例"""
    return MonitorManager()
