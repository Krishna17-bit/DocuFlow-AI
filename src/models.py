from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

DocType = Literal[
    "contract", "invoice", "proposal", "sow", "rfp", "policy", "resume",
    "financial_report", "compliance_evidence", "research_paper", "table_data", "unknown"
]

class DocumentRecord(BaseModel):
    doc_id: str = Field(default_factory=lambda: new_id("doc"))
    filename: str
    file_type: str = ""
    document_type: DocType = "unknown"
    classification_confidence: float = 0.0
    text: str = ""
    page_count: int = 0
    char_count: int = 0
    table_count: int = 0
    source: str = "upload"
    status: str = "loaded"
    error: str = ""

class ChunkRecord(BaseModel):
    chunk_id: str = Field(default_factory=lambda: new_id("chunk"))
    doc_id: str
    filename: str
    document_type: str
    chunk_index: int
    text: str
    citation: str

class ExtractedField(BaseModel):
    field_id: str = Field(default_factory=lambda: new_id("field"))
    doc_id: str
    filename: str
    document_type: str
    field_name: str
    value: str = ""
    confidence: float = 0.0
    evidence: str = ""

class ValidationRule(BaseModel):
    rule_id: str
    document_type: str = "any"
    requirement: str
    keywords: list[str] = Field(default_factory=list)
    severity: str = "medium"

class ValidationFinding(BaseModel):
    finding_id: str = Field(default_factory=lambda: new_id("finding"))
    doc_id: str
    filename: str
    rule_id: str
    requirement: str
    status: str
    severity: str
    evidence: str = ""
    confidence: float = 0.0

class ReviewItem(BaseModel):
    review_id: str = Field(default_factory=lambda: new_id("review"))
    doc_id: str
    filename: str
    category: str
    reason: str
    priority: str = "medium"
    status: str = "open"

class QAEvidence(BaseModel):
    filename: str
    citation: str
    snippet: str
    score: float

class QAResult(BaseModel):
    question: str
    answer: str
    evidence: list[QAEvidence] = Field(default_factory=list)

class PipelineResult(BaseModel):
    documents: list[DocumentRecord] = Field(default_factory=list)
    chunks: list[ChunkRecord] = Field(default_factory=list)
    fields: list[ExtractedField] = Field(default_factory=list)
    findings: list[ValidationFinding] = Field(default_factory=list)
    review_items: list[ReviewItem] = Field(default_factory=list)
    trace: list[dict[str, Any]] = Field(default_factory=list)
