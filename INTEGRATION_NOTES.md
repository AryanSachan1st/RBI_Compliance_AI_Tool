# Integration Notes — Rule Engine <-> FastAPI App

This is the combined project: Aryan's `RBI_Compliance_AI_Tool` FastAPI app
plus Venu's `rule_engine/` + `mcp_server/` (already present in this repo
on the `rule-engine-integration` branch), plus a thin new integration
layer added on top. **No existing file's code was changed or removed** —
only two small, clearly-marked additions to `main.py`, and three brand
new files.

## What's new

| File | Purpose |
|---|---|
| `routes/compliance_routes.py` | **New.** Exposes `rule_engine/` as HTTP endpoints: `GET /compliance/rules`, `POST /compliance/validate/emi`, `POST /compliance/validate/interest-rate`, `POST /compliance/validate/disclosures`. Each is a thin wrapper around `RuleExecutor.execute(...)` — no rule logic duplicated here, same pattern as `mcp_server/tools.py`. |
| `static/index.html` | **New.** A basic, dependency-free manual testing UI — three tabs (EMI / Interest / Disclosure), form inputs, calls the endpoints above via `fetch`, and renders the PASS/FAIL/UNCERTAIN `RuleResult` JSON. |
| `INTEGRATION_NOTES.md` | **New.** This file. |

## What changed in existing files

Only `main.py`, and only additive — every original line is still there,
untouched, in its original position:

```python
# --- Added for Rule Engine integration (does not change anything above) ---
from fastapi.staticfiles import StaticFiles
from routes.compliance_routes import router as compliance_router
# --- end addition ---
```

```python
# --- Added for Rule Engine integration ---
app.include_router(compliance_router)
app.mount("/ui", StaticFiles(directory="static", html=True), name="ui")
# --- end addition ---
```

`routes/document_routes.py`, `services/core_langchain_service.py`,
`services/document_controller.py`, and everything else are byte-for-byte
what they were before.

## Why this shape of integration, and not something deeper

Aryan's pipeline (`services/core_langchain_service.py`, driven by
`POST /upload-doc/`) extracts free-text clauses only —
`{clause_id, clause_type, clause_text}`. It does not extract structured
numeric entities (principal, interest rate, tenure, EMI, disclosure field
values), which is what `rule_engine/` requires as typed input. That gap
is on Aryan's side, not something this integration invents around by
guessing numbers out of clause text with regex or fabricating an
extraction step.

So `/upload-doc/` is left completely alone. Instead, `/compliance/*`
gives the rule engine its own, independent entry point — usable right
now by a human via the UI, and usable later by Aryan's pipeline directly
(in-process, importing `rule_engine.executor.RuleExecutor` the same way
`compliance_routes.py` does) the moment real numeric extraction exists.

## How to run it

Same as before, nothing new to install — `routes/compliance_routes.py`
only imports things `requirements.txt` already includes (`fastapi`,
`pydantic`) plus the existing `rule_engine/` package.

```bash
uvicorn main:app --reload
```

Then:
- `http://127.0.0.1:8000/docs` — Swagger UI, now also showing the
  `deterministic rule engine` tag with the three new endpoints.
- `http://127.0.0.1:8000/ui/` — the manual testing UI.
- `http://127.0.0.1:8000/upload-doc/` — Aryan's original pipeline,
  unchanged.

## Known, pre-existing issue independent of this integration

`services/document_controller.py`'s `upload_user_document` calls
`store_file.read()` on a file handle that was opened `"wb"` (write-only)
and is already closed by that point — this raises
`io.UnsupportedOperation: read` and makes `/upload-doc/` return
`500: Document processing failed: read` for every upload. This bug
predates this integration and is unrelated to `rule_engine/` or
`/compliance/*` (which do not touch that code path at all). It's called
out here for visibility, not fixed here, per the project's stated rule
of flagging Aryan's bugs rather than silently patching them.

## Not done in this pass (unchanged from RULE_ENGINE_README.md)

- Real RBI/IRDAI regulatory thresholds — `rule_engine/config.py` still
  uses placeholder values.
- Numeric entity extraction on Aryan's side — still the real blocker for
  wiring `/upload-doc/` straight into the rule engine.
- Audit log persistence (Phase 4).

---

## Second pass: `/upload-doc/` now DOES call the rule engine

The gap above — "numeric entity extraction on Aryan's side" — is now
built. `/upload-doc/` runs the deterministic rule engine automatically
on every upload, in addition to (not instead of) the existing clause
analysis. Nothing from the first pass was removed; `/compliance/*` and
`/ui/` still work exactly as before, for manual/direct testing.

### What's new in this pass

| File | Purpose |
|---|---|
| `models/numeric_extraction_model.py` | **New.** `ExtractedLoanNumerics` — the structured-output schema for the new numeric extraction step. Every field is `Optional[str]`, defaulting to `None` if not explicitly found — the LLM is instructed never to guess a value. |
| `system_prompts/numeric_extraction_prompt.py` | **New.** System prompt for extracting `principal`, `annual_interest_rate`, `tenure_months`, `document_emi`, and the four disclosure fields, plus a genuine `extraction_confidence` score. Same rigor/style as `clause_extraction_prompt.py` — explicit "never fabricate" and "leave null over guessing" rules. |
| `services/numeric_extraction_service.py` | **New.** `extract_loan_numerics(doc_text)` — one `ChatOpenAI` + `with_structured_output` call, same pattern as `extract_clauses()` in `core_langchain_service.py`, but a separate function in a separate file. `core_langchain_service.py` itself is untouched. |
| `services/rule_validation_service.py` | **New.** `run_rule_validations(numerics, document_id)` — the actual connective piece. Calls `mcp_server.tools.validate_emi` / `validate_interest_rate` / `validate_disclosures` directly (no rule logic duplicated). If EMI-001 or INTEREST-001 don't have enough extracted fields to run, that check is marked `skipped: true` with a reason, instead of being run with a fabricated placeholder number. DISCLOSURE-001 always runs, since detecting missing fields is exactly its job. |

