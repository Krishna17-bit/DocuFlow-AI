from __future__ import annotations

import json
import sqlite3
import zipfile
from pathlib import Path
from typing import Any

import pandas as pd

from .models import now_iso


def _json_safe_value(value: Any) -> Any:
    """
    SQLite cannot directly store lists/dicts/objects.
    Convert them to JSON strings safely.
    """
    if isinstance(value, (list, dict, tuple, set)):
        return json.dumps(value, ensure_ascii=False, default=str)

    if isinstance(value, Path):
        return str(value)

    return value


def _safe_df(df: pd.DataFrame, fallback_columns: list[str] | None = None) -> pd.DataFrame:
    """
    Make dataframe safe for SQLite export.

    Fixes:
    - empty dataframe with no columns
    - list/dict cells
    - NaN values
    """
    fallback_columns = fallback_columns or ["id", "status"]

    if df is None or df.empty:
        return pd.DataFrame(columns=fallback_columns)

    safe = df.copy()

    if safe.shape[1] == 0:
        return pd.DataFrame(columns=fallback_columns)

    safe = safe.where(pd.notna(safe), "")

    for col in safe.columns:
        safe[col] = safe[col].apply(_json_safe_value)

    return safe


def df_from_models(items) -> pd.DataFrame:
    if not items:
        return pd.DataFrame()

    rows = []

    for x in items:
        if hasattr(x, "model_dump"):
            rows.append(x.model_dump())
        elif isinstance(x, dict):
            rows.append(x)
        else:
            rows.append(dict(x))

    return pd.DataFrame(rows)


def save_sqlite(path: Path, documents, fields, findings, reviews, trace) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    documents_df = _safe_df(
        df_from_models(documents),
        [
            "doc_id",
            "filename",
            "file_type",
            "document_type",
            "classification_confidence",
            "text",
            "page_count",
            "char_count",
            "table_count",
            "source",
            "status",
            "error",
        ],
    )

    fields_df = _safe_df(
        df_from_models(fields),
        [
            "field_id",
            "doc_id",
            "filename",
            "document_type",
            "field_name",
            "value",
            "confidence",
            "evidence",
        ],
    )

    findings_df = _safe_df(
        df_from_models(findings),
        [
            "finding_id",
            "doc_id",
            "filename",
            "rule_id",
            "requirement",
            "status",
            "severity",
            "evidence",
            "confidence",
        ],
    )

    reviews_df = _safe_df(
        df_from_models(reviews),
        [
            "review_id",
            "doc_id",
            "filename",
            "category",
            "reason",
            "priority",
            "status",
        ],
    )

    trace_df = _safe_df(
        pd.DataFrame(trace or []),
        [
            "time",
            "node",
            "action",
        ],
    )

    with sqlite3.connect(path) as conn:
        documents_df.to_sql("documents", conn, if_exists="replace", index=False)
        fields_df.to_sql("fields", conn, if_exists="replace", index=False)
        findings_df.to_sql("findings", conn, if_exists="replace", index=False)
        reviews_df.to_sql("review_queue", conn, if_exists="replace", index=False)
        trace_df.to_sql("pipeline_trace", conn, if_exists="replace", index=False)


def markdown_report(documents, fields, findings, reviews, trace) -> str:
    lines = [
        "# DocuFlow AI Document Intelligence Report",
        "",
        f"Generated: {now_iso()}",
        "",
        "## Summary",
        f"- Documents processed: {len(documents)}",
        f"- Fields extracted: {len(fields)}",
        f"- Validation findings: {len(findings)}",
        f"- Human review items: {len(reviews)}",
        "",
        "## Documents",
    ]

    for d in documents:
        filename = getattr(d, "filename", "Unknown file")
        document_type = getattr(d, "document_type", "unknown")
        confidence = getattr(d, "classification_confidence", 0.0)

        lines.append(
            f"- **{filename}** — {document_type} "
            f"({float(confidence):.2f})"
        )

    lines.extend(
        [
            "",
            "## Open Review Items",
        ]
    )

    if reviews:
        for r in reviews[:50]:
            filename = getattr(r, "filename", "Unknown file")
            category = getattr(r, "category", "review")
            reason = getattr(r, "reason", "")
            priority = getattr(r, "priority", "medium")

            lines.append(
                f"- **{filename}** — {category}: {reason} [{priority}]"
            )
    else:
        lines.append("- No open review items.")

    lines.extend(
        [
            "",
            "## Pipeline Trace",
        ]
    )

    if trace:
        for e in trace:
            lines.append(
                f"- {e.get('node', 'pipeline')}: {e.get('action', 'completed')}"
            )
    else:
        lines.append("- No trace events recorded.")

    return "\n".join(lines)


def export_zip(path: Path, documents, chunks, fields, findings, reviews, trace, qa_history) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)

    docs_df = _safe_df(
        df_from_models(documents),
        ["doc_id", "filename", "file_type", "document_type", "status"],
    )

    chunks_df = _safe_df(
        df_from_models(chunks),
        ["chunk_id", "doc_id", "filename", "document_type", "chunk_index", "text", "citation"],
    )

    fields_df = _safe_df(
        df_from_models(fields),
        ["field_id", "doc_id", "filename", "document_type", "field_name", "value", "confidence", "evidence"],
    )

    findings_df = _safe_df(
        df_from_models(findings),
        ["finding_id", "doc_id", "filename", "rule_id", "requirement", "status", "severity", "evidence", "confidence"],
    )

    reviews_df = _safe_df(
        df_from_models(reviews),
        ["review_id", "doc_id", "filename", "category", "reason", "priority", "status"],
    )

    trace_df = _safe_df(
        pd.DataFrame(trace or []),
        ["time", "node", "action"],
    )

    payload = {
        "generated_at": now_iso(),
        "document_count": len(documents),
        "chunk_count": len(chunks),
        "field_count": len(fields),
        "finding_count": len(findings),
        "review_count": len(reviews),
    }

    report = markdown_report(
        documents,
        fields,
        findings,
        reviews,
        trace,
    )

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "summary.json",
            json.dumps(payload, indent=2, default=str),
        )

        z.writestr(
            "documents.csv",
            docs_df.to_csv(index=False),
        )

        z.writestr(
            "chunks.csv",
            chunks_df.to_csv(index=False),
        )

        z.writestr(
            "extracted_fields.csv",
            fields_df.to_csv(index=False),
        )

        z.writestr(
            "validation_findings.csv",
            findings_df.to_csv(index=False),
        )

        z.writestr(
            "review_queue.csv",
            reviews_df.to_csv(index=False),
        )

        z.writestr(
            "pipeline_trace.csv",
            trace_df.to_csv(index=False),
        )

        z.writestr(
            "qa_history.json",
            json.dumps(qa_history or [], indent=2, default=str),
        )

        z.writestr(
            "document_intelligence_report.md",
            report,
        )

    return path