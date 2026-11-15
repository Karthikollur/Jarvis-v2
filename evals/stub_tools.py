"""Stub tools for the command evals (P1). They record calls and do nothing.

Names and parameters mirror the real tools planned for P3, so the eval set keeps
working when the stubs are swapped for bridge-backed tools (P3.5).

Names must not collide with OpenJarvis built-ins: its registry raises on a
duplicate key (e.g. `memory_search` is taken, hence `recall_memory`).
"""

from __future__ import annotations

from typing import Any

import core.openjarvis_env  # noqa: F401  (must precede openjarvis imports)
from core.specs import APPS, SCRIPTS, SPECS  # noqa: F401
from openjarvis.core.registry import ToolRegistry
from openjarvis.core.types import ToolResult
from openjarvis.tools._stubs import BaseTool, ToolSpec

CALLS: list[tuple[str, dict[str, Any]]] = []  # the eval runner reads and clears this


def _make(name: str, description: str, parameters: dict[str, Any]) -> type[BaseTool]:
    class StubTool(BaseTool):
        tool_id = name

        @property
        def spec(self) -> ToolSpec:
            return ToolSpec(name=name, description=description, parameters=parameters)

        def execute(self, **params: Any) -> ToolResult:
            CALLS.append((name, params))
            return ToolResult(name, f"{name}: done (stub, nothing really happened)", True)

    StubTool.__name__ = f"Stub_{name}"
    return ToolRegistry.register(name)(StubTool)


for _name, (_description, _parameters) in SPECS.items():
    _make(_name, _description, _parameters)
