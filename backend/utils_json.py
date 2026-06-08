# -*- coding: utf-8 -*-
"""LLM JSON 容错解析工具"""
import json
import re


def parse_llm_json(raw: str) -> dict:
    """容错的LLM JSON解析：处理尾随逗号、缺少引号等问题"""
    text = raw.strip()
    text = re.sub(r'^```\w*\n?', '', text)
    text = re.sub(r'\n?```$', '', text)
    text = text.strip()

    # 方案1: 直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 方案2: 用正则提取最外层{}
    m = re.search(r'\{[\s\S]*\}', text)
    if m:
        candidate = m.group()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    else:
        candidate = text

    # 方案3: 修复常见LLM JSON错误
    try:
        fixed = _repair_llm_json(candidate)
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # 方案4: 逐行修复 + 宽松解析
    try:
        fixed = _aggressive_repair_json(candidate)
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    raise ValueError(f"无法解析LLM JSON: {raw[:200]}")


def _repair_llm_json(text: str) -> str:
    """修复常见LLM JSON错误"""
    # 移除尾随逗号（最常见的错误）
    text = re.sub(r',\s*}', '}', text)
    text = re.sub(r',\s*]', ']', text)

    # 修复单引号问题（在key和string value中）
    lines = text.split('\n')
    repaired_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            repaired_lines.append(line)
            continue

        match = re.match(r'^(["\']?)(\w+)(["\']?)(\s*:\s*)(.*)', stripped)
        if match:
            key = match.group(2)
            separator = match.group(4)
            value_part = match.group(5)

            if not key.startswith('"'):
                key = f'"{key}"'
            else:
                key = f'"{key.strip(chr(34))}"'

            repaired_lines.append(f'{key}{separator}{value_part}')
        else:
            repaired_lines.append(line)

    return '\n'.join(repaired_lines)


def _aggressive_repair_json(text: str) -> str:
    """激进修复：基于简单状态机"""
    result = []
    i = 0
    in_string = False
    escape_next = False

    while i < len(text):
        ch = text[i]

        if escape_next:
            result.append(ch)
            escape_next = False
            i += 1
            continue

        if ch == '\\':
            result.append(ch)
            escape_next = True
            i += 1
            continue

        if ch == '"':
            in_string = not in_string
            result.append(ch)
            i += 1
            continue

        if not in_string:
            if ch == '\n' or ch == '\r':
                result.append(' ')
                i += 1
                continue
            # 处理 // 注释
            if ch == '/' and i + 1 < len(text) and text[i+1] == '/':
                while i < len(text) and text[i] not in ('\n', '\r'):
                    i += 1
                continue
            # 处理 /* */ 注释
            if ch == '/' and i + 1 < len(text) and text[i+1] == '*':
                i += 2
                while i + 1 < len(text):
                    if text[i] == '*' and text[i+1] == '/':
                        i += 2
                        break
                    i += 1
                continue

        result.append(ch)
        i += 1

    text = ''.join(result)

    # 再次移除尾随逗号
    text = re.sub(r',\s*}', '}', text)
    text = re.sub(r',\s*]', ']', text)

    # 将单引号替换为双引号
    text = re.sub(r'([\{,]\s*)(\w+)(\s*:)', r'\1"\2"\3', text)

    # 修复字符串值中的未转义换行符
    text = text.replace('\n', '\\n')

    return text
