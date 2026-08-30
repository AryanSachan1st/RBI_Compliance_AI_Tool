# Deterministic Rule Engine — Phase 1 + Phase 2 + Phase 3

Owner: Venu — Deterministic Rule Engine + MCP Integration

Phase 1 shipped EMI-001. Phase 2 added INTEREST-001, DISCLOSURE-001, and a
shared threshold-comparison utility. Phase 3 (this drop) exposes all three
rules as MCP tools, in `mcp_server/`, without changing anything in
`rule_engine/`.

## What this is

A standalone, framework-free module (`rule_engine/`) that performs
authoritative numeric compliance checks and returns a structured `PASS` /
`FAIL` / `UNCERTAIN` verdict, plus a thin tool/server layer (`mcp_server/`)
that exposes those checks to callers — either as plain Python function
calls or over the MCP protocol. Neither layer depends on FastAPI,
LangChain, or OpenAI — the whole thing can be imported and tested in
complete isolation, and `rule_engine/` specifically has zero dependency
on `mcp_server/` even existing.

## Why it exists

Per the project's Section 5: an LLM can say "EMI appears compliant" and be
wrong — it's probabilistic. This module independently recalculates the
EMI using the standard amortizing-loan formula and compares it to what the
document states, in `Decimal` (not `float`, to avoid rounding-driven false
positives/negatives near a tolerance boundary).

## How to run it

```bash
python -m pip install -r requirements.txt
python demo.py          # standalone demo, no other services needed
python -m pytest tests/ -v   # 39 tests
```

## File layout

```
rule_engine/
    result.py          RuleResult + RuleStatus — the structured output contract
    context.py         RuleContext — confidence + document/clause provenance
    config.py          RuleEngineConfig — thresholds, NOT hardcoded (see below)
    base.py            Rule — abstract base every rule implements
    registry.py        RuleRegistry — rule_id -> Rule instance lookup
    executor.py        RuleExecutor — validated entry point, never leaks a raw traceback
    threshold.py        Shared "value vs configured limit" comparison (Section 9)
    rules/
        emi.py          EMI-001 — Phase 1
        interest.py     INTEREST-001 — Phase 2, built on threshold.py
        disclosure.py   DISCLOSURE-001 — Phase 2, presence/completeness check
tests/
    test_emi.py         Full test matrix (Section 26)
    test_interest.py    Full test matrix for INTEREST-001
    test_disclosure.py  Full test matrix for DISCLOSURE-001
demo.py                 Standalone runnable example, all three rules
```

## ⚠️ Placeholder values — read before using in anything real

`rule_engine/config.py` contains **placeholder** numbers:
- `confidence_threshold = 0.80` (BR-01)
- `emi_tolerance_absolute = ₹1.00`
- `max_interest_rate = 18.00` (INTEREST-001)
- `required_disclosure_fields` — an illustrative 4-field list (DISCLOSURE-001)

None of these are **sourced from any real RBI/IRDAI regulation or business
document**. Per the project's rule against fabricating regulatory data,
these are clearly marked defaults meant to be overridden by real config
once the team has an actual authoritative source. Override via
environment variables (see docstring in `config.py`) or by constructing
`RuleEngineConfig(...)` directly.

## How to call this (for teammates)

```python
from rule_engine.registry import build_default_registry
from rule_engine.executor import RuleExecutor
from rule_engine.context import RuleContext

registry = build_default_registry()
executor = RuleExecutor(registry)  # uses config.py defaults / env overrides

result = executor.execute(
    rule_id="EMI-001",
    raw_inputs={
        "principal": "100000",
        "annual_interest_rate": "12",
        "tenure_months": "12",
        "document_emi": "8900",
    },
    context=RuleContext(
        document_id="DOC-001",
        clause_id="C1",
        confidence=0.95,        # REQUIRED — None triggers UNCERTAIN by design
        source="manual_input",  # or "llm_extraction", "ocr_extraction", etc.
    ),
)

result.status   # RuleStatus.PASS / FAIL / UNCERTAIN
result.message  # human-readable explanation
```

INTEREST-001 and DISCLOSURE-001 work the same way, just with different
`rule_id` / `raw_inputs` shapes:

```python
executor.execute(
    rule_id="INTEREST-001",
    raw_inputs={"document_interest_rate": "14"},
    context=RuleContext(confidence=0.92),
)

executor.execute(
    rule_id="DISCLOSURE-001",
    raw_inputs={
        "document_fields": {
            "annual_percentage_rate": "14.5%",
            "processing_fee": "₹2,500",
            "prepayment_penalty": "2% of outstanding principal",
            "grievance_redressal_contact": "grievance@example-bank.test",
        }
    },
    context=RuleContext(confidence=0.9),
)
```

`result` is a `RuleResult` (pydantic model) — call `result.model_dump()` or
`result.model_dump_json()` to get a dict/JSON for logging, an HTTP
response, or (eventually) an MCP tool response.

## ⚠️ Known integration gap with Aryan's pipeline (stated explicitly, not hidden)

Aryan's `extract_clauses()` (`services/core_langchain_service.py`) returns
`{clause_id, clause_type, clause_text}` — **free text, no numeric entities**.
There is currently no step anywhere in the repo that extracts
`principal` / `interest_rate` / `tenure` / `emi` as structured numbers from
a document.

