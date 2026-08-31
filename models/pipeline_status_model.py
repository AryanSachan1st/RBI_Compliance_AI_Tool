from enum import Enum

class PipelineStatus(str, Enum):
    ANALYZING_DOCUMENT = "Running document-understanding checks..."
    EXTRACTING_ENTITIES = "Extracting structured compliance entities..."
    VERIFYING_FACTS = "Verifying numeric and disclosure facts..."
    EXTRACTING_CLAUSES = "Extracting clauses from your document..."
    SEARCHING_SOURCES  = "Searching for relevant sources..."
    SCORING_RISK = "Calculating document compliance risk..."
    GENERATING_RESPONSE = "Generating your response..."
    DONE               = "Done"
