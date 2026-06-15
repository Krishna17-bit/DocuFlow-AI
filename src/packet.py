from __future__ import annotations

import re
from typing import Any
from .models import DocumentRecord

KEYWORDS = {
    "invoice": ["invoice", "amount due", "invoice number", "subtotal", "tax"],
    "contract": ["agreement", "effective date", "termination", "liability", "governing law"],
    "policy": ["policy", "must provide", "incident notification", "security", "access review"],
    "rfp": ["request for proposal", "rfp", "submission deadline", "evaluation criteria"],
    "sow": ["statement of work", "deliverables", "milestone", "scope"],
    "resume": ["experience", "education", "skills", "employment"],
}


def classify_section(text: str) -> str:
    low = text.lower()
    scores = {kind: sum(1 for kw in kws if kw in low) for kind, kws in KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "unknown"


def split_document_packet(doc) -> list[dict[str, Any]]:
    text = doc.text or ""
    if "[Page " in text:
        raw_parts = [p.strip() for p in text.split("[Page ") if p.strip()]
        sections = []
        for idx, part in enumerate(raw_parts, start=1):
            content = "[Page " + part
            dtype = classify_section(content)
            sections.append({
                "doc_id": doc.doc_id,
                "filename": doc.filename,
                "section_id": f"{doc.doc_id}_section_{idx}",
                "start_page": idx,
                "end_page": idx,
                "detected_type": dtype,
                "confidence": 0.75 if dtype != "unknown" else 0.35,
                "preview": content[:500].replace("\n", " "),
            })
        return sections
    dtype = classify_section(text)
    return [{
        "doc_id": doc.doc_id,
        "filename": doc.filename,
        "section_id": f"{doc.doc_id}_section_1",
        "start_page": 1,
        "end_page": max(1, getattr(doc, "page_count", 1) or 1),
        "detected_type": dtype if dtype != "unknown" else getattr(doc, "document_type", "unknown"),
        "confidence": 0.72 if dtype != "unknown" else 0.42,
        "preview": text[:500].replace("\n", " "),
    }]


def split_all_packets(documents) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    for doc in documents:
        sections.extend(split_document_packet(doc))
    return sections


def split_document_into_records(doc: DocumentRecord) -> list[DocumentRecord]:
    """
    Splits a document packet into a list of child DocumentRecord objects,
    using either '[Page ' or standard form feeds (\x0c) as boundaries.
    """
    text = doc.text or ""
    records = []
    
    if "[Page " in text:
        parts = text.split("[Page ")
        page_num = 0
        for part in parts:
            if not part.strip():
                continue
            page_text = "[Page " + part
            page_num += 1
            dtype = classify_section(page_text)
            child = DocumentRecord(
                doc_id=f"{doc.doc_id}_p{page_num}",
                filename=f"{doc.filename} (Page {page_num})",
                file_type=doc.file_type,
                document_type=dtype,
                classification_confidence=0.75 if dtype != "unknown" else 0.35,
                text=page_text,
                page_count=1,
                char_count=len(page_text),
                source=doc.source,
                status="loaded"
            )
            records.append(child)
        return records
        
    elif "\x0c" in text:
        parts = text.split("\x0c")
        page_num = 0
        for part in parts:
            if not part.strip():
                continue
            page_num += 1
            dtype = classify_section(part)
            child = DocumentRecord(
                doc_id=f"{doc.doc_id}_p{page_num}",
                filename=f"{doc.filename} (Page {page_num})",
                file_type=doc.file_type,
                document_type=dtype,
                classification_confidence=0.75 if dtype != "unknown" else 0.35,
                text=part,
                page_count=1,
                char_count=len(part),
                source=doc.source,
                status="loaded"
            )
            records.append(child)
        return records
        
    return [doc]


def split_all_records(documents: list[DocumentRecord]) -> list[DocumentRecord]:
    results = []
    for doc in documents:
        results.extend(split_document_into_records(doc))
    return results

