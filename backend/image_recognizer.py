# -*- coding: utf-8 -*-
"""图片识别模块 — 视觉模型识别 + 优雅降级

不支持 vision 的模型会返回 human_readable 提示，
让 AI 知道自己"看不到图片"但能自然回应。
"""

import base64
from typing import Optional

from openai import OpenAI

from settings import logger, client, current_model


# --- 配置 ---
IMAGE_VISION_MODEL = None   # None = 使用主模型；可设为 "gpt-4o" 等
IMAGE_VISION_TEMP = 0.7

# 视觉模型不可用时的降级消息
VISION_UNAVAILABLE_HINT = (
    "[系统提示] 用户刚刚发送了一张图片，但当前模型不支持图片理解，"
    "你无法看到图片内容。请自然地告诉用户你现在看不到图片，"
    "但可以请用户描述图片内容，或者直接聊其他话题。"
    "不要编造图片内容，也不要假装你看到了。"
)


def _get_vision_client() -> Optional[OpenAI]:
    """获取用于视觉识别的 client。未配置 client 时返回 None"""
    if client is None:
        return None
    return client


def _check_vision_support() -> bool:
    """快速检测当前模型是否可能支持 vision（不发送请求）"""
    cl = _get_vision_client()
    if cl is None:
        # 即使没有API客户端，也可能有本地视觉模型
        return _has_local_vision()
    # 常见 vision 模型关键词
    model_name = (IMAGE_VISION_MODEL or current_model or "").lower()
    vision_keywords = ["gpt-4o", "gpt-4-turbo", "vision", "claude", "gemini",
                       "vl", "visual", "multimodal", "qwen-vl", "glm-4v"]
    api_supports = any(kw in model_name for kw in vision_keywords)
    return api_supports or _has_local_vision()


def _has_local_vision() -> bool:
    """检查本地视觉模型是否已加载"""
    try:
        from main import VISION_MODEL_INSTANCE
        return VISION_MODEL_INSTANCE is not None
    except Exception:
        return False


def recognize_image_base64(image_base64: str, mime_type: str = "image/png") -> dict:
    """
    使用视觉模型识别图片内容。

    Args:
        image_base64: 图片的 Base64 编码（不含 data:xxx;base64, 前缀）
        mime_type: MIME 类型，如 image/png

    Returns:
        {
            "success": bool,
            "text": str,           # 识别结果文本（识别成功时）
            "human_hint": str,     # 给 AI 的提示（识别失败时，告诉 AI 如何回应）
            "vision_supported": bool,  # 模型是否支持视觉
        }
    """
    result = {"success": False, "text": "", "human_hint": "", "vision_supported": False}

    # 1. 检查 client
    cl = _get_vision_client()
    if cl is None:
        # 没有 API 客户端，尝试本地视觉模型
        local_result = _try_local_vision(image_base64, mime_type)
        if local_result:
            return local_result
        result["human_hint"] = VISION_UNAVAILABLE_HINT
        return result

    # 2. 快速预检
    if not _check_vision_support():
        logger.info(f"[图片识别] 当前模型 {current_model} 可能不支持视觉，跳过识别")
        # 尝试本地视觉模型
        local_result = _try_local_vision(image_base64, mime_type)
        if local_result:
            return local_result
        result["human_hint"] = VISION_UNAVAILABLE_HINT
        return result

    # 3. 尝试调用视觉 API
    model = IMAGE_VISION_MODEL or current_model

    prompt = (
        "请用中文简洁描述这张图片的主要内容或主题。"
        "不要使用「这是」「这张」等开头，直接描述。"
        "如果有文字，请包含在描述中。"
        "限制在100字以内。"
    )

    try:
        logger.info(f"[图片识别] 使用模型 {model} 开始识别")
        resp = cl.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_base64}"}},
                    {"type": "text", "text": prompt},
                ]
            }],
            temperature=IMAGE_VISION_TEMP,
            max_tokens=200,
        )
        text = resp.choices[0].message.content.strip() if resp.choices else ""
        if text:
            result["success"] = True
            result["vision_supported"] = True
            result["text"] = f"[用户发送了图片，内容：{text}]"
            logger.info(f"[图片识别] 成功: {text[:80]}...")
        else:
            result["human_hint"] = VISION_UNAVAILABLE_HINT
            logger.warning("[图片识别] 返回空内容")

    except Exception as e:
        err_msg = str(e).lower()
        # 判断是否是不支持 vision 导致的错误
        if any(kw in err_msg for kw in [
            "invalid content type", "image_url not supported",
            "does not support", "unsupported", "not supported",
            "invalid_request", "bad request", "input should be",
            "content must be a string", "content_parts",
        ]):
            logger.info(f"[图片识别] 模型不支持视觉: {str(e)[:120]}")
            result["human_hint"] = VISION_UNAVAILABLE_HINT
        else:
            logger.error(f"[图片识别] 未知错误: {e}", exc_info=True)
            result["human_hint"] = VISION_UNAVAILABLE_HINT

    # 4. 如果 API 模型不支持视觉，尝试使用本地视觉模型
    if not result["success"] and result["human_hint"]:
        local_result = _try_local_vision(image_base64, mime_type)
        if local_result:
            return local_result

    return result


