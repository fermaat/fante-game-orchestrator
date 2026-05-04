"""MCPRulesAdapter — RulesPort backed by the fante-mcp-game-rules MCP server.

Spawns `python -m mcp_game_rules` (or a custom command) as a subprocess on
__init__ and keeps the connection alive in a background thread. Exposes a
synchronous interface so RulesPort stays sync throughout the orchestrator.
"""

import asyncio
import atexit
import logging
import sys
import threading
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from fante.domain.actor import Actor
from fante.domain.rules import CheckResult, RollResult

_log = logging.getLogger(__name__)

_TOOL_TIMEOUT = 30.0
_INIT_TIMEOUT = 15.0


class MCPRulesAdapter:
    """RulesPort adapter that delegates to the mcp-game-rules MCP server."""

    def __init__(self, command: list[str] | None = None) -> None:
        cmd = command or [sys.executable, "-m", "mcp_game_rules"]
        self._params = StdioServerParameters(command=cmd[0], args=cmd[1:])
        self._loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()
        self._session: ClientSession | None = None
        self._shutdown_event: asyncio.Event | None = None
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True, name="mcp-rules-loop")
        self._thread.start()
        if not self._ready.wait(timeout=_INIT_TIMEOUT):
            raise RuntimeError(
                "MCPRulesAdapter: timed out waiting for mcp-game-rules to initialize"
            )
        atexit.register(self.close)

    # ------------------------------------------------------------------
    # Background thread — keeps the async connection alive
    # ------------------------------------------------------------------

    def _run(self) -> None:
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._serve())
        except Exception:
            _log.exception("MCPRulesAdapter background loop crashed")
        finally:
            self._loop.close()

    async def _serve(self) -> None:
        self._shutdown_event = asyncio.Event()
        async with stdio_client(self._params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                self._session = session
                result = await session.call_tool("list_rules", {})
                _log.info("MCPRulesAdapter: server ready. Rules: %s", result.structuredContent)
                self._ready.set()
                await self._shutdown_event.wait()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        if self._loop.is_closed():
            return
        if self._shutdown_event is not None:
            self._loop.call_soon_threadsafe(self._shutdown_event.set)
        self._thread.join(timeout=5)

    # ------------------------------------------------------------------
    # Sync dispatch helpers
    # ------------------------------------------------------------------

    def _call_tool(self, tool: str, args: dict[str, Any]) -> Any:
        async def _inner() -> Any:
            assert self._session is not None, "session not ready"
            return await self._session.call_tool(tool, args)

        future = asyncio.run_coroutine_threadsafe(_inner(), self._loop)
        return future.result(timeout=_TOOL_TIMEOUT)

    # ------------------------------------------------------------------
    # RulesPort implementation
    # ------------------------------------------------------------------

    def roll(self, spec: str) -> RollResult:
        result = self._call_tool("roll", {"spec": spec})
        data: dict[str, Any] = result.structuredContent or {}
        return RollResult(spec=data["spec"], total=data["total"], breakdown=data["breakdown"])

    def check(
        self,
        rule_id: str,
        actor: Actor,
        context: dict[str, Any] | None = None,
        player_score: int | None = None,
    ) -> CheckResult:
        args: dict[str, Any] = {
            "rule_id": rule_id,
            "actor": actor.model_dump(),
        }
        if context:
            args["context"] = context
        if player_score is not None:
            args["player_score"] = player_score
        result = self._call_tool("check", args)
        data: dict[str, Any] = result.structuredContent or {}
        return CheckResult.model_validate(data)
