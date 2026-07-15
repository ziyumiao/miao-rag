"""LangGraph Agent 状态定义"""

from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    messages: list[dict[str, Any]]
    session_id: str
    buyer_nick: str | None

    intent: str
    corrected_entities: dict[str, Any]
    sentiment: str
    pending_business: list[dict[str, Any]]

    keyboard_type: str | None
    switch_structure: str | None
    switch_height: str | None
    compatibility: str

    retrieved_nodes: list[dict[str, Any]]
    graph_context: str
    retrieval_score: float

    missing_info: list[str]
    ask_count: int

    final_answer: str | None
    product_recommendations: list[dict[str, Any]]

    escalate: bool
    escalate_reason: str | None

    orders: list[dict[str, Any]] | None
    web_search_result: dict[str, Any] | None