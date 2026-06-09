from __future__ import annotations

import re
from typing import Any


def tokens(text: str) -> set[str]:
    stop = {"the", "and", "for", "with", "this", "that", "shall", "will", "from", "into", "date", "page"}
    return {t.lower() for t in re.findall(r"[A-Za-z0-9_]+", text or "") if len(t) > 3 and t.lower() not in stop}


def compare_documents(doc_a, doc_b) -> dict[str, Any]:
    ta = tokens(doc_a.text or "")
    tb = tokens(doc_b.text or "")
    overlap = sorted(list(ta & tb))[:60]
    only_a = sorted(list(ta - tb))[:60]
    only_b = sorted(list(tb - ta))[:60]
    similarity = round(len(ta & tb) / max(1, len(ta | tb)), 3)
    risks = []
    low_a = (doc_a.text or "").lower()
    low_b = (doc_b.text or "").lower()
    for clause in ["termination", "liability", "payment terms", "data privacy", "governing law", "incident notification"]:
        in_a = clause in low_a
        in_b = clause in low_b
        if in_a != in_b:
            risks.append(f"Clause/topic mismatch: {clause}")
    return {
        "document_a": doc_a.filename,
        "document_b": doc_b.filename,
        "type_a": getattr(doc_a, "document_type", "unknown"),
        "type_b": getattr(doc_b, "document_type", "unknown"),
        "similarity": similarity,
        "shared_terms": overlap,
        "unique_to_a": only_a,
        "unique_to_b": only_b,
        "risk_notes": risks or ["No major keyword-level mismatch detected."],
    }
