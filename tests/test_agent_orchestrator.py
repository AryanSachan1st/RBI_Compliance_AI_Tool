import asyncio
from types import SimpleNamespace

from services.agent_orchestrator import ComplianceAgentOrchestrator, ComplianceWorkflowState


def test_six_agents_produce_a_trace(monkeypatch):
    orchestrator = ComplianceAgentOrchestrator()
    state = ComplianceWorkflowState("doc-1", {})
    monkeypatch.setattr("services.agent_orchestrator.log_audit_event", lambda *args: {})
    monkeypatch.setattr("services.agent_orchestrator.extract_structured_entities", lambda _: asyncio.sleep(0, result=SimpleNamespace(entities=[], model_dump=lambda: {})))
    monkeypatch.setattr("services.agent_orchestrator.extract_clauses", lambda _: asyncio.sleep(0, result=[]))
    monkeypatch.setattr("services.agent_orchestrator.retrieve_all_chunks", lambda _: asyncio.sleep(0, result=[]))
    monkeypatch.setattr("services.agent_orchestrator.analyze_retrieved_clauses", lambda _: asyncio.sleep(0, result=[]))
    monkeypatch.setattr("services.agent_orchestrator.apply_clause_confidence_gate", lambda analyses: analyses)
    monkeypatch.setattr("services.agent_orchestrator.run_deterministic_verifications", lambda *args, **kwargs: [])
    monkeypatch.setattr("services.agent_orchestrator.score_document_risk", lambda *args: {"risk_tier": "LOW"})

    asyncio.run(orchestrator.document_analysis_agent(state, "text"))
    asyncio.run(orchestrator.regulatory_retrieval_agent(state))
    asyncio.run(orchestrator.compliance_reasoning_agent(state))
    orchestrator.numerical_verification_agent(state)
    orchestrator.risk_assessment_agent(state)
    payload = orchestrator.reporting_agent(state)
    assert [item["agent"] for item in payload["agent_trace"]] == [
        "document_analysis", "regulatory_retrieval", "compliance_reasoning",
        "numerical_verification", "risk_assessment", "reporting",
    ]
