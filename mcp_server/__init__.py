"""
mcp_server/

Phase 3: exposes the deterministic rule engine (rule_engine/) as callable
tools, both as plain Python functions (tools.py) and as an MCP server
(server.py) for agent/LLM callers.

Nothing in this package reimplements any calculation or comparison logic
(Section 15) — every function here is a thin pass-through to
rule_engine.executor.RuleExecutor. If a number looks wrong, the bug is in
rule_engine/, not here.
"""
