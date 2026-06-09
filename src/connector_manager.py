from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

import pandas as pd


def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


CATEGORY_LABELS = {
    "document_source": "Document Sources",
    "notification": "Workflow Actions",
    "knowledge_base": "Workflow Actions",
    "workflow": "Workflow Actions",
    "engineering": "Workflow Actions",
    "crm": "Business Systems",
    "database": "Business Systems",
    "data_warehouse": "Business Systems",
    "storage": "Document Sources",
    "automation": "Automation",
}


def env_list(value: Any) -> list[str]:
    text = str(value or "").strip()
    if not text or text.lower() == "nan":
        return []
    return [x.strip() for x in text.replace(",", ";").split(";") if x.strip()]


def connector_ready(row: dict[str, Any]) -> bool:
    needed = env_list(row.get("env_vars", ""))
    return bool(needed) and all(os.getenv(x, "").strip() for x in needed)


def connector_status(row: dict[str, Any], session_connected: set[str] | None = None) -> str:
    name = str(row.get("connector", ""))
    if session_connected and name in session_connected:
        return "Connected in demo"
    needed = env_list(row.get("env_vars", ""))
    if not needed:
        return "Ready"
    configured = [x for x in needed if os.getenv(x, "").strip()]
    if len(configured) == len(needed):
        return "Connected"
    if configured:
        return "Needs config"
    return "Not connected"


def status_class(status: str) -> str:
    if status in {"Connected", "Ready", "Connected in demo"}:
        return "pill-ok"
    if status == "Needs config":
        return "pill-warn"
    return "pill-danger"


def env_snippet(row: dict[str, Any]) -> str:
    needed = env_list(row.get("env_vars", ""))
    if not needed:
        return "# No environment variables required for this connector"
    return "\n".join([f"{key}=" for key in needed])


def setup_steps(row: dict[str, Any]) -> list[str]:
    name = str(row.get("connector", "Connector"))
    needed = env_list(row.get("env_vars", ""))
    steps = [
        f"Create or open your {name} developer/workspace settings.",
        "Generate the required API token, webhook URL, OAuth client, or service credentials.",
        "Paste the values into your local .env file using the generated snippet.",
        "Restart Streamlit so the app can read the new environment variables.",
        "Use Test Connection to confirm readiness before enabling real workflow actions.",
    ]
    if needed:
        steps.insert(2, "Required variables: " + ", ".join(needed))
    return steps


def sample_payload(row: dict[str, Any]) -> dict[str, Any]:
    name = str(row.get("connector", "connector"))
    low = name.lower()
    if "slack" in low:
        return {"action": "slack.send_review_alert", "channel": "#document-review", "message": "3 documents failed validation and need review."}
    if "jira" in low:
        return {"action": "jira.create_ticket", "title": "Missing liability clause in vendor contract", "priority": "High", "source_document": "vendor_contract.pdf"}
    if "github" in low:
        return {"action": "github.create_issue", "repo": "org/repo", "title": "Review technical document discrepancy", "labels": ["docuflow", "review"]}
    if "gmail" in low:
        return {"action": "gmail.import_attachments", "query": "has:attachment newer_than:7d", "allowed_file_types": ["pdf", "docx", "xlsx"]}
    if "drive" in low:
        return {"action": "drive.import_folder", "folder": "Vendor Onboarding", "file_types": ["pdf", "docx", "xlsx"]}
    if "s3" in low:
        return {"action": "s3.archive_audit_pack", "bucket": "docuflow-audit", "path": "processed/2026/"}
    if "notion" in low:
        return {"action": "notion.create_summary_page", "database": "Document Reviews", "fields": ["document", "status", "owner"]}
    if "airtable" in low:
        return {"action": "airtable.upsert_records", "table": "Extracted Fields", "records": "extracted_fields.csv"}
    if "hubspot" in low or "salesforce" in low:
        return {"action": "crm.attach_document_intelligence", "object": "company", "document_summary": "validated contract fields"}
    if "postgres" in low or "snowflake" in low:
        return {"action": "database.upsert_document_tables", "tables": ["documents", "extracted_fields", "validation_findings"]}
    if "n8n" in low or "zapier" in low or "make" in low:
        return {"action": "automation.trigger_workflow", "event": "docuflow.batch.completed", "payload": {"review_items": 3}}
    return {"action": f"{name}.run", "mode": "simulation", "document_batch": "current_workspace"}


def test_connection(row: dict[str, Any], session_connected: set[str] | None = None) -> tuple[bool, str]:
    status = connector_status(row, session_connected)
    if status in {"Connected", "Ready", "Connected in demo"}:
        return True, f"{row.get('connector')} is ready for configured/simulated workflow actions."
    needed = env_list(row.get("env_vars", ""))
    missing = [x for x in needed if not os.getenv(x, "").strip()]
    return False, "Missing environment variables: " + ", ".join(missing)


def build_manifest(connectors: pd.DataFrame, session_connected: set[str] | None = None) -> dict[str, Any]:
    records = []
    for r in connectors.fillna("").to_dict(orient="records"):
        records.append({
            "name": r.get("connector"),
            "category": r.get("category"),
            "description": r.get("description"),
            "env_vars": env_list(r.get("env_vars")),
            "status": connector_status(r, session_connected),
            "sample_payload": sample_payload(r),
        })
    return {"name": "docuflow-connectors", "generated_at": now_iso(), "connectors": records}


def connector_audit_event(connector: str, action: str, status: str, details: str = "") -> dict[str, Any]:
    return {"time": now_iso(), "connector": connector, "action": action, "status": status, "details": details}
