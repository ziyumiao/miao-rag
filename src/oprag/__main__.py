#!/usr/bin/env python3
"""启动 oprag 服务"""

from __future__ import annotations

import uvicorn

from oprag.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "oprag.api:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )