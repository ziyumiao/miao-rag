"""输入清洗：过滤 Prompt 注入模式"""

from __future__ import annotations

import re

_BLOCKED_PATTERNS = [
    # 英文注入
    r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?|messages?)",
    r"disregard\s+(previous|prior|above)\s+(instructions?|prompts?)",
    r"forget\s+(all\s+)?(previous|prior)\s+(instructions?|context)",
    r"you\s+are\s+now\s+(a\s+)?(different|new)\s+(assistant|role|persona)",
    r"act\s+as\s+(if\s+you\s+are|a)\s",
    r"(system|secret)\s+(prompt|instruction|message)",
    r"\bAPI\s*Key\b",
    r"override\s+(system\s+)?(prompt|instruction)",
    r"jailbreak",

    # 中文注入
    r"忽略(所有)?(之前|前面|以上)的(指令|提示|对话)",
    r"忘记(之前|前面)的(指令|内容|规则)",
    r"你现在是(一个)?(新的|不同的)(助手|角色|身份)",
    r"系统提示[词词]",
    r"告诉我你的(指令|提示|规则|API)",
    r"不要(遵守|遵循)(系统|之前)的",
    r"越狱[指指令]",
]


def filter_input(text: str) -> str:
    """过滤输入中的 Prompt 注入模式，返回清洗后的文本"""
    result = text
    for pattern in _BLOCKED_PATTERNS:
        result = re.sub(pattern, "[已过滤]", result, flags=re.IGNORECASE)
    return result
