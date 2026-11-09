import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture()
def server(tmp_path, monkeypatch):
    monkeypatch.setenv("RELEASE_DB", str(tmp_path / "test.db"))
    import importlib
    import server as srv
    importlib.reload(srv)
    return srv


def test_ready_release_is_go(server):
    result = server.check_release_readiness("checkout-api")
    assert result["decision"] == "GO" and result["blockers"] == []


def test_failing_tests_and_missing_approval_block(server):
    result = server.check_release_readiness("payments-service")
    assert result["decision"] == "NO-GO"
    assert any("tests" in b for b in result["blockers"])
    assert any("approvals" in b for b in result["blockers"])


def test_exhausted_error_budget_blocks(server):
    result = server.check_release_readiness("inventory-sync")
    assert result["decision"] == "NO-GO"
    assert any("Error budget" in b for b in result["blockers"])


def test_approval_is_recorded_once(server):
    first = server.approve_release("payments-service", "Dana")
    again = server.approve_release("payments-service", "Dana")
    assert "Recorded" in first["message"] and "already" in again["message"]
    assert server.get_release_status("payments-service")["approvals"].count("Dana") == 1


def test_unknown_service(server):
    assert "error" in server.get_release_status("nope")


@pytest.mark.anyio
async def test_tools_over_mcp_protocol(server):
    from mcp import Client
    async with Client(server.mcp) as client:
        names = {t.name for t in (await client.list_tools()).tools}
        assert names == {"list_releases", "get_release_status", "check_release_readiness", "approve_release"}
        result = await client.call_tool("check_release_readiness", {"service": "checkout-api"})
        text = "".join(getattr(b, "text", "") for b in result.content)
        assert json.loads(text)["decision"] == "GO"
