"""LangGraph Agent 节点实现（P0 占位）"""

from __future__ import annotations

from oprag.agent.state import AgentState


async def intent_recognition(state: AgentState) -> dict:
    """P0 占位：意图识别节点"""
    return {
        "intent": "unknown",
        "sentiment": "neutral",
        "pending_business": [],
        "missing_info": [],
        "ask_count": state.get("ask_count", 0) + 1,
    }


async def retrieve(state: AgentState) -> dict:
    """P0 占位：检索节点"""
    return {
        "retrieved_nodes": [],
        "graph_context": "",
        "retrieval_score": 0.0,
    }


async def generate_answer(state: AgentState) -> dict:
    """P0 占位：生成答案节点"""
    return {
        "final_answer": "系统初始化中，请稍后再试。",
        "escalate": False,
    }


async def escalate(state: AgentState) -> dict:
    """P0 占位：人工转接节点"""
    return {
        "final_answer": "已为您转接人工客服，请稍候。",
        "escalate": True,
        "escalate_reason": state.get("escalate_reason", "系统未就绪"),
    }