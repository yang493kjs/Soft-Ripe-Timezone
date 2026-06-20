# -*- coding: utf-8 -*-
"""媒体文件处理（CDN 上传/下载）

严格参考 weclaw/messaging/cdn.go 和 weclaw/messaging/media.go：
- 上传：生成 AES Key → 加密 → getuploadurl → POST 到 CDN → 获取 download_param
- 下载：从 CDN GET 密文 → 用 AES Key 解密
- CDN 基地址：https://novac2c.cdn.weixin.qq.com/c2c
"""
import os
import logging
from typing import Optional, Tuple
from urllib.parse import quote

import httpx

from . import cdma
from .ilink_client import ILinkClient
from .ilink_types import (
    GetUploadURLRequest, GetUploadURLResponse,
    MediaInfo, MessageItem, ImageItem, VideoItem, FileItem,
    ItemType, CDNMediaType, EncryptType,
)

logger = logging.getLogger("soft_ripe.wechat.media")

CDN_BASE_URL = "https://novac2c.cdn.weixin.qq.com/c2c"
CDN_UPLOAD_TIMEOUT = 60.0
CDN_DOWNLOAD_TIMEOUT = 60.0


# ==================== CDN 上传 ====================

async def upload_to_cdn(
    client: ILinkClient,
    data: bytes,
    to_user_id: str,
    media_type: int = CDNMediaType.IMAGE,
) -> Tuple[str, str, int, int]:
    """
    加密并上传文件到微信 CDN

    严格参考 weclaw 的 UploadFileToCDN。

    Args:
        client: iLink 客户端
        data: 原始文件数据
        to_user_id: 接收方用户 ID
        media_type: CDN 媒体类型（1=image, 2=video, 3=file）

    Returns:
        (download_param, aes_key_hex, raw_size, cipher_size)
        - download_param: 加密的下载参数（用于消息中的 encrypt_query_param）
        - aes_key_hex: AES Key 的 hex 字符串
        - raw_size: 明文大小
        - cipher_size: 密文大小
    """
    # 1. 生成随机 filekey 和 AES key（各 16 字节）
    filekey_bytes = cdma.generate_file_key()
    aeskey_bytes = cdma.generate_aes_key()
    filekey_hex = cdma.key_to_hex(filekey_bytes)
    aeskey_hex = cdma.key_to_hex(aeskey_bytes)

    # 2. 计算明文 MD5
    raw_md5 = cdma.md5_hex(data)

    # 3. 计算密文大小
    cipher_size = cdma.padded_size(len(data))

    # 4. 调用 getuploadurl 获取上传地址
    upload_req = GetUploadURLRequest(
        file_key=filekey_hex,
        media_type=media_type,
        to_user_id=to_user_id,
        raw_size=len(data),
        raw_file_md5=raw_md5,
        file_size=cipher_size,
        no_need_thumb=True,
        aes_key=aeskey_hex,
    )
    upload_resp = await client.get_upload_url(upload_req)

    # 5. AES-128-ECB 加密
    encrypted = cdma.encrypt(data, aeskey_bytes)

    # 6. 确定 CDN 上传 URL
    cdn_url = (upload_resp.upload_full_url or "").strip()
    if not cdn_url:
        if not upload_resp.upload_param:
            raise RuntimeError("getuploadurl returned no upload URL")
        cdn_url = (
            f"{CDN_BASE_URL}/upload"
            f"?encrypted_query_param={quote(upload_resp.upload_param)}"
            f"&filekey={quote(filekey_hex)}"
        )

    # 7. 上传到 CDN
    download_param = await _upload_to_cdn(encrypted, cdn_url)

    logger.info(f"CDN 上传成功: {len(data)} bytes → download_param={download_param[:32]}...")
    return download_param, aeskey_hex, len(data), cipher_size


async def _upload_to_cdn(encrypted_data: bytes, cdn_url: str) -> str:
    """
    执行 CDN 上传请求

    严格参考 weclaw 的 uploadToCDN。
    从响应头 X-Encrypted-Param 获取 download_param。
    """
    async with httpx.AsyncClient(timeout=CDN_UPLOAD_TIMEOUT) as http_client:
        resp = await http_client.post(
            cdn_url,
            content=encrypted_data,
            headers={"Content-Type": "application/octet-stream"},
        )
        if resp.status_code != 200:
            raise RuntimeError(f"CDN upload HTTP {resp.status_code}: {resp.text}")

        download_param = resp.headers.get("X-Encrypted-Param", "")
        if not download_param:
            raise RuntimeError("CDN upload: missing X-Encrypted-Param header")
        return download_param


# ==================== CDN 下载 ====================

