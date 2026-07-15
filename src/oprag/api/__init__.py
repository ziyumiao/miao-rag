"""FastAPI 服务入口"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from oprag.agent.graph import create_agent


class ChatRequest(BaseModel):
    session_id: str | None = Field(default=None, description="会话 ID，新会话传 null")
    buyer_nick: str | None = Field(default=None, description="买家旺旺昵称")
    message: str = Field(..., description="用户消息")
    image: str | None = Field(default=None, description="可选，base64 图片")


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    escalated: bool
    compatibility: str | None = None
    suggestions: list[dict] = Field(default_factory=list)


_agent = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _agent
    _agent = create_agent(use_pg=False)
    yield


app = FastAPI(
    title="oprag - 售前键帽客服",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


@app.post("/qa/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if _agent is None:
        raise HTTPException(status_code=503, detail="服务尚未初始化")

    session_id = req.session_id or str(uuid.uuid4())

    config = {"configurable": {"thread_id": session_id}}
    state: dict = {
        "messages": [
            {"role": "user", "content": req.message},
        ],
        "session_id": session_id,
        "buyer_nick": req.buyer_nick,
    }

    result = await _agent.ainvoke(state, config)

    final_answer = result.get("final_answer", "抱歉，暂时无法处理您的问题。")
    escalated = result.get("escalate", False)

    return ChatResponse(
        session_id=session_id,
        reply=final_answer,
        escalated=escalated,
        compatibility=result.get("compatibility"),
    )


@app.post("/qa/reset")
async def reset_session(session_id: str = Query(..., description="会话 ID")):
    return {"message": "会话已重置", "session_id": session_id}


@app.get("/knowledge/stats")
async def knowledge_stats():
    return {
        "documents": 0,
        "chunks": 0,
        "entities": 0,
        "relations": 0,
        "status": "not_built",
    }
