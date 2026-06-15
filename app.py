from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from src.doc_graph import run_docflow_graph
from src.intelligence import answer_question
from src.loaders import parse_bytes, load_sample_documents, load_rules
from src.provider_router import ProviderRouter
from src.reporting import df_from_models, save_sqlite, export_zip, markdown_report
from src.ui_styles import APP_CSS
from src.workspace_connectors import (
    build_export_workflow,
    build_intake_workflow,
    connector_audit_event,
    connector_catalog,
    connector_categories,
    connector_manifest,
    connector_status_table,
    connectors_by_category,
    generate_env_snippet,
    get_connector,
    sample_action_payload,
    test_connector,
)

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

st.set_page_config(
    page_title="DocuFlow AI",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(APP_CSS, unsafe_allow_html=True)


def metric_card(label: str, value: str, note: str = "") -> None:
    st.markdown(
        f"""
        <div class='metric-card'>
            <div class='metric-label'>{label}</div>
            <div class='metric-value'>{value}</div>
            <div class='metric-note'>{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def pill(text: str, cls: str = "") -> str:
    return f"<span class='status-pill {cls}'>{text}</span>"


def safe_columns(df: pd.DataFrame, cols: list[str]) -> list[str]:
    return [c for c in cols if c in df.columns]


def connector_card(connector_id: str) -> None:
    connector = get_connector(connector_id)

    if connector is None:
        return

    status = test_connector(connector)
    ready = status["ok"]

    badge_class = "pill-ok" if ready else "pill-warn"
    badge_text = "Connected" if ready else "Needs config"

    st.markdown(
        f"""
        <div class='panel'>
            <div style='display:flex; justify-content:space-between; align-items:flex-start; gap:16px;'>
                <div>
                    <h4 style='margin:0 0 6px 0;'>{connector.name}</h4>
                    <div style='color:#475569; font-size:14px; line-height:1.45;'>{connector.description}</div>
                    <div style='margin-top:10px;'>
                        {pill(connector.category, "pill-blue")}
                        {pill(connector.auth_type, "pill-blue")}
                        {pill(badge_text, badge_class)}
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    b1, b2, b3 = st.columns(3)

    with b1:
        if st.button(
            "Connect",
            key=f"connect_{connector.connector_id}",
            use_container_width=True,
        ):
            st.session_state.selected_connector_id = connector.connector_id

            st.session_state.connector_audit.append(
                connector_audit_event(
                    connector=connector,
                    action="open_connect_flow",
                    status="opened",
                    details={
                        "required_env_vars": connector.env_vars,
                    },
                )
            )

            st.success(f"Opened setup flow for {connector.name}.")

    with b2:
        if st.button(
            "Test",
            key=f"test_{connector.connector_id}",
            use_container_width=True,
        ):
            test_result = test_connector(connector)

            st.session_state.connector_audit.append(
                connector_audit_event(
                    connector=connector,
                    action="test_connection",
                    status=test_result["status"],
                    details=test_result,
                )
            )

            if test_result["ok"]:
                st.success(test_result["message"])
            else:
                st.warning(test_result["message"])

    with b3:
        payload = sample_action_payload(
            connector,
            context={
                "document_count": len(st.session_state.documents),
                "review_count": len(st.session_state.reviews),
            },
        )

        st.download_button(
            "Payload",
            data=json.dumps(payload, indent=2, default=str),
            file_name=f"{connector.connector_id}_payload.json",
            mime="application/json",
            key=f"payload_{connector.connector_id}",
            use_container_width=True,
        )


router = ProviderRouter()

SESSION_DEFAULTS = {
    "documents": [],
    "tables": [],
    "chunks": [],
    "fields": [],
    "findings": [],
    "reviews": [],
    "trace": [],
    "qa_history": [],
    "connector_audit": [],
    "intake_workflows": [],
    "export_workflows": [],
    "selected_connector_id": "google_drive",
    "custom_connector_rows": [],
    "review_comments": {},
    "rules_df": None,
}

for key, default in SESSION_DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default


with st.sidebar:
    st.markdown("### DocuFlow AI")
    st.caption(
        "Batch document intelligence, extraction, validation, Q&A, review workflows, connectors, and exports."
    )

    st.divider()

    with st.expander("Settings & API Keys", expanded=False):
        st.markdown("Provide API keys for your current session. These override local environment variables.")
        
        ui_openai_key = st.text_input(
            "OpenAI API Key",
            value=st.session_state.get("ui_openai_key", ""),
            type="password",
            key="ui_openai_key_input"
        )
        ui_openai_model = st.text_input(
            "OpenAI Model",
            value=st.session_state.get("ui_openai_model", "gpt-4o-mini"),
            key="ui_openai_model_input"
        )
        
        st.divider()
        
        ui_gemini_key = st.text_input(
            "Gemini API Key",
            value=st.session_state.get("ui_gemini_key", ""),
            type="password",
            key="ui_gemini_key_input"
        )
        ui_gemini_model = st.text_input(
            "Gemini Model",
            value=st.session_state.get("ui_gemini_model", "gemini-1.5-flash"),
            key="ui_gemini_model_input"
        )
        
        st.divider()
        
        ui_anthropic_key = st.text_input(
            "Anthropic API Key",
            value=st.session_state.get("ui_anthropic_key", ""),
            type="password",
            key="ui_anthropic_key_input"
        )
        ui_anthropic_model = st.text_input(
            "Anthropic Model",
            value=st.session_state.get("ui_anthropic_model", "claude-3-5-sonnet-20241022"),
            key="ui_anthropic_model_input"
        )

        st.session_state.ui_openai_key = ui_openai_key
        st.session_state.ui_openai_model = ui_openai_model
        st.session_state.ui_gemini_key = ui_gemini_key
        st.session_state.ui_gemini_model = ui_gemini_model
        st.session_state.ui_anthropic_key = ui_anthropic_key
        st.session_state.ui_anthropic_model = ui_anthropic_model
        
        router.refresh_keys()

    st.markdown("**AI status**")
    router.refresh_keys()
    st.info(router.status)

    provider_choice = st.selectbox(
        "AI route",
        ["auto", "openai", "gemini", "anthropic", "local"],
        index=0,
    )

    use_ai = st.checkbox(
        "Use optional AI for Q&A synthesis",
        value=True,
    )

    st.divider()

    st.markdown("**Pipeline**")
    st.markdown(
        "- ingest documents\n"
        "- split packets\n"
        "- classify documents\n"
        "- extract tables\n"
        "- build chunks\n"
        "- structured extraction\n"
        "- rule validation\n"
        "- review queue\n"
        "- connector workflows\n"
        "- export packaging"
    )


st.markdown(
    """
    <div class='hero'>
      <div class='hero-title'>DocuFlow AI</div>
      <div class='hero-subtitle'>
        Multi-document intelligence platform for batch PDF/DOCX/TXT/CSV/Excel parsing, document classification,
        structured field extraction, table handling, multi-document Q&A with citations, rule validation,
        human review queues, connector marketplace workflows, and export-ready audit packs.
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

connector_status_df = connector_status_table()
connected_count = int(
    (connector_status_df["connection_status"] == "Connected").sum()
    if not connector_status_df.empty
    else 0
)

m1, m2, m3, m4, m5 = st.columns(5)

with m1:
    metric_card(
        "Documents",
        str(len(st.session_state.documents)),
        "Loaded files",
    )

with m2:
    metric_card(
        "Extracted fields",
        str(len(st.session_state.fields)),
        "Structured outputs",
    )

with m3:
    findings_count = len(
        [
            f
            for f in st.session_state.findings
            if getattr(f, "status", "") in {"fail", "needs_review"}
        ]
    )

    metric_card(
        "Findings",
        str(findings_count),
        "Failed / review rules",
    )

with m4:
    metric_card(
        "Review queue",
        str(len(st.session_state.reviews)),
        "Human review items",
    )

with m5:
    metric_card(
        "Connectors",
        str(connected_count),
        "Ready workspace tools",
    )


tabs = st.tabs(
    [
        "Workspace",
        "Dashboard",
        "Documents",
        "Classification",
        "Tables",
        "Extraction",
        "Document Q&A",
        "Validation",
        "Review Queue",
        "Comparison Lab",
        "Evaluation Lab",
        "Connector Marketplace",
        "Workflow Builder",
        "Export",
    ]
)


with tabs[0]:
    st.markdown("### Build document workspace")

    mode = st.radio(
        "Workspace mode",
        [
            "Use sample document pack",
            "Upload my documents",
            "Combine sample + uploads",
        ],
        horizontal=True,
    )

    uploads = st.file_uploader(
        "Upload PDFs, DOCX, TXT, CSV, Excel, or ZIP",
        type=["pdf", "docx", "txt", "md", "csv", "xlsx", "xls", "zip"],
        accept_multiple_files=True,
    )

    rules_file = st.file_uploader(
        "Optional validation rules CSV/Excel",
        type=["csv", "xlsx", "xls"],
        key="rules_upload",
    )

    enable_splitting = st.checkbox(
        "Enable Smart Packet Splitting (splits multi-page/multi-type documents)",
        value=False,
        key="enable_splitting_toggle"
    )

    c1, c2 = st.columns([1, 2])

    with c1:
        run_btn = st.button(
            "Run document pipeline",
            use_container_width=True,
        )

    with c2:
        st.caption(
            "Use sample mode first, then test with client-style packets: contracts, invoices, policies, SOWs, RFPs, reports, and spreadsheets."
        )

    if run_btn:
        documents = []
        tables = []

        if mode in {
            "Use sample document pack",
            "Combine sample + uploads",
        }:
            documents.extend(load_sample_documents(BASE_DIR))

        if mode in {
            "Upload my documents",
            "Combine sample + uploads",
        } and uploads:
            for up in uploads:
                parsed_docs, parsed_tables = parse_bytes(
                    up.getvalue(),
                    up.name,
                )

                documents.extend(parsed_docs)
                tables.extend(parsed_tables)

        if rules_file is not None:
            if rules_file.name.lower().endswith(".csv"):
                rules_df = pd.read_csv(rules_file).fillna("")
            else:
                rules_df = pd.read_excel(rules_file).fillna("")
            st.session_state.rules_df = rules_df
        elif st.session_state.rules_df is None:
            rules_df = load_rules(BASE_DIR)
            st.session_state.rules_df = rules_df
        else:
            rules_df = st.session_state.rules_df

        result = run_docflow_graph(
            documents,
            rules_df,
            enable_splitting=enable_splitting
        )

        st.session_state.documents = result.documents
        st.session_state.chunks = result.chunks
        st.session_state.fields = result.fields
        st.session_state.findings = result.findings
        st.session_state.reviews = result.review_items
        st.session_state.trace = result.trace
        st.session_state.tables = tables

        save_sqlite(
            OUTPUT_DIR / "docuflow.db",
            result.documents,
            result.fields,
            result.findings,
            result.review_items,
            result.trace,
        )

        st.success("Document intelligence pipeline completed.")

    st.markdown("### Pipeline trace")

    if st.session_state.trace:
        st.dataframe(
            pd.DataFrame(st.session_state.trace),
            use_container_width=True,
            height=280,
        )
    else:
        st.info("Run the pipeline to see the LangGraph trace.")


with tabs[1]:
    st.markdown("### Document intelligence dashboard")

    if st.session_state.documents:
        ddf = df_from_models(st.session_state.documents)

        c1, c2 = st.columns(2)

        with c1:
            fig = px.histogram(
                ddf,
                x="document_type",
                title="Documents by type",
            )

            fig.update_layout(
                height=360,
                paper_bgcolor="#ffffff",
                plot_bgcolor="#ffffff",
                font_color="#111827",
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
            )

        with c2:
            fig = px.histogram(
                ddf,
                x="classification_confidence",
                nbins=10,
                title="Classification confidence",
            )

            fig.update_layout(
                height=360,
                paper_bgcolor="#ffffff",
                plot_bgcolor="#ffffff",
                font_color="#111827",
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
            )

        dashboard_cols = safe_columns(
            ddf,
            [
                "filename",
                "file_type",
                "document_type",
                "classification_confidence",
                "page_count",
                "char_count",
                "status",
            ],
        )

        st.dataframe(
            ddf[dashboard_cols],
            use_container_width=True,
            height=360,
        )
    else:
        st.info("No documents processed yet.")

    st.markdown("### Workspace readiness")

    c1, c2 = st.columns(2)

    with c1:
        st.dataframe(
            connector_status_df[
                [
                    "name",
                    "category",
                    "connection_status",
                    "missing_env_vars",
                ]
            ],
            use_container_width=True,
            height=300,
        )

    with c2:
        if st.session_state.connector_audit:
            st.dataframe(
                pd.DataFrame(st.session_state.connector_audit),
                use_container_width=True,
                height=300,
            )
        else:
            st.info("No connector audit events yet.")


with tabs[2]:
    st.markdown("### Parsed documents")

    if st.session_state.documents:
        for doc in st.session_state.documents:
            cls = "pill-ok" if doc.status == "loaded" else "pill-danger"

            with st.expander(f"{doc.filename} · {doc.document_type}"):
                st.markdown(
                    pill(doc.status, cls)
                    + pill(doc.document_type, "pill-blue")
                    + pill(f"{doc.classification_confidence:.2f}", "pill-warn"),
                    unsafe_allow_html=True,
                )

                if doc.error:
                    st.error(doc.error)

                st.text_area(
                    "Extracted text preview",
                    value=(doc.text or "")[:6000],
                    height=260,
                    key=f"text_{doc.doc_id}",
                )
    else:
        st.info("No parsed documents yet.")


with tabs[3]:
    st.markdown("### Classification results")

    if st.session_state.documents:
        cdf = df_from_models(st.session_state.documents)

        classification_cols = safe_columns(
            cdf,
            [
                "filename",
                "document_type",
                "classification_confidence",
                "source",
                "status",
            ],
        )

        st.dataframe(
            cdf[classification_cols],
            use_container_width=True,
            height=420,
        )
    else:
        st.info("Run pipeline first.")


with tabs[4]:
    st.markdown("### Table extraction and table files")

    if st.session_state.tables:
        for i, df in enumerate(st.session_state.tables):
            st.markdown(f"#### Uploaded table {i + 1}")

            st.dataframe(
                df,
                use_container_width=True,
                height=300,
            )

            st.download_button(
                f"Download table {i + 1} CSV",
                data=df.to_csv(index=False),
                file_name=f"table_{i + 1}.csv",
                mime="text/csv",
                use_container_width=True,
            )
    else:
        st.info(
            "Upload CSV/Excel files to view extracted tables. PDF table extraction can be added with Docling/Camelot/Tabula in the next version."
        )


with tabs[5]:
    st.markdown("### Structured extraction")

    template = st.selectbox(
        "Extraction template",
        [
            "Auto-detect",
            "Invoice extractor",
            "Contract extractor",
            "RFP extractor",
            "SOW extractor",
            "Policy extractor",
            "Resume extractor",
            "Compliance evidence extractor",
            "Financial report extractor",
        ],
    )

    st.caption(
        f"Selected template: {template}. Current extraction uses document type detection and template-style field patterns."
    )

    if st.session_state.fields:
        st.dataframe(
            df_from_models(st.session_state.fields),
            use_container_width=True,
            height=460,
        )
    else:
        st.info("No structured fields extracted yet. Try sample invoice/contract documents.")


with tabs[6]:
    st.markdown("### Multi-document Q&A with citations")

    question = st.text_input(
        "Ask across all documents",
        value="Which documents mention payment terms or termination?",
    )

    if st.button(
        "Answer question",
        use_container_width=True,
    ):
        qa = answer_question(
            question,
            st.session_state.chunks,
            router=router,
            use_ai=use_ai,
            provider=provider_choice,
        )

        st.session_state.qa_history.append(qa.model_dump())

    if st.session_state.qa_history:
        latest = st.session_state.qa_history[-1]

        st.markdown("#### Answer")
        st.write(latest["answer"])

        st.markdown("#### Evidence")

        for ev in latest["evidence"]:
            st.markdown(
                f"""
                <div class='evidence'>
                    <b>{ev['citation']}</b>
                    <br>
                    {ev['snippet']}
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("Ask a question after running the pipeline.")


with tabs[7]:
    st.markdown("### Rule validation findings")

    if st.session_state.findings:
        fdf = df_from_models(st.session_state.findings)

        st.dataframe(
            fdf,
            use_container_width=True,
            height=300,
        )

        st.download_button(
            "Download validation findings CSV",
            data=fdf.to_csv(index=False),
            file_name="validation_findings.csv",
            mime="text/csv",
            use_container_width=True,
        )
    else:
        st.info("No validation findings yet.")

    st.markdown("### Validation Rules Manager")
    
    if st.session_state.rules_df is None:
        st.session_state.rules_df = load_rules(BASE_DIR)
        
    edited_rules_df = st.data_editor(
        st.session_state.rules_df,
        num_rows="dynamic",
        use_container_width=True,
        key="rules_data_editor"
    )
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Save Rules Changes", key="apply_rules_btn", use_container_width=True):
            st.session_state.rules_df = edited_rules_df
            st.success("Rules saved successfully! Click 'Run document pipeline' in the Workspace tab to re-evaluate.")
    with c2:
        if st.button("Re-evaluate on current documents", key="reeval_rules_btn", use_container_width=True):
            st.session_state.rules_df = edited_rules_df
            if st.session_state.documents:
                from src.intelligence import parse_rules, validate_documents, create_review_items
                rules = parse_rules(edited_rules_df)
                findings = validate_documents(st.session_state.documents, rules)
                st.session_state.findings = findings
                
                # Re-generate review items
                new_reviews = create_review_items(st.session_state.documents, st.session_state.fields, findings)
                st.session_state.reviews = new_reviews
                
                save_sqlite(
                    OUTPUT_DIR / "docuflow.db",
                    st.session_state.documents,
                    st.session_state.fields,
                    findings,
                    new_reviews,
                    st.session_state.trace,
                )
                
                st.success("Re-evaluated current documents successfully! Findings and review queue have been updated.")
            else:
                st.warning("No documents loaded in the workspace yet. Run the pipeline in the Workspace tab first.")


with tabs[8]:
    st.markdown("### Human review queue")

    if st.session_state.reviews:
        for i, review in enumerate(st.session_state.reviews):
            current_status = getattr(review, "status", "open")

            with st.expander(
                f"{getattr(review, 'filename', 'Document')} · {getattr(review, 'category', 'review')} · {current_status}",
                expanded=i < 3,
            ):
                st.markdown(
                    pill(getattr(review, "priority", "medium"), "pill-warn")
                    + pill(current_status, "pill-blue"),
                    unsafe_allow_html=True,
                )

                st.write(getattr(review, "reason", ""))

                comment_key = f"review_comment_{getattr(review, 'review_id', i)}"

                comment = st.text_input(
                    "Reviewer comment",
                    key=comment_key,
                    placeholder="Add reviewer note or assignment...",
                )

                # HITL Extracted Fields Editing
                doc_fields = [f for f in st.session_state.fields if f.doc_id == review.doc_id]
                if doc_fields:
                    st.markdown("##### Extracted Fields Correction (HITL)")
                    for f in doc_fields:
                        new_val = st.text_input(
                            f"Field: {f.field_name}",
                            value=f.value,
                            key=f"edit_field_{f.field_id}_{getattr(review, 'review_id', i)}"
                        )
                        if new_val != f.value:
                            f.value = new_val
                            f.confidence = 1.0  # Manually verified

                # Manual Field Addition
                with st.expander("Add manual structured field"):
                    new_field_name = st.text_input("Field Name", key=f"new_fieldname_{getattr(review, 'review_id', i)}")
                    new_field_val = st.text_input("Field Value", key=f"new_fieldval_{getattr(review, 'review_id', i)}")
                    if st.button("Add Field", key=f"add_field_btn_{getattr(review, 'review_id', i)}"):
                        if new_field_name and new_field_val:
                            from src.models import ExtractedField
                            st.session_state.fields.append(ExtractedField(
                                doc_id=review.doc_id,
                                filename=review.filename,
                                document_type="unknown",
                                field_name=new_field_name,
                                value=new_field_val,
                                confidence=1.0,
                                evidence="Manually added by reviewer"
                            ))
                            st.success(f"Added field '{new_field_name}'!")
                            st.rerun()

                st.markdown("##### Dispatch Workflow Action")
                disp_conn = st.selectbox(
                    "Select target connector",
                    ["Slack", "GitHub", "Jira"],
                    key=f"disp_conn_select_{getattr(review, 'review_id', i)}"
                )

                if disp_conn == "Slack":
                    alert_msg = st.text_area(
                        "Alert Message",
                        value=f"Review alert for {review.filename}: {review.reason}",
                        key=f"slack_msg_{getattr(review, 'review_id', i)}"
                    )
                elif disp_conn == "GitHub":
                    issue_title = st.text_input(
                        "Issue Title",
                        value=f"DocuFlow: Review needed for {review.filename}",
                        key=f"github_title_{getattr(review, 'review_id', i)}"
                    )
                    issue_body = st.text_area(
                        "Issue Description",
                        value=f"Document: {review.filename}\nCategory: {review.category}\nReason: {review.reason}\nPriority: {review.priority}\nReviewer comment: {comment}",
                        key=f"github_body_{getattr(review, 'review_id', i)}"
                    )
                elif disp_conn == "Jira":
                    jira_title = st.text_input(
                        "Jira Ticket Title",
                        value=f"DocuFlow AI Ticket: {review.filename}",
                        key=f"jira_title_{getattr(review, 'review_id', i)}"
                    )

                b1, b2, b3, b4 = st.columns(4)

                with b1:
                    if st.button(
                        "Approve",
                        key=f"approve_{getattr(review, 'review_id', i)}",
                        use_container_width=True,
                    ):
                        review.status = "approved"
                        st.session_state.review_comments[getattr(review, "review_id", str(i))] = comment
                        st.success("Marked approved.")

                with b2:
                    if st.button(
                        "Reject",
                        key=f"reject_{getattr(review, 'review_id', i)}",
                        use_container_width=True,
                    ):
                        review.status = "rejected"
                        st.session_state.review_comments[getattr(review, "review_id", str(i))] = comment
                        st.warning("Marked rejected.")

                with b3:
                    if st.button(
                        "Mark fixed",
                        key=f"fixed_{getattr(review, 'review_id', i)}",
                        use_container_width=True,
                    ):
                        review.status = "fixed"
                        st.session_state.review_comments[getattr(review, "review_id", str(i))] = comment
                        st.success("Marked fixed.")

                with b4:
                    if st.button(
                        "Execute Action (Live Dispatch)",
                        key=f"export_task_{getattr(review, 'review_id', i)}",
                        use_container_width=True,
                    ):
                        from src.workspace_connectors import dispatch_connector_action, get_connector, connector_audit_event

                        conn_id = disp_conn.lower()
                        connector = get_connector(conn_id)

                        if conn_id == "slack":
                            payload = {
                                "connector_id": "slack",
                                "connector_name": "Slack",
                                "message": alert_msg,
                                "context": {
                                    "review_id": review.review_id,
                                    "filename": review.filename,
                                    "reason": review.reason,
                                    "priority": review.priority
                                }
                            }
                        elif conn_id == "github":
                            payload = {
                                "connector_id": "github",
                                "connector_name": "GitHub",
                                "title": issue_title,
                                "body": issue_body,
                                "context": {
                                    "review_id": review.review_id,
                                    "filename": review.filename,
                                    "reason": review.reason,
                                    "priority": review.priority
                                }
                            }
                        else:
                            payload = {
                                "connector_id": "jira",
                                "connector_name": "Jira",
                                "title": jira_title,
                                "context": {
                                    "review_id": review.review_id,
                                    "filename": review.filename,
                                    "reason": review.reason,
                                    "priority": review.priority
                                }
                            }

                        res = dispatch_connector_action(conn_id, f"{conn_id}.create_task", payload)

                        st.session_state.connector_audit.append(
                            connector_audit_event(
                                connector=connector or get_connector("jira"),
                                action="live_dispatch",
                                status="success" if res.get("ok") else "failed",
                                details=res
                            )
                        )

                        if res.get("ok"):
                            st.success(res.get("message"))
                            if not res.get("simulated") and conn_id == "github" and "issue_url" in res:
                                st.markdown(f"[View GitHub Issue]({res['issue_url']})")
                        else:
                            st.warning(res.get("message"))
        rdf = df_from_models(st.session_state.reviews)

        st.markdown("### Review queue table")

        st.dataframe(
            rdf,
            use_container_width=True,
            height=300,
        )
    else:
        st.success("No open review items.")


with tabs[9]:
    st.markdown("### Document Comparison Lab")
    
    if st.session_state.documents:
        filenames = [d.filename for d in st.session_state.documents]
        
        c1, c2 = st.columns(2)
        with c1:
            doc_a_name = st.selectbox("Select Document A", filenames, key="comp_doc_a")
        with c2:
            doc_b_name = st.selectbox("Select Document B", filenames, index=min(1, len(filenames)-1), key="comp_doc_b")
            
        if doc_a_name == doc_b_name:
            st.warning("Please select two different documents to compare.")
        else:
            doc_a = next(d for d in st.session_state.documents if d.filename == doc_a_name)
            doc_b = next(d for d in st.session_state.documents if d.filename == doc_b_name)
            
            if st.button("Compare Documents", key="run_comparison_btn"):
                from src.comparison import compare_documents
                comp = compare_documents(doc_a, doc_b)
                
                st.markdown(f"#### Comparison: {doc_a_name} vs {doc_b_name}")
                st.markdown(f"**Similarity score:** `{comp['similarity']:.2%}`")
                
                for note in comp.get("risk_notes", []):
                    if "mismatch" in note.lower() or "not found" in note.lower():
                        st.error(note)
                    else:
                        st.info(note)
                        
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f"**Unique to {doc_a_name}**")
                    st.write(", ".join(comp.get("unique_to_a", [])) or "None")
                with col2:
                    st.markdown("**Shared keywords**")
                    st.write(", ".join(comp.get("shared_terms", [])) or "None")
                with col3:
                    st.markdown(f"**Unique to {doc_b_name}**")
                    st.write(", ".join(comp.get("unique_to_b", [])) or "None")
                    
                router = ProviderRouter()
                if router.gemini_key or router.anthropic_key:
                    st.markdown("##### Premium AI Semantic Comparison Report")
                    with st.spinner("Generating AI report..."):
                        comp_prompt = f"""You are an expert contract and legal document analyst.
Compare the two documents below and provide a professional 1-paragraph summary highlighting key differences, potential legal/compliance risks, and payment term mismatches.

Document A ({doc_a.filename} - {doc_a.document_type}):
{doc_a.text[:6000]}

Document B ({doc_b.filename} - {doc_b.document_type}):
{doc_b.text[:6000]}

Summary Comparison Report:"""
                        res = router.generate(comp_prompt, temperature=0.2)
                        st.write(res.text)
    else:
        st.info("Please load and process documents in the Workspace tab first.")

with tabs[10]:
    st.markdown("### Workspace Quality & Evaluation Lab")
    
    if st.session_state.documents:
        from src.evaluation import run_document_eval
        
        eval_results = run_document_eval(
            st.session_state.documents,
            st.session_state.fields,
            st.session_state.findings,
            st.session_state.chunks,
            st.session_state.qa_history
        )
        
        passed = sum(1 for e in eval_results if e["status"] == "pass")
        total_checks = len(eval_results)
        success_rate = (passed / total_checks) if total_checks else 0.0
        
        sc1, sc2 = st.columns(2)
        with sc1:
            metric_card("Observability Score", f"{success_rate:.1%}", "Passed workspace checks")
        with sc2:
            st.info("This evaluation scorecard runs compliance and data quality sanity checks across the current pipeline results (checking table parsing, total extraction, and rule validation integrity).")
            
        st.markdown("#### Detailed Diagnostic Checklist")
        eval_df = pd.DataFrame(eval_results)
        st.dataframe(
            eval_df,
            use_container_width=True
        )
    else:
        st.info("No evaluation data. Run the document pipeline in the Workspace tab first.")

with tabs[11]:
    st.markdown("### Connector Marketplace")

    st.markdown(
        """
        <div class='panel'>
            Connect workspace sources and business systems to turn DocuFlow AI into a full document automation platform.
            Public mode is safe: connectors generate setup snippets, readiness checks, and action payloads without storing secrets.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### Connector readiness")

    status_table = connector_status_table()

    st.dataframe(
        status_table,
        use_container_width=True,
        height=260,
    )

    st.markdown("### Browse connectors")

    for category in connector_categories():
        st.markdown(f"#### {category}")

        category_connectors = connectors_by_category(category)

        for start in range(0, len(category_connectors), 2):
            cols = st.columns(2)

            for col, connector in zip(cols, category_connectors[start:start + 2]):
                with col:
                    connector_card(connector.connector_id)

        st.divider()

    st.markdown("### Configure selected connector")

    selected_options = [
        f"{c.name} · {c.connector_id}"
        for c in connector_catalog()
    ]

    default_index = 0

    for i, option in enumerate(selected_options):
        if option.endswith(st.session_state.selected_connector_id):
            default_index = i
            break

    selected = st.selectbox(
        "Connector",
        selected_options,
        index=default_index,
        key="connector_config_select",
    )

    selected_id = selected.split(" · ")[-1]
    selected_connector = get_connector(selected_id)

    if selected_connector is not None:
        st.session_state.selected_connector_id = selected_connector.connector_id

        c1, c2 = st.columns([1, 1])

        with c1:
            st.markdown("#### Setup instructions")

            for step in selected_connector.setup_steps:
                st.markdown(f"- {step}")

            st.markdown("#### Required environment variables")

            if selected_connector.env_vars:
                for env_var in selected_connector.env_vars:
                    configured = bool(os.getenv(env_var, "").strip())

                    st.markdown(
                        pill(env_var, "pill-ok" if configured else "pill-warn")
                        + (" configured" if configured else " missing"),
                        unsafe_allow_html=True,
                    )
            else:
                st.success("No environment variables required.")

        with c2:
            st.markdown("#### Generate `.env` snippet")

            env_snippet = generate_env_snippet(selected_connector)

            st.code(
                env_snippet,
                language="env",
            )

            st.download_button(
                "Download .env snippet",
                data=env_snippet,
                file_name=f"{selected_connector.connector_id}_env_snippet.env",
                mime="text/plain",
                use_container_width=True,
            )

            if st.button(
                "Test selected connector",
                key="test_selected_connector",
                use_container_width=True,
            ):
                test_result = test_connector(selected_connector)

                st.session_state.connector_audit.append(
                    connector_audit_event(
                        connector=selected_connector,
                        action="test_selected_connector",
                        status=test_result["status"],
                        details=test_result,
                    )
                )

                if test_result["ok"]:
                    st.success(test_result["message"])
                else:
                    st.warning(test_result["message"])

        st.markdown("#### Sample connector action payload")

        payload = sample_action_payload(
            selected_connector,
            context={
                "document_count": len(st.session_state.documents),
                "field_count": len(st.session_state.fields),
                "finding_count": len(st.session_state.findings),
                "review_count": len(st.session_state.reviews),
            },
        )

        st.code(
            json.dumps(payload, indent=2, default=str),
            language="json",
        )

    st.markdown("### Add custom connector")

    with st.expander("Create custom connector definition"):
        cc1, cc2 = st.columns(2)

        with cc1:
            custom_name = st.text_input(
                "Connector name",
                placeholder="Example: Internal SharePoint",
            )

            custom_category = st.selectbox(
                "Category",
                [
                    "Document Sources",
                    "Workflow Actions",
                    "Business Systems",
                    "Databases",
                    "Automation",
                    "Custom",
                ],
            )

            custom_env = st.text_input(
                "Required env vars",
                placeholder="SHAREPOINT_CLIENT_ID;SHAREPOINT_SECRET",
            )

        with cc2:
            custom_description = st.text_area(
                "Description",
                placeholder="What does this connector do?",
                height=100,
            )

            custom_actions = st.text_input(
                "Actions",
                placeholder="import_folder;send_report;create_task",
            )

        if st.button(
            "Add custom connector to session",
            use_container_width=True,
        ):
            row = {
                "name": custom_name,
                "category": custom_category,
                "description": custom_description,
                "env_vars": custom_env,
                "actions": custom_actions,
                "status": "session_only",
            }

            st.session_state.custom_connector_rows.append(row)

            st.success("Custom connector added for this session.")

    if st.session_state.custom_connector_rows:
        st.markdown("### Custom connectors added this session")

        st.dataframe(
            pd.DataFrame(st.session_state.custom_connector_rows),
            use_container_width=True,
            height=220,
        )

    st.markdown("### Connector audit log")

    if st.session_state.connector_audit:
        st.dataframe(
            pd.DataFrame(st.session_state.connector_audit),
            use_container_width=True,
            height=260,
        )
    else:
        st.info("No connector activity yet.")

    manifest = connector_manifest()

    manifest["custom_connectors"] = st.session_state.custom_connector_rows

    st.download_button(
        "Download full connector manifest JSON",
        data=json.dumps(manifest, indent=2, default=str),
        file_name="docuflow_connector_manifest.json",
        mime="application/json",
        use_container_width=True,
    )


with tabs[12]:
    st.markdown("### Workflow Builder")

    st.markdown(
        """
        <div class='panel'>
            Build document automation flows such as:
            Google Drive → DocuFlow pipeline → validation → Slack/Jira review queue → database/export archive.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### Intake workflow")

    source_connectors = [
        c.name
        for c in connector_catalog()
        if c.category in {"Document Sources"}
    ]

    if not source_connectors:
        source_connectors = ["Manual upload"]

    i1, i2, i3 = st.columns(3)

    with i1:
        intake_source = st.selectbox(
            "Document source",
            source_connectors,
            key="intake_source",
        )

    with i2:
        intake_schedule = st.selectbox(
            "Schedule",
            [
                "manual",
                "hourly",
                "daily",
                "weekly",
                "on_new_file",
            ],
            key="intake_schedule",
        )

    with i3:
        intake_doc_types = st.multiselect(
            "Document types",
            [
                "PDF",
                "DOCX",
                "TXT",
                "CSV",
                "Excel",
                "ZIP",
            ],
            default=["PDF", "DOCX", "Excel"],
            key="intake_doc_types",
        )

    if st.button(
        "Build intake workflow",
        use_container_width=True,
    ):
        workflow = build_intake_workflow(
            source_connector=intake_source,
            schedule=intake_schedule,
            document_types=intake_doc_types,
        )

        st.session_state.intake_workflows.append(workflow)

        st.success("Intake workflow added.")

    st.markdown("### Export workflow")

    destination_connectors = [
        c.name
        for c in connector_catalog()
        if c.category in {
            "Workflow Actions",
            "Business Systems",
            "Databases",
            "Automation",
            "Document Sources",
        }
    ]

    e1, e2, e3 = st.columns(3)

    with e1:
        export_destination = st.selectbox(
            "Destination",
            destination_connectors,
            key="export_destination",
        )

    with e2:
        export_trigger = st.selectbox(
            "Trigger",
            [
                "after_pipeline_completed",
                "when_validation_fails",
                "when_review_queue_created",
                "manual_approval",
                "scheduled_summary",
            ],
            key="export_trigger",
        )

    with e3:
        include_payloads = st.multiselect(
            "Include payloads",
            [
                "documents",
                "extracted_fields",
                "validation_findings",
                "review_queue",
                "qa_history",
                "audit_trace",
                "export_zip",
            ],
            default=[
                "validation_findings",
                "review_queue",
                "audit_trace",
            ],
            key="include_payloads",
        )

    if st.button(
        "Build export workflow",
        use_container_width=True,
    ):
        workflow = build_export_workflow(
            destination_connector=export_destination,
            trigger=export_trigger,
            include_payloads=include_payloads,
        )

        st.session_state.export_workflows.append(workflow)

        st.success("Export workflow added.")

    st.markdown("### Saved intake workflows")

    if st.session_state.intake_workflows:
        st.dataframe(
            pd.DataFrame(st.session_state.intake_workflows),
            use_container_width=True,
            height=260,
        )
    else:
        st.info("No intake workflows created yet.")

    st.markdown("### Saved export workflows")

    if st.session_state.export_workflows:
        st.dataframe(
            pd.DataFrame(st.session_state.export_workflows),
            use_container_width=True,
            height=260,
        )
    else:
        st.info("No export workflows created yet.")

    workflow_payload = {
        "intake_workflows": st.session_state.intake_workflows,
        "export_workflows": st.session_state.export_workflows,
    }

    st.download_button(
        "Download workflow JSON",
        data=json.dumps(workflow_payload, indent=2, default=str),
        file_name="docuflow_workflows.json",
        mime="application/json",
        use_container_width=True,
    )

    st.markdown("### Recommended automation blueprint")

    st.code(
        """
Document source connector
  → fetch new document packets
  → run DocuFlow LangGraph pipeline
  → classify + extract + validate
  → route failed/uncertain items to review queue
  → notify Slack/Jira/CRM
  → export structured records to DB/warehouse
  → archive audit pack to storage
        """.strip(),
        language="text",
    )


with tabs[13]:
    st.markdown("### Export Center")

    if st.session_state.documents:
        report = markdown_report(
            st.session_state.documents,
            st.session_state.fields,
            st.session_state.findings,
            st.session_state.reviews,
            st.session_state.trace,
        )

        zip_path = export_zip(
            OUTPUT_DIR / "docuflow_export_pack.zip",
            st.session_state.documents,
            st.session_state.chunks,
            st.session_state.fields,
            st.session_state.findings,
            st.session_state.reviews,
            st.session_state.trace,
            st.session_state.qa_history,
        )

        export_context = {
            "connector_manifest": connector_manifest(),
            "custom_connectors": st.session_state.custom_connector_rows,
            "connector_audit": st.session_state.connector_audit,
            "intake_workflows": st.session_state.intake_workflows,
            "export_workflows": st.session_state.export_workflows,
            "review_comments": st.session_state.review_comments,
        }

        e1, e2, e3, e4 = st.columns(4)

        with e1:
            st.download_button(
                "Documents CSV",
                data=df_from_models(st.session_state.documents).to_csv(index=False),
                file_name="documents.csv",
                mime="text/csv",
                use_container_width=True,
            )

        with e2:
            st.download_button(
                "Fields CSV",
                data=df_from_models(st.session_state.fields).to_csv(index=False),
                file_name="extracted_fields.csv",
                mime="text/csv",
                use_container_width=True,
            )

        with e3:
            st.download_button(
                "Report MD",
                data=report,
                file_name="document_report.md",
                mime="text/markdown",
                use_container_width=True,
            )

        with e4:
            st.download_button(
                "Export ZIP",
                data=zip_path.read_bytes(),
                file_name="docuflow_export_pack.zip",
                mime="application/zip",
                use_container_width=True,
            )

        st.download_button(
            "Download connector/workflow context JSON",
            data=json.dumps(export_context, indent=2, default=str),
            file_name="docuflow_connector_workflow_context.json",
            mime="application/json",
            use_container_width=True,
        )

        st.markdown(report)
    else:
        st.info("Run a pipeline before exporting.")