"""One BridgeTool per bridge tool. The bridge decides; this only carries the call."""

from __future__ import annotations

import json
import time
from collections.abc import Callable

import core.openjarvis_env  # noqa: F401  before openjarvis
from openjarvis.core.types import ToolResult
from openjarvis.tools._stubs import BaseTool, ToolSpec

from core.specs import SPECS
from safety.policy import MAX_SECONDS, TOOLS

POLL = 0.5  # seconds between /outcome reads while an action waits for a click


class BridgeTool(BaseTool):
    """One bridge tool. The bridge and safety/ decide; this only carries the call (rule 13)."""

    def __init__(self, name, client, task: Callable[[], str], on_pending=None, clock=time.monotonic, sleep=time.sleep):
        self.tool_id = name
        self._client = client
        self._task = task
        self._on_pending = on_pending
        self._clock = clock
        self._sleep = sleep

    @property
    def spec(self) -> ToolSpec:
        description, parameters = SPECS[self.tool_id]
        return ToolSpec(name=self.tool_id, description=description, parameters=parameters,
                        timeout_seconds=MAX_SECONDS + 10)  # the executor must not cut an approval wait

    def execute(self, **params) -> ToolResult:
        return self.call(params)

    def call(self, params: dict) -> ToolResult:
        status, body = self._client.tool(self._task(), self.tool_id, params)
        if status == 202:
            status, body = self._wait(body["pending_id"])
            if status != 200:  # a bridge error while waiting
                return ToolResult(self.tool_id, f"bridge {status}: {body.get('detail', '')}", False)
            if body["status"] != "done":
                return ToolResult(self.tool_id, body["status"], False)  # denied / expired / cancelled / failed
            return ToolResult(self.tool_id, json.dumps(body["result"]), True)
        if status == 200:
            return ToolResult(self.tool_id, json.dumps(body["result"]), True)
        if status == 403:
            return ToolResult(self.tool_id, f"refused: {body.get('detail', '')}", False)
        return ToolResult(self.tool_id, f"bridge {status}: {body.get('detail', '')}", False)

    def _wait(self, pending_id):
        if self._on_pending:
            self._on_pending(pending_id)
        deadline = self._clock() + MAX_SECONDS
        while True:
            status, body = self._client.outcome(pending_id)
            if status != 200 or body.get("status") != "pending" or self._clock() >= deadline:
                return (status, body) if status != 200 or body.get("status") != "pending" else (200, {"status": "timed out"})
            self._sleep(POLL)


HIDDEN = frozenset({"recall_memory"})  # policy only until P4: the bridge has no handler yet


def bridge_tools(client, task, on_pending=None) -> list[BridgeTool]:
    return [BridgeTool(name, client, task, on_pending) for name in TOOLS if name not in HIDDEN]
