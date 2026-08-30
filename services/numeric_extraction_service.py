"""
services/numeric_extraction_service.py

NEW FILE — added for Rule Engine <-> FastAPI integration.

This does NOT modify services/core_langchain_service.py. It is a new,
separate extraction step, following the exact same pattern already used
there (ChatOpenAI + with_structured_output), just for a different
output schema (ExtractedLoanNumerics instead of ExtractedClauses).

This is the extraction step that was missing per INTEGRATION_NOTES.md
and RULE_ENGINE_README.md's "Known integration gap" section: Aryan's
existing pipeline extracts free-text clauses only. This function
extracts the structured NUMBERS that rule_engine/ (via
mcp_server/tools.py) requires as typed input.
"""

from __future__ import annotations

from langchain_openai import ChatOpenAI

from config.settings import OPENAI_API_KEY
from models.numeric_extraction_model import ExtractedLoanNumerics
from system_prompts.numeric_extraction_prompt import NUMERIC_EXTRACTION_SYSTEM_PROMPT

numeric_llm = ChatOpenAI(
    model="gpt-5.6-luna",
    temperature=0,
    api_key=OPENAI_API_KEY,
)

numeric_extractor = numeric_llm.with_structured_output(ExtractedLoanNumerics)


def extract_loan_numerics(user_doc: str) -> ExtractedLoanNumerics:
    """
    Extracts structured numeric loan fields from the raw document text,
    for handoff to run_rule_validations() (services/rule_validation_service.py).

    Takes the same raw doc_text that extract_clauses() also receives —
    this is a second, independent extraction pass over the same source
    text, not derived from the clause-extraction output.
    """
    messages = [
        ("system", NUMERIC_EXTRACTION_SYSTEM_PROMPT),
        ("human", user_doc),
    ]

    result: ExtractedLoanNumerics = numeric_extractor.invoke(messages)
    return result
