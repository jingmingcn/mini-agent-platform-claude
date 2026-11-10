"""Tool registry with permission + argument validation (OpenAI function-calling format)."""
from __future__ import annotations

import ast
import json
import operator
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, ValidationError


class ToolError(Exception):
    pass


@dataclass
class Tool:
    name: str
    description: str
    args_model: type[BaseModel]
    handler: Callable[[BaseModel], str]

    def schema(self) -> dict:
        params = self.args_model.model_json_schema()
        params.pop("title", None)
        return {"type": "function", "function": {"name": self.name, "description": self.description, "parameters": params}}


class CurrentTimeArgs(BaseModel):
    timezone: str = Field("Asia/Shanghai", description="IANA 时区，如 Asia/Shanghai")


def _current_time(args: CurrentTimeArgs) -> str:
    try:
        tz = ZoneInfo(args.timezone)
    except (ZoneInfoNotFoundError, ValueError) as e:
        raise ToolError(f"未知时区: {args.timezone}") from e
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S %A (%Z)")


class CalculatorArgs(BaseModel):
    expression: str = Field(..., max_length=200, description="四则运算表达式，例如 (3+4)*2/7")


_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Pow: operator.pow, ast.Mod: operator.mod, ast.FloorDiv: operator.floordiv,
        ast.USub: operator.neg, ast.UAdd: operator.pos}


def _eval(node):
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ToolError("指数过大")
        return _OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand))
    raise ToolError("表达式只允许数字和 + - * / % ** //")


def _calculator(args: CalculatorArgs) -> str:
    try:
        return str(_eval(ast.parse(args.expression, mode="eval")))
    except ZeroDivisionError as e:
        raise ToolError("除数不能为 0") from e
    except SyntaxError as e:
        raise ToolError("表达式语法错误") from e


class ToolManager:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def list(self) -> list[Tool]:
        return list(self._tools.values())

    def schemas(self, allowed: list[str]) -> list[dict]:
        return [self._tools[n].schema() for n in allowed if n in self._tools]

    def execute(self, name: str, arguments: str, allowed: list[str]) -> str:
        if name not in allowed:
            raise ToolError(f"工具 {name} 未授权给该智能体")
        tool = self._tools.get(name)
        if tool is None:
            raise ToolError(f"工具 {name} 不存在")
        try:
            raw = json.loads(arguments or "{}")
            args = tool.args_model.model_validate(raw)
        except (json.JSONDecodeError, ValidationError) as e:
            raise ToolError(f"工具参数不合法: {e}") from e
        return tool.handler(args)


tool_manager = ToolManager()
tool_manager.register(Tool("get_current_time", "获取指定时区的当前日期和时间", CurrentTimeArgs, _current_time))
tool_manager.register(Tool("calculator", "精确计算数学四则运算表达式", CalculatorArgs, _calculator))
