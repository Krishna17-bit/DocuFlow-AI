# DocuFlow AI

**DocuFlow AI** is a multi-document intelligence and workflow automation platform for batch document parsing, classification, structured extraction, table handling, multi-document Q&A, rule validation, human review queues, connector workflows, and audit-ready exports.

It is designed for document-heavy operations such as vendor onboarding, contract review, invoice processing, compliance evidence review, RFP/SOW analysis, research review, financial document screening, and business workflow automation.

---

## What it does

DocuFlow AI turns messy document packets into structured, searchable, reviewable intelligence.

```text
Upload documents
→ classify document types
→ extract text and tables
→ create searchable chunks
→ extract structured fields
→ validate against rules/checklists
→ answer questions with citations
→ create human review queue
→ export reports and audit packs
```

---

## Key features

- Batch PDF upload
- DOCX, TXT, Markdown, CSV, Excel, and ZIP support
- Sample document pack
- Document type classification
- Contract, invoice, policy, RFP, SOW, proposal, resume, financial report, research paper, and unknown document labels
- Structured field extraction
- Table file handling and CSV export
- Multi-document search and Q&A with citations
- Rule/checklist validation
- Human review queue
- LangGraph workflow trace
- Optional AI provider support
- Local heuristic mode without API keys
- Connector registry for workspace integration planning
- Export ZIP with CSV, JSON, Markdown, audit trace, and report files
- Local SQLite database export

---

## LangGraph workflow

The document pipeline uses a real LangGraph workflow:

```text
ingest_documents
→ classify_documents
→ extract_tables
→ build_chunks
→ structured_extraction
→ rule_validation
→ human_review
→ export_packaging
```

---

## Run locally

### Windows

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
streamlit run app.py
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```

---

## Optional AI setup

The app works without an API key using local heuristics.

For richer Q&A synthesis, configure an optional provider in `.env`:

```env
GEMINI_API_KEY=
GEMINI_MODEL=gemini-flash-latest

ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-4-6

DEFAULT_PROVIDER=auto
```

---

## Quick test

1. Run the app.
2. Open **Workspace**.
3. Select **Use sample document pack**.
4. Click **Run document pipeline**.
5. Open **Dashboard** to inspect document types.
6. Open **Extraction** to see structured fields.
7. Open **Document Q&A** and ask a question.
8. Open **Validation** to review checklist results.
9. Open **Review Queue** to inspect human-review items.
10. Open **Export** to download the report pack.

---

## Connector roadmap

DocuFlow AI includes connector planning for Google Drive, Dropbox, OneDrive, Gmail attachments, Slack, Notion, Airtable, HubSpot, Salesforce, Jira, GitHub, PostgreSQL, Snowflake, S3, n8n, Zapier, and Make.

---

## Tech stack

- Python
- Streamlit
- LangGraph
- LangChain Core
- Pydantic
- Pandas
- Plotly
- pypdf
- python-docx
- OpenPyXL
- SQLite
- optional AI provider APIs

---

## Roadmap

- OCR for scanned PDFs/images
- PDF table extraction with Docling/Camelot/Tabula
- vector database indexing
- document packet splitting
- contract redline/risk comparison
- invoice vs PO matching
- resume vs JD matching
- compliance evidence mapping
- workflow approval buttons
- real Google Drive/Gmail/S3 ingestion
- Slack/Jira/CRM export
- PostgreSQL backend
- FastAPI service layer
- user authentication
- role-based review queues
- more advanced evaluation suite

---

## Disclaimer

DocuFlow AI is a document intelligence and workflow automation tool. Extracted data, legal clauses, financial fields, and compliance findings should be reviewed against the original source documents before decisions are made.
