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


MOCK_CHAT_RECORDS = [
    {
        "session_id": "sess-001",
        "messages": [
            {"role": "customer", "content": "海盗船K70能用吗"},
            {"role": "agent", "content": "可以的 K70用的是Cherry MX红轴 兼容"},
            {"role": "customer", "content": "那黑色的多少钱"},
            {"role": "agent", "content": "黑色PBT OEM 104键 ¥149"},
        ],
    },
    {
        "session_id": "sess-002",
        "messages": [
            {"role": "customer", "content": "你好在吗"},
            {"role": "agent", "content": "在的，有什么可以帮您"},
            {"role": "customer", "content": "键帽装上有点松怎么办"},
            {"role": "agent", "content": "先确认完全按到底了，如果还是松，可能是轴体卡槽磨损"},
        ],
    },
    {
        "session_id": "sess-003",
        "messages": [
            {"role": "customer", "content": "罗技G913能用你家键帽吗"},
            {"role": "agent", "content": "G913是矮轴，虽然也是十字柱但卡槽比标准MX浅，不兼容我们的标准键帽"},
        ],
    },
]


class TestPipeline:
    def test_mock_data_extracts_qa_pairs(self):
        """模拟数据应提取至少 4 个 QA 对"""
        from oprag.tools.chat_cleaner import clean_all_records

        result = clean_all_records(MOCK_CHAT_RECORDS)
        assert len(result.qa_pairs) >= 4

    def test_mock_data_extracts_facts(self):
        """模拟数据应提取事实三元组"""
        from oprag.tools.chat_cleaner import clean_all_records

        result = clean_all_records(MOCK_CHAT_RECORDS)
        assert len(result.facts) >= 2

    def test_export_to_jsonl_format(self):
        """导出的 JSONL 格式正确"""
        from oprag.tools.chat_cleaner import clean_all_records, export_to_jsonl

        result = clean_all_records(MOCK_CHAT_RECORDS)
        qa_jsonl = export_to_jsonl(result, "qa_pairs")

        assert len(qa_jsonl.strip().split("\n")) >= 2
        for line in qa_jsonl.strip().split("\n"):
            item = json.loads(line)
            assert "id" in item
            assert "question" in item
            assert "answer" in item
            assert "tags" in item
            assert "confidence" in item

    def test_export_facts_to_jsonl_format(self):
        """导出的事実 JSONL 格式正确"""
        from oprag.tools.chat_cleaner import clean_all_records, export_to_jsonl

        result = clean_all_records(MOCK_CHAT_RECORDS)
        facts_jsonl = export_to_jsonl(result, "facts")

        assert len(facts_jsonl.strip().split("\n")) >= 1
        for line in facts_jsonl.strip().split("\n"):
            item = json.loads(line)
            assert "id" in item
            assert "entity" in item
            assert "relation" in item
            assert "value" in item


class TestLLMFallback:
    def test_llm_prompt_has_correct_format(self):
        """LLM 兜底提取 prompt 格式正确"""
        from oprag.tools.chat_cleaner import build_llm_extraction_prompt

        conversation = """
        客户: 我上次买的键帽用了一个月就掉色了，这是正常现象吗
        客服: 热升华工艺的一般不会掉色，您方便拍张照片给我看看吗
        """
        prompt = build_llm_extraction_prompt(conversation)
        assert "对话" in prompt or "聊天" in prompt
        assert "提取" in prompt
        assert "JSON" in prompt
        assert "qa_pairs" in prompt
        assert "facts" in prompt

    def test_complex_conversation_falls_back_to_llm(self):
        """无规则匹配的复杂对话进入 LLM 兜底"""
        messages = [
            ChatMessage(role="customer", content="我上次买的键帽用了一个月就掉色了，售后能处理吗"),
            ChatMessage(role="agent", content="请提供订单号，我帮您查看"),
        ]
        # 不用 LLM 时规则不匹配，应返回空结果
        result = clean_chat_record(messages)
        assert len(result.qa_pairs) == 0

    def test_pipeline_records_rule_misses(self):
        """管线记录规则未命中的对话供 LLM 处理"""
        from oprag.tools.chat_cleaner import clean_all_records

        records = [
            {
                "session_id": "sess-004",
                "messages": [
                    {"role": "customer", "content": "键帽掉色了要退货"},
                    {"role": "agent", "content": "请提供订单号"},
                ],
            },
        ]
        result = clean_all_records(records)
        # 规则未命中，应标记为 LLM 待处理
        assert result.rule_misses >= 1
        assert len(result.qa_pairs) == 0
