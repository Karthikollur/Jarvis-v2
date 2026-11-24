"""Stub tools for the command evals (P1). They record calls and do nothing.

Names and parameters mirror the real tools planned for P3, so the eval set keeps
working when the stubs are swapped for bridge-backed tools (P3.5).

Names must not collide with OpenJarvis built-ins: its registry raises on a
duplicate key (e.g. `memory_search` is taken, hence `recall_memory`).
"""

from __future__ import annotations

import json
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
            if name == "list_dir":
                content = json.dumps({
                    "entries": [
                        {"name": "a.pdf", "type": "file", "size": 3},
                        {"name": "b.pdf", "type": "file", "size": 3},
                        {"name": "c.txt", "type": "file", "size": 3},
                        {"name": "report.pdf", "type": "file", "size": 3},
                    ],
                    "total": 4,
                    "truncated": False,
                })
            elif name == "recall_memory":
                content = json.dumps({
                    "results": [{
                        "kind": "document",
                        "source": "notes\\deadlines.md",
                        "chunk": 0,
                        "text": "The project deadline is Friday.",
                        "score": 1.0,
                    }],
                })
            else:
                content = f"{name}: done (stub, nothing really happened)"
            return ToolResult(name, content, True)

    StubTool.__name__ = f"Stub_{name}"
    return ToolRegistry.register(name)(StubTool)


for _name, (_description, _parameters) in SPECS.items():
    _make(_name, _description, _parameters)
