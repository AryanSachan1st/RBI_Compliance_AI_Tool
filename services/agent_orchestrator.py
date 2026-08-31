"""Explicit six-agent orchestration for the compliance-review workflow."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from mcp_server.tools import log_audit_event
from services.core_langchain_service import (
    analyze_retrieved_clauses,
    build_analysis_context,
    extract_clauses,
    extract_structured_entities,
    retrieve_all_chunks,
)
from services.governance_service import apply_clause_confidence_gate
from services.risk_scoring_service import score_document_risk
from services.verification_service import run_deterministic_verifications


@dataclass
class ComplianceWorkflowState:
    document_id: str
    document_understanding: dict[str, Any]
    entities: Any = None
    clauses: list[dict[str, Any]] = field(default_factory=list)
    clause_chunks: list[dict[str, Any]] = field(default_factory=list)
    clause_analyses: list[Any] = field(default_factory=list)
    verification_results: list[dict[str, Any]] = field(default_factory=list)
    document_risk: dict[str, Any] = field(default_factory=dict)
    agent_trace: list[dict[str, Any]] = field(default_factory=list)


class ComplianceAgentOrchestrator:
    """Six single-responsibility agents with explicit state hand-offs."""

    def _trace(self, state: ComplianceWorkflowState, agent: str, summary: dict[str, Any]) -> None:
        state.agent_trace.append({"agent": agent, "status": "complete", "summary": summary})
        log_audit_event("agent_completed", state.document_id, {"agent": agent, "summary": summary})

    async def document_analysis_agent(self, state: ComplianceWorkflowState, document_text: str) -> None:
        state.entities, state.clauses = await asyncio.gather(
            extract_structured_entities(document_text), extract_clauses(document_text)
        )
        self._trace(state, "document_analysis", {"entity_count": len(state.entities.entities), "clause_count": len(state.clauses)})

    async def regulatory_retrieval_agent(self, state: ComplianceWorkflowState) -> None:
        state.clause_chunks = await retrieve_all_chunks(state.clauses)
        citations = sum(len(item["relevant_source_chunks"]) for item in state.clause_chunks)
        self._trace(state, "regulatory_retrieval", {"clause_count": len(state.clause_chunks), "citation_count": citations})

    async def compliance_reasoning_agent(self, state: ComplianceWorkflowState) -> None:
        analyses = await analyze_retrieved_clauses(build_analysis_context(state.clause_chunks))
        state.clause_analyses = apply_clause_confidence_gate(analyses)
        self._trace(state, "compliance_reasoning", {"verdict_count": len(state.clause_analyses)})

    def numerical_verification_agent(self, state: ComplianceWorkflowState) -> None:
        state.verification_results = run_deterministic_verifications(state.entities, document_id=state.document_id)
        self._trace(state, "numerical_verification", {"rule_count": len(state.verification_results)})

    def risk_assessment_agent(self, state: ComplianceWorkflowState) -> None:
        state.document_risk = score_document_risk(state.clause_analyses, state.verification_results)
        self._trace(state, "risk_assessment", {"risk_tier": state.document_risk.get("risk_tier")})

    def reporting_agent(self, state: ComplianceWorkflowState) -> dict[str, Any]:
        payload = {
            "entities": state.entities.model_dump(),
            "deterministic_verification": state.verification_results,
            "document_risk": state.document_risk,
            "results": [item.model_dump() for item in state.clause_analyses],
            "agent_trace": state.agent_trace,
        }
        self._trace(state, "reporting", {"report_sections": list(payload)})
        payload["agent_trace"] = state.agent_trace
        return payload
