"""
mcp_server/server.py

The actual MCP server: registers the three functions in tools.py as MCP
tools, so an LLM agent (e.g. Aryan's LangChain pipeline, or Claude itself)
can call them over the MCP protocol instead of a direct Python import.

This file contains NO rule logic of its own â€” every tool here is a
one-line pass-through to mcp_server.tools, which is a one-line pass-
through to rule_engine.executor.RuleExecutor. If you're debugging a wrong
answer, the bug is in rule_engine/, not here (Section 15).

Requires the `mcp` package (NOT installed by the phase 1/2 setup):
    pip install mcp

Written against `mcp` v2.x (the SDK renamed its main server class from
`FastMCP` to `MCPServer` and moved the import path in v2 â€” see
https://py.sdk.modelcontextprotocol.io/v2/migration/). If your installed
`mcp` is actually v1.x (`pip show mcp`), use
`from mcp.server.fastmcp import FastMCP as MCPServer` instead of the
import below â€” everything else in this file is unaffected, since
`@mcp.tool()` and `mcp.run()` did not change between v1 and v2.

Run standalone (stdio transport - the default, for local process/subprocess
integration, e.g. a LangChain MCP client spawning this as a subprocess):
    python -m mcp_server.server

See README.md's "Phase 3: MCP server" section for how Aryan's project
would actually connect to this.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

# Make the project root importable regardless of HOW this file is run.
# Normal execution (`python -m mcp_server.server`) already has this on
# sys.path, but `mcp dev mcp_server/server.py` loads this file directly
# via importlib with only mcp_server/'s own folder on the path â€” not its
# parent â€” so `import mcp_server` fails there without this. Safe either
# way: inserting an already-present path is a no-op.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server.mcpserver import MCPServer

from mcp_server.tools import log_audit_event, validate_disclosures, validate_emi, validate_interest_rate

mcp = MCPServer(
    "rbi-rule-engine",
    instructions=(
        "Deterministic compliance checks for BFSI loan documents: EMI "
        "correctness, interest rate ceiling, and mandatory disclosure "
        "presence. Every tool returns PASS, FAIL, or UNCERTAIN â€” never "
        "guesses. UNCERTAIN means either the inputs were incomplete/"
        "invalid, or the extraction confidence was below the configured "
        "threshold; in both cases this requires manual review, not a "
        "retry with different wording."
    ),
)


@mcp.tool(name="validate_emi")
def validate_emi_tool(
    principal: str,
    annual_interest_rate: str,
    tenure_months: str,
    document_emi: str,
    confidence: Optional[float] = None,
    document_id: Optional[str] = None,
    clause_id: Optional[str] = None,
    source: str = "manual_input",
) -> dict:
    """Validate a document's stated EMI against the amortization formula (EMI-001)."""
    return validate_emi(
        principal=principal,
        annual_interest_rate=annual_interest_rate,
        tenure_months=tenure_months,
        document_emi=document_emi,
        confidence=confidence,
        document_id=document_id,
        clause_id=clause_id,
        source=source,
    )


@mcp.tool(name="validate_interest_rate")
def validate_interest_rate_tool(
    document_interest_rate: str,
    confidence: Optional[float] = None,
    document_id: Optional[str] = None,
    clause_id: Optional[str] = None,
    source: str = "manual_input",
) -> dict:
    """Validate a document's stated interest rate against the configured maximum (INTEREST-001)."""
    return validate_interest_rate(
        document_interest_rate=document_interest_rate,
        confidence=confidence,
        document_id=document_id,
        clause_id=clause_id,
        source=source,
    )


@mcp.tool(name="validate_disclosures")
def validate_disclosures_tool(
    document_fields: dict[str, Optional[str]],
    confidence: Optional[float] = None,
    document_id: Optional[str] = None,
    clause_id: Optional[str] = None,
    source: str = "manual_input",
) -> dict:
    """Validate that all mandatory disclosure fields are present in a document (DISCLOSURE-001)."""
    return validate_disclosures(
        document_fields=document_fields,
        confidence=confidence,
        document_id=document_id,
        clause_id=clause_id,
        source=source,
    )

@mcp.tool(name="log_audit_event")
def log_audit_event_tool(event_type: str, document_id: Optional[str], payload: dict) -> dict:
    """Persist a structured pipeline/tool event in the compliance audit trail."""
    return log_audit_event(event_type=event_type, document_id=document_id, payload=payload)


@mcp.tool(name="search_regulatory_corpus")
def search_regulatory_corpus_tool(
    query: str,
    semantic_matches: list[dict] | None = None,
    limit: int = 3,
    document_id: Optional[str] = None,
) -> list[dict]:
    """Hybrid-search the regulatory corpus and return citation-ready excerpts."""
    return search_regulatory_corpus(query, semantic_matches, limit, document_id)

if __name__ == "__main__":
    # stdio transport: this process communicates over stdin/stdout, which
    # is what you want when a client (LangChain's MCP adapter, Claude
    # Desktop, etc.) spawns this as a subprocess. For a network-accessible
    # server instead, see the "Alternative: SSE transport" note in
    # README.md before changing this.
    mcp.run()
