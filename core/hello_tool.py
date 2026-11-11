"""P0.4 spike: a custom OpenJarvis tool that calls an HTTP endpoint on 127.0.0.1.

Run the self-check (needs Ollama running with the model from core/config.toml):

    uv run python core/hello_tool.py

Throwaway proof of the wiring. The real bridge client replaces it in P2/P3.
"""

from __future__ import annotations

import os
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
# Must be set before openjarvis is imported: it resolves its home at import time.
os.environ.setdefault("OPENJARVIS_HOME", str(REPO / ".openjarvis"))
os.environ.setdefault("OPENJARVIS_CONFIG", str(REPO / "core" / "config.toml"))

from openjarvis.core.registry import ToolRegistry  # noqa: E402
from openjarvis.core.types import ToolResult  # noqa: E402
from openjarvis.tools._stubs import BaseTool, ToolSpec  # noqa: E402

HELLO_URL = "http://127.0.0.1:8765/hello"  # fixed: the model never chooses the host


@ToolRegistry.register("hello_bridge")
class HelloBridgeTool(BaseTool):
    """Greets a name by asking the local hello server."""

    tool_id = "hello_bridge"

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="hello_bridge",
            description="Get a greeting for a person from the local hello service.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Who to greet."},
                },
                "required": ["name"],
            },
            category="demo",
        )

    def execute(self, **params: Any) -> ToolResult:
        query = urllib.parse.urlencode({"name": str(params.get("name", ""))})
        try:
            with urllib.request.urlopen(f"{HELLO_URL}?{query}", timeout=5) as resp:
                body = resp.read().decode("utf-8")
        except OSError as exc:
            return ToolResult("hello_bridge", f"hello service failed: {exc}", False)
        return ToolResult("hello_bridge", body, True)


def demo() -> None:
    """Self-check: model -> custom tool -> localhost server; built-ins locked out."""
    import secrets
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    from openjarvis import Jarvis
    from openjarvis.core.types import ToolCall
    from openjarvis.tools._stubs import ToolExecutor

    nonce = secrets.token_hex(4)  # the model cannot guess this; proves the HTTP hit
    hits: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            hits.append(self.path)
            name = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get(
                "name", ["?"]
            )[0]
            body = f"Hello {name}, code {nonce}".encode()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args: Any) -> None:
            pass

    server = HTTPServer(("127.0.0.1", 8765), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        # 1. Built-in tools exist in the registry but are not callable unless listed.
        import openjarvis.tools  # noqa: F401  (registers every built-in)

        assert ToolRegistry.contains("shell_exec"), "expected built-in to be registered"
        executor = ToolExecutor([HelloBridgeTool()])
        assert [s.name for s in executor.available_tools()] == ["hello_bridge"]
        for forbidden in ("shell_exec", "file_write", "http_request", "apply_patch"):
            refused = executor.execute(ToolCall("x", forbidden, "{}"))
            assert not refused.success and "Unknown tool" in refused.content, forbidden

        # 2. A typed request makes the model call our tool, which hits the server.
        with Jarvis(config_path=os.environ["OPENJARVIS_CONFIG"]) as jarvis:
            result = jarvis.ask_full(
                "Use the hello_bridge tool to greet Karthik, then tell me the code it"
                " returned.",
                agent="orchestrator",
                tools=["hello_bridge"],
                context=False,
            )
        used = [t["tool_name"] for t in result["tool_results"]]
        assert used and set(used) == {"hello_bridge"}, f"tools used: {used}"
        assert hits, "server was never called"
        assert any(nonce in t["content"] for t in result["tool_results"])
        print(f"server hits: {hits}")
        print(f"answer: {result['content']!r}")
        print(f"nonce {nonce} in answer: {nonce in (result['content'] or '')}")
        print("OK")
    finally:
        server.shutdown()


if __name__ == "__main__":
    demo()
