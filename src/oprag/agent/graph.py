"""LangGraph 状态图构建（P0 空壳流程）"""

from __future__ import annotations

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from oprag.agent.state import AgentState
from oprag.agent.nodes import intent_recognition, retrieve, generate_answer, escalate


def _route_after_intent(state: AgentState) -> str:
    if state.get("escalate"):
        return "escalate"
    return "retrieve"


def _route_after_retrieve(state: AgentState) -> str:
    return "generate_answer"


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

    builder.add_conditional_edges(
        "retrieve",
        _route_after_retrieve,
        {"generate_answer": "generate_answer"},
    )

    builder.add_conditional_edges(
        "generate_answer",
        _route_after_generate,
        {END: END, "escalate": "escalate"},
    )

    builder.add_edge("escalate", END)

    return builder


def create_agent(use_pg: bool = False):
    graph = build_graph()
    if use_pg:
        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
            from oprag.config import settings

            checkpointer = AsyncPostgresSaver.from_conn_string(
                settings.pg_connection_string
            )
            return graph.compile(checkpointer=checkpointer)
        except Exception:
            pass
    return graph.compile(checkpointer=MemorySaver())