"""The core agent. One task per request; the bridge and safety/ decide every call."""

from __future__ import annotations

from pathlib import Path

import core.openjarvis_env  # noqa: F401  before openjarvis
from openjarvis.agents._stubs import AgentContext
from openjarvis.agents.orchestrator import OrchestratorAgent
from openjarvis.core.config import load_config
from openjarvis.core.types import Message, Role
from openjarvis.engine.ollama import OllamaEngine

from core.bridge_client import BridgeClient
from core.router import route
from core.tools import BridgeTool, HIDDEN, bridge_tools
from safety.policy import MAX_CALLS, TOOLS

REPO = Path(__file__).resolve().parent.parent


class GuardError(RuntimeError):
    """The agent's tool set is not the bridge's: nothing runs."""


class Core:
    def __init__(self, client, engine, model, system_prompt, *, temperature, max_tokens, router=route, on_pending=None):
        self._client = client
        self._router = router
        self._task_id = None
        self._tools = bridge_tools(client, lambda: self._task_id, on_pending)
        self._agent = OrchestratorAgent(engine, model, tools=self._tools, parallel_tools=False,
                                        system_prompt=system_prompt, temperature=temperature,
                                        max_tokens=max_tokens, max_turns=MAX_CALLS + 1,
                                        before_tool_call=self._record)
        self._context = AgentContext()
        self.calls: list[tuple[str, dict]] = []  # every tool call the model made, for evals --real

    def handle(self, text: str, fresh: bool = True) -> str:
        self._guard()  # rule 14, before anything
        self.results = []  # last request only; the reply strings below stay as they are
        routed = self._router(text) if self._router else None
        if routed == ("stop", {}):
            self._client.stop()  # a spoken stop: ends tasks, no latch
            return "Stopped."
        if fresh:
            self._context = AgentContext()
        self._task_id = self._client.new_task(fresh)  # rule 15: one task per request
        try:
            if routed:
                name, args = routed
                self._record(name, args)
                result = self._tool(name).call(args)
                self.results = [result]
                return result.content if result.success else f"Could not {name}: {result.content}"
            run = self._agent.run(text, self._context)
            self.results = run.tool_results
            answer = run.content
            self._context.conversation.add(Message(role=Role.USER, content=text))
            self._context.conversation.add(Message(role=Role.ASSISTANT, content=answer))
            return answer
        finally:
            self._end()

    def _end(self) -> None:
        try:
            self._client.end(self._task_id)  # a non-200 is ignored: rule 13, no retry
        except OSError:
            return  # the bridge is gone; the task expires by itself

    def _guard(self):
        held = list(self._agent._tools)  # the agent's own list (upstream pinned at e6b7137)
        run = self._agent._executor._tools  # what OpenJarvis offers and dispatches: a dict built once from that list
        if (
            {t.spec.name for t in held} != set(TOOLS) - HIDDEN
            or any(type(t) is not BridgeTool for t in held)
            or set(run) != set(TOOLS) - HIDDEN
            or any(run[t.spec.name] is not t for t in held)
        ):
            raise GuardError("agent tool set is not the bridge tool table")

    def _record(self, name, args) -> bool:  # OrchestratorAgent.before_tool_call hook
        self.calls.append((name, args))
        return True

    def _tool(self, name):
        return next(tool for tool in self._tools if tool.tool_id == name)


def build(config_path=REPO / "core" / "config.toml", on_pending=None, router=route) -> Core:
    import core.openjarvis_env  # noqa: F401
    config = load_config(str(config_path))
    engine = OllamaEngine(host=config.engine.ollama.host)
    return Core(BridgeClient(), engine, config.intelligence.default_model, config.agent.default_system_prompt,
                temperature=config.intelligence.temperature, max_tokens=config.intelligence.max_tokens,
                on_pending=on_pending, router=router)
