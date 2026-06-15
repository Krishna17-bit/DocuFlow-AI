from __future__ import annotations
import re
import json
import pandas as pd
from .models import DocumentRecord, ChunkRecord, ExtractedField, ValidationRule, ValidationFinding, ReviewItem, QAEvidence, QAResult
from .provider_router import ProviderRouter

TYPE_KEYWORDS = {
    "invoice": ["invoice", "amount due", "invoice number", "due date", "bill to", "tax", "subtotal"],
    "contract": ["agreement", "effective date", "termination", "liability", "governing law", "renew", "party"],
    "policy": ["policy", "required", "compliance", "incident notification", "security", "access review"],
    "rfp": ["request for proposal", "rfp", "submission deadline", "bid", "evaluation criteria"],
    "sow": ["statement of work", "sow", "deliverables", "milestone", "scope"],
    "proposal": ["proposal", "proposed solution", "pricing", "implementation plan"],
    "resume": ["experience", "education", "skills", "projects", "employment"],
    "financial_report": ["balance sheet", "income statement", "cash flow", "ebitda", "revenue"],
    "research_paper": ["abstract", "methodology", "references", "doi", "conclusion"],
    "compliance_evidence": ["soc 2", "iso 27001", "audit", "evidence", "control"],
}


def classify_document(doc: DocumentRecord) -> DocumentRecord:
    text = (doc.text or "").lower()
    if doc.file_type == "table":
        doc.document_type = "table_data"; doc.classification_confidence = 0.9; return doc
    scores = {dtype: sum(1 for k in keywords if k in text) for dtype, keywords in TYPE_KEYWORDS.items()}
    best = max(scores, key=scores.get) if scores else "unknown"
    score = scores.get(best, 0)
    doc.document_type = best if score > 0 else "unknown"
    doc.classification_confidence = min(0.95, 0.35 + score * 0.12) if score > 0 else 0.25
    return doc


def chunk_document(doc: DocumentRecord, chunk_size: int = 1200, overlap: int = 180) -> list[ChunkRecord]:
    text = doc.text or ""
    chunks, start, idx = [], 0, 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append(ChunkRecord(doc_id=doc.doc_id, filename=doc.filename, document_type=doc.document_type, chunk_index=idx, text=chunk_text, citation=f"{doc.filename} · chunk {idx + 1}"))
        idx += 1
        if end >= len(text): break
        start = max(0, end - overlap)
    return chunks


def _find_value(patterns: list[str], text: str) -> tuple[str, str]:
    for pat in patterns:
        m = re.search(pat, text, flags=re.IGNORECASE | re.MULTILINE)
        if m:
            value = m.group(1).strip() if m.groups() else m.group(0).strip()
            evidence = text[max(0, m.start()-120): min(len(text), m.end()+160)].strip()
            return value, evidence
    return "", ""

FIELD_PATTERNS = {
    "invoice": {
        "vendor": [r"vendor\s*:\s*(.+)", r"from\s*:\s*(.+)"],
        "invoice_number": [r"invoice\s*(?:number|#)\s*:\s*([A-Za-z0-9\-]+)"],
        "invoice_date": [r"invoice\s*date\s*:\s*(.+)", r"date\s*:\s*(.+)"],
        "due_date": [r"due\s*date\s*:\s*(.+)"],
        "total_amount": [r"total\s*(?:amount\s*)?(?:due)?\s*:\s*([$€£]?[\d,]+(?:\.\d{2})?)", r"amount\s*due\s*:\s*([$€£]?[\d,]+(?:\.\d{2})?)"],
        "payment_terms": [r"payment\s*terms\s*:\s*(.+)"],
    },
    "contract": {
        "parties": [r"between\s+(.+?)(?:\.|\n)", r"entered into between\s+(.+?)(?:\.|\n)"],
        "effective_date": [r"effective\s*date\s*:\s*(.+)"],
        "payment_terms": [r"payment\s*terms\s*:\s*(.+)"],
        "term": [r"term\s*:\s*(.+)"],
        "termination": [r"(termination\s*:\s*.+)"],
        "liability": [r"(liability\s*:\s*.+)"],
        "governing_law": [r"governing\s*law\s*:\s*(.+)"],
    },
    "policy": {
        "policy_name": [r"^(.+policy.+)$"],
        "incident_notification": [r"(incident notification.+)", r"(within\s+\d+\s+hours.+)"],
        "required_items": [r"must provide\s*:\s*(.+)"],
    },
}


