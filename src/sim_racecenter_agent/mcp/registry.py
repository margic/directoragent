from __future__ import annotations
from typing import Callable, Any, Dict

ToolHandler = Callable[[dict], dict]

class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, dict] = {}

    def register(self, name: str, description: str, input_schema: dict, output_schema: dict, handler: ToolHandler):
        self._tools[name] = {
            "name": name,
            "description": description,
            "input_schema": input_schema,
            "output_schema": output_schema,
            "handler": handler,
        }

    def list_tools(self) -> list[dict]:
        return [
            {k: v for k, v in tool.items() if k != "handler"}
            for tool in self._tools.values()
        ]

    def call(self, name: str, arguments: dict) -> dict:
        if name not in self._tools:
            raise ValueError(f"Unknown tool '{name}'")
        return self._tools[name]["handler"](arguments)

tool_registry = ToolRegistry()