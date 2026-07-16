"""聊天记录清洗流水线

规则引擎（70% 覆盖率）+ LLM 兜底（30%）。

规则覆盖句式：
- 兼容性："xxx能用吗"
- 轴体："xxx是什么轴"
- 价格："xxx多少钱"
- 材质/高度/安装等

输入：对话消息列表 [{role, content}]
输出：ExtractedResult {qa_pairs, facts}
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field


@dataclass
class ExtractedQA:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    question: str = ""
    answer: str = ""
    tags: list[str] = field(default_factory=list)
    source: str = ""
    confidence: float = 0.9


@dataclass
class ExtractedFact:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    entity: str = ""
    relation: str = ""
    value: str = ""
    source: str = ""
    confidence: float = 0.9


@dataclass
class ExtractedResult:
    qa_pairs: list[ExtractedQA] = field(default_factory=list)
    facts: list[ExtractedFact] = field(default_factory=list)


# 品牌中文 → 英文标准化映射
BRAND_ALIAS = {
    "海盗船": "Corsair",
    "罗技": "Logitech",
    "樱桃": "Cherry",
    "雷蛇": "Razer",
    "利奥博德": "Leopold",
    "阿米洛": "Varmilo",
    "鸭子": "Ducky",
    "渴创": "Keychron",
    "阿克": "Akko",
    "铝厂": "iQunix",
    "怒喵": "Angry Miao",
}

# 规则模板：{pattern, qa_generator, fact_extractor}
QUESTION_PATTERNS = [
    # 兼容性
    (
        re.compile(r"(?P<model>.+?)(?:能不能用|能用[吗不]|兼容吗|适配吗|能不能装|可不可以用|支持吗)"),
        lambda m: ExtractedQA(
            question=f"{m['model']}兼容性",
            answer="",
            tags=["兼容性", m["model"]],
        ),
        lambda m, agent_reply: _extract_switch_fact(m["model"], agent_reply),
    ),
    # 兼容性变体："xxx能用你家键帽不"
    (
        re.compile(r"(?P<model>.+?)能用(?:你家|你们|这个|这些|你这里)(?:键帽|键盘帽|的)?[不吗]"),
        lambda m: ExtractedQA(
            question=f"{m['model']}兼容性",
            answer="",
            tags=["兼容性", m["model"]],
        ),
        lambda m, agent_reply: _extract_switch_fact(m["model"], agent_reply),
    ),
    # 轴体类型
    (
        re.compile(r"(?P<keyboard>.+?)(?:用什么轴|是什么轴|轴体是什么|什么轴体|用的什么轴)"),
        lambda m: ExtractedQA(
            question=f"{m['keyboard']}轴体类型",
            answer="",
            tags=["轴体查询", m["keyboard"]],
        ),
        lambda m, agent_reply: _extract_switch_fact(m["keyboard"], agent_reply),
    ),
    # 价格
    (
        re.compile(r"(?P<product>.+?)(?:多少钱|价格|怎么卖|什么价|报价)"),
        lambda m: ExtractedQA(
            question=f"{m['product']}价格",
            answer="",
            tags=["价格查询", m["product"]],
        ),
        lambda m, agent_reply: None,
    ),
    # 材质
    (
        re.compile(r"(?P<product>.+?)(?:什么材质|材质|PBT|ABS)"),
        lambda m: ExtractedQA(
            question=f"{m['product']}材质",
            answer="",
            tags=["材质查询", m["product"]],
        ),
        lambda m, agent_reply: None,
    ),
]

# 客服回复中的信息提取
AGENT_SWITCH_PATTERN = re.compile(
    r"(?:用的是|使用的是|搭载的是|采用|是|用)[\s的]*(?P<switch>.+?)(?:轴)",
)
AGENT_COMPAT_POSITIVE = re.compile(
    r"(?:可以的|没问题|能用的|兼容|支持|适配|可以的|能用)",
)
AGENT_COMPAT_NEGATIVE = re.compile(
    r"(?:不行|不能|不兼容|不支持|不适用|装不了)",
)


def _normalize_model(model_str: str) -> str:
    """标准化键盘型号名"""
    for cn, en in BRAND_ALIAS.items():
        if cn in model_str:
            remainder = model_str.replace(cn, "").strip()
            return f"{en} {remainder}" if remainder else en
    return model_str.strip()


def _extract_switch_fact(model_str: str, agent_reply: str) -> ExtractedFact | None:
    """从客服回复中提取键盘-轴体关系"""
    entity = _normalize_model(model_str)
    match = AGENT_SWITCH_PATTERN.search(agent_reply)
    if match:
        switch_val = match.group("switch").rstrip("轴").strip()
        return ExtractedFact(
            entity=entity,
            relation="uses_switch",
            value=switch_val,
        )
    return None


def _find_agent_reply(messages: list, customer_idx: int) -> str:
    """找到客户消息后最近的一条客服回复"""
    for i in range(customer_idx + 1, len(messages)):
        if messages[i].role == "agent":
            return messages[i].content
    return ""


def clean_chat_record(messages: list) -> ExtractedResult:
    """清洗一段聊天记录，提取 QA 对和事实

    Args:
        messages: [{role: "customer"|"agent", content: "消息内容"}]

    Returns:
        ExtractedResult 包含 qa_pairs 和 facts
    """
    result = ExtractedResult()

    for i, msg in enumerate(messages):
        if msg.role != "customer":
            continue

        content = msg.content.strip()
        agent_reply = _find_agent_reply(messages, i)

        for pattern, qa_gen, fact_gen in QUESTION_PATTERNS:
            m = pattern.search(content)
            if m:
                qa = qa_gen(m)
                if agent_reply:
                    qa.answer = agent_reply
                result.qa_pairs.append(qa)

                if fact_gen and agent_reply:
                    fact = fact_gen(m, agent_reply)
                    if fact:
                        result.facts.append(fact)
                break  # 一条客户消息只匹配一个规则

    return result
