# -*- coding: utf-8 -*-
"""iLink HTTP API 客户端

严格参考 weclaw/ilink/client.go，使用 httpx 异步客户端。
封装与微信 iLink 服务端的 HTTP 通信。
"""
import os
import base64
import struct
import logging
from typing import Optional

import httpx

from .ilink_types import (
    Credentials, BaseInfo,
    GetUpdatesRequest, GetUpdatesResponse,
    SendMessageRequest, SendMessageResponse,
    GetUploadURLRequest, GetUploadURLResponse,
    GetConfigRequest, GetConfigResponse,
    SendTypingRequest, SendTypingResponse,
    QRCodeResponse, QRStatusResponse,
    TypingStatus,
)

logger = logging.getLogger("soft_ripe.wechat.ilink")

DEFAULT_BASE_URL = "https://ilinkai.weixin.qq.com"
LONG_POLL_TIMEOUT = 35.0       # 长轮询超时（秒）
LONG_POLL_MARGIN = 5.0         # 长轮询额外余量
SEND_TIMEOUT = 15.0            # 发送消息超时
CONFIG_TIMEOUT = 10.0          # 获取配置超时
LOGIN_TIMEOUT = 40.0           # 扫码登录超时

# 扫码登录相关 URL（固定，不需要凭证）
QR_CODE_URL = f"{DEFAULT_BASE_URL}/ilink/bot/get_bot_qrcode?bot_type=3"
QR_STATUS_URL = f"{DEFAULT_BASE_URL}/ilink/bot/get_qrcode_status?qrcode="

# 扫码状态常量（参考 weclaw 的 statusWait/statusScanned/statusConfirmed/statusExpired）
QR_STATUS_WAIT = "wait"
QR_STATUS_SCANNED = "scaned"       # 注意：微信 API 返回的是 "scaned"（少一个 n）
QR_STATUS_CONFIRMED = "confirmed"
QR_STATUS_EXPIRED = "expired"


def _generate_wechat_uin() -> str:
    """
    生成随机 X-WECHAT-UIN 请求头

    参考 weclaw 的 generateWechatUIN：
    1. 生成随机 uint32
    2. 转为十进制字符串
    3. base64 编码
    """
    n = struct.unpack("<I", os.urandom(4))[0]
    s = str(n)
    return base64.b64encode(s.encode("ascii")).decode("ascii")


