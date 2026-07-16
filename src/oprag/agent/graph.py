"""LangGraph 状态图构建（P0 空壳流程）"""

from __future__ import annotations

import logging

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from oprag.agent.state import AgentState
from oprag.agent.nodes import intent_recognition, retrieve, generate_answer, escalate
from oprag.config import settings

logger = logging.getLogger(__name__)


def _route_after_intent(state: AgentState) -> str:
    # TODO P4: 扩展为三分路由 — direct_answer / retrieve / escalate
    if state.get("escalate"):
        return "escalate"
    return "retrieve"


def _route_after_generate(state: AgentState) -> str:
    if state.get("escalate"):
        return "escalate"
    return END


def build_graph() -> StateGraph:
    builder = StateGraph(AgentState)

    builder.add_node("intent_recognition", intent_recognition)
    builder.add_node("retrieve", retrieve)
    builder.add_node("generate_answer", generate_answer)
    builder.add_node("escalate", escalate)

    builder.add_edge(START, "intent_recognition")

    builder.add_conditional_edges(
        "intent_recognition",
        _route_after_intent,
        {"retrieve": "retrieve", "escalate": "escalate"},
    )

    # P0 阶段常量路由，P4 引入检索质量判断后改为 conditional_edges
    builder.add_edge("retrieve", "generate_answer")

    builder.add_conditional_edges(
        "generate_answer",
        _route_after_generate,
        {END: END, "escalate": "escalate"},
    )

    builder.add_edge("escalate", END)

    return builder


def create_agent(use_pg: bool | None = None):
    graph = build_graph()
    if use_pg is None:
        use_pg = bool(settings.pg_connection_string and "postgresql" in settings.pg_connection_string)

    if use_pg:
        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

            checkpointer = AsyncPostgresSaver.from_conn_string(
                settings.pg_connection_string
            )
            return graph.compile(checkpointer=checkpointer)
        except Exception as exc:
            logger.error(
                "PG checkpointer 连接失败，降级为 MemorySaver（会话重启后丢失）: %s",
                exc,
            )
    return graph.compile(checkpointer=MemorySaver())