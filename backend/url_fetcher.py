# -*- coding: utf-8 -*-
"""URL 链接内容提取模块"""

import re
from typing import Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from settings import logger

# --- 配置 ---
MAX_WEB_CONTENT_LENGTH = 2000
REQUESTS_TIMEOUT = 10
REQUESTS_USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/91.0.4472.124 Mobile Safari/537.36"
)

URL_PATTERN = re.compile(r"https?://[^\s，,。！？!?\u4e00-\u9fff]+")


def extract_urls(text: str) -> list:
    """从文本中提取所有 URL"""
    return URL_PATTERN.findall(text)


def fetch_and_extract_text(url: str) -> Optional[str]:
    """获取 URL 网页内容并提取主要文本"""
    try:
        parsed = urlparse(url)
        if not all([parsed.scheme, parsed.netloc]):
            logger.warning(f"[URL抓取] 无效URL: {url}")
            return None

        logger.info(f"[URL抓取] 开始: {url}")
        resp = requests.get(
            url, headers={"User-Agent": REQUESTS_USER_AGENT},
            timeout=REQUESTS_TIMEOUT, allow_redirects=True
        )
        resp.raise_for_status()

        ct = resp.headers.get("Content-Type", "").lower()
        if "html" not in ct:
            logger.warning(f"[URL抓取] 非HTML({ct}): {url}")
            return None

        soup = BeautifulSoup(resp.content, "lxml")
        main_selectors = ["article", "main", ".main-content", "#content", ".post-content"]
        main_text = ""
        for sel in main_selectors:
            el = soup.select_one(sel)
            if el:
                main_text = el.get_text(separator="\n", strip=True)
                break

        if not main_text and soup.body:
            main_text = soup.body.get_text(separator="\n", strip=True)
        elif not main_text:
            main_text = soup.get_text(separator="\n", strip=True)

        lines = [ln for ln in main_text.splitlines() if ln.strip()]
        cleaned = "\n".join(lines)

        if len(cleaned) > MAX_WEB_CONTENT_LENGTH:
            cleaned = cleaned[:MAX_WEB_CONTENT_LENGTH] + "..."
            logger.info(f"[URL抓取] 截断至 {MAX_WEB_CONTENT_LENGTH} 字符")
        elif cleaned:
            logger.info(f"[URL抓取] 成功 {len(cleaned)} 字符")
        else:
            logger.warning(f"[URL抓取] 无有效文本: {url}")
            return None

        return cleaned

    except requests.exceptions.Timeout:
        logger.error(f"[URL抓取] 超时: {url}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"[URL抓取] 网络错误: {url}, {e}")
        return None
    except Exception as e:
        logger.error(f"[URL抓取] 未知错误: {url}, {e}", exc_info=True)
        return None


def process_urls_in_message(message: str) -> dict:
    """处理消息中的 URL，返回抓取结果"""
    urls = extract_urls(message)
    if not urls:
        return {"urls": [], "fetched": {}}

    logger.info(f"[URL抓取] 检测到 {len(urls)} 个URL")
    fetched = {}
    for url in urls[:3]:
        text = fetch_and_extract_text(url)
        if text:
            fetched[url] = text

    return {"urls": urls, "fetched": fetched}