class ILinkClient:
    """iLink HTTP API 客户端

    每个机器人对应一个 Client 实例，持有该机器人的凭证。
    """

    def __init__(self, creds: Optional[Credentials] = None):
        """
        Args:
            creds: 机器人凭证。为 None 时创建未认证客户端（用于扫码登录流程）。
        """
        if creds and creds.bot_token:
            self._base_url = creds.base_url or DEFAULT_BASE_URL
            self._bot_token = creds.bot_token
            self._bot_id = creds.ilink_bot_id
            self._ilink_user_id = creds.ilink_user_id
            self._authenticated = True
        else:
            self._base_url = DEFAULT_BASE_URL
            self._bot_token = ""
            self._bot_id = ""
            self._ilink_user_id = ""
            self._authenticated = False

        self._wechat_uin = _generate_wechat_uin()
        # httpx 异步客户端，不设全局超时（各方法单独控制）
        self._http_client = httpx.AsyncClient(timeout=httpx.Timeout(None))

    # ==================== 属性 ====================

    @property
    def bot_id(self) -> str:
        return self._bot_id

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def is_authenticated(self) -> bool:
        return self._authenticated

    # ==================== 内部方法 ====================

    def _headers(self) -> dict:
        """构造请求头（参考 weclaw 的 setHeaders）"""
        return {
            "Content-Type": "application/json",
            "AuthorizationType": "ilink_bot_token",
            "Authorization": f"Bearer {self._bot_token}",
            "X-WECHAT-UIN": self._wechat_uin,
        }

    async def _do_post(self, path: str, body: dict, timeout: float) -> dict:
        """POST 请求（参考 weclaw 的 doPost）"""
        url = self._base_url + path
        try:
            resp = await self._http_client.post(
                url,
                json=body,
                headers=self._headers(),
                timeout=timeout,
            )
            if resp.status_code != 200:
                raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")
            return resp.json()
        except httpx.TimeoutException as e:
            raise RuntimeError(f"request timeout: {e}") from e
        except httpx.HTTPError as e:
            raise RuntimeError(f"HTTP error: {e}") from e

    async def _do_get(self, url: str, timeout: float) -> dict:
        """GET 请求（参考 weclaw 的 doGet，用于扫码登录）"""
        try:
            resp = await self._http_client.get(url, timeout=timeout)
            if resp.status_code != 200:
                raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")
            return resp.json()
        except httpx.TimeoutException as e:
            raise RuntimeError(f"request timeout: {e}") from e
        except httpx.HTTPError as e:
            raise RuntimeError(f"HTTP error: {e}") from e

    # ==================== 扫码登录（无需凭证）====================

    @staticmethod
    async def fetch_qr_code() -> QRCodeResponse:
        """获取登录二维码（参考 weclaw 的 FetchQRCode）"""
        client = ILinkClient(creds=None)
        data = await client._do_get(QR_CODE_URL, LOGIN_TIMEOUT)
        await client.close()
        return QRCodeResponse.from_dict(data)

    @staticmethod
    async def poll_qr_status(qrcode: str) -> QRStatusResponse:
        """
        查询扫码状态（单次查询，参考 weclaw 的 PollQRStatus 单次循环）

        返回状态：wait / scaned / confirmed / expired
        confirmed 时响应中包含 bot_token 等凭证。
        """
        client = ILinkClient(creds=None)
        url = QR_STATUS_URL + qrcode
        data = await client._do_get(url, LOGIN_TIMEOUT)
        await client.close()
        return QRStatusResponse.from_dict(data)

    # ==================== 消息相关（需要凭证）====================

    async def get_updates(self, buf: str = "") -> GetUpdatesResponse:
        """长轮询拉取新消息（参考 weclaw 的 GetUpdates）"""
        req = GetUpdatesRequest(get_updates_buf=buf, base_info=BaseInfo())
        data = await self._do_post(
            "/ilink/bot/getupdates",
            req.to_dict(),
            LONG_POLL_TIMEOUT + LONG_POLL_MARGIN,
        )
        return GetUpdatesResponse.from_dict(data)

    async def send_message(self, req: SendMessageRequest) -> SendMessageResponse:
        """发送消息（参考 weclaw 的 SendMessage）"""
        data = await self._do_post(
            "/ilink/bot/sendmessage",
            req.to_dict(),
            SEND_TIMEOUT,
        )
        resp = SendMessageResponse.from_dict(data)
        if resp.ret != 0:
            raise RuntimeError(f"sendmessage failed: ret={resp.ret} errmsg={resp.err_msg}")
        return resp

    async def send_text(
        self,
        to_user_id: str,
        text: str,
        context_token: str = "",
        client_id: str = "",
    ) -> SendMessageResponse:
        """发送文本消息的便捷方法"""
        from .ilink_types import MessageItem, TextItem, SendMsg
        import uuid

        if not client_id:
            client_id = str(uuid.uuid4())

        req = SendMessageRequest(
            msg=SendMsg(
                from_user_id=self._bot_id,
                to_user_id=to_user_id,
                client_id=client_id,
                item_list=[MessageItem(type=1, text_item=TextItem(text=text))],
                context_token=context_token,
            )
        )
        return await self.send_message(req)

    async def get_config(self, user_id: str, context_token: str = "") -> GetConfigResponse:
        """获取配置（含 typing_ticket，参考 weclaw 的 GetConfig）"""
        req = GetConfigRequest(
            ilink_user_id=user_id,
            context_token=context_token,
            base_info=BaseInfo(),
        )
        data = await self._do_post(
            "/ilink/bot/getconfig",
            req.to_dict(),
            CONFIG_TIMEOUT,
        )
        return GetConfigResponse.from_dict(data)

    async def send_typing(
        self,
        user_id: str,
        typing_ticket: str,
        status: int = TypingStatus.TYPING,
    ) -> None:
        """发送"正在输入"状态（参考 weclaw 的 SendTyping）"""
        req = SendTypingRequest(
            ilink_user_id=user_id,
            typing_ticket=typing_ticket,
            status=status,
            base_info=BaseInfo(),
        )
        data = await self._do_post(
            "/ilink/bot/sendtyping",
            req.to_dict(),
            CONFIG_TIMEOUT,
        )
        resp = SendTypingResponse.from_dict(data)
        if resp.ret != 0:
            raise RuntimeError(f"sendtyping failed: ret={resp.ret} errmsg={resp.err_msg}")

    async def get_upload_url(self, req: GetUploadURLRequest) -> GetUploadURLResponse:
        """获取 CDN 上传 URL（参考 weclaw 的 GetUploadURL）"""
        data = await self._do_post(
            "/ilink/bot/getuploadurl",
            req.to_dict(),
            SEND_TIMEOUT,
        )
        resp = GetUploadURLResponse.from_dict(data)
        if resp.ret != 0:
            raise RuntimeError(f"getuploadurl failed: ret={resp.ret} errmsg={resp.err_msg}")
        return resp

    # ==================== 生命周期 ====================

    async def close(self):
        """关闭 HTTP 客户端"""
        await self._http_client.aclose()
