export type PipelineStage = "ANALYZING_DOCUMENT"|"EXTRACTING_ENTITIES"|"EXTRACTING_CLAUSES"|"VERIFYING_FACTS"|"SEARCHING_SOURCES"|"GENERATING_RESPONSE"|"SCORING_RISK"|"DONE"|"FAILED";
export interface RegulatoryCitation { source_title: string; page_number: number|null; excerpt: string; }
export interface ClauseAnalysis { clause_id:string; clause_type:string; clause_text:string; matching_source_rules:string[]; citations:RegulatoryCitation[]; verdict:string; confidence:number; analysis:string; risk:string; recommendation:string; }
export interface ComplianceReport { results:ClauseAnalysis[]; document_risk:{risk_tier?:string}; deterministic_verification:{rule_id:string;status:string;message:string}[]; report?:{report_id:string;download_url:string}; }
export interface StreamPayload extends Partial<ComplianceReport> { stage:PipelineStage; }
