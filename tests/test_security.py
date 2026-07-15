"""P0.5 安全模块测试"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from oprag.api import create_api, ChatRequest, ChatResponse
from oprag.agent.graph import create_agent


def build_test_app(api_key: str = "test-secret-key"):
    """构造测试用的 FastAPI 应用"""
    app = create_api(api_key=api_key)
    # TestClient 不会自动触发 lifespan，手动注入 agent
    app.state.agent = create_agent(use_pg=False)
    return app


@pytest.fixture
def app():
    return build_test_app()


@pytest.fixture
def client(app):
    return TestClient(app)


class TestApiKeyAuth:
    def test_no_api_key_returns_401(self, client):
        """无 X-API-Key header 时返回 401"""
        response = client.post(
            "/qa/chat",
            json={"message": "你好"},
        )
        assert response.status_code == 401

    def test_wrong_api_key_returns_401(self, client):
        """错误的 API Key 返回 401"""
        response = client.post(
            "/qa/chat",
            json={"message": "你好"},
            headers={"X-API-Key": "wrong-key"},
        )
        assert response.status_code == 401

    def test_correct_api_key_passes(self, client):
        """正确的 API Key 放行"""
        response = client.post(
            "/qa/chat",
            json={"message": "你好"},
            headers={"X-API-Key": "test-secret-key"},
        )
        assert response.status_code == 200

    def test_health_does_not_require_api_key(self, client):
        """/health 端点不需要 API Key"""
        response = client.get("/health")
        assert response.status_code == 200
