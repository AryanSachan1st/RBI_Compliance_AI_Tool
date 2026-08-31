export type PipelineStage = "ANALYZING_DOCUMENT"|"EXTRACTING_ENTITIES"|"EXTRACTING_CLAUSES"|"VERIFYING_FACTS"|"SEARCHING_SOURCES"|"GENERATING_RESPONSE"|"SCORING_RISK"|"DONE"|"FAILED";
export interface RegulatoryCitation { source_title: string; page_number: number|null; excerpt: string; }
export interface ClauseAnalysis { clause_id:string; clause_type:string; clause_text:string; matching_source_rules:string[]; citations:RegulatoryCitation[]; verdict:string; confidence:number; analysis:string; risk:string; recommendation:string; }
export interface ReviewerDecision { decision:string; reviewer_id:string; note:string|null; decided_at:string; }
export interface DocumentPage { page_number:number; scan_quality:string; signature_present:boolean; layout:string; document_type:string; classification_confidence:number|null; }
export interface DocumentUnderstanding { status:string; message:string; page_count?:number; missing_page_numbers?:number[]; page_sequence_status?:string; cnn_classifier?:{available:boolean; reason?:string|null}; pages?:DocumentPage[]; }
export interface Entity { entity_type?:string; value?:string; confidence?:number; [key:string]:unknown; }
export interface ComplianceReport { results:ClauseAnalysis[]; document_risk:{risk_tier?:string; [key:string]:unknown}; deterministic_verification:{rule_id:string;status:string;message:string}[]; entities?:{entities?:Entity[]; [key:string]:unknown}; structured_entities?:{entities?:Entity[]; [key:string]:unknown}; document_understanding?:DocumentUnderstanding; report?:{report_id:string;download_url:string}; reviewer_decision?:ReviewerDecision|null; }
export interface StreamPayload extends Partial<ComplianceReport> { stage:PipelineStage; }
