"""A tiny, well-behaved MCP server — a reproducible target for mcp-vitals' own tests.

Run standalone:  python examples/sample_server.py
Grade it:        mcpvitals grade "python examples/sample_server.py" --behavioral
"""

from __future__ import annotations

import time

from fastmcp import FastMCP

mcp = FastMCP("Sample Server")


@mcp.tool
def echo(text: str) -> str:
    """Return the given text unchanged. A trivial read-only probe."""
    return text


@mcp.tool
def add(a: int, b: int) -> int:
    """Add two integers and return their sum."""
    return a + b


@mcp.tool
def divide(a: float, b: float) -> float:
    """Divide a by b. Raises a clear error when b is zero (graceful-error probe)."""
    if b == 0:
        raise ValueError("division by zero is not allowed")
    return a / b


@mcp.tool
def slow(seconds: float = 0.05) -> str:
    """Sleep for the given number of seconds, then acknowledge (a latency probe)."""
    time.sleep(min(seconds, 1.0))
    return f"waited {seconds}s"


if __name__ == "__main__":
    mcp.run()
