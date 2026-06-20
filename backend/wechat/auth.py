# -*- coding: utf-8 -*-
"""微信扫码登录、凭证管理

参考 weclaw/ilink/auth.go，适配多用户独立机器人架构。
凭证存储路径：~/.soft_ripe_timezone/wechat_accounts/{bot_id}.json
"""
import os
import json
import logging
from datetime import datetime
from typing import Optional, List

from .ilink_types import Credentials, QRCodeResponse, QRStatusResponse
from .ilink_client import ILinkClient

logger = logging.getLogger("soft_ripe.wechat.auth")

# ==================== 路径管理 ====================

def _home_dir() -> str:
    return os.path.expanduser("~")

def accounts_dir() -> str:
    """凭证存储目录：~/.soft_ripe_timezone/wechat_accounts/"""
    return os.path.join(_home_dir(), ".soft_ripe_timezone", "wechat_accounts")

def bot_state_path() -> str:
    """bot_state 文件路径：~/.soft_ripe_timezone/wechat_bot_state.json"""
    return os.path.join(_home_dir(), ".soft_ripe_timezone", "wechat_bot_state.json")

def _normalize_bot_id(raw: str) -> str:
    """
    将原始 bot ID 转为文件系统安全的格式

    参考 weclaw 的 NormalizeAccountID
    """
    s = raw
    for ch in ["@", ".", ":"]:
        s = s.replace(ch, "-")
    return s

def _credential_file_path(bot_id: str) -> str:
    """获取指定机器人的凭证文件路径"""
    safe_id = _normalize_bot_id(bot_id)
    return os.path.join(accounts_dir(), f"{safe_id}.json")


# ==================== 凭证持久化 ====================

def save_credentials(creds: Credentials) -> str:
    """
    保存凭证到文件

    参考 weclaw 的 SaveCredentials
    文件路径：~/.soft_ripe_timezone/wechat_accounts/{bot_id}.json
    权限：目录 0o700，文件 0o600

    Returns:
        保存的文件路径
    """
    dir_path = accounts_dir()
    os.makedirs(dir_path, mode=0o700, exist_ok=True)

    file_path = _credential_file_path(creds.ilink_bot_id)
    data = creds.to_json()

    # 写入文件（Windows 不支持 chmod，忽略权限设置）
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(data)

    # 非 Windows 系统设置文件权限
    if os.name != "nt":
        os.chmod(file_path, 0o600)

    logger.info(f"凭证已保存: {file_path}")
    return file_path


def load_all_credentials() -> List[Credentials]:
    """
    加载所有已保存的凭证文件

    参考 weclaw 的 LoadAllCredentials
    启动时批量恢复所有机器人凭证。

    Returns:
        凭证列表（可能为空）
    """
    dir_path = accounts_dir()
    if not os.path.exists(dir_path):
        return []

    result = []
    for entry in os.listdir(dir_path):
        if not entry.endswith(".json"):
            continue
        file_path = os.path.join(dir_path, entry)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            creds = Credentials.from_dict(data)
            if creds.bot_token:
                result.append(creds)
        except Exception as e:
            logger.warning(f"加载凭证失败 {file_path}: {e}")
    return result


def load_credentials(bot_id: str) -> Optional[Credentials]:
    """加载指定机器人的凭证"""
    file_path = _credential_file_path(bot_id)
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Credentials.from_dict(data)
    except Exception as e:
        logger.error(f"加载凭证失败 {file_path}: {e}")
        return None


def delete_credentials(bot_id: str) -> bool:
    """
    删除指定机器人的凭证文件

    Returns:
        True 如果删除成功，False 如果文件不存在
    """
    file_path = _credential_file_path(bot_id)
    if os.path.exists(file_path):
        os.remove(file_path)
        logger.info(f"凭证已删除: {file_path}")
        return True
    return False


# ==================== 扫码登录流程 ====================

async def fetch_qr_code() -> QRCodeResponse:
    """
    获取登录二维码

    参考 weclaw 的 FetchQRCode
    Returns:
        QRCodeResponse: qrcode（token）+ qrcode_img_content（base64 图片）
    """
    return await ILinkClient.fetch_qr_code()


async def poll_qr_status(qrcode: str) -> QRStatusResponse:
    """
    查询扫码状态（单次查询）

    参考 weclaw 的 PollQRStatus（单次循环）
    前端轮询时反复调用此方法。

    Returns:
        QRStatusResponse: status 为 wait/scaned/confirmed/expired
        confirmed 时包含 bot_token 等凭证
    """
    return await ILinkClient.poll_qr_status(qrcode)


def build_credentials_from_qr(
    qr_resp: QRStatusResponse,
    user_id: str,
) -> Credentials:
    """
    从扫码确认响应构建凭证对象

    Args:
        qr_resp: 扫码状态响应（status=confirmed）
        user_id: 归属的系统用户 ID

    Returns:
        完整的 Credentials 对象（含 bot_id, user_id, created_at）
    """
    return Credentials(
        bot_token=qr_resp.bot_token,
        ilink_bot_id=qr_resp.ilink_bot_id,
        base_url=qr_resp.base_url or "https://ilinkai.weixin.qq.com",
        ilink_user_id=qr_resp.ilink_user_id,
        bot_id=qr_resp.ilink_bot_id,
        user_id=user_id,
        created_at=datetime.now().isoformat(),
    )
