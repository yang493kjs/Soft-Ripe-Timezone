# -*- coding: utf-8 -*-
"""微信连接模块

提供微信机器人集成功能：
- 扫码登录与凭证管理（auth）
- 机器人状态管理（bot_state）
- iLink HTTP API 客户端（ilink_client）
- 消息适配层（adapter）
- 长轮询监控（monitor）
- 媒体文件处理（media）
- 主动消息推送（wechat_proactive）

生命周期：
1. 应用启动时调用 init() 加载所有凭证并启动监控
2. 应用关闭时调用 shutdown() 优雅停止所有循环
"""
import logging
from typing import Optional

from .ilink_types import (
    Credentials, WeixinMessage, MessageItem,
    MessageType, MessageState, ItemType,
)
from .ilink_client import ILinkClient
from .auth import (
    fetch_qr_code, poll_qr_status, build_credentials_from_qr,
    save_credentials, load_credentials, load_all_credentials, delete_credentials,
)
from .bot_state import get_bot_state_manager, BotStateManager
from .monitor import get_monitor_manager, MonitorManager
from .wechat_proactive import get_proactive_manager, ProactiveManager

logger = logging.getLogger("soft_ripe.wechat")

_initialized = False


async def init() -> None:
    """
    初始化微信模块

    在应用启动时调用：
    1. 加载 bot_state 文件
    2. 从凭证文件重建未在 bot_state 中的机器人
    3. 启动所有机器人的监控循环
    4. 启动所有机器人的主动消息循环
    """
    global _initialized
    if _initialized:
        return

    logger.info("初始化微信模块...")

    # 1. 加载 bot_state
    bot_state_mgr = get_bot_state_manager()
    bot_state_mgr.load()

    # 2. 从凭证文件重建 bot_state 中缺失的机器人
    all_creds = load_all_credentials()
    for creds in all_creds:
        if not bot_state_mgr.get_user_id(creds.ilink_bot_id):
            # bot_state 中没有，但凭证文件有 → 重建
            # user_id 从凭证文件的 user_id 字段获取
            user_id = creds.user_id or "default_user"
            bot_state_mgr.register_bot(creds.ilink_bot_id, user_id)
            logger.info(f"从凭证文件重建机器人状态: {creds.ilink_bot_id} → {user_id}")

    # 3. 启动所有监控
    monitor_mgr = get_monitor_manager()
    await monitor_mgr.start_all()

    # 4. 启动所有主动消息循环
    proactive_mgr = get_proactive_manager()
    await proactive_mgr.start_all()

    _initialized = True
    logger.info(f"微信模块初始化完成，已启动 {len(all_creds)} 个机器人")


async def shutdown() -> None:
    """关闭微信模块"""
    global _initialized
    if not _initialized:
        return

    logger.info("关闭微信模块...")

    # 停止所有主动消息循环
    await get_proactive_manager().stop_all()

    # 停止所有监控
    await get_monitor_manager().stop_all()

    _initialized = False
    logger.info("微信模块已关闭")


def is_initialized() -> bool:
    return _initialized


__all__ = [
    # 类型
    "Credentials", "WeixinMessage", "MessageItem",
    "MessageType", "MessageState", "ItemType", "ILinkClient",
    # 认证
    "fetch_qr_code", "poll_qr_status", "build_credentials_from_qr",
    "save_credentials", "load_credentials", "load_all_credentials", "delete_credentials",
    # 状态管理
    "get_bot_state_manager", "BotStateManager",
    # 监控
    "get_monitor_manager", "MonitorManager",
    # 主动消息
    "get_proactive_manager", "ProactiveManager",
    # 生命周期
    "init", "shutdown", "is_initialized",
]
