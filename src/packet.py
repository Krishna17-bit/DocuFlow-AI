from __future__ import annotations

from typing import Any

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
