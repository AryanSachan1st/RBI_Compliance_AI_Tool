from enum import Enum

class PipelineStatus(str, Enum):
    EXTRACTING_CLAUSES = "Extracting clauses from your document..."
    SEARCHING_SOURCES  = "Searching for relevant sources..."
    # --- Added for Rule Engine integration (does not change anything above) ---
    VALIDATING_RULES   = "Validating regulatory compliance rules..."
    # --- end addition ---
    GENERATING_RESPONSE = "Generating your response..."
    DONE               = "Done"

