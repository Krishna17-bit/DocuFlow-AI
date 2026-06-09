from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from src.doc_graph import run_docflow_graph
from src.intelligence import answer_question
from src.loaders import parse_bytes, load_sample_documents, load_rules, load_connectors
from src.provider_router import ProviderRouter
from src.reporting import df_from_models, save_sqlite, export_zip, markdown_report
from src.ui_styles import APP_CSS

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
}

for key, default in SESSION_DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default


with st.sidebar:
    st.markdown("### DocuFlow AI")
    st.caption(
        "Batch document intelligence, extraction, validation, Q&A, review workflows, and exports."
    )

    st.divider()

    st.markdown("**AI status**")
    st.info(router.status)

    provider_choice = st.selectbox(
        "AI route",
        ["auto", "gemini", "anthropic", "local"],
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
        "- classify documents\n"
        "- extract tables\n"
        "- build chunks\n"
        "- structured extraction\n"
        "- rule validation\n"
        "- review queue\n"
        "- export packaging"
    )


st.markdown(
    """
    <div class='hero'>
      <div class='hero-title'>DocuFlow AI</div>
      <div class='hero-subtitle'>
        Multi-document intelligence platform for batch PDF/DOCX/TXT/CSV/Excel parsing, document classification,
        structured field extraction, table handling, multi-document Q&A with citations, rule validation,
        human review queues, connector workflows, and export-ready audit packs.
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)


m1, m2, m3, m4 = st.columns(4)

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
        "Connectors",
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
        else:
            rules_df = load_rules(BASE_DIR)

        result = run_docflow_graph(
            documents,
            rules_df,
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
    st.markdown("### Rule validation")

    if st.session_state.findings:
        fdf = df_from_models(st.session_state.findings)

        st.dataframe(
            fdf,
            use_container_width=True,
            height=460,
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


with tabs[8]:
    st.markdown("### Human review queue")

    if st.session_state.reviews:
        rdf = df_from_models(st.session_state.reviews)

        st.dataframe(
            rdf,
            use_container_width=True,
            height=460,
        )
    else:
        st.success("No open review items.")


with tabs[9]:
    st.markdown("### Workspace connectors")

    connectors = load_connectors(BASE_DIR)

    if "env_vars" in connectors.columns:
        connectors["env_configured"] = connectors["env_vars"].apply(
            lambda s: all(
                os.getenv(x.strip(), "").strip()
                for x in str(s).split(";")
                if x.strip()
            )
            if str(s).strip()
            else False
        )
    else:
        connectors["env_configured"] = False

    st.dataframe(
        connectors,
        use_container_width=True,
        height=440,
    )

    manifest = {
        "name": "docuflow-connectors",
        "description": "Connector manifest for document intake, workflow routing, notifications, storage, and downstream automation.",
        "connectors": connectors.to_dict(orient="records"),
    }

    st.download_button(
        "Download connector manifest JSON",
        data=json.dumps(manifest, indent=2, default=str),
        file_name="docuflow_connector_manifest.json",
        mime="application/json",
        use_container_width=True,
    )

    st.markdown("### Future connector workflow")

    st.code(
        "Drive/Gmail/S3 intake → DocuFlow pipeline → validation/review → Slack/Jira/CRM/DB export → audit archive",
        language="text",
    )


with tabs[10]:
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

        st.markdown(report)
    else:
        st.info("Run a pipeline before exporting.")