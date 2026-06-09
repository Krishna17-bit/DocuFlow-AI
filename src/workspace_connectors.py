from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class ConnectorDefinition:
    connector_id: str
    name: str
    category: str
    description: str
    env_vars: list[str] = field(default_factory=list)
    auth_type: str = "api_key"
    status: str = "available"
    actions: list[str] = field(default_factory=list)
    setup_steps: list[str] = field(default_factory=list)
    sample_payload: dict[str, Any] = field(default_factory=dict)


def _env_ready(env_vars: list[str]) -> tuple[bool, list[str], list[str]]:
    configured = []
    missing = []

    for key in env_vars:
        if os.getenv(key, "").strip():
            configured.append(key)
        else:
            missing.append(key)

    return len(missing) == 0, configured, missing


def connector_catalog() -> list[ConnectorDefinition]:
    return [
        ConnectorDefinition(
            connector_id="google_drive",
            name="Google Drive",
            category="Document Sources",
            description="Import PDFs, DOCX files, spreadsheets, and document packets from approved Drive folders.",
            env_vars=[
                "GOOGLE_DRIVE_CLIENT_ID",
                "GOOGLE_DRIVE_CLIENT_SECRET",
            ],
            auth_type="oauth",
            actions=[
                "List folders",
                "Import folder documents",
                "Watch folder for new files",
                "Export processed report",
            ],
            setup_steps=[
                "Create a Google Cloud project.",
                "Enable Google Drive API.",
                "Create OAuth client credentials.",
                "Add GOOGLE_DRIVE_CLIENT_ID and GOOGLE_DRIVE_CLIENT_SECRET to .env.",
                "Restart the Streamlit app.",
            ],
            sample_payload={
                "action": "google_drive.import_folder",
                "folder_id": "drive_folder_id",
                "file_types": ["pdf", "docx", "xlsx"],
                "schedule": "daily",
            },
        ),
        ConnectorDefinition(
            connector_id="gmail",
            name="Gmail",
            category="Document Sources",
            description="Import email attachments from selected labels/search queries and route processed outputs.",
            env_vars=[
                "GMAIL_SMTP_HOST",
                "GMAIL_SMTP_PORT",
                "GMAIL_SMTP_USER",
                "GMAIL_SMTP_PASSWORD",
            ],
            auth_type="smtp_or_oauth",
            actions=[
                "Import attachments",
                "Search mailbox",
                "Send processed report",
                "Send review request",
            ],
            setup_steps=[
                "Use Gmail SMTP/app password for local testing or OAuth for production.",
                "Add Gmail SMTP variables to .env.",
                "Restart the app.",
                "Use safe test mode before enabling real sending.",
            ],
            sample_payload={
                "action": "gmail.import_attachments",
                "query": "has:attachment newer_than:7d",
                "allowed_extensions": ["pdf", "docx", "xlsx"],
            },
        ),
        ConnectorDefinition(
            connector_id="dropbox",
            name="Dropbox",
            category="Document Sources",
            description="Import document folders from Dropbox for batch processing.",
            env_vars=[
                "DROPBOX_ACCESS_TOKEN",
            ],
            auth_type="api_key",
            actions=[
                "Import folder",
                "Watch folder",
                "Archive processed documents",
            ],
            setup_steps=[
                "Create Dropbox app token.",
                "Add DROPBOX_ACCESS_TOKEN to .env.",
                "Restart the app.",
            ],
            sample_payload={
                "action": "dropbox.import_folder",
                "path": "/vendor-documents",
                "file_types": ["pdf", "docx"],
            },
        ),
        ConnectorDefinition(
            connector_id="onedrive",
            name="OneDrive",
            category="Document Sources",
            description="Import documents from Microsoft OneDrive or SharePoint-style libraries.",
            env_vars=[
                "ONEDRIVE_CLIENT_ID",
                "ONEDRIVE_CLIENT_SECRET",
                "ONEDRIVE_TENANT_ID",
            ],
            auth_type="oauth",
            actions=[
                "Import library",
                "Watch folder",
                "Export report",
            ],
            setup_steps=[
                "Create Azure app registration.",
                "Enable Microsoft Graph permissions.",
                "Add OneDrive/Microsoft credentials to .env.",
                "Restart the app.",
            ],
            sample_payload={
                "action": "onedrive.import_library",
                "folder": "Contracts",
                "file_types": ["pdf", "docx"],
            },
        ),
        ConnectorDefinition(
            connector_id="s3",
            name="Amazon S3",
            category="Document Sources",
            description="Import and archive documents from S3 buckets.",
            env_vars=[
                "AWS_ACCESS_KEY_ID",
                "AWS_SECRET_ACCESS_KEY",
                "AWS_REGION",
                "S3_BUCKET",
            ],
            auth_type="api_key",
            actions=[
                "Import bucket prefix",
                "Archive audit pack",
                "Store processed files",
            ],
            setup_steps=[
                "Create IAM user/role with limited S3 permissions.",
                "Add AWS and S3 variables to .env.",
                "Restart the app.",
            ],
            sample_payload={
                "action": "s3.import_prefix",
                "bucket": "company-documents",
                "prefix": "incoming/",
            },
        ),
        ConnectorDefinition(
            connector_id="slack",
            name="Slack",
            category="Workflow Actions",
            description="Send validation failures, review queue alerts, and approval requests to Slack.",
            env_vars=[
                "SLACK_WEBHOOK_URL",
            ],
            auth_type="webhook",
            actions=[
                "Send review alert",
                "Send approval request",
                "Send daily summary",
            ],
            setup_steps=[
                "Create Slack incoming webhook.",
                "Add SLACK_WEBHOOK_URL to .env.",
                "Restart the app.",
                "Use test payload before enabling live notifications.",
            ],
            sample_payload={
                "action": "slack.send_review_alert",
                "channel": "#document-review",
                "message": "3 documents need human review.",
            },
        ),
        ConnectorDefinition(
            connector_id="jira",
            name="Jira",
            category="Workflow Actions",
            description="Create review tickets for missing clauses, failed rules, or low-confidence extracted fields.",
            env_vars=[
                "JIRA_BASE_URL",
                "JIRA_EMAIL",
                "JIRA_API_TOKEN",
                "JIRA_PROJECT_KEY",
            ],
            auth_type="api_key",
            actions=[
                "Create review ticket",
                "Create missing-document task",
                "Create failed-validation issue",
            ],
            setup_steps=[
                "Create Jira API token.",
                "Add Jira base URL, email, token, and project key to .env.",
                "Restart the app.",
            ],
            sample_payload={
                "action": "jira.create_ticket",
                "project_key": "DOC",
                "title": "Missing liability clause in contract",
                "priority": "High",
                "source_document": "vendor_contract.pdf",
            },
        ),
        ConnectorDefinition(
            connector_id="github",
            name="GitHub",
            category="Workflow Actions",
            description="Create GitHub issues for technical document review, policy gaps, or engineering follow-up.",
            env_vars=[
                "GITHUB_TOKEN",
                "GITHUB_REPO",
            ],
            auth_type="api_key",
            actions=[
                "Create issue",
                "Attach review summary",
                "Open follow-up task",
            ],
            setup_steps=[
                "Create GitHub fine-grained token.",
                "Add GITHUB_TOKEN and GITHUB_REPO to .env.",
                "Restart the app.",
            ],
            sample_payload={
                "action": "github.create_issue",
                "repo": "owner/repo",
                "title": "Review failed document validation",
                "body": "DocuFlow found missing required evidence.",
            },
        ),
        ConnectorDefinition(
            connector_id="notion",
            name="Notion",
            category="Workflow Actions",
            description="Export document summaries, review notes, and structured extraction records to Notion.",
            env_vars=[
                "NOTION_API_KEY",
                "NOTION_DATABASE_ID",
            ],
            auth_type="api_key",
            actions=[
                "Create summary page",
                "Append review notes",
                "Store extracted fields",
            ],
            setup_steps=[
                "Create Notion integration.",
                "Share target database/page with the integration.",
                "Add NOTION_API_KEY and NOTION_DATABASE_ID to .env.",
                "Restart the app.",
            ],
            sample_payload={
                "action": "notion.create_page",
                "database_id": "database_id",
                "title": "Vendor packet review summary",
            },
        ),
        ConnectorDefinition(
            connector_id="airtable",
            name="Airtable",
            category="Business Systems",
            description="Send extracted fields, validation findings, and review items to Airtable.",
            env_vars=[
                "AIRTABLE_API_KEY",
                "AIRTABLE_BASE_ID",
                "AIRTABLE_TABLE_NAME",
            ],
            auth_type="api_key",
            actions=[
                "Create extracted field records",
                "Create review queue records",
                "Update document status",
            ],
            setup_steps=[
                "Create Airtable API token.",
                "Add base ID and table name to .env.",
                "Restart the app.",
            ],
            sample_payload={
                "action": "airtable.create_records",
                "base_id": "app...",
                "table": "Document Review",
                "records": [],
            },
        ),
        ConnectorDefinition(
            connector_id="hubspot",
            name="HubSpot",
            category="Business Systems",
            description="Attach document intelligence to companies, deals, vendors, or customer records.",
            env_vars=[
                "HUBSPOT_API_KEY",
            ],
            auth_type="api_key",
            actions=[
                "Create note",
                "Attach document summary",
                "Create review task",
            ],
            setup_steps=[
                "Create HubSpot private app token.",
                "Add HUBSPOT_API_KEY to .env.",
                "Restart the app.",
            ],
            sample_payload={
                "action": "hubspot.create_note",
                "object_type": "company",
                "summary": "Document packet processed by DocuFlow AI.",
            },
        ),
        ConnectorDefinition(
            connector_id="salesforce",
            name="Salesforce",
            category="Business Systems",
            description="Sync structured document intelligence to Salesforce objects.",
            env_vars=[
                "SALESFORCE_CLIENT_ID",
                "SALESFORCE_CLIENT_SECRET",
                "SALESFORCE_USERNAME",
            ],
            auth_type="oauth",
            actions=[
                "Create task",
                "Attach summary",
                "Update record fields",
            ],
            setup_steps=[
                "Create Salesforce connected app.",
                "Add Salesforce credentials to .env.",
                "Restart the app.",
            ],
            sample_payload={
                "action": "salesforce.create_task",
                "object": "Account",
                "subject": "Review document validation findings",
            },
        ),
        ConnectorDefinition(
            connector_id="postgres",
            name="PostgreSQL",
            category="Databases",
            description="Store extracted fields, validation findings, review queue items, and audit logs.",
            env_vars=[
                "DATABASE_URL",
            ],
            auth_type="connection_string",
            actions=[
                "Write extracted fields",
                "Write validation findings",
                "Write audit logs",
                "Read historical packets",
            ],
            setup_steps=[
                "Create database and user.",
                "Add DATABASE_URL to .env.",
                "Restart the app.",
            ],
            sample_payload={
                "action": "postgres.insert_extracted_fields",
                "table": "docuflow_extracted_fields",
                "rows": [],
            },
        ),
        ConnectorDefinition(
            connector_id="snowflake",
            name="Snowflake",
            category="Databases",
            description="Export document intelligence tables to Snowflake for analytics.",
            env_vars=[
                "SNOWFLAKE_ACCOUNT",
                "SNOWFLAKE_USER",
                "SNOWFLAKE_PASSWORD",
                "SNOWFLAKE_DATABASE",
                "SNOWFLAKE_SCHEMA",
            ],
            auth_type="warehouse_credentials",
            actions=[
                "Export document records",
                "Export findings",
                "Export review queue",
            ],
            setup_steps=[
                "Create Snowflake user/role with limited permissions.",
                "Add Snowflake variables to .env.",
                "Restart the app.",
            ],
            sample_payload={
                "action": "snowflake.export_table",
                "table": "DOCUFLOW_FINDINGS",
                "mode": "append",
            },
        ),
        ConnectorDefinition(
            connector_id="n8n",
            name="n8n",
            category="Automation",
            description="Trigger downstream workflow automation through n8n webhooks.",
            env_vars=[
                "N8N_WEBHOOK_URL",
            ],
            auth_type="webhook",
            actions=[
                "Trigger workflow",
                "Send review queue",
                "Send export payload",
            ],
            setup_steps=[
                "Create n8n webhook workflow.",
                "Add N8N_WEBHOOK_URL to .env.",
                "Restart the app.",
            ],
            sample_payload={
                "action": "n8n.trigger_workflow",
                "event": "docuflow.review.ready",
                "review_count": 3,
            },
        ),
        ConnectorDefinition(
            connector_id="zapier",
            name="Zapier",
            category="Automation",
            description="Trigger Zapier automations after document processing.",
            env_vars=[
                "ZAPIER_WEBHOOK_URL",
            ],
            auth_type="webhook",
            actions=[
                "Trigger Zap",
                "Send extracted data",
                "Send review item",
            ],
            setup_steps=[
                "Create Zapier webhook trigger.",
                "Add ZAPIER_WEBHOOK_URL to .env.",
                "Restart the app.",
            ],
            sample_payload={
                "action": "zapier.trigger",
                "event": "docuflow.export.completed",
            },
        ),
        ConnectorDefinition(
            connector_id="make",
            name="Make",
            category="Automation",
            description="Trigger Make scenarios for review, approval, export, and routing workflows.",
            env_vars=[
                "MAKE_WEBHOOK_URL",
            ],
            auth_type="webhook",
            actions=[
                "Trigger scenario",
                "Send document packet",
                "Send validation findings",
            ],
            setup_steps=[
                "Create Make custom webhook.",
                "Add MAKE_WEBHOOK_URL to .env.",
                "Restart the app.",
            ],
            sample_payload={
                "action": "make.trigger_scenario",
                "event": "docuflow.validation.completed",
            },
        ),
    ]


