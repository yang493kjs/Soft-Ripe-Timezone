# -*- coding: utf-8 -*-
"""iLink API 数据结构定义

严格参考 weclaw/ilink/types.go，使用 dataclass 实现。
所有字段与 iLink API JSON 格式一一对应。
"""
from dataclasses import dataclass, field
from typing import Optional, List
import json


# ==================== 消息类型常量 ====================

class MessageType:
    NONE = 0
    USER = 1
    BOT = 2


class MessageState:
    NEW = 0
    GENERATING = 1
    FINISH = 2


class ItemType:
    NONE = 0
    TEXT = 1
    IMAGE = 2
    VOICE = 3
    FILE = 4
    VIDEO = 5


class CDNMediaType:
    IMAGE = 1
    VIDEO = 2
    FILE = 3


class TypingStatus:
    TYPING = 1
    CANCEL = 2


class EncryptType:
    """CDN 媒体加密类型"""
    AES_128_ECB = 1


# ==================== 扫码登录相关 ====================

@dataclass
class QRCodeResponse:
    """get_bot_qrcode 响应"""
    qrcode: str = ""
    qrcode_img_content: str = ""  # base64 编码的二维码图片

    @classmethod
    def from_dict(cls, d: dict) -> "QRCodeResponse":
        return cls(
            qrcode=d.get("qrcode", ""),
            qrcode_img_content=d.get("qrcode_img_content", ""),
        )


@dataclass
class QRStatusResponse:
    """get_qrcode_status 响应"""
    status: str = ""  # wait / scaned / confirmed / expired
    bot_token: str = ""
    ilink_bot_id: str = ""
    base_url: str = ""  # JSON key: baseurl
    ilink_user_id: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "QRStatusResponse":
        return cls(
            status=d.get("status", ""),
            bot_token=d.get("bot_token", ""),
            ilink_bot_id=d.get("ilink_bot_id", ""),
            base_url=d.get("baseurl", ""),
            ilink_user_id=d.get("ilink_user_id", ""),
        )


# ==================== 凭证 ====================