### What changed in existing files (additive only, same as the first pass)

- `models/pipeline_status_model.py` — one new enum value added,
  `VALIDATING_RULES`. Nothing removed or renumbered.
- `routes/document_routes.py` — `run_pipeline()` has one new block
  inserted between the existing "Stage 2" (source retrieval) and the
  existing "Generating response" stage. Every original line is still
  there, unchanged, in its original position. The new block:
  1. Yields a new SSE stage, `VALIDATING_RULES`.
  2. Calls `extract_loan_numerics(doc_text)` — an independent pass over
     the same raw document text (not derived from `clauses`).
  3. Calls `run_rule_validations(...)` and captures the result list.
  4. Wrapped in `try/except`: if this new step throws for any reason,
     the exception is caught, a single `skipped` marker explaining the
     failure is used instead, and **the rest of the original pipeline
     still runs untouched** — a bug in the new code must never break the
     existing, already-working clause-analysis flow.
  5. The final `DONE` event now has one extra key, `rule_validations`,
     alongside the pre-existing `results` key. `results` (the clause
     analysis) is exactly the same shape it always was.
- `main.py` — no further changes beyond the first pass.

### Why the LLM's final analysis does NOT get the rule verdicts injected into it

The original integration plan considered feeding the deterministic
verdicts into `analyze_retrieved_clauses`'s prompt/context, so the LLM
"cannot contradict" a FAIL. That was deliberately NOT done in this pass,
for one concrete reason: it would require editing
`build_analysis_context()` and/or `CONTRACT_ANALYSIS_SYSTEM_PROMPT` —
i.e. changing the behavior of the existing, already-verified clause
analysis step — which conflicts with this pass's explicit constraint of
not modifying existing working functions. Instead, `rule_validations` is
returned as its own independent array in the same `DONE` event, fully
available to the frontend/caller, without altering what
`analyze_retrieved_clauses` does or receives. Wiring it into the
analysis prompt is a reasonable next step, but is a deliberate, visible
change to an existing function's behavior — flagging it here rather than
making that call silently.

### Example `DONE` event shape now

```json
{
  "stage": "Done",
  "results": [ /* unchanged clause analysis, exactly as before */ ],
  "rule_validations": [
    {"rule_id": "EMI-001", "status": "FAIL", "message": "...", "...": "..."},
    {"rule_id": "INTEREST-001", "status": "PASS", "message": "...", "...": "..."},
    {"rule_id": "DISCLOSURE-001", "status": "FAIL", "message": "...", "...": "..."}
  ]
}
```
or, if extraction couldn't find enough fields for a given check:
```json
{"rule_id": "EMI-001", "skipped": true, "reason": "principal, annual_interest_rate, tenure_months, and document_emi were not all extracted"}
```
A `skipped` entry never has a `status` field, so it can't be mistaken
for a real PASS/FAIL/UNCERTAIN verdict.

### Known pre-existing bug (still not fixed here, per this project's rule of flagging rather than silently patching Aryan's code)

The `/upload-doc/` 500 error noted in the first pass
(`services/document_controller.py` reading a file handle opened
write-only) is unrelated to this change and still present. This
integration pass adds a NEW stage inside `run_pipeline()`, which only
runs once `upload_user_document()` has already succeeded — if that
pre-existing bug is still live, `/upload-doc/` will still fail before
ever reaching the new `VALIDATING_RULES` stage. Fixing that bug is
outside this pass's scope (it's Aryan's file, and the fix looks like
re-opening the saved file in `"rb"` mode, or reading text before the
`"wb"` handle closes — flagged for him to confirm and apply).

### Not done in this second pass either

- Real RBI/IRDAI thresholds — still placeholders in `rule_engine/config.py`.
- Feeding `rule_validations` into the LLM analysis prompt (see above).
- Fixing the pre-existing `/upload-doc/` 500 error (not this integration's bug).
- Audit log persistence (Phase 4).

---

## Third pass: presentation-friendly demo page

Added for visibility/demo purposes — makes the LLM-extraction-to-rule-
engine flow obvious to look at, instead of buried inside one large JSON
response.

### What's new

| File | Purpose |
|---|---|
| `static/pipeline_demo.html` | **New.** Uploads a file to `/upload-doc/`, reads the SSE stream, and renders two clearly separated sections: "Step 1: LLM Extracted These Numbers" (the raw `extracted_numerics`) and "Step 2: Deterministic Rule Engine Output" (each rule's exact `input_snapshot` next to its verdict). The pre-existing clause-by-clause LLM analysis is still shown, but collapsed behind a toggle, since it's a separate, unrelated output. No build step — plain HTML/CSS/JS, same as `static/index.html`. Served automatically at `/ui/pipeline_demo.html` since `main.py` already mounts the whole `static/` directory — no `main.py` changes needed for this pass. |

### What changed in an existing file

- `routes/document_routes.py` — the final `DONE` event now includes one
  more key, `extracted_numerics` (the LLM's raw extraction output),
  alongside the pre-existing `results` and `rule_validations` keys nothing
  else in the file changed. If the extraction step fails, this key is
  `null` rather than omitted, so the frontend can distinguish "step
  failed" from "step never ran".

### How to use it

```
http://127.0.0.1:8000/ui/pipeline_demo.html
```
Upload a document, watch the stage progress, then see the two-step
input→output flow rendered directly — useful for demonstrating that the
rule engine, not the LLM, is what produces the PASS/FAIL/UNCERTAIN
verdict.
