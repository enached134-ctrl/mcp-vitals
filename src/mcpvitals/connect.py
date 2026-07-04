"""Connect to an MCP server and enumerate its surface (tools / resources / prompts).

Target may be an http(s):// URL or a stdio command (e.g. "python -m my_server").
"""

from __future__ import annotations

import asyncio
import os
import shlex
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolInfo:
    name: str
    description: str
    schema: dict[str, Any]  # JSON Schema of the tool's arguments

    @property
    def params(self) -> dict[str, Any]:
        return (self.schema or {}).get("properties", {}) or {}

    @property
    def required(self) -> list[str]:
        return (self.schema or {}).get("required", []) or []


@dataclass
class Inventory:
    target: str
    tools: list[ToolInfo] = field(default_factory=list)
    resources: list[dict[str, Any]] = field(default_factory=list)
    prompts: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None


def _client(target: str):
    from fastmcp import Client

    if target.startswith(("http://", "https://")):
        return Client(target)
    parts = shlex.split(target, posix=False)
    from fastmcp.client.transports import StdioTransport

    # Silence the graded server's own stderr (startup banners, shutdown-pipe noise) so it
    # doesn't pollute mcp-vitals' output. Fall back gracefully on older transport signatures.
    try:
        errlog = open(os.devnull, "w")  # noqa: SIM115 - closed with the transport process
        return Client(StdioTransport(command=parts[0], args=parts[1:], errlog=errlog))
    except TypeError:
        return Client(StdioTransport(command=parts[0], args=parts[1:]))


async def _inspect(target: str) -> Inventory:
    inv = Inventory(target=target)
    try:
        client = _client(target)
        async with client:
            tools = await client.list_tools()
            for t in tools:
                schema = getattr(t, "inputSchema", None) or getattr(t, "input_schema", None) or {}
                inv.tools.append(
                    ToolInfo(
                        name=t.name,
                        description=getattr(t, "description", "") or "",
                        schema=schema,
                    )
                )
            try:
                inv.resources = [
                    {"uri": str(getattr(r, "uri", "")), "name": getattr(r, "name", "")}
                    for r in await client.list_resources()
                ]
            except Exception:
                inv.resources = []
            try:
                prompts = await client.list_prompts()
                inv.prompts = [{"name": getattr(p, "name", "")} for p in prompts]
            except Exception:
                inv.prompts = []
    except Exception as exc:  # connection / handshake failure
        inv.error = f"{type(exc).__name__}: {exc}"
    return inv


def inspect(target: str) -> Inventory:
    """Synchronous entry point."""
    return asyncio.run(_inspect(target))
