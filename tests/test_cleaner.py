"""P2 清洗流水线测试"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from oprag.tools.chat_cleaner import (
    ExtractedQA,
    ExtractedFact,
    clean_chat_record,
)


@dataclass
class ChatMessage:
    role: str  # "customer" | "agent"
    content: str


class TestRuleEngine:
    def test_extracts_compatibility_qa(self):
        """兼容性句式：xxx能用吗 → QA 对"""
        messages = [
            ChatMessage(role="customer", content="海盗船K70能用你家键帽不"),
            ChatMessage(role="agent", content="可以的，K70用的是Cherry MX轴，我们的键帽都适配标准MX轴体"),
        ]
        result = clean_chat_record(messages)
        assert len(result.qa_pairs) >= 1
        qa = result.qa_pairs[0]
        assert "K70" in qa.question
        assert "兼容" in qa.question or "K70" in qa.question
        assert "MX" in qa.answer
        assert len(qa.tags) >= 1

    def test_extracts_switch_type_qa(self):
        """轴体句式：xxx用什么轴 → QA 对"""
        messages = [
            ChatMessage(role="customer", content="Filco忍者87是什么轴体"),
            ChatMessage(role="agent", content="Filco用的Cherry MX轴，标准十字柱结构"),
        ]
        result = clean_chat_record(messages)
        assert len(result.qa_pairs) >= 1
        qa = result.qa_pairs[0]
        assert "Filco" in qa.question
        assert "Cherry MX" in qa.answer or "MX" in qa.answer

    def test_extracts_price_inquiry(self):
        """价格句式：xxx多少钱 → QA 对"""
        messages = [
            ChatMessage(role="customer", content="OEM PBT那套多少钱"),
            ChatMessage(role="agent", content="OEM PBT 104键套 ¥149，现在还有满减"),
        ]
        result = clean_chat_record(messages)
        assert len(result.qa_pairs) >= 1
        qa = result.qa_pairs[0]
        assert "OEM" in qa.question or "PBT" in qa.question
        assert "149" in qa.answer

    def test_ignores_chitchat(self):
        """闲聊不提取为 QA 对"""
        messages = [
            ChatMessage(role="customer", content="在吗"),
            ChatMessage(role="agent", content="在的，有什么可以帮您"),
            ChatMessage(role="customer", content="好的谢谢"),
        ]
        result = clean_chat_record(messages)
        assert len(result.qa_pairs) == 0

    def test_extracts_fact_from_agent_reply(self):
        """提取事实三元组：K70 uses Cherry MX"""
        messages = [
            ChatMessage(role="customer", content="海盗船K70能用不"),
            ChatMessage(role="agent", content="可以的，K70用的是Cherry MX轴"),
        ]
        result = clean_chat_record(messages)
        assert len(result.facts) >= 1
        fact = result.facts[0]
        assert fact.entity == "Corsair K70"
        assert fact.relation == "uses_switch"
        assert fact.value == "Cherry MX"

    def test_extracts_multi_turn_conversation(self):
        """多轮对话中提取多个 QA 对"""
        messages = [
            ChatMessage(role="customer", content="海盗船K70能用吗"),
            ChatMessage(role="agent", content="可以的，K70是Cherry MX轴，适配"),
            ChatMessage(role="customer", content="那黑色的多少钱"),
            ChatMessage(role="agent", content="黑色PBT OEM高度 ¥149"),
        ]
        result = clean_chat_record(messages)
        assert len(result.qa_pairs) >= 1
        assert len(result.facts) >= 1
