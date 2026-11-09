# Release Assistant MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that gives an LLM real release-management tools, so it can answer *"Is checkout-api ready to ship?"* by calling tools and checking data instead of guessing.

## Why I built this

I managed production releases at Lowe's: scheduling deployments, approving changes and coordinating release timing across teams. Most of a go/no-go decision is checking the same things every time: did the tests pass, are there enough approvals, is there a change ticket, is there error budget left? This project turns those checks into tools an AI agent can call, with the decision logic in code rather than in the model.

## Tools

| Tool | What it does | Type |
|---|---|---|
| `list_releases(status?)` | Lists releases, optionally filtered by status | read-only |
| `get_release_status(service)` | Latest release for a service, with its approvals | read-only |
| `check_release_readiness(service)` | Go/no-go decision with a list of blockers | read-only |
| `approve_release(service, approver)` | Records an approval | write (MCP clients ask the user to confirm) |

**Go/no-go rules:** automated tests passed, at least 2 approvals, a linked change ticket, and error budget remaining above 0% (an SRE practice: when the error budget is spent, reliability work comes before new releases).

Tools carry MCP annotations (`readOnlyHint`, `idempotentHint`) so clients can tell safe lookups from actions that change data.

## Architecture

```
LLM / agent (Claude Desktop, MCP Inspector, any MCP client)
        |  MCP over stdio (JSON-RPC)
        v
release-assistant MCP server (Python, MCP SDK v2)
        |
        v
SQLite (releases, approvals)  <- seeded with sample data on first run
```

## Run it

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python demo_client.py      # starts the server over stdio, lists its tools and calls them
pytest -q                  # 6 tests, including one that calls the tools over the MCP protocol
```

### Use it from Claude Desktop

Add this to `claude_desktop_config.json` (Settings > Developer > Edit Config), using the full paths on your machine:

```json
{
  "mcpServers": {
    "release-assistant": {
      "command": "/full/path/to/.venv/bin/python",
      "args": ["/full/path/to/release-assistant-mcp/server.py"]
    }
  }
}
```

Restart Claude Desktop and ask: *"Which releases are in review, and which of them are ready to ship?"*

## Example output

```
check_release_readiness('payments-service'):
{
  "decision": "NO-GO",
  "blockers": ["Automated tests have not passed.", "Needs 2 approvals, has 1."]
}
```

## Next steps

- Read live data from Jira and a CI system instead of SQLite
- Add a `rollback_release` tool behind an explicit human confirmation
- Add evaluation tests that check an agent picks the right tools for a set of questions
