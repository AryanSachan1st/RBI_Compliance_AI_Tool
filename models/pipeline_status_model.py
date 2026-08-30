from enum import Enum

class PipelineStatus(str, Enum):
    EXTRACTING_CLAUSES = "Extracting clauses from your document..."
    SEARCHING_SOURCES  = "Searching for relevant sources..."
    GENERATING_RESPONSE = "Generating your response..."
    DONE               = "Done"