async def download_from_cdn(encrypt_query_param: str, aes_key_base64: str) -> bytes:
    """
    从微信 CDN 下载并解密文件

    严格参考 weclaw 的 DownloadFileFromCDN。

    Args:
        encrypt_query_param: 加密的下载参数
        aes_key_base64: base64 编码的 AES Key（内部为 hex 字符串）

    Returns:
        解密后的原始文件数据
    """
    # 1. 解码 AES Key：base64 → hex 字符串 → 原始字节
    aes_key_hex = cdma.base64_to_key_hex(aes_key_base64)
    aes_key = cdma.hex_to_key(aes_key_hex)

    # 2. 构造下载 URL
    download_url = (
        f"{CDN_BASE_URL}/download"
        f"?encrypted_query_param={quote(encrypt_query_param)}"
    )

    # 3. 下载密文
    async with httpx.AsyncClient(timeout=CDN_DOWNLOAD_TIMEOUT) as http_client:
        resp = await http_client.get(download_url)
        if resp.status_code != 200:
            raise RuntimeError(f"CDN download HTTP {resp.status_code}: {resp.text}")
        encrypted = resp.content

    # 4. AES-128-ECB 解密
    plaintext = cdma.decrypt(encrypted, aes_key)
    logger.info(f"CDN 下载成功: {len(encrypted)} bytes → {len(plaintext)} bytes")
    return plaintext


async def download_from_url(url: str) -> Tuple[bytes, str]:
    """
    直接 HTTP GET 下载文件（用于 img.URL 不为空的情况）

    参考 weclaw 的 downloadFile。

    Returns:
        (data, content_type)
    """
    async with httpx.AsyncClient(timeout=CDN_DOWNLOAD_TIMEOUT) as http_client:
        resp = await http_client.get(url)
        if resp.status_code != 200:
            raise RuntimeError(f"download {url} HTTP {resp.status_code}")
        content_type = resp.headers.get("Content-Type", "")
        if not content_type:
            content_type = _infer_content_type(url)
        return resp.content, content_type


# ==================== 媒体类型判断 ====================

def classify_media(content_type: str, url: str) -> Tuple[int, int]:
    """
    根据内容类型和 URL 判断媒体类型

    参考 weclaw 的 classifyMedia。

    Returns:
        (cdn_media_type, item_type)
    """
    ct = content_type.lower()
    if ct.startswith("image/") or _is_image_ext(url):
        return CDNMediaType.IMAGE, ItemType.IMAGE
    if ct.startswith("video/") or _is_video_ext(url):
        return CDNMediaType.VIDEO, ItemType.VIDEO
    return CDNMediaType.FILE, ItemType.FILE


def _is_image_ext(url: str) -> bool:
    ext = _get_ext(url)
    return ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")


def _is_video_ext(url: str) -> bool:
    ext = _get_ext(url)
    return ext in (".mp4", ".mov", ".webm", ".mkv", ".avi")


def _get_ext(url: str) -> str:
    """从 URL 提取扩展名（去除 query string）"""
    path = url.split("?")[0]
    return os.path.splitext(path)[1].lower()


def _infer_content_type(url: str) -> str:
    """根据 URL 扩展名推断 Content-Type"""
    import mimetypes
    ext = _get_ext(url)
    ct, _ = mimetypes.guess_type(url)
    return ct or "application/octet-stream"


# ==================== 发送媒体消息 ====================

async def send_media_from_url(
    client: ILinkClient,
    to_user_id: str,
    media_url: str,
    context_token: str = "",
) -> None:
    """
    从 URL 下载文件并发送为媒体消息

    严格参考 weclaw 的 SendMediaFromURL。
    用于 AI 回复中的 ![](url) 图片链接。
    """
    # 1. 下载文件
    data, content_type = await download_from_url(media_url)

    # 2. 判断媒体类型
    cdn_media_type, item_type = classify_media(content_type, media_url)

    # 3. 上传到 CDN
    download_param, aes_key_hex, raw_size, cipher_size = await upload_to_cdn(
        client, data, to_user_id, cdn_media_type
    )

    # 4. 构造 MediaInfo
    media = MediaInfo(
        encrypt_query_param=download_param,
        aes_key=cdma.key_hex_to_base64(aes_key_hex),
        encrypt_type=EncryptType.AES_128_ECB,
    )

    # 5. 构造消息项
    import os
    filename = os.path.basename(media_url.split("?")[0]) or "file"

    if item_type == ItemType.IMAGE:
        item = MessageItem(type=ItemType.IMAGE, image_item=ImageItem(media=media, mid_size=cipher_size))
    elif item_type == ItemType.VIDEO:
        item = MessageItem(type=ItemType.VIDEO, video_item=VideoItem(media=media, video_size=cipher_size))
    else:
        item = MessageItem(
            type=ItemType.FILE,
            file_item=FileItem(media=media, file_name=filename, len=str(raw_size)),
        )

    # 6. 发送消息
    import uuid
    from .ilink_types import SendMessageRequest, SendMsg
    req = SendMessageRequest(
        msg=SendMsg(
            from_user_id=client.bot_id,
            to_user_id=to_user_id,
            client_id=str(uuid.uuid4()),
            item_list=[item],
            context_token=context_token,
        )
    )
    await client.send_message(req)
    logger.info(f"已发送媒体消息到 {to_user_id}: {content_type}, {len(data)} bytes")