@dataclass
class Credentials:
    """微信机器人登录凭证"""
    bot_token: str = ""
    ilink_bot_id: str = ""
    base_url: str = ""  # JSON key: baseurl
    ilink_user_id: str = ""

    # 以下字段由本系统附加，不在 iLink API 原始响应中
    bot_id: str = ""       # 本系统内部 bot 标识（= ilink_bot_id 的规范化形式）
    user_id: str = ""      # 归属的系统用户 ID
    created_at: str = ""   # 创建时间 ISO 格式

    def to_dict(self) -> dict:
        return {
            "bot_token": self.bot_token,
            "ilink_bot_id": self.ilink_bot_id,
            "base_url": self.base_url,
            "ilink_user_id": self.ilink_user_id,
            "bot_id": self.bot_id,
            "user_id": self.user_id,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Credentials":
        return cls(
            bot_token=d.get("bot_token", ""),
            ilink_bot_id=d.get("ilink_bot_id", ""),
            base_url=d.get("base_url", d.get("baseurl", "")),
            ilink_user_id=d.get("ilink_user_id", ""),
            bot_id=d.get("bot_id", ""),
            user_id=d.get("user_id", ""),
            created_at=d.get("created_at", ""),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


# ==================== 消息相关 ====================

@dataclass
class BaseInfo:
    """请求体中的基础信息"""
    channel_version: str = "1.0.0"


@dataclass
class MediaInfo:
    """CDN 媒体引用（已上传文件的下载信息）"""
    encrypt_query_param: str = ""
    aes_key: str = ""         # base64 编码（内部为 hex 字符串）
    encrypt_type: int = 0     # 1 = AES-128-ECB

    def to_dict(self) -> dict:
        return {
            "encrypt_query_param": self.encrypt_query_param,
            "aes_key": self.aes_key,
            "encrypt_type": self.encrypt_type,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Optional["MediaInfo"]:
        if d is None:
            return None
        return cls(
            encrypt_query_param=d.get("encrypt_query_param", ""),
            aes_key=d.get("aes_key", ""),
            encrypt_type=d.get("encrypt_type", 0),
        )


@dataclass
class TextItem:
    text: str = ""

    def to_dict(self) -> dict:
        return {"text": self.text}

    @classmethod
    def from_dict(cls, d: dict) -> "TextItem":
        return cls(text=d.get("text", ""))


@dataclass
class ImageItem:
    url: str = ""
    media: Optional[MediaInfo] = None
    mid_size: int = 0  # 密文大小

    def to_dict(self) -> dict:
        d = {}
        if self.url:
            d["url"] = self.url
        if self.media:
            d["media"] = self.media.to_dict()
        if self.mid_size:
            d["mid_size"] = self.mid_size
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "ImageItem":
        return cls(
            url=d.get("url", ""),
            media=MediaInfo.from_dict(d.get("media")),
            mid_size=d.get("mid_size", 0),
        )


@dataclass
class VoiceItem:
    media: Optional[MediaInfo] = None
    voice_size: int = 0
    encode_type: int = 0    # 1=pcm 2=adpcm 3=feature 4=speex 5=amr 6=silk 7=mp3
    bits_per_sample: int = 0
    sample_rate: int = 0    # Hz
    playtime: int = 0       # 毫秒
    text: str = ""          # 微信自动语音转文字结果

    def to_dict(self) -> dict:
        d = {}
        if self.media:
            d["media"] = self.media.to_dict()
        if self.voice_size:
            d["voice_size"] = self.voice_size
        if self.encode_type:
            d["encode_type"] = self.encode_type
        if self.bits_per_sample:
            d["bits_per_sample"] = self.bits_per_sample
        if self.sample_rate:
            d["sample_rate"] = self.sample_rate
        if self.playtime:
            d["playtime"] = self.playtime
        if self.text:
            d["text"] = self.text
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "VoiceItem":
        return cls(
            media=MediaInfo.from_dict(d.get("media")),
            voice_size=d.get("voice_size", 0),
            encode_type=d.get("encode_type", 0),
            bits_per_sample=d.get("bits_per_sample", 0),
            sample_rate=d.get("sample_rate", 0),
            playtime=d.get("playtime", 0),
            text=d.get("text", ""),
        )


@dataclass
class VideoItem:
    media: Optional[MediaInfo] = None
    video_size: int = 0

    def to_dict(self) -> dict:
        d = {}
        if self.media:
            d["media"] = self.media.to_dict()
        if self.video_size:
            d["video_size"] = self.video_size
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "VideoItem":
        return cls(
            media=MediaInfo.from_dict(d.get("media")),
            video_size=d.get("video_size", 0),
        )


@dataclass
class FileItem:
    media: Optional[MediaInfo] = None
    file_name: str = ""
    len: str = ""  # 明文大小，字符串形式

    def to_dict(self) -> dict:
        d = {}
        if self.media:
            d["media"] = self.media.to_dict()
        if self.file_name:
            d["file_name"] = self.file_name
        if self.len:
            d["len"] = self.len
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "FileItem":
        return cls(
            media=MediaInfo.from_dict(d.get("media")),
            file_name=d.get("file_name", ""),
            len=d.get("len", ""),
        )


@dataclass
class MessageItem:
    """消息子项"""
    type: int = ItemType.TEXT
    text_item: Optional[TextItem] = None
    image_item: Optional[ImageItem] = None
    voice_item: Optional[VoiceItem] = None
    video_item: Optional[VideoItem] = None
    file_item: Optional[FileItem] = None

    def to_dict(self) -> dict:
        d = {"type": self.type}
        if self.text_item:
            d["text_item"] = self.text_item.to_dict()
        if self.image_item:
            d["image_item"] = self.image_item.to_dict()
        if self.voice_item:
            d["voice_item"] = self.voice_item.to_dict()
        if self.video_item:
            d["video_item"] = self.video_item.to_dict()
        if self.file_item:
            d["file_item"] = self.file_item.to_dict()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "MessageItem":
        return cls(
            type=d.get("type", ItemType.TEXT),
            text_item=TextItem.from_dict(d["text_item"]) if d.get("text_item") else None,
            image_item=ImageItem.from_dict(d["image_item"]) if d.get("image_item") else None,
            voice_item=VoiceItem.from_dict(d["voice_item"]) if d.get("voice_item") else None,
            video_item=VideoItem.from_dict(d["video_item"]) if d.get("video_item") else None,
            file_item=FileItem.from_dict(d["file_item"]) if d.get("file_item") else None,
        )


@dataclass
class WeixinMessage:
    """单条微信消息"""
    seq: int = 0
    message_id: int = 0
    from_user_id: str = ""
    to_user_id: str = ""
    message_type: int = MessageType.USER
    message_state: int = MessageState.FINISH
    item_list: List[MessageItem] = field(default_factory=list)
    context_token: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "WeixinMessage":
        items = [MessageItem.from_dict(item) for item in d.get("item_list", [])]
        return cls(
            seq=d.get("seq", 0),
            message_id=d.get("message_id", 0),
            from_user_id=d.get("from_user_id", ""),
            to_user_id=d.get("to_user_id", ""),
            message_type=d.get("message_type", MessageType.USER),
            message_state=d.get("message_state", MessageState.FINISH),
            item_list=items,
            context_token=d.get("context_token", ""),
        )


# ==================== 请求/响应结构 ====================

@dataclass
class GetUpdatesRequest:
    get_updates_buf: str = ""
    base_info: BaseInfo = field(default_factory=BaseInfo)

    def to_dict(self) -> dict:
        return {
            "get_updates_buf": self.get_updates_buf,
            "base_info": {"channel_version": self.base_info.channel_version},
        }


@dataclass
class GetUpdatesResponse:
    """长轮询响应"""
    ret: int = 0
    err_code: int = 0
    err_msg: str = ""
    msgs: List[WeixinMessage] = field(default_factory=list)
    get_updates_buf: str = ""
    long_polling_timeout_ms: int = 0

    @classmethod
    def from_dict(cls, d: dict) -> "GetUpdatesResponse":
        msgs = [WeixinMessage.from_dict(m) for m in d.get("msgs", [])]
        return cls(
            ret=d.get("ret", 0),
            err_code=d.get("errcode", 0),
            err_msg=d.get("errmsg", ""),
            msgs=msgs,
            get_updates_buf=d.get("get_updates_buf", ""),
            long_polling_timeout_ms=d.get("longpolling_timeout_ms", 0),
        )


@dataclass
class SendMsg:
    """发送消息的消息体"""
    from_user_id: str = ""
    to_user_id: str = ""
    client_id: str = ""
    message_type: int = MessageType.BOT
    message_state: int = MessageState.FINISH
    item_list: List[MessageItem] = field(default_factory=list)
    context_token: str = ""

    def to_dict(self) -> dict:
        return {
            "from_user_id": self.from_user_id,
            "to_user_id": self.to_user_id,
            "client_id": self.client_id,
            "message_type": self.message_type,
            "message_state": self.message_state,
            "item_list": [item.to_dict() for item in self.item_list],
            "context_token": self.context_token,
        }


@dataclass
class SendMessageRequest:
    msg: SendMsg = field(default_factory=SendMsg)
    base_info: BaseInfo = field(default_factory=BaseInfo)

    def to_dict(self) -> dict:
        return {
            "msg": self.msg.to_dict(),
            "base_info": {"channel_version": self.base_info.channel_version},
        }


@dataclass
class SendMessageResponse:
    ret: int = 0
    err_msg: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "SendMessageResponse":
        return cls(
            ret=d.get("ret", 0),
            err_msg=d.get("errmsg", ""),
        )


@dataclass
class GetUploadURLRequest:
    file_key: str = ""
    media_type: int = CDNMediaType.IMAGE
    to_user_id: str = ""
    raw_size: int = 0
    raw_file_md5: str = ""
    file_size: int = 0
    no_need_thumb: bool = True
    aes_key: str = ""  # hex 编码
    base_info: BaseInfo = field(default_factory=BaseInfo)

    def to_dict(self) -> dict:
        return {
            "filekey": self.file_key,
            "media_type": self.media_type,
            "to_user_id": self.to_user_id,
            "rawsize": self.raw_size,
            "rawfilemd5": self.raw_file_md5,
            "filesize": self.file_size,
            "no_need_thumb": self.no_need_thumb,
            "aeskey": self.aes_key,
            "base_info": {"channel_version": self.base_info.channel_version},
        }


@dataclass
class GetUploadURLResponse:
    ret: int = 0
    err_msg: str = ""
    upload_param: str = ""
    upload_full_url: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "GetUploadURLResponse":
        return cls(
            ret=d.get("ret", 0),
            err_msg=d.get("errmsg", ""),
            upload_param=d.get("upload_param", ""),
            upload_full_url=d.get("upload_full_url", ""),
        )


@dataclass
class GetConfigRequest:
    ilink_user_id: str = ""
    context_token: str = ""
    base_info: BaseInfo = field(default_factory=BaseInfo)

    def to_dict(self) -> dict:
        return {
            "ilink_user_id": self.ilink_user_id,
            "context_token": self.context_token,
            "base_info": {"channel_version": self.base_info.channel_version},
        }


@dataclass
class GetConfigResponse:
    ret: int = 0
    err_msg: str = ""
    typing_ticket: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "GetConfigResponse":
        return cls(
            ret=d.get("ret", 0),
            err_msg=d.get("errmsg", ""),
            typing_ticket=d.get("typing_ticket", ""),
        )


@dataclass
class SendTypingRequest:
    ilink_user_id: str = ""
    typing_ticket: str = ""
    status: int = TypingStatus.TYPING
    base_info: BaseInfo = field(default_factory=BaseInfo)

    def to_dict(self) -> dict:
        return {
            "ilink_user_id": self.ilink_user_id,
            "typing_ticket": self.typing_ticket,
            "status": self.status,
            "base_info": {"channel_version": self.base_info.channel_version},
        }


@dataclass
class SendTypingResponse:
    ret: int = 0
    err_msg: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "SendTypingResponse":
        return cls(
            ret=d.get("ret", 0),
            err_msg=d.get("errmsg", ""),
        )
