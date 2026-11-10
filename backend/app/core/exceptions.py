"""Unified business exceptions and FastAPI handlers."""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app.errors")


class AppError(Exception):
    status_code = 400
    code = 40000

    def __init__(self, message: str = "请求错误", *, code: int | None = None, status_code: int | None = None, data=None):
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        self.data = data


class BadRequest(AppError):
    status_code, code = 400, 40000


class Unauthorized(AppError):
    status_code, code = 401, 40100

    def __init__(self, message: str = "未登录或登录已过期", **kw):
        super().__init__(message, **kw)


class Forbidden(AppError):
    status_code, code = 403, 40300

    def __init__(self, message: str = "无权访问该资源", **kw):
        super().__init__(message, **kw)


class NotFound(AppError):
    status_code, code = 404, 40400

    def __init__(self, message: str = "资源不存在", **kw):
        super().__init__(message, **kw)


class Conflict(AppError):
    status_code, code = 409, 40900


class TooManyRequests(AppError):
    status_code, code = 429, 42900


class UpstreamError(AppError):
    """Errors from LLM / embedding providers."""
    status_code, code = 502, 50200


def _body(code: int, message: str, data=None) -> dict:
    return {"code": code, "message": message, "data": data}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return JSONResponse(status_code=exc.status_code, content=_body(exc.code, exc.message, exc.data))

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        errors = [
            {"loc": ".".join(str(x) for x in e.get("loc", [])), "msg": e.get("msg")} for e in exc.errors()
        ]
        return JSONResponse(status_code=422, content=_body(42200, "参数校验失败", errors))

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        return JSONResponse(status_code=exc.status_code, content=_body(exc.status_code * 100, str(exc.detail)))

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        logger.exception("Unhandled error: %s", exc)
        return JSONResponse(status_code=500, content=_body(50000, "服务器内部错误"))
