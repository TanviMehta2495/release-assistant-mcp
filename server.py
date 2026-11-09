"""Release Assistant MCP server.

Exposes release-management tools to any MCP client (Claude Desktop, MCP Inspector, an agent),
so an LLM can answer questions like "Is checkout-api ready to ship?" by calling real tools
instead of guessing.

Run:  python server.py          (stdio transport, for MCP clients)
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from seed_data import seed

DB_PATH = Path(os.environ.get("RELEASE_DB", Path(__file__).parent / "releases.db"))
MIN_APPROVALS = 2

mcp = MCPServer(
    name="release-assistant",
    instructions=(
        "Tools for checking software release status and go/no-go readiness. "
        "Use check_release_readiness before recommending that a release ships."
    ),
)


def _connect() -> sqlite3.Connection:
    if not DB_PATH.exists():
        seed(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _latest_release(conn: sqlite3.Connection, service: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM releases WHERE service = ? ORDER BY id DESC LIMIT 1", (service,)
    ).fetchone()


def _approvals(conn: sqlite3.Connection, release_id: int) -> list[str]:
    rows = conn.execute(
        "SELECT approver FROM approvals WHERE release_id = ? ORDER BY id", (release_id,)
    ).fetchall()
    return [r["approver"] for r in rows]


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def list_releases(status: str | None = None) -> list[dict]:
    """List releases, optionally filtered by status (planned, in_review, deployed, rolled_back)."""
    with _connect() as conn:
        if status:
            rows = conn.execute("SELECT * FROM releases WHERE status = ? ORDER BY id", (status,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM releases ORDER BY id").fetchall()
        return [dict(r) for r in rows]


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def get_release_status(service: str) -> dict:
    """Get the latest release for a service, including its approvals."""
    with _connect() as conn:
        rel = _latest_release(conn, service)
        if rel is None:
            return {"error": f"No releases found for service '{service}'."}
        return {**dict(rel), "approvals": _approvals(conn, rel["id"])}


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def check_release_readiness(service: str) -> dict:
    """Run go/no-go checks on a service's latest release: tests, approvals, change ticket, error budget."""
    with _connect() as conn:
        rel = _latest_release(conn, service)
        if rel is None:
            return {"error": f"No releases found for service '{service}'."}
        approvals = _approvals(conn, rel["id"])

    blockers = []
    if not rel["tests_passed"]:
        blockers.append("Automated tests have not passed.")
    if len(approvals) < MIN_APPROVALS:
        blockers.append(f"Needs {MIN_APPROVALS} approvals, has {len(approvals)}.")
    if not rel["change_ticket"]:
        blockers.append("No change ticket linked.")
    if rel["error_budget_remaining_pct"] <= 0:
        blockers.append("Error budget is exhausted; reliability work should come first.")

    return {
        "service": service,
        "version": rel["version"],
        "decision": "GO" if not blockers else "NO-GO",
        "blockers": blockers,
        "approvals": approvals,
    }


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True))
def approve_release(service: str, approver: str) -> dict:
    """Record an approval for a service's latest release. MCP clients ask the user to confirm before calling this."""
    approver = approver.strip()
    if not approver:
        return {"error": "Approver name is required."}
    with _connect() as conn:
        rel = _latest_release(conn, service)
        if rel is None:
            return {"error": f"No releases found for service '{service}'."}
        if approver in _approvals(conn, rel["id"]):
            return {"message": f"{approver} already approved {service} {rel['version']}."}
        conn.execute("INSERT INTO approvals (release_id, approver) VALUES (?, ?)", (rel["id"], approver))
        return {"message": f"Recorded approval from {approver} for {service} {rel['version']}.",
                "approvals": _approvals(conn, rel["id"])}


if __name__ == "__main__":
    mcp.run()  # stdio transport
