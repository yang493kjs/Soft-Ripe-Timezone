# -*- coding: utf-8 -*-
"""消息适配层 — 微信消息 ↔ 半熟时区消息

这是最关键的模块，负责：
1. 将微信消息转换为半熟时区内部格式
2. 调用现有 AI 引擎（通过内部 HTTP 调用 /api/chat）
3. 将 AI 回复分段发送到微信

严格遵循需求文档第五章「消息处理流程」的 11 步流程。
"""
import re
import uuid
import asyncio
import logging
from typing import Optional, List, Tuple

import httpx

from .ilink_types import (
    WeixinMessage, MessageItem, ItemType, MessageType, MessageState,
    TypingStatus,
)
from .ilink_client import ILinkClient
from .bot_state import get_bot_state_manager
from . import media

logger = logging.getLogger("soft_ripe.wechat.adapter")

# 后端服务地址（用于内部 HTTP 调用 /api/chat 和下载表情图片）
BACKEND_BASE_URL = "http://localhost:8765"

# Markdown 图片正则（参考 weclaw 的 reMarkdownImage）
RE_MARKDOWN_IMAGE = re.compile(r'!\[[^\]]*\]\(([^)]+)\)')

# <emoji:分类> 正则
RE_EMOJI_TAG = re.compile(r'<emoji:(\w+)>')