def extract_fields_llm(doc: DocumentRecord, router: ProviderRouter) -> list[ExtractedField] | None:
    dtype = str(doc.document_type)
    if dtype not in FIELD_PATTERNS:
        return None
    fields_list = list(FIELD_PATTERNS[dtype].keys())
    fields_str = ", ".join(fields_list)
    prompt = f"""You are an expert document extraction system.
Extract the requested structured fields from the document text below.
Document Type: {dtype}
Fields to extract: {fields_str}

Document Text:
{doc.text}

For each field, extract:
1. The extracted 'value' (keep it concise).
2. The 'evidence' (the exact sentence or surrounding context where you found it).
3. The 'confidence' (a float between 0.0 and 1.0 representing your confidence).

Format your response as a raw JSON object matching this schema (do NOT wrap in markdown code blocks like ```json):
{{
  "field_name": {{
    "value": "...",
    "evidence": "...",
    "confidence": 0.85
  }}
}}
"""
    try:
        res = router.generate(prompt, temperature=0.1)
        text_resp = res.text.strip()
        if text_resp.startswith("```"):
            text_resp = re.sub(r"^```(?:json)?\n", "", text_resp)
            text_resp = re.sub(r"\n```$", "", text_resp)
            text_resp = text_resp.strip()
        data = json.loads(text_resp)
        extracted = []
        for name in fields_list:
            if name in data and isinstance(data[name], dict):
                val = str(data[name].get("value", "")).strip()
                ev = str(data[name].get("evidence", "")).strip()
                conf = float(data[name].get("confidence", 0.85))
                if val:
                    extracted.append(ExtractedField(
                        doc_id=doc.doc_id,
                        filename=doc.filename,
                        document_type=doc.document_type,
                        field_name=name,
                        value=val[:500],
                        confidence=conf,
                        evidence=ev[:900]
                    ))
        return extracted
    except Exception:
        return None


def extract_fields(doc: DocumentRecord) -> list[ExtractedField]:
    router = ProviderRouter()
    if router.gemini_key or router.anthropic_key:
        extracted = extract_fields_llm(doc, router)
        if extracted is not None:
            return extracted
    
    # Fallback to regex patterns
    fields = []
    for field_name, pats in FIELD_PATTERNS.get(str(doc.document_type), {}).items():
        value, evidence = _find_value(pats, doc.text or "")
        if value:
            fields.append(ExtractedField(doc_id=doc.doc_id, filename=doc.filename, document_type=doc.document_type, field_name=field_name, value=value[:500], confidence=0.82, evidence=evidence[:900]))
    return fields


def parse_rules(df: pd.DataFrame) -> list[ValidationRule]:
    rules = []
    if df is None or df.empty: return rules
    for r in df.fillna("").to_dict(orient="records"):
        kws = [x.strip().lower() for x in str(r.get("keywords", "")).replace(",", ";").split(";") if x.strip()]
        rules.append(ValidationRule(rule_id=str(r.get("rule_id", "")).strip() or f"R{len(rules)+1:03d}", document_type=str(r.get("document_type", "any")).strip().lower() or "any", requirement=str(r.get("requirement", "")).strip(), keywords=kws, severity=str(r.get("severity", "medium")).strip() or "medium"))
    return rules


def validate_rule_llm(doc: DocumentRecord, rule: ValidationRule, router: ProviderRouter) -> ValidationFinding | None:
    prompt = f"""You are an expert compliance and rule validation assistant.
Verify if the following rule requirement is satisfied by the document text below.

Document Name: {doc.filename}
Document Type: {doc.document_type}
Rule ID: {rule.rule_id}
Requirement: {rule.requirement}

Document Text:
{doc.text}

Evaluate if the document passes, fails, or needs review for this requirement.
- "pass": The requirement is clearly and explicitly satisfied.
- "fail": The requirement is violated or explicitly contradicted.
- "needs_review": The requirement status is ambiguous, or it cannot be verified with high certainty.

Format your response as a raw JSON object matching this schema (do NOT wrap in markdown code blocks like ```json):
{{
  "status": "pass",
  "evidence": "exact sentence or explanation",
  "confidence": 0.9
}}
"""
    try:
        res = router.generate(prompt, temperature=0.1)
        text_resp = res.text.strip()
        if text_resp.startswith("```"):
            text_resp = re.sub(r"^```(?:json)?\n", "", text_resp)
            text_resp = re.sub(r"\n```$", "", text_resp)
            text_resp = text_resp.strip()
        data = json.loads(text_resp)
        status = str(data.get("status", "needs_review")).strip().lower()
        if status not in {"pass", "fail", "needs_review"}:
            status = "needs_review"
        evidence = str(data.get("evidence", "")).strip()
        confidence = float(data.get("confidence", 0.75))
        return ValidationFinding(
            doc_id=doc.doc_id,
            filename=doc.filename,
            rule_id=rule.rule_id,
            requirement=rule.requirement,
            status=status,
            severity=rule.severity,
            evidence=evidence[:900],
            confidence=confidence
        )
    except Exception:
        return None