def connector_status_table() -> pd.DataFrame:
    rows = []

    for c in connector_catalog():
        ready, configured, missing = _env_ready(c.env_vars)

        rows.append(
            {
                "connector_id": c.connector_id,
                "name": c.name,
                "category": c.category,
                "description": c.description,
                "auth_type": c.auth_type,
                "required_env_vars": "; ".join(c.env_vars),
                "configured_env_vars": "; ".join(configured),
                "missing_env_vars": "; ".join(missing),
                "connection_status": "Connected" if ready else "Needs configuration",
                "actions": "; ".join(c.actions),
            }
        )

    return pd.DataFrame(rows)


def get_connector(connector_id: str) -> ConnectorDefinition | None:
    for connector in connector_catalog():
        if connector.connector_id == connector_id:
            return connector

    return None


def generate_env_snippet(connector: ConnectorDefinition) -> str:
    lines = [f"# {connector.name} connector"]

    for env_var in connector.env_vars:
        lines.append(f"{env_var}=")

    return "\n".join(lines)


def test_connector(connector: ConnectorDefinition) -> dict[str, Any]:
    ready, configured, missing = _env_ready(connector.env_vars)

    if ready:
        return {
            "ok": True,
            "status": "connected",
            "message": f"{connector.name} has all required environment variables configured.",
            "configured_env_vars": configured,
            "missing_env_vars": [],
        }

    return {
        "ok": False,
        "status": "missing_config",
        "message": f"{connector.name} is missing required configuration.",
        "configured_env_vars": configured,
        "missing_env_vars": missing,
    }


