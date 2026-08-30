# schema.py
from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class Source(Enum):
    RBI = "RBI"
    IRDAI = "IRDAI"


class DOC_TYPE(Enum):
    MasterDirection = "Master Direction"
    Circular = "Circular"
    Regulation = "Regulation"
    Guideline = "Guideline"


class DOC_STAUTS(Enum):
    Active = "active"
    Superseded = "superseded"
    Withdrawn = "withdrawn"


@dataclass
class RegulatoryDocument:
    doc_id: str  # e.g. "RBI-MD-2023-KYC-001"
    source: Source  # "RBI" or "IRDAI"
    doc_type: DOC_TYPE  # "Master Direction", "Circular", "Regulation", "Guideline"
    title: str
    circular_number: str | None  # official reference number
    issue_date: date
    effective_date: date | None
    superseded_by: str | None = None  # doc_id of newer version, if any
    supersedes: str | None = None  # doc_id of older version, if any
    source_url: str = ""
    local_pdf_path: str = ""
    topics: list = field(
        default_factory=list
    )  # tagged later, e.g. ["KYC", "advertising"]
    raw_text_path: str = ""  # where extracted text lives
    status: DOC_STAUTS = DOC_STAUTS.Active  # "active", "superseded", "withdrawn"