def _try_local_vision(image_base64: str, mime_type: str = "image/png") -> Optional[dict]:
    """尝试使用本地视觉模型识别图片"""
    try:
        # 检查是否配置了本地视觉模型
        from main import VISION_MODEL_INSTANCE, VISION_PROCESSOR_INSTANCE, VISION_CURRENT_MODEL
        
        if VISION_MODEL_INSTANCE is None or VISION_PROCESSOR_INSTANCE is None:
            logger.info("[图片识别] 本地视觉模型未加载，跳过")
            return None
        
        import torch
        from PIL import Image
        from io import BytesIO
        from qwen_vl_utils import process_vision_info
        
        # 解码图片
        image_bytes = base64.b64decode(image_base64)
        pil_image = Image.open(BytesIO(image_bytes)).convert("RGB")
        
        # 缩放
        max_size = 768
        if max(pil_image.size) > max_size:
            ratio = max_size / max(pil_image.size)
            new_size = (int(pil_image.size[0] * ratio), int(pil_image.size[1] * ratio))
            pil_image = pil_image.resize(new_size, Image.LANCZOS)
        
        prompt = "请用中文简洁描述这张图片的主要内容或主题。不要使用「这是」「这张」等开头，直接描述。限制在100字以内。"
        
        messages = [{
            "role": "user",
            "content": [
                {"type": "image", "image": pil_image},
                {"type": "text", "text": prompt},
            ],
        }]
        
        text_input = VISION_PROCESSOR_INSTANCE.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = VISION_PROCESSOR_INSTANCE(
            text=[text_input],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        )
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        if device == "cuda":
            inputs = inputs.to(device)
        
        with torch.inference_mode():
            generated_ids = VISION_MODEL_INSTANCE.generate(
                **inputs,
                max_new_tokens=100,
                do_sample=False,
            )
        
        generated_ids_trimmed = [
            out_ids[len(in_ids):]
            for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        output_text = VISION_PROCESSOR_INSTANCE.batch_decode(
            generated_ids_trimmed,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )[0]
        
        text = output_text.strip()
        if text:
            logger.info(f"[图片识别] 本地视觉模型({VISION_CURRENT_MODEL})成功: {text[:80]}...")
            return {
                "success": True,
                "text": f"[用户发送了图片，内容：{text}]",
                "human_hint": "",
                "vision_supported": True,
            }
    except ImportError:
        logger.info("[图片识别] 本地视觉模型依赖未安装")
    except Exception as e:
        logger.warning(f"[图片识别] 本地视觉模型调用失败: {e}")
    
    return None


def recognize_image_file(file_path: str) -> dict:
    """从文件路径读取图片并识别"""
    import os
    try:
        if not os.path.exists(file_path):
            return {"success": False, "text": "", "human_hint": "", "vision_supported": False}

        ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else "png"
        mime_map = {
            "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "gif": "image/gif", "webp": "image/webp", "bmp": "image/bmp",
        }
        mime = mime_map.get(ext, "image/png")

        with open(file_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")

        return recognize_image_base64(b64, mime)

    except Exception as e:
        logger.error(f"[图片识别] 读取文件失败: {e}")
        return {"success": False, "text": "", "human_hint": VISION_UNAVAILABLE_HINT, "vision_supported": False}