def validate_documents(docs: list[DocumentRecord], rules: list[ValidationRule]) -> list[ValidationFinding]:
    router = ProviderRouter()
    use_llm = bool(router.gemini_key or router.anthropic_key)
    findings = []
    for doc in docs:
        for rule in rules:
            if rule.document_type not in {"any", str(doc.document_type)}: continue
            finding = None
            if use_llm:
                finding = validate_rule_llm(doc, rule, router)
            if finding is None:
                # Fallback to keyword search
                text = (doc.text or "").lower()
                matched = [k for k in rule.keywords if k and k in text]
                status = "pass" if matched else ("fail" if rule.severity in {"high", "critical"} else "needs_review")
                finding = ValidationFinding(doc_id=doc.doc_id, filename=doc.filename, rule_id=rule.rule_id, requirement=rule.requirement, status=status, severity=rule.severity, evidence=matched[0] if matched else "", confidence=0.86 if matched else 0.72)
            findings.append(finding)
    return findings



def create_review_items(docs: list[DocumentRecord], fields: list[ExtractedField], findings: list[ValidationFinding]) -> list[ReviewItem]:
    items, field_docs = [], {f.doc_id for f in fields}
    for doc in docs:
        if doc.status == "error": items.append(ReviewItem(doc_id=doc.doc_id, filename=doc.filename, category="parse_error", reason=doc.error, priority="high"))
        if doc.classification_confidence < 0.55: items.append(ReviewItem(doc_id=doc.doc_id, filename=doc.filename, category="low_classification_confidence", reason="Document type classification needs human review.", priority="medium"))
        if doc.doc_id not in field_docs and doc.document_type in {"invoice", "contract", "policy"}: items.append(ReviewItem(doc_id=doc.doc_id, filename=doc.filename, category="low_extraction", reason="No structured fields were extracted.", priority="medium"))
    for f in findings:
        if f.status in {"fail", "needs_review"}: items.append(ReviewItem(doc_id=f.doc_id, filename=f.filename, category="rule_validation", reason=f"{f.status}: {f.requirement}", priority=f.severity))
    return items


def search_chunks(question: str, chunks: list[ChunkRecord], top_k: int = 5) -> list[QAEvidence]:
    q_terms = {t.lower() for t in re.findall(r"[A-Za-z0-9_]+", question) if len(t) > 2}
    results = []
    for ch in chunks:
        terms = {t.lower() for t in re.findall(r"[A-Za-z0-9_]+", ch.text) if len(t) > 2}
        score = len(q_terms & terms) / max(1, len(q_terms)) if terms else 0
        if score > 0:
            results.append(QAEvidence(filename=ch.filename, citation=ch.citation, snippet=ch.text[:900].replace("\n", " "), score=round(score, 3)))
    results.sort(key=lambda x: x.score, reverse=True)
    return results[:top_k]


def answer_question(question: str, chunks: list[ChunkRecord], router=None, use_ai: bool = True, provider: str = "auto") -> QAResult:
    evidence = search_chunks(question, chunks, top_k=5)
    if not evidence:
        return QAResult(question=question, answer="I could not find strong supporting evidence in the uploaded documents.", evidence=[])
    context = "\n\n".join([f"[{e.citation}] {e.snippet}" for e in evidence])
    if router and use_ai:
        prompt = f"Answer the question using only the evidence below. Include concise source references.\n\nQuestion: {question}\n\nEvidence:\n{context}"
        res = router.generate(prompt, provider=provider)
        if res.text and res.provider != "local":
            return QAResult(question=question, answer=res.text, evidence=evidence)
    answer = "Based on the strongest matching document evidence, review these sources: " + "; ".join([e.citation for e in evidence[:3]]) + "."
    return QAResult(question=question, answer=answer, evidence=evidence)
