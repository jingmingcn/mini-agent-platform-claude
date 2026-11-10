"""FastAPI application entrypoint. Swagger UI: /docs"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401
from app.api import agents, auth, chat, conversations, documents, files, knowledge, logs, models, prompts, system, users
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.core.rate_limit import RateLimitMiddleware

setup_logging(settings.DEBUG)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.SECRET_KEY.startswith("change-me") and settings.ENV == "production":
        raise RuntimeError("SECRET_KEY must be changed in production")
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME, version="0.1.0", lifespan=lifespan,
                  description="通用智能体开发平台 API。统一响应格式 `{code, message, data}`，code=0 表示成功。")
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True,
                       allow_methods=["*"], allow_headers=["*"])
    register_exception_handlers(app)
    for r in (auth, models, agents, prompts, knowledge, documents, chat, conversations, files, users, logs, system):
        app.include_router(r.router, prefix=settings.API_PREFIX)

    @app.get("/healthz", tags=["系统"])
    def healthz():
        return {"status": "ok"}

    return app


app = create_app()