def build_intake_workflow(source_connector: str, schedule: str, document_types: list[str]) -> dict[str, Any]:
    return {
        "workflow_type": "document_intake",
        "source_connector": source_connector,
        "schedule": schedule,
        "document_types": document_types,
        "steps": [
            "connect_source",
            "fetch_new_documents",
            "deduplicate_files",
            "run_docuflow_pipeline",
            "classify_documents",
            "extract_fields",
            "validate_rules",
            "create_review_queue",
        ],
    }


def build_export_workflow(destination_connector: str, trigger: str, include_payloads: list[str]) -> dict[str, Any]:
    return {
        "workflow_type": "document_export",
        "destination_connector": destination_connector,
        "trigger": trigger,
        "include_payloads": include_payloads,
        "steps": [
            "collect_pipeline_outputs",
            "filter_failed_or_review_items",
            "prepare_connector_payload",
            "send_to_destination",
            "write_connector_audit_log",
        ],
    }


def sample_action_payload(connector: ConnectorDefinition, context: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = dict(connector.sample_payload or {})

    if context:
        payload["context"] = context

    payload["connector_id"] = connector.connector_id
    payload["connector_name"] = connector.name
    payload["execution_mode"] = "simulation_safe"

    return payload


def connector_manifest() -> dict[str, Any]:
    return {
        "name": "docuflow-connectors",
        "description": "Connector manifest for document intake, workflow routing, notifications, storage, business systems, and downstream automation.",
        "connectors": [
            {
                "connector_id": c.connector_id,
                "name": c.name,
                "category": c.category,
                "description": c.description,
                "auth_type": c.auth_type,
                "env_vars": c.env_vars,
                "actions": c.actions,
                "sample_payload": c.sample_payload,
            }
            for c in connector_catalog()
        ],
    }


def connector_categories() -> list[str]:
    return sorted({c.category for c in connector_catalog()})


def connectors_by_category(category: str) -> list[ConnectorDefinition]:
    return [c for c in connector_catalog() if c.category == category]


def connector_audit_event(
    connector: ConnectorDefinition,
    action: str,
    status: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "connector_id": connector.connector_id,
        "connector_name": connector.name,
        "category": connector.category,
        "action": action,
        "status": status,
        "details": details or {},
    }