class WeChatAdapter:
    """微信消息适配器

    每个机器人对应一个 Adapter 实例。
    """

    def __init__(self, client: ILinkClient, bot_id: str):
        self.client = client
        self.bot_id = bot_id
        self.bot_state = get_bot_state_manager()
        # 内部 session token 缓存（user_id → token），避免每次调用 /api/chat 都创建
        self._token_cache: dict = {}

    # ==================== 主入口 ====================

    async def handle_message(self, msg: WeixinMessage) -> None:
        """
        处理单条微信消息

        严格遵循需求文档第五章的 11 步流程。
        """
        try:
            # 步骤 1: 过滤 — 只处理用户消息且状态为完成
            if msg.message_type != MessageType.USER:
                return
            if msg.message_state != MessageState.FINISH:
                return

            # 步骤 2: 查询归属
            user_id = self.bot_state.get_user_id(self.bot_id)
            if not user_id:
                logger.warning(f"机器人 {self.bot_id} 无归属用户，丢弃消息")
                return

            from_user_id = msg.from_user_id
            context_token = msg.context_token

            # 步骤 3: 提取内容
            text_content, image_base64, image_mime, has_unsupported = self._extract_content(msg)

            # 如果消息完全无内容（如纯贴纸），回复友好提示
            if not text_content and not image_base64:
                if has_unsupported:
                    await self._send_text_reply(
                        from_user_id, "这个表情好可爱～ 😊", context_token
                    )
                return

            # 步骤 4: 角色路由 — 检查是否为命令
            cmd_result = self._parse_command(text_content)
            if cmd_result:
                await self._handle_command(cmd_result, from_user_id, context_token)
                return  # 命令不写入 messages 表，直接返回

            # 步骤 5: 图片识别（在 /api/chat 内部处理，这里只传递 image_base64）

            # 步骤 6-7: 调用现有 AI 引擎（内部 HTTP 调用 /api/chat）
            persona_id = self.bot_state.get_current_persona(self.bot_id)
            chat_result = await self._call_chat_api(
                user_id, persona_id, text_content, image_base64, image_mime
            )

            if not chat_result or "segments" not in chat_result:
                logger.error(f"AI 引擎返回异常: {chat_result}")
                await self._send_text_reply(
                    from_user_id, "嗯……我有点走神了，再说一次好吗？", context_token
                )
                return

            # 步骤 8: 发送"正在输入"状态
            await self._send_typing_indicator(from_user_id, context_token)

            # 步骤 9-10: 文本处理 + 分段发送
            segments = chat_result.get("segments", [])
            delays = chat_result.get("delays", [])
            emojis = chat_result.get("emojis", [])  # [{"category", "url", "tag"}, ...]

            # 处理 AI 回复中的图片链接和表情标记
            await self._send_reply_segments(
                from_user_id, context_token, segments, delays, persona_id, emojis
            )

            # 步骤 11: 清除"正在输入"状态
            await self._clear_typing_indicator(from_user_id, context_token)

        except Exception as e:
            logger.error(f"处理消息失败: {e}", exc_info=True)
            try:
                await self._send_text_reply(
                    msg.from_user_id,
                    "刚刚走神了一下……你再说一遍好吗？",
                    msg.context_token,
                )
            except Exception:
                pass

    # ==================== 步骤 3: 内容提取 ====================

    def _extract_content(self, msg: WeixinMessage) -> Tuple[str, Optional[str], str, bool]:
        """
        遍历 item_list 提取内容

        Returns:
            (text, image_base64, image_mime, has_unsupported)
        """
        text_parts: List[str] = []
        image_base64: Optional[str] = None
        image_mime = "image/png"
        has_unsupported = False

        for item in msg.item_list:
            if item.type == ItemType.TEXT and item.text_item:
                text_parts.append(item.text_item.text)
            elif item.type == ItemType.IMAGE and item.image_item:
                # 图片需要异步下载，这里先标记，在 handle_message 中处理
                # 实际下载在 _download_image 中完成
                image_base64 = "PENDING"  # 占位符，表示有图片待下载
            elif item.type == ItemType.VOICE and item.voice_item:
                # 语音：使用微信自动转文字结果
                if item.voice_item.text:
                    text_parts.append(item.voice_item.text)
            elif item.type == ItemType.VIDEO:
                has_unsupported = True
                text_parts.append("[用户发送了视频]")
            elif item.type == ItemType.FILE:
                has_unsupported = True
                text_parts.append("[用户发送了文件]")

        text = "\n".join(text_parts) if text_parts else ""

        # 如果有图片，需要异步下载
        if image_base64 == "PENDING":
            image_base64 = None  # 重置，实际下载在 handle_message 中异步进行
            for item in msg.item_list:
                if item.type == ItemType.IMAGE and item.image_item:
                    # 这里返回 image_item 供异步下载
                    return text, "PENDING_IMAGE", "image/png", has_unsupported

        return text, image_base64, image_mime, has_unsupported

    async def _download_image_as_base64(self, image_item) -> Optional[Tuple[str, str]]:
        """
        下载图片并返回 base64 编码

        支持两种来源（参考 weclaw）：
        1. img.URL 不为空 → 直接 HTTP GET 下载
        2. img.Media.EncryptQueryParam 不为空 → CDN 加密下载 + AES 解密
        """
        try:
            if image_item.url:
                data, content_type = await media.download_from_url(image_item.url)
                import base64
                return base64.b64encode(data).decode("ascii"), content_type
            elif image_item.media and image_item.media.encrypt_query_param:
                data = await media.download_from_cdn(
                    image_item.media.encrypt_query_param,
                    image_item.media.aes_key,
                )
                import base64
                return base64.b64encode(data).decode("ascii"), "image/png"
        except Exception as e:
            logger.error(f"下载图片失败: {e}")
        return None

    # ==================== 步骤 4: 命令处理 ====================

    def _parse_command(self, text: str) -> Optional[Tuple[str, str]]:
        """
        解析角色切换命令

        Returns:
            (cmd, arg) 或 None
            cmd: "帮助" / "切换" / "当前"
            arg: 角色名（仅 /切换 有）
        """
        text = text.strip()
        if not text.startswith("/"):
            return None

        # /帮助
        if text in ("/帮助", "/help", "/？", "/?"):
            return ("帮助", "")

        # /当前
        if text in ("/当前", "/current"):
            return ("当前", "")

        # /切换 sunny
        m = re.match(r'^/(?:切换|switch)\s+(\S+)', text)
        if m:
            return ("切换", m.group(1))

        return None

    async def _handle_command(self, cmd_result: Tuple[str, str], to_user_id: str, context_token: str) -> None:
        """处理角色切换命令（不写入 messages 表）"""
        cmd, arg = cmd_result

        if cmd == "帮助":
            reply = self._build_help_reply()
            await self._send_text_reply(to_user_id, reply, context_token)

        elif cmd == "当前":
            reply = await self._build_current_reply()
            await self._send_text_reply(to_user_id, reply, context_token)

        elif cmd == "切换":
            reply = await self._handle_switch_persona(arg)
            await self._send_text_reply(to_user_id, reply, context_token)

    def _build_help_reply(self) -> str:
        """构建 /帮助 回复"""
        from settings import PERSONAS
        current = self.bot_state.get_current_persona(self.bot_id)
        all_personas = self.bot_state.get_all_personas("")

        lines = ["可用角色："]
        for pid in all_personas:
            name = PERSONAS.get(pid, {}).get("name", pid)
            marker = "● " if pid == current else "  "
            suffix = " ← 当前" if pid == current else ""
            lines.append(f"{marker}{pid}（{name}）{suffix}")
        lines.append("")
        lines.append("使用 /切换 角色名 来切换角色")
        lines.append("使用 /当前 查看当前角色详情")
        return "\n".join(lines)

    async def _build_current_reply(self) -> str:
        """构建 /当前 回复"""
        from settings import PERSONAS
        current = self.bot_state.get_current_persona(self.bot_id)
        name = PERSONAS.get(current, {}).get("name", current)

        # 获取关系数据
        user_id = self.bot_state.get_user_id(self.bot_id)
        agent_id = f"{user_id}_{current}"

        lines = [f"当前角色：{current}（{name}）", "", "关系状态："]

        try:
            from emotion_system import EmotionSystem
            emo = EmotionSystem(agent_id)
            rel = emo.relationship
            lines.append(f"● 阶段：{rel.get('phase', '初识')}")
            lines.append(f"● 亲密度：{rel.get('intimacy', 0):.0f}/100")
            lines.append(f"● 激情度：{rel.get('passion', 0):.0f}/100")
            lines.append(f"● 承诺度：{rel.get('commitment', 0):.0f}/100")
            lines.append(f"● 当前情绪：{rel.get('current_emotion', '平静')}")
        except Exception as e:
            logger.warning(f"获取关系数据失败: {e}")
            lines.append("（关系数据暂不可用）")

        return "\n".join(lines)

    async def _handle_switch_persona(self, persona_id: str) -> str:
        """处理 /切换 命令"""
        from settings import PERSONAS

        if persona_id not in PERSONAS:
            available = ", ".join(PERSONAS.keys())
            return f"角色 '{persona_id}' 不存在。可用角色：{available}"

        name = PERSONAS[persona_id]["name"]
        self.bot_state.set_current_persona(self.bot_id, persona_id)
        return f"已切换到 {persona_id}（{name}），有什么想聊的？"

    # ==================== 步骤 6-7: 调用 AI 引擎 ====================

    async def _call_chat_api(
        self,
        user_id: str,
        persona_id: str,
        message: str,
        image_base64: Optional[str],
        image_mime: str,
    ) -> Optional[dict]:
        """
        内部 HTTP 调用 /api/chat

        用户选择了此方式复用现有 chat 流程。
        需要为微信用户创建内部 session token 进行鉴权。
        """
        token = self._get_or_create_token(user_id)

        payload = {
            "user_id": user_id,
            "persona_id": persona_id,
            "message": message or "[图片]",
            "user_is_typing": False,
        }
        if image_base64:
            payload["image_base64"] = image_base64
            payload["image_mime_type"] = image_mime

        try:
            async with httpx.AsyncClient(timeout=120.0) as http_client:
                resp = await http_client.post(
                    f"{BACKEND_BASE_URL}/api/chat",
                    json=payload,
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code != 200:
                    logger.error(f"/api/chat 返回 {resp.status_code}: {resp.text}")
                    return None
                return resp.json()
        except Exception as e:
            logger.error(f"调用 /api/chat 失败: {e}")
            return None

    def _get_or_create_token(self, user_id: str) -> str:
        """
        为微信用户获取或创建内部 session token

        微信用户是系统用户，直接为其创建 token。
        token 缓存在内存中，避免重复创建。
        """
        if user_id in self._token_cache:
            # 验证 token 是否仍然有效
            from auth import _verify_session_token
            if _verify_session_token(self._token_cache[user_id]):
                return self._token_cache[user_id]

        # _create_session_token 接收 username 参数，实际作为 user_id 使用
        from auth import _create_session_token
        token = _create_session_token(user_id)
        self._token_cache[user_id] = token
        return token

    # ==================== 步骤 8: 正在输入 ====================

    async def _send_typing_indicator(self, to_user_id: str, context_token: str) -> None:
        """发送"正在输入"状态"""
        try:
            config = await self.client.get_config(to_user_id, context_token)
            if config.typing_ticket:
                await self.client.send_typing(to_user_id, config.typing_ticket, TypingStatus.TYPING)
        except Exception as e:
            logger.debug(f"发送 typing 失败（非致命）: {e}")

    async def _clear_typing_indicator(self, to_user_id: str, context_token: str) -> None:
        """清除"正在输入"状态"""
        try:
            config = await self.client.get_config(to_user_id, context_token)
            if config.typing_ticket:
                await self.client.send_typing(to_user_id, config.typing_ticket, TypingStatus.CANCEL)
        except Exception as e:
            logger.debug(f"清除 typing 失败（非致命）: {e}")

    # ==================== 步骤 9-10: 文本处理与分段发送 ====================

    async def _send_reply_segments(
        self,
        to_user_id: str,
        context_token: str,
        segments: List[str],
        delays: List[float],
        persona_id: str,
        emojis: Optional[List[dict]] = None,
    ) -> None:
        """
        处理 AI 回复并分段发送到微信

        步骤 9: 文本处理（Markdown 转纯文本、提取图片链接）
        步骤 10: 分段发送（段间停顿模拟真人打字）
        表情包：/api/chat 已将 <emoji:xxx> 标记解析为 emojis 列表，在此发送
        """
        if not segments:
            return

        # 先发送表情包图片（/api/chat 返回的 emojis 字段）
        # emojis 结构: [{"category": "happy", "url": "/static/...", "tag": "<emoji:happy>"}, ...]
        if emojis:
            for emoji_info in emojis:
                emoji_url = emoji_info.get("url")
                if emoji_url:
                    full_url = f"{BACKEND_BASE_URL}{emoji_url}" if emoji_url.startswith("/") else emoji_url
                    try:
                        await media.send_media_from_url(self.client, to_user_id, full_url, context_token)
                        logger.info(f"已发送表情 {emoji_info.get('category')}: {full_url}")
                    except Exception as e:
                        logger.error(f"发送表情失败 {emoji_info.get('category')}: {e}")

        for i, segment in enumerate(segments):
            # 9a. Markdown 转纯文本
            plain_text = _markdown_to_plain_text(segment)

            # 9b. 提取 Markdown 图片链接并发送
            image_urls = _extract_image_urls(segment)
            for url in image_urls:
                try:
                    await media.send_media_from_url(self.client, to_user_id, url, context_token)
                except Exception as e:
                    logger.error(f"发送图片失败 {url}: {e}")

            # 从纯文本中移除图片链接
            plain_text = RE_MARKDOWN_IMAGE.sub("", plain_text)
            plain_text = plain_text.strip()

            if plain_text:
                # 10. 段间停顿 + 发送
                if i > 0 and i - 1 < len(delays):
                    delay = delays[i - 1]
                    if delay > 0:
                        await asyncio.sleep(min(delay, 5.0))  # 限制最大停顿

                await self._send_text_reply(to_user_id, plain_text, context_token)

    def _get_emoji_url(self, category: str) -> Optional[str]:
        """
        获取表情图片的完整 URL

        用户选择了"拼接本地后端地址"方式。
        emoji_engine 返回的是相对路径如 /static/emojis/happy/1.gif
        需要拼接为 http://localhost:8765/static/emojis/happy/1.gif
        """
        try:
            from emoji_engine import get_random_emoji
            relative_url = get_random_emoji(category)
            if relative_url:
                return f"{BACKEND_BASE_URL}{relative_url}"
        except Exception as e:
            logger.warning(f"获取表情 URL 失败 {category}: {e}")
        return None

    async def _send_text_reply(self, to_user_id: str, text: str, context_token: str) -> None:
        """发送文本回复"""
        try:
            await self.client.send_text(to_user_id, text, context_token)
        except Exception as e:
            logger.error(f"发送文本消息失败: {e}")


# ==================== Markdown 处理（参考 weclaw/messaging/markdown.go）====================

def _markdown_to_plain_text(text: str) -> str:
    """
    将 Markdown 转为纯文本（微信不支持 Markdown 渲染）

    严格参考 weclaw 的 MarkdownToPlainText。
    """
    import re

    # 代码块：去除围栏，保留代码内容
    text = re.sub(r'(?s)```[^\n]*\n?(.*?)```', lambda m: m.group(1).strip(), text)

    # 图片：移除（单独处理为图片消息）
    text = RE_MARKDOWN_IMAGE.sub("", text)

    # 链接：保留显示文本
    text = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', text)

    # 表格分隔行：移除
    text = re.sub(r'(?m)^\|[\s:|\-]+\|$', "", text)

    # 表格行：管道分隔 → 空格分隔
    text = re.sub(r'(?m)^\|(.+)\|$', lambda m: "  ".join(c.strip() for c in m.group(1).split("|")), text)

    # 标题：移除 # 前缀
    text = re.sub(r'(?m)^#{1,6}\s+', "", text)

    # 粗体
    text = re.sub(r'\*\*(.+?)\*\*|__(.+?)__', lambda m: m.group(1) or m.group(2), text)

    # 删除线
    text = re.sub(r'~~(.+?)~~', r'\1', text)

    # 引用
    text = re.sub(r'(?m)^>\s?', "", text)

    # 水平线 → 空行
    text = re.sub(r'(?m)^[-*_]{3,}\s*$', "", text)

    # 无序列表：标记替换为 •
    text = re.sub(r'(?m)^(\s*)[-*+]\s+', r'\1• ', text)

    # 行内代码：去除反引号
    text = re.sub(r'`([^`]+)`', r'\1', text)

    # 清理多余空行
    text = re.sub(r'\n{3,}', "\n\n", text)

    return text.strip()


def _extract_image_urls(text: str) -> List[str]:
    """
    从 Markdown 文本中提取图片 URL

    严格参考 weclaw 的 ExtractImageURLs。
    """
    urls = []
    for m in RE_MARKDOWN_IMAGE.finditer(text):
        url = m.group(1).strip()
        if url.startswith("http://") or url.startswith("https://"):
            urls.append(url)
    return urls
