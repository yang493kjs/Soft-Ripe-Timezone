# -*- coding: utf-8 -*-
"""AES-128-ECB 加密/解密工具

严格参考 weclaw/messaging/cdn.go 中的实现：
- 加密：PKCS7 填充 → AES-128-ECB 加密
- 解密：AES-128-ECB 解密 → 去除 PKCS7 填充
- Key 生成：16 字节随机数
- Key 编码：原始字节 → hex 字符串（用于 API 传输）→ base64（用于消息项）
"""
import os
import base64
import hashlib

from Crypto.Cipher import AES

BLOCK_SIZE = AES.block_size  # 16


def generate_aes_key() -> bytes:
    """生成 16 字节随机 AES Key（原始字节）"""
    return os.urandom(16)


def generate_file_key() -> bytes:
    """生成 16 字节随机 filekey（原始字节）"""
    return os.urandom(16)


def key_to_hex(key: bytes) -> str:
    """原始字节 → hex 字符串"""
    return key.hex()


def hex_to_key(hex_str: str) -> bytes:
    """hex 字符串 → 原始字节"""
    return bytes.fromhex(hex_str)


def key_hex_to_base64(hex_str: str) -> str:
    """
    hex 字符串 → base64 编码（用于消息项中的 aes_key 字段）

    参考 weclaw 的 AESKeyToBase64：
    base64( hex_string_as_bytes )
    注意：不是 base64(raw_key_bytes)，而是 base64(hex_string)
    """
    return base64.b64encode(hex_str.encode("ascii")).decode("ascii")


def base64_to_key_hex(b64_str: str) -> str:
    """
    base64 编码 → hex 字符串

    参考 weclaw 的 DownloadFileFromCDN：
    base64_decode → 得到 hex 字符串
    """
    return base64.b64decode(b64_str).decode("ascii")


def _pkcs7_pad(data: bytes) -> bytes:
    """PKCS7 填充"""
    pad_len = BLOCK_SIZE - (len(data) % BLOCK_SIZE)
    return data + bytes([pad_len] * pad_len)


def _pkcs7_unpad(data: bytes) -> bytes:
    """去除 PKCS7 填充"""
    if not data:
        return data
    pad_len = data[-1]
    if pad_len > BLOCK_SIZE or pad_len == 0:
        raise ValueError("invalid PKCS7 padding")
    return data[:-pad_len]


def encrypt(data: bytes, key: bytes) -> bytes:
    """
    AES-128-ECB 加密（PKCS7 填充）

    参考 weclaw 的 encryptAESECB
    """
    if len(key) != 16:
        raise ValueError(f"AES key must be 16 bytes, got {len(key)}")
    cipher = AES.new(key, AES.MODE_ECB)
    padded = _pkcs7_pad(data)
    return cipher.encrypt(padded)


def decrypt(ciphertext: bytes, key: bytes) -> bytes:
    """
    AES-128-ECB 解密（去除 PKCS7 填充）

    参考 weclaw 的 decryptAESECB
    """
    if len(key) != 16:
        raise ValueError(f"AES key must be 16 bytes, got {len(key)}")
    if len(ciphertext) % BLOCK_SIZE != 0:
        raise ValueError("ciphertext is not a multiple of block size")
    cipher = AES.new(key, AES.MODE_ECB)
    plaintext = cipher.decrypt(ciphertext)
    return _pkcs7_unpad(plaintext)


def padded_size(plaintext_size: int) -> int:
    """计算 PKCS7 填充后的密文大小

    参考 weclaw 的 aesECBPaddedSize
    """
    return (plaintext_size // BLOCK_SIZE + 1) * BLOCK_SIZE


def md5_hex(data: bytes) -> str:
    """计算 MD5 并返回 hex 字符串"""
    return hashlib.md5(data).hexdigest()
