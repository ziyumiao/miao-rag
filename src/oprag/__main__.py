#!/usr/bin/env python3
"""启动 oprag 服务"""

from __future__ import annotations

import uvicorn

from oprag.config import settings


def get_app():
    from oprag.api import create_api
    return create_api(api_key=settings.api_key)


if __name__ == "__main__":
    uvicorn.run(
        "oprag.__main__:get_app",
        host=settings.host,
        port=settings.port,
        reload=True,
        factory=True,
    )
