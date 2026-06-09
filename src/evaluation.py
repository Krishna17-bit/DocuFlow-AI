from __future__ import annotations

from typing import Any


def run_document_eval(documents, fields, findings, chunks, qa_history) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    doc_types = {getattr(d, "document_type", "unknown") for d in documents}
    field_names = {getattr(f, "field_name", "") for f in fields}
    finding_statuses = {getattr(f, "status", "") for f in findings}

    checks = [
        ("document_classification", "At least one document should be classified beyond unknown", any(t != "unknown" for t in doc_types)),
        ("invoice_total_extraction", "Invoice total amount should be extracted when invoice sample is present", ("total_amount" in field_names) if "invoice" in doc_types else True),
        ("contract_clause_extraction", "Contract fields such as payment terms or termination should be extracted", bool({"payment_terms", "termination", "liability"} & field_names) if "contract" in doc_types else True),
        ("rule_validation", "Validation should produce pass/fail/needs_review findings", bool(finding_statuses)),
        ("chunk_indexing", "Searchable chunks should exist for Q&A", len(chunks) > 0),
        ("citation_qa", "Q&A answers should include evidence when questions are asked", True if not qa_history else bool(qa_history[-1].get("evidence"))),
    ]
    for name, description, passed in checks:
        results.append({
            "check": name,
            "description": description,
            "status": "pass" if passed else "fail",
            "score": 100 if passed else 35,
        })
    return results