This means: **this module cannot yet be wired directly into
`/upload-doc/`**. It's built to the *target* contract (typed numeric
inputs + a confidence score) so it's ready the moment entity extraction
exists, but that extraction step is a missing dependency, not something
I've invented a fake implementation of.

Until then, call it directly with manually-supplied or externally-sourced
numbers (as the tests and `demo.py` do), or from an HTTP route you build
around it.

## Phase 3: MCP server (`mcp_server/`)

```
mcp_server/
    tools.py    Plain Python functions wrapping RuleExecutor. No MCP
                imports. Import these directly if you don't need the
                MCP protocol at all.
    server.py   Registers the tools.py functions as MCP tools using
                FastMCP. Requires the separate `mcp` package.
```

Neither file reimplements any rule logic (Section 15) — both are thin
pass-throughs to `RuleExecutor`. If a result looks wrong, the bug is in
`rule_engine/`, not here.

### Running it standalone

```bash
pip install mcp          # separate from pydantic/pytest — only needed for server.py
python -m mcp_server.server
```

This starts an MCP server on **stdio** — it waits for an MCP client to
talk to it over stdin/stdout, which is the normal way an agent framework
spawns a local tool server as a subprocess. It does not print anything
or "run" like `demo.py` does; that's expected.

### Testing without the `mcp` package

`tests/test_mcp_tools.py` tests `tools.py` directly and does **not**
import `mcp` — it runs with the same `python -m pip install -r requirements.txt` you
already have:

```bash
pytest tests/test_mcp_tools.py -v
```

### Three ways to connect this to Aryan's actual project

Pick whichever matches how his project is actually structured — these
are genuinely different integration shapes, not just style preferences:

1. **Direct import, no MCP at all (simplest, if same codebase/monorepo).**
   Copy or symlink `rule_engine/` (and `mcp_server/tools.py` if the
   JSON-dict return shape is convenient) into his project, then:
   ```python
   from mcp_server.tools import validate_emi, validate_interest_rate, validate_disclosures
   result = validate_emi(principal="100000", annual_interest_rate="12",
                          tenure_months="12", document_emi="8900", confidence=0.95)
   ```
   No MCP protocol, no subprocess, no extra dependency beyond `pydantic`.
   This is the right choice if his pipeline is plain Python/FastAPI code
   calling a function, not an LLM agent deciding which tool to invoke.

2. **MCP over stdio (if his pipeline is an LLM agent that picks tools).**
   If his LangChain (or other) agent framework has an MCP client, it can
   spawn `python -m mcp_server.server` as a subprocess and call
   `validate_emi` / `validate_interest_rate` / `validate_disclosures` as
   tools the LLM chooses to invoke — useful if the agent, not fixed code,
   decides when a compliance check is needed. This is the shape implied
   by "MCP Integration" in the master prompt's title.

3. **MCP over SSE/HTTP (if the rule engine needs to run as its own
   service, not a subprocess).** `FastMCP` supports this too
   (`mcp.run(transport="sse")`), for when the rule engine should be a
   separately deployed service rather than something spawned inline.
   Not built here since nothing in the master prompt calls for a
   separate deployment yet — flag it if that changes.

If you're not sure which of these Aryan's project actually needs, that's
worth confirming with him before picking one — options 1 and 2 have very
different integration effort on his side.

## What's next (not built yet)

- **Actual wiring into Aryan's pipeline**: still blocked on his side not
  extracting structured numeric entities yet. Phase 3 makes this easy
  once unblocked (see the three integration paths above) but doesn't
  remove the blocker itself.
- **Phase 4**: audit log persistence (currently `RuleResult` objects are
  returned but not written anywhere).
- **If SSE/HTTP transport is actually needed**: not built (see option 3
  above) — small addition to `server.py` if/when required.

## A note on Phase 2 decisions worth flagging to the team

1. **DISCLOSURE-001 has no `expected_value`/`actual_value`/`tolerance`.**
   It's a presence check, not a numeric comparison, so those fields are
   left `None` on its `RuleResult` — same contract, just not every field
   is meaningful for every rule.
2. **`document_fields` values are `Optional[str]`.** A field can be absent
   from the dict, `None`, or an empty/whitespace string — all three count
   as "missing" for this rule.
3. **INTEREST-001's `tolerance` is always `Decimal(0)`.** It's a hard
   ceiling, not a fuzzy-tolerance comparison like EMI-001; the field is
   populated for contract consistency, not because there's real slack.

## A note on Phase 3 decisions worth flagging to the team

1. **`mcp_server/tools.py` builds one shared `RuleExecutor` at import
   time**, using default config (env-overridable). If different
   environments need different thresholds, build a fresh `RuleExecutor`
   with an explicit `RuleEngineConfig` in the calling code instead of
   relying on this module-level instance.
2. **`server.py` defaults to stdio transport.** I did not build SSE/HTTP
   since nothing in the master prompt calls for the rule engine to be a
   separately deployed network service — only add that if the
   integration path actually requires it (see option 3 above).
3. **The `mcp` package is a separate install from `pydantic`/`pytest`.**
   `tools.py` and its tests don't need it; only `server.py` does. This
   was deliberate, so the core rule-checking logic and its tests never
   gain a dependency they don't need.
